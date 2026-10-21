"""Настройка логирования без утечки секретов и содержимого документов."""

from __future__ import annotations

import logging
import logging.config
import sys

_CONFIGURED = False


class _RedactingFilter(logging.Filter):
    """Маскирует значения, похожие на секреты, в сообщениях логов."""

    _SENSITIVE_KEYS = (
        "password",
        "secret",
        "api_key",
        "apikey",
        "token",
        "authorization",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - defensive
            return True
        lowered = message.lower()
        if any(key in lowered for key in self._SENSITIVE_KEYS):
            record.msg = "[сообщение скрыто: возможно содержатся чувствительные данные]"
            record.args = ()
        return True


def configure_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"redact": {"()": _RedactingFilter}},
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                    "filters": ["redact"],
                }
            },
            "root": {"handlers": ["console"], "level": level.upper()},
            "loggers": {
                "app": {"handlers": ["console"], "level": level.upper(), "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            },
        }
    )
    _CONFIGURED = True
