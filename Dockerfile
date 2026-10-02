FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --only-upgrade -y libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall --yes setuptools wheel jaraco.context || true

COPY --chown=appuser:appgroup app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]