from __future__ import annotations

import time
from typing import Any

import requests

from adguard_exporter.observability import get_logger, get_telemetry


class AdGuardClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.last_login = 0.0
        self.logger = get_logger("adguard_exporter.clients.adguard")
        self.telemetry = get_telemetry()

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/control/login"

    @property
    def stats_url(self) -> str:
        return f"{self.base_url}/control/stats"

    @property
    def querylog_url(self) -> str:
        return f"{self.base_url}/control/querylog"

    @property
    def clients_url(self) -> str:
        return f"{self.base_url}/control/clients"

    def login(self) -> None:
        payload = {
            "name": self.username,
            "password": self.password,
        }
        try:
            response = self.session.post(self.login_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException:
            self.telemetry.record_api_failure("login")
            self.logger.warning(
                "AdGuard login request failed",
                extra={"event": "adguard_login_failed", "base_url": self.base_url},
                exc_info=True,
            )
            raise

        self.last_login = time.time()

    def _ensure_login(self) -> None:
        if time.time() - self.last_login > 600:
            self.login()

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        endpoint = self._endpoint_name(url)
        self._ensure_login()

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 401:
                self.login()
                response = self.session.get(url, params=params, timeout=self.timeout)

            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            self.telemetry.record_api_failure(endpoint)
            self.logger.warning(
                "AdGuard API request failed",
                extra={"event": "adguard_api_request_failed", "endpoint": endpoint, "base_url": self.base_url},
                exc_info=True,
            )
            raise

    def get_stats(self) -> dict[str, Any]:
        return self._get_json(self.stats_url)

    def get_querylog(self, limit: int = 1000) -> dict[str, Any]:
        return self._get_json(self.querylog_url, params={"limit": limit})

    def get_clients(self) -> dict[str, Any]:
        return self._get_json(self.clients_url)

    @staticmethod
    def _endpoint_name(url: str) -> str:
        if url.endswith("/control/stats"):
            return "stats"
        if url.endswith("/control/querylog"):
            return "querylog"
        if url.endswith("/control/clients"):
            return "clients"
        if url.endswith("/control/login"):
            return "login"
        return "unknown"
