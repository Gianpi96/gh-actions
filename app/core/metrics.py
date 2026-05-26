from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as pfi_metrics

# ── Custom metrics ────────────────────────────────────────────────────────────

groq_api_calls_total = Counter(
    "groq_api_calls_total",
    "Total Groq API calls",
    ["model", "endpoint"],
)
groq_tokens_total = Counter(
    "groq_tokens_total",
    "Total tokens consumed via Groq API",
    ["model", "token_type"],   # token_type: prompt | completion
)
groq_estimated_cost_usd = Counter(
    "groq_estimated_cost_usd_total",
    "Estimated Groq API cost in USD (llama-3.3-70b = $0, tracked for future pricing)",
    ["model"],
)

# Project-5 WebSocket connections
websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Number of currently active WebSocket connections",
    ["endpoint"],
)


# ── Instrumentator ────────────────────────────────────────────────────────────

def setup_metrics(app) -> Instrumentator:
    """Attach prometheus-fastapi-instrumentator + custom metrics."""
    instr = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        env_var_name="ENABLE_METRICS",
        should_instrument_requests_inprogress=True,
        inprogress_name="fastapi_requests_inprogress",
        inprogress_labels=True,
        excluded_handlers=["/health", "/metrics"],
    )

    # counter  → fastapi_requests_total{handler, method, status_code}
    instr.add(
        pfi_metrics.requests(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="fastapi",
        )
    )

    # histogram → fastapi_http_request_duration_seconds{handler, method, status_code}
    instr.add(
        pfi_metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="fastapi",
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
        )
    )

    instr.add(
        pfi_metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    ).add(
        pfi_metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    instr.instrument(app)
    return instr


# ── Helper for Groq service layer ─────────────────────────────────────────────

def track_groq_call(
    *,
    model: str,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    groq_api_calls_total.labels(model=model, endpoint=endpoint).inc()
    groq_tokens_total.labels(model=model, token_type="prompt").inc(prompt_tokens)
    groq_tokens_total.labels(model=model, token_type="completion").inc(completion_tokens)
    # llama-3.3-70b-versatile: currently $0/token on Groq free tier
    groq_estimated_cost_usd.labels(model=model).inc(0.0)
