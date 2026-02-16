FROM python:3.12-slim

WORKDIR /srv

COPY packages/common /srv/packages/common
COPY packages/event-contracts /srv/packages/event-contracts
RUN pip install --no-cache-dir /srv/packages/common /srv/packages/event-contracts

COPY apps/audit-service/pyproject.toml .
COPY apps/audit-service/app/ app/
COPY apps/audit-service/alembic.ini .
COPY apps/audit-service/alembic/ alembic/
RUN pip install --no-cache-dir -e .

EXPOSE 8007
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
