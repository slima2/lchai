FROM python:3.12-slim

WORKDIR /srv

COPY packages/common /srv/packages/common
COPY packages/event-contracts /srv/packages/event-contracts
COPY packages/langgraph-workflows /srv/packages/langgraph-workflows
RUN pip install --no-cache-dir /srv/packages/common /srv/packages/event-contracts /srv/packages/langgraph-workflows

COPY apps/graph-service/pyproject.toml .
COPY apps/graph-service/app/ app/
COPY apps/graph-service/alembic.ini .
COPY apps/graph-service/alembic/ alembic/
RUN pip install --no-cache-dir -e .

EXPOSE 8005
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
