FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/api/requirements.txt /tmp/api-requirements.txt
COPY packages/contracts/requirements.txt /tmp/contracts-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/contracts-requirements.txt \
    -r /tmp/api-requirements.txt

COPY packages /app/packages
COPY services/api /app/services/api

EXPOSE 8080

CMD ["uvicorn", "services.api.src.main:app", "--host", "0.0.0.0", "--port", "8080"]
