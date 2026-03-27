from __future__ import annotations

from adguard_exporter.app import app
from adguard_exporter.config import EXPORTER_PORT


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=EXPORTER_PORT)
