from __future__ import annotations

from flask import Flask

from adguard_exporter.clients.adguard import AdGuardClient
from adguard_exporter.config import (
    ADGUARD_PASSWORD,
    ADGUARD_URL,
    ADGUARD_USERNAME,
    QUERYLOG_LIMIT,
    REQUEST_TIMEOUT,
)
from adguard_exporter.metrics.exporter import build_metrics_response

app = Flask(__name__)

client = AdGuardClient(
    base_url=ADGUARD_URL,
    username=ADGUARD_USERNAME,
    password=ADGUARD_PASSWORD,
    timeout=REQUEST_TIMEOUT,
)


@app.route("/metrics")
def metrics():
    return build_metrics_response(client=client, querylog_limit=QUERYLOG_LIMIT)


@app.route("/")
def index():
    return "ok\n"
