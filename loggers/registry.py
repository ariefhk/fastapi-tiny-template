import logging
import logging.config

from commons.config import get_configs
from middlewares.request_id_middleware import RequestIDLogFilter


def register_logging() -> None:
    cfg = get_configs()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {
                    "()": RequestIDLogFilter,
                }
            },
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                }
            },
            "root": {
                "level": "DEBUG" if cfg.DEBUG else "INFO",
                "handlers": ["console"],
            },
        }
    )
