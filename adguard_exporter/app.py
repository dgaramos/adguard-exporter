from __future__ import annotations

from flask import Flask

from adguard_exporter.clients.adguard import AdGuardClient
from adguard_exporter.config import (
    ADGUARD_PASSWORD,
    ADGUARD_URL,
    ADGUARD_USERNAME,
    QUERYLOG_LIMIT,
    QUERYLOG_RECENT_FINGERPRINTS_LIMIT,
    QUERYLOG_STATE_PATH,
    REQUEST_TIMEOUT,
)
from adguard_exporter.metrics.exporter import build_metrics_response
from adguard_exporter.state.file import FileStateStore

app = Flask(__name__)

client = AdGuardClient(
    base_url=ADGUARD_URL,
    username=ADGUARD_USERNAME,
    password=ADGUARD_PASSWORD,
    timeout=REQUEST_TIMEOUT,
)
state_store = FileStateStore(
    path=QUERYLOG_STATE_PATH,
    recent_fingerprints_limit=QUERYLOG_RECENT_FINGERPRINTS_LIMIT,
)


@app.route("/metrics")
def metrics():
    return build_metrics_response(
        client=client,
        querylog_limit=QUERYLOG_LIMIT,
        state_store=state_store,
        recent_fingerprints_limit=QUERYLOG_RECENT_FINGERPRINTS_LIMIT,
    )


@app.route("/")
def index():
    return "ok\n"
