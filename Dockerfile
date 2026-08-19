FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DBT_PROFILES_DIR=/app/profiles

RUN chmod +x /app/scripts/run.sh \
    && chmod +x /app/scripts/test.sh

CMD ["/app/scripts/run.sh"]