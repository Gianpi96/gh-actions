# FastAPI Template

![CI](https://github.com/YOUR_ORG/YOUR_REPO/actions/workflows/test.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-76%25-yellow)
![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)

Template riutilizzabile per FastAPI con osservabilità completa.

## Stack

| Layer | Tecnologia |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2 async |
| Cache | Redis 7 |
| LLM | Groq `llama-3.3-70b-versatile` |
| Metrics | Prometheus + Grafana |
| Logging | structlog (JSON strutturato) |
| Tracing | Sentry SDK |
| CI | GitHub Actions (matrix 3.12/3.13/3.14) |
| Tests | pytest + pytest-asyncio + PostgreSQL reale |

## Avvio rapido

```bash
cp .env.example .env
# Imposta GROQ_API_KEY in .env

docker compose up -d
```

| Servizio | URL |
|---|---|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Metrics (raw) | http://localhost:8000/metrics |
| Health | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |

## Test

```bash
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/testdb \
  pytest --cov=app --cov-fail-under=70 -v
```

## Debug N+1 queries

```bash
# 1. Abilita SQL logging
echo "DB_ECHO=true" >> .env

# 2. Conta le query nel log per una singola request
#    /posts/bad  → 1 + N query  ← PROBLEMA
#    /posts/     → 2 query      ← selectinload (fix)
#    /posts/joined → 1 query    ← joinedload   (fix)

# 3. Analisi con PostgreSQL
psql -U postgres -d appdb -c "
  EXPLAIN (ANALYZE, BUFFERS)
  SELECT p.*, a.name FROM posts p
  JOIN authors a ON a.id = p.author_id
  WHERE p.status = 'published';
"
```

## Metriche Prometheus

| Metrica | Tipo | Label |
|---|---|---|
| `fastapi_requests_total` | Counter | handler, method, status_code |
| `fastapi_http_request_duration_seconds` | Histogram | handler, method, status_code |
| `fastapi_requests_inprogress` | Gauge | handler, method |
| `websocket_connections_active` | Gauge | endpoint |
| `groq_api_calls_total` | Counter | model, endpoint |
| `groq_tokens_total` | Counter | model, token_type |
| `groq_estimated_cost_usd_total` | Counter | model |

## Log JSON (structlog)

Ogni log line include automaticamente:

```json
{
  "event": "request_completed",
  "request_id": "uuid-...",
  "user_id": "42",
  "tenant_id": "acme",
  "method": "GET",
  "path": "/posts/",
  "status_code": 200,
  "duration_ms": 12.3,
  "timestamp": "2026-05-26T07:00:00Z",
  "level": "info"
}
```

## Struttura

```
.github/workflows/test.yml     CI matrix 3.12/3.13/3.14 + badge auto-update
app/
├── main.py                    app factory, Sentry, Prometheus, middleware
├── core/
│   ├── config.py              Settings via pydantic-settings
│   ├── database.py            engine pool_size=10 max_overflow=20
│   ├── logging_config.py      structlog JSON + context vars
│   └── metrics.py             Prometheus counters/histograms/gauges
├── api/
│   ├── health.py              GET /health → 200 ok | 503 degraded
│   └── posts.py               selectinload / joinedload examples
├── middleware/
│   └── logging_middleware.py  X-Request-ID, user_id, tenant_id su ogni log
└── models/
    └── base.py                SQLAlchemy models con indici espliciti
docker-compose.yml             app + postgres + redis + prometheus + grafana
prometheus/prometheus.yml
grafana/dashboards/fastapi.json  dashboard pre-configurata
conftest.py                    fixtures PostgreSQL con rollback per test
```
