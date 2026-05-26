import logging
import sys
from contextvars import ContextVar

import structlog

# Per-request context vars (set by middleware, read by every log processor)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var:    ContextVar[str] = ContextVar("user_id",    default="")
tenant_id_var:  ContextVar[str] = ContextVar("tenant_id",  default="")


def _inject_request_context(logger: object, method: str, event_dict: dict) -> dict:
    event_dict["request_id"] = request_id_var.get("")
    event_dict["user_id"]    = user_id_var.get("")
    event_dict["tenant_id"]  = tenant_id_var.get("")
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        _inject_request_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())

    for name in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
