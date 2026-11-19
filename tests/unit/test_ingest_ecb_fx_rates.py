from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


@pytest.fixture(scope="module")
def fx_module():
    """Load the script as a module so unit tests avoid subprocess execution."""
    path = Path(__file__).parents[2] / "scripts" / "ingest_ecb_fx_rates.py"
    spec = importlib.util.spec_from_file_location("ingest_ecb_fx_rates", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def csv_data(rows: list[tuple[str, str]]) -> str:
    """Build a minimal, valid ECB CSVdata fixture from date/rate pairs."""
    header = "KEY,CURRENCY,CURRENCY_DENOM,TIME_PERIOD,OBS_VALUE\n"
    values = [f"EXR.D.GBP.EUR.SP00.A,GBP,EUR,{day},{rate}" for day, rate in rows]
    return header + "\n".join(values) + ("\n" if values else "")


def read_rows(path: Path) -> list[dict[str, object]]:
    """Read persisted Parquet rows in Python-native types for assertions."""
    return pq.read_table(path).to_pylist()


@pytest.fixture
def config(fx_module, tmp_path):
    """Provide an isolated destination and fixed end date for ingestion tests."""
    return fx_module.IngestionConfig(
        destination=tmp_path / "ecb_fx_rates.parquet",
        end_date=date(2024, 1, 10),
    )


def test_initial_backfill_persists_explicit_schema(fx_module, config):
    written = fx_module.ingest(
        config,
        fetcher=lambda start, end: csv_data(
            [("2024-01-02", "0.8567000000"), ("2024-01-03", "0.8570000000")]
        ),
    )

    assert written is True
    table = pq.read_table(config.destination)
    assert table.schema.equals(fx_module.FX_SCHEMA, check_metadata=False)
    assert read_rows(config.destination)[0]["quote_per_eur"] == Decimal("0.8567000000")


def test_explicit_date_range_is_used_for_replay(fx_module, tmp_path):
    config = fx_module.IngestionConfig(
        destination=tmp_path / "rates.parquet",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 31),
    )
    captured: list[tuple[date, date]] = []
    fx_module.ingest(
        config,
        fetcher=lambda start, end: (
            captured.append((start, end)) or csv_data([("2024-03-01", "0.8500000000")])
        ),
    )
    assert captured == [(date(2024, 3, 1), date(2024, 3, 31))]


def test_easter_2024_non_publication_gap_preserves_distinct_equal_rates(
    fx_module, tmp_path, monkeypatch
):
    """Keep equal ECB rates distinct across the Easter non-publication gap."""
    config = fx_module.IngestionConfig(
        destination=tmp_path / "easter_fx_rates.parquet",
        start_date=date(2024, 3, 28),
        end_date=date(2024, 4, 2),
    )
    payload = csv_data([("2024-03-28", "0.8551"), ("2024-04-02", "0.8551")])

    assert fx_module.ingest(config, fetcher=lambda start, end: payload) is True
    table = pq.read_table(config.destination)
    rows = read_rows(config.destination)

    assert table.schema.equals(fx_module.FX_SCHEMA, check_metadata=False)
    assert [(row["rate_date"], row["quote_currency"]) for row in rows] == [
        (date(2024, 3, 28), "GBP"),
        (date(2024, 4, 2), "GBP"),
    ]
    assert {row["quote_per_eur"] for row in rows} == {Decimal("0.8551000000")}
    assert {
        date(2024, 3, 29),
        date(2024, 3, 30),
        date(2024, 3, 31),
        date(2024, 4, 1),
    }.isdisjoint({row["rate_date"] for row in rows})

    monkeypatch.setattr(
        fx_module,
        "atomic_write",
        lambda destination, table: pytest.fail("identical replay must not persist"),
    )
    assert fx_module.ingest(config, fetcher=lambda start, end: payload) is False


def test_incremental_window_has_seven_day_inclusive_overlap(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-10", "0.8500000000")])
    )
    captured: list[tuple[date, date]] = []
    fx_module.ingest(
        config,
        fetcher=lambda start, end: (
            captured.append((start, end)) or csv_data([("2024-01-10", "0.8500000000")])
        ),
    )
    assert captured == [(date(2024, 1, 4), date(2024, 1, 10))]


def test_incremental_preserves_history_and_replaces_revised_rate(fx_module, config):
    config = fx_module.IngestionConfig(destination=config.destination)
    fx_module.ingest(
        config,
        fetcher=lambda start, end: csv_data(
            [("2024-01-02", "0.8500000000"), ("2024-01-10", "0.8600000000")]
        ),
        today=date(2024, 1, 10),
    )
    fx_module.ingest(
        config,
        fetcher=lambda start, end: csv_data(
            [("2024-01-10", "0.8610000000"), ("2024-01-11", "0.8620000000")]
        ),
        today=date(2024, 1, 11),
    )
    rows = read_rows(config.destination)
    assert [(row["rate_date"], row["quote_per_eur"]) for row in rows] == [
        (date(2024, 1, 2), Decimal("0.8500000000")),
        (date(2024, 1, 10), Decimal("0.8610000000")),
        (date(2024, 1, 11), Decimal("0.8620000000")),
    ]


def test_identical_ingestion_skips_rewrite(fx_module, config, monkeypatch):
    payload = csv_data([("2024-01-10", "0.8500000000")])
    fx_module.ingest(config, fetcher=lambda start, end: payload)
    monkeypatch.setattr(
        fx_module,
        "atomic_write",
        lambda destination, table: pytest.fail("unchanged data must not be written"),
    )
    assert fx_module.ingest(config, fetcher=lambda start, end: payload) is False


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ("TIME_PERIOD,OBS_VALUE\n2024-01-02,0.8500000000\n", "missing required"),
        (csv_data([("not-a-date", "0.8500000000")]), "Invalid ECB observation date"),
        (csv_data([("2024-01-02", "0")]), "finite and positive"),
        (csv_data([("2024-01-02", "NaN")]), "finite and positive"),
        (csv_data([("2024-01-02", "0.12345678901")]), "representable"),
    ],
)
def test_invalid_csv_is_rejected(fx_module, payload, error):
    with pytest.raises(fx_module.ResponseValidationError, match=error):
        fx_module.parse_ecb_csv(payload, date(2024, 1, 1), date(2024, 1, 31))


def test_unexpected_series_currency_and_duplicate_keys_are_rejected(fx_module):
    unexpected = csv_data([("2024-01-02", "0.8500000000")]).replace(
        "GBP,EUR", "USD,EUR"
    )
    with pytest.raises(fx_module.ResponseValidationError, match="currency pair"):
        fx_module.parse_ecb_csv(unexpected, date(2024, 1, 1), date(2024, 1, 31))
    unexpected_key = csv_data([("2024-01-02", "0.8500000000")]).replace(
        "EXR.D.GBP.EUR.SP00.A", "EXR.D.USD.EUR.SP00.A"
    )
    with pytest.raises(fx_module.ResponseValidationError, match="series key"):
        fx_module.parse_ecb_csv(
            unexpected_key,
            date(2024, 1, 1),
            date(2024, 1, 31),
        )
    duplicate = csv_data(
        [("2024-01-02", "0.8500000000"), ("2024-01-02", "0.8510000000")]
    )
    with pytest.raises(fx_module.DataContractError, match="duplicate"):
        fx_module.parse_ecb_csv(duplicate, date(2024, 1, 1), date(2024, 1, 31))


def test_invalid_existing_schema_is_rejected_before_fetch(fx_module, config):
    pq.write_table(pa.table({"wrong": ["schema"]}), config.destination)
    with pytest.raises(fx_module.DataContractError, match="schema"):
        fx_module.ingest(
            config, fetcher=lambda start, end: pytest.fail("must not fetch")
        )


def test_initial_empty_response_fails_but_valid_empty_increment_is_noop(
    fx_module, config
):
    with pytest.raises(fx_module.IngestionError, match="Initial"):
        fx_module.ingest(config, fetcher=lambda start, end: csv_data([]))

    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-02", "0.8500000000")])
    )
    later_config = fx_module.IngestionConfig(
        destination=config.destination,
        start_date=date(2024, 2, 3),
        end_date=date(2024, 2, 4),
    )
    assert (
        fx_module.ingest(later_config, fetcher=lambda start, end: csv_data([])) is False
    )


def test_empty_response_contradicting_existing_data_fails(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-10", "0.8500000000")])
    )
    with pytest.raises(fx_module.IngestionError, match="contradicts"):
        fx_module.ingest(config, fetcher=lambda start, end: csv_data([]))


def test_partial_response_omitting_persisted_dates_fails_before_persistence(
    fx_module, config
):
    fx_module.ingest(
        config,
        fetcher=lambda start, end: csv_data(
            [("2024-01-02", "0.8500000000"), ("2024-01-10", "0.8600000000")]
        ),
    )
    before = config.destination.read_bytes()
    replay_config = fx_module.IngestionConfig(
        destination=config.destination,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    with pytest.raises(
        fx_module.IngestionError, match="omitted persisted observations"
    ):
        fx_module.ingest(
            replay_config,
            fetcher=lambda start, end: csv_data([("2024-01-10", "0.8610000000")]),
        )
    assert config.destination.read_bytes() == before


def test_present_ecb_sdmx_dimensions_are_validated(fx_module):
    payload = (
        "KEY,FREQ,EXR_TYPE,EXR_SUFFIX,CURRENCY,CURRENCY_DENOM,TIME_PERIOD,OBS_VALUE\n"
        "EXR.D.GBP.EUR.SP00.A,D,SP00,A,GBP,EUR,2024-01-02,0.8500000000\n"
    )
    assert fx_module.parse_ecb_csv(payload, date(2024, 1, 1), date(2024, 1, 31))
    invalid = payload.replace(",SP00,A,GBP", ",SP01,A,GBP")
    with pytest.raises(fx_module.ResponseValidationError, match="EXR_TYPE"):
        fx_module.parse_ecb_csv(invalid, date(2024, 1, 1), date(2024, 1, 31))


class FakeResponse:
    """Provide the minimal context-managed HTTP response interface for tests."""

    status = 200

    def __init__(self, body: str):
        """Store a UTF-8 body returned by ``read`` during a fake request."""
        self.body = body.encode()

    def __enter__(self):
        """Enter the fake response context used by the standard-library opener."""
        return self

    def __exit__(self, *args):
        """Exit without suppressing exceptions raised by the request code."""
        return False

    def read(self):
        """Return the configured response bytes."""
        return self.body

    def getcode(self):
        """Return the successful HTTP status expected by the ingestion client."""
        return self.status


def opener_from_attempts(attempts):
    """Create a fake opener that consumes response or exception attempts in order."""

    def opener(request, timeout):
        """Raise queued failures or return the next queued fake response."""
        attempt = next(attempts)
        if isinstance(attempt, BaseException):
            raise attempt
        return attempt

    return opener


def test_http_transient_errors_retry_without_sleeping(fx_module):
    attempts = iter(
        [
            URLError("temporary"),
            FakeResponse(csv_data([("2024-01-02", "0.8500000000")])),
        ]
    )
    sleeps: list[float] = []
    result = fx_module.fetch_csv(
        date(2024, 1, 1),
        date(2024, 1, 2),
        timeout_seconds=1,
        max_retries=2,
        opener=opener_from_attempts(attempts),
        sleeper=sleeps.append,
        jitter=lambda low, high: 0,
    )
    assert "2024-01-02" in result
    assert sleeps == [1]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_http_statuses_retry(fx_module, status):
    error = HTTPError("https://example.test", status, "temporary", {}, None)
    attempts = iter([error, FakeResponse(csv_data([("2024-01-02", "0.8500000000")]))])
    assert fx_module.fetch_csv(
        date(2024, 1, 1),
        date(2024, 1, 2),
        timeout_seconds=1,
        max_retries=1,
        opener=opener_from_attempts(attempts),
        sleeper=lambda seconds: None,
        jitter=lambda low, high: 0,
    )


def test_retry_after_header_overrides_exponential_backoff(fx_module):
    error = HTTPError("https://example.test", 429, "busy", {"Retry-After": "7"}, None)
    attempts = iter([error, FakeResponse(csv_data([("2024-01-02", "0.8500000000")]))])
    sleeps: list[float] = []
    fx_module.fetch_csv(
        date(2024, 1, 1),
        date(2024, 1, 2),
        timeout_seconds=1,
        max_retries=1,
        opener=opener_from_attempts(attempts),
        sleeper=sleeps.append,
        jitter=lambda low, high: 0,
    )
    assert sleeps == [7]


def test_retry_after_http_date_is_converted_to_a_delay(fx_module):
    current_time = datetime(2024, 1, 1, 12, tzinfo=UTC)
    headers = {"Retry-After": format_datetime(current_time + timedelta(seconds=30))}
    assert fx_module.retry_after_seconds(headers, now=lambda: current_time) == 30


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "not-a-delay"])
def test_invalid_retry_after_values_are_rejected(fx_module, value):
    assert fx_module.retry_after_seconds({"Retry-After": value}) is None


def test_excessive_retry_after_value_is_capped(fx_module):
    assert (
        fx_module.retry_after_seconds({"Retry-After": "999999"})
        == fx_module.MAX_RETRY_DELAY_SECONDS
    )


def test_valid_empty_404_replay_is_a_noop_but_other_404s_fail(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-02", "0.8500000000")])
    )
    empty_body = csv_data([]).encode()

    def empty_404(request, timeout):
        raise HTTPError(
            "https://example.test", 404, "not found", {}, BytesIO(empty_body)
        )

    response = fx_module.fetch_csv(
        date(2024, 2, 3),
        date(2024, 2, 4),
        timeout_seconds=1,
        max_retries=0,
        opener=empty_404,
    )
    replay_config = fx_module.IngestionConfig(
        destination=config.destination,
        start_date=date(2024, 2, 3),
        end_date=date(2024, 2, 4),
    )
    before = config.destination.read_bytes()
    assert fx_module.ingest(replay_config, fetcher=lambda start, end: response) is False
    assert config.destination.read_bytes() == before

    def invalid_404(request, timeout):
        raise HTTPError(
            "https://example.test", 404, "not found", {}, BytesIO(b"not found")
        )

    with pytest.raises(fx_module.HttpRequestError, match="HTTP 404"):
        fx_module.fetch_csv(
            date(2024, 2, 3),
            date(2024, 2, 4),
            timeout_seconds=1,
            max_retries=0,
            opener=invalid_404,
        )


def test_recognized_no_data_problem_404_replay_is_a_noop(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-02", "0.8500000000")])
    )
    problem_body = (
        b'{"title":"Not Found","status":404,'
        b'"detail":"No Series was returned for the query"}'
    )

    def no_data_404(request, timeout):
        raise HTTPError(
            "https://example.test",
            404,
            "not found",
            {"Content-Type": "application/problem+json; charset=utf-8"},
            BytesIO(problem_body),
        )

    response = fx_module.fetch_csv(
        date(2024, 2, 3),
        date(2024, 2, 4),
        timeout_seconds=1,
        max_retries=0,
        opener=no_data_404,
    )
    replay_config = fx_module.IngestionConfig(
        destination=config.destination,
        start_date=date(2024, 2, 3),
        end_date=date(2024, 2, 4),
    )
    before = config.destination.read_bytes()
    assert fx_module.ingest(replay_config, fetcher=lambda start, end: response) is False
    assert config.destination.read_bytes() == before


def test_zero_byte_success_response_replay_is_a_noop(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-02", "0.8500000000")])
    )
    response = fx_module.fetch_csv(
        date(2024, 2, 3),
        date(2024, 2, 4),
        timeout_seconds=1,
        max_retries=0,
        opener=lambda request, timeout: FakeResponse(""),
    )
    replay_config = fx_module.IngestionConfig(
        destination=config.destination,
        start_date=date(2024, 2, 3),
        end_date=date(2024, 2, 4),
    )
    before = config.destination.read_bytes()
    assert fx_module.ingest(replay_config, fetcher=lambda start, end: response) is False
    assert config.destination.read_bytes() == before


@pytest.mark.parametrize(
    "problem_body",
    [
        b'{"title":"not found","status":404}',
        b'{"title":"No results found","status":404}',
        b'{"title":"No results found","status":400}',
        b'{"error":"No results found"}',
    ],
)
def test_unrelated_problem_json_404_fails(fx_module, problem_body):
    def unrelated_404(request, timeout):
        raise HTTPError(
            "https://example.test",
            404,
            "not found",
            {"Content-Type": "application/problem+json"},
            BytesIO(problem_body),
        )

    with pytest.raises(fx_module.HttpRequestError, match="HTTP 404"):
        fx_module.fetch_csv(
            date(2024, 2, 3),
            date(2024, 2, 4),
            timeout_seconds=1,
            max_retries=0,
            opener=unrelated_404,
        )


def test_noop_logs_latest_persisted_date(fx_module, config, caplog):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-10", "0.8500000000")])
    )
    with caplog.at_level("INFO"):
        assert (
            fx_module.ingest(
                config,
                fetcher=lambda start, end: csv_data([("2024-01-10", "0.8500000000")]),
            )
            is False
        )
    assert "Latest persisted ECB FX observation date: 2024-01-10" in caplog.text


def test_http_failures_exhaust_or_fail_fast(fx_module):
    with pytest.raises(fx_module.HttpRequestError, match="HTTP 500"):
        fx_module.fetch_csv(
            date(2024, 1, 1),
            date(2024, 1, 2),
            timeout_seconds=1,
            max_retries=1,
            opener=lambda request, timeout: (_ for _ in ()).throw(
                HTTPError("https://x", 500, "", {}, None)
            ),
            sleeper=lambda seconds: None,
            jitter=lambda low, high: 0,
        )
    with pytest.raises(fx_module.HttpRequestError, match="HTTP 404"):
        fx_module.fetch_csv(
            date(2024, 1, 1),
            date(2024, 1, 2),
            timeout_seconds=1,
            max_retries=3,
            opener=lambda request, timeout: (_ for _ in ()).throw(
                HTTPError("https://x", 404, "", {}, None)
            ),
        )


def test_parsing_and_write_failures_preserve_existing_dataset(
    fx_module, config, monkeypatch
):
    original = csv_data([("2024-01-10", "0.8500000000")])
    fx_module.ingest(config, fetcher=lambda start, end: original)
    before = config.destination.read_bytes()
    with pytest.raises(fx_module.ResponseValidationError):
        fx_module.ingest(config, fetcher=lambda start, end: "bad csv")
    assert config.destination.read_bytes() == before

    monkeypatch.setattr(
        fx_module.pq,
        "write_table",
        lambda table, path: (_ for _ in ()).throw(OSError("disk full")),
    )
    with pytest.raises(OSError, match="disk full"):
        fx_module.ingest(
            config,
            fetcher=lambda start, end: csv_data([("2024-01-10", "0.8510000000")]),
        )
    assert config.destination.read_bytes() == before
    assert not list(config.destination.parent.glob(".ecb_fx_rates.parquet.*"))


def test_atomic_write_replaces_destination(fx_module, config):
    fx_module.ingest(
        config, fetcher=lambda start, end: csv_data([("2024-01-10", "0.8500000000")])
    )
    old_inode = config.destination.stat().st_ino
    fx_module.ingest(
        config,
        fetcher=lambda start, end: csv_data([("2024-01-10", "0.8510000000")]),
    )
    assert config.destination.stat().st_ino != old_inode
    assert read_rows(config.destination)[0]["quote_per_eur"] == Decimal("0.8510000000")
