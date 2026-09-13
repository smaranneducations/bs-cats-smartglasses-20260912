FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY services/api/requirements.txt /app/services/api/requirements.txt
RUN pip install --no-cache-dir -r /app/services/api/requirements.txt

COPY packages /app/packages
COPY services/api /app/services/api
COPY apps /app/apps
COPY assets /app/assets
COPY config /app/config
COPY docs/architecture /app/docs/architecture

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "uvicorn services.api.src.main:app --host 0.0.0.0 --port ${PORT}"]
