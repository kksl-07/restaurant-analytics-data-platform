from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import math
import os
import random
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyarrow as pa
import pyarrow.parquet as pq

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = PROJECT_ROOT / "data" / "raw" / "ecb_fx_rates.parquet"
DEFAULT_START_DATE = date(2024, 1, 1)
DEFAULT_OVERLAP_DAYS = 7
ECB_ENDPOINT = "https://data-api.ecb.europa.eu/service/data/EXR/D.GBP.EUR.SP00.A"
SERIES_KEY = "EXR.D.GBP.EUR.SP00.A"
API_SERIES_KEY = "D.GBP.EUR.SP00.A"
BASE_CURRENCY = "EUR"
QUOTE_CURRENCY = "GBP"
SOURCE = "ECB"
RATE_QUANTUM = Decimal("0.0000000001")
MAX_RETRY_DELAY_SECONDS = 60.0
EXPECTED_DIMENSIONS = {
    "FREQ": "D",
    "EXR_TYPE": "SP00",
    "EXR_SUFFIX": "A",
}

FX_SCHEMA = pa.schema(
    [
        pa.field("rate_date", pa.date32(), nullable=False),
        pa.field("base_currency", pa.string(), nullable=False),
        pa.field("quote_currency", pa.string(), nullable=False),
        pa.field("quote_per_eur", pa.decimal128(20, 10), nullable=False),
        pa.field("source", pa.string(), nullable=False),
        pa.field("series_key", pa.string(), nullable=False),
    ]
)


class IngestionError(Exception):
    """Base exception for ECB FX ingestion failures."""


class HttpRequestError(IngestionError):
    """Raised when a request cannot retrieve an ECB response."""


class ResponseValidationError(IngestionError):
    """Raised when an ECB response violates its expected contract."""


class DataContractError(IngestionError):
    """Raised when Parquet data violates the local FX data contract."""


@dataclass(frozen=True)
class IngestionConfig:
    """Configure one ECB FX ingestion run and its retry behavior."""

    destination: Path = DEFAULT_DESTINATION
    start_date: date | None = None
    end_date: date | None = None
    overlap_days: int = DEFAULT_OVERLAP_DAYS
    timeout_seconds: float = 20.0
    max_retries: int = 3


@dataclass(frozen=True)
class FxObservation:
    """Represent one validated ECB daily rate at the dataset business grain."""

    rate_date: date
    base_currency: str
    quote_currency: str
    quote_per_eur: Decimal
    source: str = SOURCE
    series_key: str = SERIES_KEY

    @property
    def key(self) -> tuple[date, str]:
        """Return the `(rate_date, quote_currency)` idempotent-upsert key."""
        return (self.rate_date, self.quote_currency)


def parse_iso_date(value: str) -> date:
    """Parse an ISO-8601 CLI date.

    Raises:
        argparse.ArgumentTypeError: If ``value`` is not a calendar date.
    """
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"Invalid ISO date: {value}") from error


def utc_today() -> date:
    """Return the current UTC calendar date for the default request boundary."""
    return datetime.now(UTC).date()


def validate_date_range(start_date: date, end_date: date) -> None:
    """Ensure an inclusive ECB request interval is chronologically valid.

    Raises:
        IngestionError: If ``start_date`` is after ``end_date``.
    """
    if start_date > end_date:
        raise IngestionError("start date must not be after end date")


def request_url(start_date: date, end_date: date) -> str:
    """Build the official ECB CSVdata URL for an inclusive date window."""
    parameters = urlencode(
        {
            "startPeriod": start_date.isoformat(),
            "endPeriod": end_date.isoformat(),
            "format": "csvdata",
        }
    )
    return f"{ECB_ENDPOINT}?{parameters}"


def bounded_retry_delay(delay: float) -> float | None:
    """Validate and cap a server-provided retry delay.

    Non-finite and negative values are rejected so malformed headers fall back
    to bounded exponential backoff. Valid delays are capped to avoid allowing
    an upstream response to stall a local ingestion process indefinitely.
    """
    if not math.isfinite(delay) or delay < 0:
        return None
    return min(delay, MAX_RETRY_DELAY_SECONDS)


def retry_after_seconds(
    headers: object, *, now: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> float | None:
    """Read a non-negative ``Retry-After`` delay, if supplied by ECB.

    Both delta-seconds and HTTP-date values are supported. Invalid or unsupported
    values return ``None`` so normal exponential backoff applies instead.

    Args:
        headers: HTTP response headers that may contain ``Retry-After``.
        now: Injectable UTC clock used when converting an HTTP-date to seconds.
    """
    value = getattr(headers, "get", lambda _: None)("Retry-After")
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return bounded_retry_delay((retry_at - now()).total_seconds())
    return bounded_retry_delay(seconds)


def recognized_no_data_problem(headers: object, content: str) -> bool:
    """Return whether a 404 body is the ECB no-results problem document.

    ECB documents 404 as ``No results found``. External ECB integrations also
    report a ``Not Found`` title with a ``No Series was returned for the query``
    detail. The content type, JSON object, status, title, and detail must all
    match this narrow contract; arbitrary JSON 404 error messages are never
    converted into successful empty windows.
    """
    content_type = getattr(headers, "get", lambda _: None)("Content-Type")
    if not isinstance(content_type, str):
        return False
    if (
        content_type.split(";", maxsplit=1)[0].strip().lower()
        != "application/problem+json"
    ):
        return False
    try:
        problem = json.loads(content)
    except json.JSONDecodeError:
        return False
    if not isinstance(problem, dict) or problem.get("status") != 404:
        return False
    title = problem.get("title")
    detail = problem.get("detail")
    normalized_title = title.casefold() if isinstance(title, str) else ""
    normalized_detail = (
        " ".join(detail.casefold().split()) if isinstance(detail, str) else ""
    )
    return (
        normalized_title in {"no results found", "not found"}
        and normalized_detail.rstrip(".") == "no series was returned for the query"
    )


def empty_csvdata_response(content: str) -> bool:
    """Return whether a 404 body is a structurally valid ECB CSVdata empty set.

    A 404 is accepted as a no-observation result only with the requested CSV
    schema and no records. Error pages and malformed bodies remain failures.
    """
    reader = csv.DictReader(io.StringIO(content))
    required_fields = {
        "KEY",
        "CURRENCY",
        "CURRENCY_DENOM",
        "TIME_PERIOD",
        "OBS_VALUE",
    }
    return required_fields.issubset(reader.fieldnames or []) and not list(reader)


def csv_empty_response() -> str:
    """Create the minimal valid CSVdata body used for recognized JSON no-results."""
    return "KEY,CURRENCY,CURRENCY_DENOM,TIME_PERIOD,OBS_VALUE\n"


def fetch_csv(
    start_date: date,
    end_date: date,
    *,
    timeout_seconds: float,
    max_retries: int,
    opener: Callable[..., object] = urlopen,
    sleeper: Callable[[float], None] = time.sleep,
    jitter: Callable[[float, float], float] = random.uniform,
) -> str:
    """Retrieve CSVdata for one date window with bounded transient retries.

    Args:
        start_date: Inclusive ECB observation-date lower bound.
        end_date: Inclusive ECB observation-date upper bound.
        timeout_seconds: Per-request I/O timeout.
        max_retries: Number of retries after the first request attempt.
        opener: Injectable HTTP opener used by offline tests.
        sleeper: Injectable delay function used by retry handling.
        jitter: Injectable jitter generator added to exponential backoff.

    Returns:
        The UTF-8 ECB CSV response body.

    Raises:
        IngestionError: If ``max_retries`` is negative.
        HttpRequestError: If a non-retryable HTTP error occurs or all retryable
            connection, 429, or 5xx failures are exhausted.
    """
    if max_retries < 0:
        raise IngestionError("max retries must be zero or greater")

    url = request_url(start_date, end_date)
    request = Request(
        url,
        headers={"Accept": "text/csv", "User-Agent": "restaurant-analytics-fx/1.0"},
    )
    attempts = max_retries + 1
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with opener(request, timeout=timeout_seconds) as response:
                status = getattr(response, "status", response.getcode())
                if 200 <= status < 300:
                    response_bytes = response.read()
                    # ECB can return a zero-byte 200 for a valid non-publication window.
                    if not response_bytes:
                        LOGGER.info("ECB returned a zero-byte successful result window")
                        return csv_empty_response()
                    return response_bytes.decode("utf-8")
                raise HTTPError(
                    url, status, "Unexpected HTTP response", response.headers, None
                )
        except HTTPError as error:
            if error.code == 404:
                body = error.read().decode("utf-8", errors="replace")
                if empty_csvdata_response(body) or recognized_no_data_problem(
                    error.headers, body
                ):
                    LOGGER.info("ECB returned a recognized empty result window")
                    return csv_empty_response()
            last_error = error
            retryable = error.code == 429 or 500 <= error.code <= 599
            retry_after = retry_after_seconds(error.headers)
            message = f"ECB request failed with HTTP {error.code}"
        except (URLError, TimeoutError, OSError) as error:
            last_error = error
            retryable = True
            retry_after = None
            message = f"ECB request failed: {error}"

        if not retryable or attempt == attempts:
            raise HttpRequestError(message) from last_error

        delay = (
            retry_after
            if retry_after is not None
            else (2 ** (attempt - 1)) + jitter(0, 1)
        )
        LOGGER.warning(
            "%s; retrying attempt %s of %s in %.2f seconds",
            message,
            attempt + 1,
            attempts,
            delay,
        )
        sleeper(delay)

    raise AssertionError("unreachable")


def parse_decimal(value: str) -> Decimal:
    """Parse one ECB rate exactly as the target ``DECIMAL(20,10)`` value.

    Rates never pass through binary floating point. Values must be finite,
    strictly positive, and exactly quantizable to ten decimal places.

    Raises:
        ResponseValidationError: If the rate is invalid or cannot be represented
            by the Parquet decimal contract.
    """
    try:
        rate = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ResponseValidationError(
            f"Invalid ECB exchange rate: {value!r}"
        ) from error
    if not rate.is_finite() or rate <= 0:
        raise ResponseValidationError("ECB exchange rate must be finite and positive")
    try:
        quantized = rate.quantize(RATE_QUANTUM)
    except InvalidOperation as error:
        raise ResponseValidationError(
            "ECB exchange rate exceeds DECIMAL(20,10)"
        ) from error
    if quantized != rate or len(quantized.as_tuple().digits) > 20:
        raise ResponseValidationError(
            "ECB exchange rate is not representable as DECIMAL(20,10)"
        )
    return quantized


def parse_ecb_csv(
    content: str,
    start_date: date,
    end_date: date,
) -> list[FxObservation]:
    """Parse and validate CSVdata for the configured GBP-per-EUR ECB series.

    Required ECB fields are addressed by name, not position. Empty CSV files
    with headers are valid here because their business meaning depends on the
    ingestion mode and existing dataset, which ``ingest`` evaluates. Optional
    SDMX dimensions must match the configured daily spot-rate series when sent.

    Raises:
        ResponseValidationError: If the CSV is malformed, incomplete, outside
            the requested date window, or identifies another ECB series/pair.
        DataContractError: If the batch contains duplicate business keys.
    """
    if not content.strip():
        raise ResponseValidationError("ECB returned an empty response body")
    reader = csv.DictReader(io.StringIO(content))
    required_fields = {"KEY", "CURRENCY", "CURRENCY_DENOM", "TIME_PERIOD", "OBS_VALUE"}
    fieldnames = set(reader.fieldnames or [])
    missing_fields = required_fields - fieldnames
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ResponseValidationError(f"ECB CSV missing required fields: {missing}")

    observations: list[FxObservation] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise ResponseValidationError(f"Malformed ECB CSV row {line_number}")
        if any(row.get(field) in (None, "") for field in required_fields):
            raise ResponseValidationError(f"Incomplete ECB CSV row {line_number}")
        if row["KEY"] != SERIES_KEY:
            raise ResponseValidationError(
                f"Unexpected ECB series key on row {line_number}"
            )
        if row["CURRENCY"] != QUOTE_CURRENCY or row["CURRENCY_DENOM"] != BASE_CURRENCY:
            raise ResponseValidationError(
                f"Unexpected ECB currency pair on row {line_number}"
            )
        for field, expected_value in EXPECTED_DIMENSIONS.items():
            if field in fieldnames and row.get(field) != expected_value:
                raise ResponseValidationError(
                    f"Unexpected ECB {field} value on row {line_number}"
                )
        try:
            rate_date = date.fromisoformat(row["TIME_PERIOD"])
        except ValueError as error:
            raise ResponseValidationError(
                f"Invalid ECB observation date on row {line_number}"
            ) from error
        if not start_date <= rate_date <= end_date:
            raise ResponseValidationError(
                f"ECB date outside requested range on row {line_number}"
            )
        observations.append(
            FxObservation(
                rate_date=rate_date,
                base_currency=BASE_CURRENCY,
                quote_currency=QUOTE_CURRENCY,
                quote_per_eur=parse_decimal(row["OBS_VALUE"]),
            )
        )
    validate_observations(observations, start_date=start_date, end_date=end_date)
    return observations


def validate_observations(
    observations: Iterable[FxObservation],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[FxObservation]:
    """Validate FX records against the local data contract and business key.

    Optional bounds constrain incoming ECB observations to their requested
    window. Decimal values must retain the exact scale accepted by
    ``DECIMAL(20,10)``; duplicate ``(rate_date, quote_currency)`` keys fail.

    Raises:
        DataContractError: If fields, currencies, source identity, decimal
            precision, bounds, or keys violate the contract.
    """
    validated = list(observations)
    seen_keys: set[tuple[date, str]] = set()
    for observation in validated:
        if not isinstance(observation.rate_date, date):
            raise DataContractError("rate_date must be a date")
        if observation.base_currency != BASE_CURRENCY:
            raise DataContractError("base_currency must be EUR")
        if observation.quote_currency != QUOTE_CURRENCY:
            raise DataContractError("quote_currency must be GBP")
        if observation.source != SOURCE or observation.series_key != SERIES_KEY:
            raise DataContractError("unexpected FX source or series key")
        if not isinstance(observation.quote_per_eur, Decimal):
            raise DataContractError("quote_per_eur must be Decimal")
        try:
            normalized_rate = parse_decimal(str(observation.quote_per_eur))
        except ResponseValidationError as error:
            raise DataContractError(str(error)) from error
        if normalized_rate != observation.quote_per_eur:
            raise DataContractError("quote_per_eur must have scale 10")
        if start_date is not None and observation.rate_date < start_date:
            raise DataContractError("rate_date is before requested range")
        if end_date is not None and observation.rate_date > end_date:
            raise DataContractError("rate_date is after requested range")
        if observation.key in seen_keys:
            raise DataContractError("duplicate FX business key")
        seen_keys.add(observation.key)
    return validated


def table_from_observations(observations: Iterable[FxObservation]) -> pa.Table:
    """Create a deterministically ordered Arrow table with the explicit schema."""
    rows = [
        {
            "rate_date": observation.rate_date,
            "base_currency": observation.base_currency,
            "quote_currency": observation.quote_currency,
            "quote_per_eur": observation.quote_per_eur,
            "source": observation.source,
            "series_key": observation.series_key,
        }
        for observation in sorted(observations, key=lambda item: item.key)
    ]
    return pa.Table.from_pylist(rows, schema=FX_SCHEMA)


def observations_from_table(table: pa.Table) -> list[FxObservation]:
    """Deserialize and validate a persisted table before it can be merged.

    Raises:
        DataContractError: If the schema or any persisted observation is invalid.
    """
    if not table.schema.equals(FX_SCHEMA, check_metadata=False):
        raise DataContractError(
            "Existing Parquet schema does not match the ECB FX contract"
        )
    observations = [FxObservation(**row) for row in table.to_pylist()]
    return validate_observations(observations)


def read_existing(destination: Path) -> list[FxObservation]:
    """Read the current Parquet snapshot, or return no records when absent.

    Existing data is fully validated before ingestion proceeds, preventing a
    corrupt snapshot from being silently merged or overwritten.

    Raises:
        DataContractError: If Parquet cannot be read or violates the contract.
    """
    if not destination.exists():
        return []
    try:
        return observations_from_table(pq.read_table(destination))
    except (OSError, pa.ArrowException) as error:
        raise DataContractError(
            f"Unable to read existing FX data: {destination}"
        ) from error


def merge_observations(
    existing: Iterable[FxObservation], incoming: Iterable[FxObservation]
) -> tuple[list[FxObservation], int]:
    """Idempotently merge validated observations with incoming ECB revisions.

    Incoming records replace matching business keys, allowing the configured
    overlap to repair revised rates while retaining unaffected history.

    Returns:
        The sorted merged records and the number of inserted or changed keys.

    Raises:
        DataContractError: If either input violates the contract.
    """
    existing_rows = validate_observations(existing)
    incoming_rows = validate_observations(incoming)
    merged = {observation.key: observation for observation in existing_rows}
    changed = 0
    for observation in incoming_rows:
        if merged.get(observation.key) != observation:
            changed += 1
        merged[observation.key] = observation
    result = sorted(merged.values(), key=lambda item: item.key)
    validate_observations(result)
    return result, changed


def tables_equal(left: pa.Table, right: pa.Table) -> bool:
    """Compare logical Arrow contents while ignoring non-contract metadata."""
    return left.equals(right, check_metadata=False)


def atomic_write(destination: Path, table: pa.Table) -> None:
    """Validate and atomically replace the Parquet snapshot.

    The temporary file is created beside ``destination`` so ``os.replace`` is
    atomic on the local filesystem. It is validated before replacement and
    removed after write failures, preserving the previous valid snapshot.

    Raises:
        OSError: If creating, writing, validating, or replacing the file fails.
        DataContractError: If the temporary Parquet result violates the contract.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".parquet",
            prefix=f".{destination.name}.",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        pq.write_table(table, temporary_path)
        observations_from_table(pq.read_table(temporary_path))
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def resolve_window(
    existing: list[FxObservation], config: IngestionConfig, today: date
) -> tuple[str, date, date]:
    """Choose initial, incremental, or replay dates for an ingestion request.

    An explicit start date selects replay mode. Otherwise incremental mode
    re-fetches ``overlap_days`` calendar dates inclusive of the latest stored
    rate, allowing ECB revisions without maintaining a separate watermark.

    Raises:
        IngestionError: If overlap is invalid or the resulting range is invalid.
    """
    end_date = config.end_date or today
    if config.start_date is not None:
        start_date = config.start_date
        mode = "replay"
    elif existing:
        if config.overlap_days < 1:
            raise IngestionError("overlap days must be at least one")
        latest_date = max(observation.rate_date for observation in existing)
        start_date = latest_date - timedelta(days=config.overlap_days - 1)
        mode = "incremental"
    else:
        start_date = DEFAULT_START_DATE
        mode = "initial"
    validate_date_range(start_date, end_date)
    return mode, start_date, end_date


def ingest(
    config: IngestionConfig,
    *,
    today: date | None = None,
    fetcher: Callable[[date, date], str] | None = None,
) -> bool:
    """Ingest an ECB GBP/EUR window and atomically upsert the local snapshot.

    Initial runs backfill from 2024-01-01; later runs use the inclusive overlap
    determined by ``resolve_window``. ECB weekend and holiday gaps remain
    absent. An empty window is a no-op only when it does not contradict an
    already persisted observation; an empty initial backfill fails.

    Args:
        config: Destination, date-selection, timeout, and retry configuration.
        today: Injectable UTC date for deterministic tests.
        fetcher: Injectable CSV retrieval function for deterministic tests.

    Returns:
        ``True`` when an atomic Parquet replacement occurred; ``False`` when
        an empty valid window or identical merge made persistence unnecessary.

    Raises:
        IngestionError: For invalid windows, empty initial backfills, conflicting
            empty responses, HTTP/response failures, or invalid persisted data.
        OSError: If atomic persistence fails before replacement.
    """
    existing = read_existing(config.destination)
    mode, start_date, end_date = resolve_window(existing, config, today or utc_today())
    LOGGER.info(
        "Starting %s ECB FX ingestion for %s from %s through %s",
        mode,
        SERIES_KEY,
        start_date,
        end_date,
    )
    if fetcher is None:

        def fetcher(start: date, end: date) -> str:
            """Fetch one ECB range using this run's configured HTTP settings."""
            return fetch_csv(
                start,
                end,
                timeout_seconds=config.timeout_seconds,
                max_retries=config.max_retries,
            )

    incoming = parse_ecb_csv(fetcher(start_date, end_date), start_date, end_date)
    LOGGER.info("Received %s ECB observations", len(incoming))
    if not incoming:
        if not existing:
            raise IngestionError("Initial ECB backfill returned no valid observations")
        requested_existing = [
            observation
            for observation in existing
            if start_date <= observation.rate_date <= end_date
        ]
        if requested_existing:
            raise IngestionError(
                "Empty ECB response contradicts persisted observations"
            )
        LOGGER.info("No ECB publication in requested window; persistence skipped")
        LOGGER.info(
            "Latest persisted ECB FX observation date: %s",
            max(observation.rate_date for observation in existing),
        )
        return False

    persisted_keys = {
        observation.key
        for observation in existing
        if start_date <= observation.rate_date <= end_date
    }
    incoming_keys = {observation.key for observation in incoming}
    missing_keys = persisted_keys - incoming_keys
    if missing_keys:
        missing_dates = ", ".join(str(key[0]) for key in sorted(missing_keys))
        raise IngestionError(
            "ECB response omitted persisted observations in requested range: "
            f"{missing_dates}"
        )

    merged, changed = merge_observations(existing, incoming)
    result_table = table_from_observations(merged)
    if existing and tables_equal(table_from_observations(existing), result_table):
        LOGGER.info("ECB FX dataset unchanged; persistence skipped")
        LOGGER.info(
            "Latest persisted ECB FX observation date: %s",
            max(observation.rate_date for observation in existing),
        )
        return False
    atomic_write(config.destination, result_table)
    latest_date = max(observation.rate_date for observation in merged)
    LOGGER.info(
        "Persisted %s ECB FX records (%s inserted or updated); latest rate date: %s",
        len(merged),
        changed,
        latest_date,
    )
    return True


def parse_arguments() -> IngestionConfig:
    """Parse CLI options into one validated-by-ingestion configuration object."""
    parser = argparse.ArgumentParser(
        description="Ingest ECB GBP/EUR reference exchange rates"
    )
    parser.add_argument("--start-date", type=parse_iso_date)
    parser.add_argument("--end-date", type=parse_iso_date)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--overlap-days", type=int, default=DEFAULT_OVERLAP_DAYS)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int, default=3)
    arguments = parser.parse_args()
    return IngestionConfig(
        destination=arguments.destination,
        start_date=arguments.start_date,
        end_date=arguments.end_date,
        overlap_days=arguments.overlap_days,
        timeout_seconds=arguments.timeout_seconds,
        max_retries=arguments.max_retries,
    )


def main() -> int:
    """Run the CLI and convert expected ingestion failures into exit status one."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        ingest(parse_arguments())
    except IngestionError as error:
        LOGGER.error("ECB FX ingestion failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
