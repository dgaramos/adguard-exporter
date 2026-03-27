from __future__ import annotations

import json
import logging
import sys
import threading
import time
from typing import Any


class JsonLogFormatter(logging.Formatter):
    _STANDARD_ATTRS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in self._STANDARD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, sort_keys=True)


class ExporterTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.last_scrape_duration_seconds = 0.0
            self.last_scrape_timestamp_seconds = 0.0
            self.last_success_timestamp_seconds = 0.0
            self.last_stats_duration_seconds = 0.0
            self.last_stats_success_timestamp_seconds = 0.0
            self.last_querylog_duration_seconds = 0.0
            self.last_querylog_success_timestamp_seconds = 0.0
            self.api_request_failures_total = {
                "login": 0,
                "stats": 0,
                "querylog": 0,
                "clients": 0,
            }
            self.processing_failures_total = {
                "stats": 0,
                "querylog": 0,
                "client_mapping": 0,
            }
            self.state_operation_failures_total = {
                "load": 0,
                "save": 0,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "last_scrape_duration_seconds": self.last_scrape_duration_seconds,
                "last_scrape_timestamp_seconds": self.last_scrape_timestamp_seconds,
                "last_success_timestamp_seconds": self.last_success_timestamp_seconds,
                "last_stats_duration_seconds": self.last_stats_duration_seconds,
                "last_stats_success_timestamp_seconds": self.last_stats_success_timestamp_seconds,
                "last_querylog_duration_seconds": self.last_querylog_duration_seconds,
                "last_querylog_success_timestamp_seconds": self.last_querylog_success_timestamp_seconds,
                "api_request_failures_total": dict(self.api_request_failures_total),
                "processing_failures_total": dict(self.processing_failures_total),
                "state_operation_failures_total": dict(self.state_operation_failures_total),
            }

    def record_scrape_completed(self, duration_seconds: float, success: bool) -> None:
        now = time.time()
        with self._lock:
            self.last_scrape_duration_seconds = duration_seconds
            self.last_scrape_timestamp_seconds = now
            if success:
                self.last_success_timestamp_seconds = now

    def record_stats_success(self, duration_seconds: float) -> None:
        now = time.time()
        with self._lock:
            self.last_stats_duration_seconds = duration_seconds
            self.last_stats_success_timestamp_seconds = now

    def record_querylog_success(self, duration_seconds: float) -> None:
        now = time.time()
        with self._lock:
            self.last_querylog_duration_seconds = duration_seconds
            self.last_querylog_success_timestamp_seconds = now

    def record_api_failure(self, endpoint: str) -> None:
        with self._lock:
            if endpoint in self.api_request_failures_total:
                self.api_request_failures_total[endpoint] += 1

    def record_processing_failure(self, stage: str) -> None:
        with self._lock:
            if stage in self.processing_failures_total:
                self.processing_failures_total[stage] += 1

    def record_state_failure(self, operation: str) -> None:
        with self._lock:
            if operation in self.state_operation_failures_total:
                self.state_operation_failures_total[operation] += 1


_TELEMETRY = ExporterTelemetry()


def get_telemetry() -> ExporterTelemetry:
    return _TELEMETRY


def get_logger(name: str = "adguard_exporter") -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(level: str = "INFO", log_format: str = "json") -> None:
    root = logging.getLogger()
    if getattr(root, "_adguard_exporter_logging_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    if log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root._adguard_exporter_logging_configured = True  # type: ignore[attr-defined]
