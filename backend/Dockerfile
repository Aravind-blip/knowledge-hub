FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini ./alembic.ini
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY infra/db/migrations ./infra/db/migrations

RUN chmod +x ./scripts/start_backend.sh

EXPOSE 8000

CMD ["./scripts/start_backend.sh"]
