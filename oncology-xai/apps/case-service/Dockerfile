FROM python:3.12-slim

WORKDIR /srv

COPY packages/common /srv/packages/common
COPY packages/event-contracts /srv/packages/event-contracts
RUN pip install --no-cache-dir /srv/packages/common /srv/packages/event-contracts

COPY apps/case-service/pyproject.toml .
COPY apps/case-service/app/ app/
COPY apps/case-service/alembic.ini .
COPY apps/case-service/alembic/ alembic/
RUN pip install --no-cache-dir -e .

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
