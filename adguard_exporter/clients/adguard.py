from __future__ import annotations

import time
from typing import Any

import requests


class AdGuardClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.last_login = 0.0

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/control/login"

    @property
    def stats_url(self) -> str:
        return f"{self.base_url}/control/stats"

    @property
    def querylog_url(self) -> str:
        return f"{self.base_url}/control/querylog"

    def login(self) -> None:
        payload = {
            "name": self.username,
            "password": self.password,
        }
        response = self.session.post(self.login_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        self.last_login = time.time()

    def _ensure_login(self) -> None:
        if time.time() - self.last_login > 600:
            self.login()

    def get_stats(self) -> dict[str, Any]:
        self._ensure_login()

        response = self.session.get(self.stats_url, timeout=self.timeout)
        if response.status_code == 401:
            self.login()
            response = self.session.get(self.stats_url, timeout=self.timeout)

        response.raise_for_status()
        return response.json()

    def get_querylog(self, limit: int = 1000) -> dict[str, Any]:
        self._ensure_login()

        response = self.session.get(
            self.querylog_url,
            params={"limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 401:
            self.login()
            response = self.session.get(
                self.querylog_url,
                params={"limit": limit},
                timeout=self.timeout,
            )

        response.raise_for_status()
        return response.json()
