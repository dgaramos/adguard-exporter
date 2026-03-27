from __future__ import annotations

import os

ADGUARD_URL = os.getenv("ADGUARD_URL", "http://adguard:3000")
ADGUARD_USERNAME = os.getenv("ADGUARD_USERNAME", "")
ADGUARD_PASSWORD = os.getenv("ADGUARD_PASSWORD", "")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
QUERYLOG_LIMIT = int(os.getenv("QUERYLOG_LIMIT", "1000"))
QUERYLOG_STATE_PATH = os.getenv("QUERYLOG_STATE_PATH", "/tmp/adguard_exporter_querylog_state.json")
QUERYLOG_RECENT_FINGERPRINTS_LIMIT = int(os.getenv("QUERYLOG_RECENT_FINGERPRINTS_LIMIT", "5000"))
EXPORTER_PORT = int(os.getenv("EXPORTER_PORT", "9911"))
