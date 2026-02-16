FROM python:3.12-slim

WORKDIR /srv

COPY packages/common /srv/packages/common
COPY packages/event-contracts /srv/packages/event-contracts
RUN pip install --no-cache-dir /srv/packages/common /srv/packages/event-contracts

COPY apps/image-service/pyproject.toml .
COPY apps/image-service/app/ app/
COPY apps/image-service/alembic.ini .
COPY apps/image-service/alembic/ alembic/
RUN pip install --no-cache-dir -e .

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
