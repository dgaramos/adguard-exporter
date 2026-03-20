from __future__ import annotations

import os
import time
from typing import Any

import requests
from flask import Flask, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST

ADGUARD_URL = os.getenv("ADGUARD_URL", "http://adguard:3000")
ADGUARD_USERNAME = os.getenv("ADGUARD_USERNAME", "")
ADGUARD_PASSWORD = os.getenv("ADGUARD_PASSWORD", "")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
QUERYLOG_LIMIT = int(os.getenv("QUERYLOG_LIMIT", "1000"))

LOGIN_URL = f"{ADGUARD_URL}/control/login"
STATS_URL = f"{ADGUARD_URL}/control/stats"
QUERYLOG_URL = f"{ADGUARD_URL}/control/querylog"

app = Flask(__name__)


class AdGuardClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.last_login = 0.0

    def login(self) -> None:
        payload = {
            "name": self.username,
            "password": self.password,
        }
        response = self.session.post(LOGIN_URL, json=payload, timeout=self.timeout)
        response.raise_for_status()
        self.last_login = time.time()

    def _ensure_login(self) -> None:
        if time.time() - self.last_login > 600:
            self.login()

    def get_stats(self) -> dict[str, Any]:
        self._ensure_login()

        response = self.session.get(STATS_URL, timeout=self.timeout)
        if response.status_code == 401:
            self.login()
            response = self.session.get(STATS_URL, timeout=self.timeout)

        response.raise_for_status()
        return response.json()

    def get_querylog(self, limit: int = 1000) -> dict[str, Any]:
        self._ensure_login()

        response = self.session.get(
            QUERYLOG_URL,
            params={"limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 401:
            self.login()
            response = self.session.get(
                QUERYLOG_URL,
                params={"limit": limit},
                timeout=self.timeout,
            )

        response.raise_for_status()
        return response.json()


client = AdGuardClient(
    base_url=ADGUARD_URL,
    username=ADGUARD_USERNAME,
    password=ADGUARD_PASSWORD,
    timeout=REQUEST_TIMEOUT,
)


def _set_top_map(metric: Gauge, items: list[dict[str, int]]) -> None:
    metric.clear()
    for item in items:
        for key, value in item.items():
            metric.labels(name=key).set(value)


def _set_top_map_custom_label(metric: Gauge, items: list[dict[str, float | int]], label_name: str) -> None:
    metric.clear()
    for item in items:
        for key, value in item.items():
            metric.labels(**{label_name: key}).set(value)


def _extract_client(entry: dict[str, Any]) -> str:
    if isinstance(entry.get("client"), str) and entry["client"]:
        return entry["client"]

    client_info = entry.get("client_info")
    if isinstance(client_info, dict):
        if isinstance(client_info.get("name"), str) and client_info["name"]:
            return client_info["name"]
        if isinstance(client_info.get("ip"), str) and client_info["ip"]:
            return client_info["ip"]

    if isinstance(entry.get("client_ip"), str) and entry["client_ip"]:
        return entry["client_ip"]

    return "unknown"


def _extract_blocked(entry: dict[str, Any]) -> bool | None:
    """
    Retorna:
      True  -> claramente bloqueado
      False -> claramente NÃO bloqueado
      None  -> indeterminado
    """

    # Caso explícito mais confiável
    if isinstance(entry.get("blocked"), bool):
        return entry["blocked"]

    # Algumas versões colocam isso em result.is_filtered
    result = entry.get("result")
    if isinstance(result, dict):
        is_filtered = result.get("is_filtered")
        if isinstance(is_filtered, bool):
            return is_filtered

    # Algumas versões trazem "reason"
    reason = str(entry.get("reason", "")).strip().lower()
    blocked_reasons = {
        "filtered",
        "blocked",
        "filteredblacklist",
        "safebrowsing",
        "parental",
        "safesearch",
    }
    non_blocked_reasons = {
        "",
        "notfiltered",
        "processed",
        "rewrite",
        "rewritten",
        "cached",
    }

    if reason in blocked_reasons:
        return True
    if reason in non_blocked_reasons:
        return False

    # Algumas versões trazem "status"
    status = str(entry.get("status", "")).strip().lower()
    if status in {"blocked", "filtered"}:
        return True
    if status in {"processed", "ok", "success", "answered", "cached"}:
        return False

    # Não inventa moda: se não deu pra saber, marca como indeterminado.
    return None


@app.route("/metrics")
def metrics() -> Response:
    registry = CollectorRegistry()

    # Stats gerais vindas do /control/stats
    g_num_dns_queries = Gauge("adguard_num_dns_queries", "Total DNS queries", registry=registry)
    g_num_blocked = Gauge("adguard_num_blocked_filtering", "Total blocked DNS queries", registry=registry)
    g_avg_processing = Gauge("adguard_avg_processing_time_seconds", "Average DNS processing time in seconds", registry=registry)
    g_blocked_ratio = Gauge("adguard_blocked_ratio", "Blocked DNS ratio (0..1)", registry=registry)

    g_dns_queries_hour = Gauge("adguard_dns_queries_hour", "DNS queries by hour", ["hour"], registry=registry)
    g_blocked_hour = Gauge("adguard_blocked_filtering_hour", "Blocked DNS queries by hour", ["hour"], registry=registry)

    g_top_domain = Gauge("adguard_top_queried_domain_queries", "Top queried domains", ["name"], registry=registry)
    g_top_client = Gauge("adguard_top_client_queries", "Top clients", ["name"], registry=registry)
    g_top_blocked = Gauge("adguard_top_blocked_domain_queries", "Top blocked domains", ["name"], registry=registry)

    g_top_upstream_responses = Gauge("adguard_top_upstream_responses", "Top upstream responses", ["upstream"], registry=registry)
    g_top_upstream_avg_time = Gauge("adguard_top_upstream_avg_time_seconds", "Upstream avg time", ["upstream"], registry=registry)

    # Client-aware metrics vindas do /control/querylog
    g_client_queries = Gauge(
        "adguard_client_queries_total",
        "Queries per client from querylog snapshot",
        ["client"],
        registry=registry,
    )
    g_client_blocked = Gauge(
        "adguard_client_blocked_total",
        "Blocked queries per client from querylog snapshot",
        ["client"],
        registry=registry,
    )
    g_client_blocked_ratio = Gauge(
        "adguard_client_blocked_ratio",
        "Blocked ratio per client from querylog snapshot",
        ["client"],
        registry=registry,
    )

    # Debug/saúde
    g_exporter_up = Gauge("adguard_exporter_up", "Exporter status", registry=registry)
    g_querylog_up = Gauge("adguard_querylog_up", "Querylog collection status", registry=registry)
    g_querylog_entries_total = Gauge("adguard_querylog_entries_total", "Total querylog entries parsed", registry=registry)
    g_querylog_blocked_detected_total = Gauge("adguard_querylog_blocked_detected_total", "Entries confidently detected as blocked", registry=registry)
    g_querylog_nonblocked_detected_total = Gauge("adguard_querylog_nonblocked_detected_total", "Entries confidently detected as non-blocked", registry=registry)
    g_querylog_unknown_blocked_state_total = Gauge("adguard_querylog_unknown_blocked_state_total", "Entries where blocked state could not be determined", registry=registry)

    # 1) /control/stats
    try:
        stats = client.get_stats()

        num_dns_queries = float(stats.get("num_dns_queries", 0))
        num_blocked = float(stats.get("num_blocked_filtering", 0))
        avg_processing_time = float(stats.get("avg_processing_time", 0))

        g_num_dns_queries.set(num_dns_queries)
        g_num_blocked.set(num_blocked)
        g_avg_processing.set(avg_processing_time)
        g_blocked_ratio.set((num_blocked / num_dns_queries) if num_dns_queries > 0 else 0)

        for idx, value in enumerate(stats.get("dns_queries", [])):
            g_dns_queries_hour.labels(hour=str(idx)).set(value)

        for idx, value in enumerate(stats.get("blocked_filtering", [])):
            g_blocked_hour.labels(hour=str(idx)).set(value)

        _set_top_map(g_top_domain, stats.get("top_queried_domains", []))
        _set_top_map(g_top_client, stats.get("top_clients", []))
        _set_top_map(g_top_blocked, stats.get("top_blocked_domains", []))
        _set_top_map_custom_label(g_top_upstream_responses, stats.get("top_upstreams_responses", []), "upstream")
        _set_top_map_custom_label(g_top_upstream_avg_time, stats.get("top_upstreams_avg_time", []), "upstream")

        g_exporter_up.set(1)
    except Exception:
        g_exporter_up.set(0)
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    # 2) /control/querylog
    try:
        querylog = client.get_querylog(limit=QUERYLOG_LIMIT)
        entries = querylog.get("data", [])

        client_counts: dict[str, int] = {}
        client_blocked_counts: dict[str, int] = {}
        client_classified_counts: dict[str, int] = {}

        blocked_detected = 0
        nonblocked_detected = 0
        unknown_detected = 0

        for entry in entries:
            client_name = _extract_client(entry)
            blocked_state = _extract_blocked(entry)

            client_counts[client_name] = client_counts.get(client_name, 0) + 1

            if blocked_state is True:
                client_blocked_counts[client_name] = client_blocked_counts.get(client_name, 0) + 1
                client_classified_counts[client_name] = client_classified_counts.get(client_name, 0) + 1
                blocked_detected += 1
            elif blocked_state is False:
                client_classified_counts[client_name] = client_classified_counts.get(client_name, 0) + 1
                nonblocked_detected += 1
            else:
                unknown_detected += 1

        g_client_queries.clear()
        g_client_blocked.clear()
        g_client_blocked_ratio.clear()

        for client_name, total in client_counts.items():
            blocked_total = client_blocked_counts.get(client_name, 0)
            classified_total = client_classified_counts.get(client_name, 0)

            # ratio só sobre entradas classificadas com confiança
            ratio = (blocked_total / classified_total) if classified_total > 0 else 0

            g_client_queries.labels(client=client_name).set(total)
            g_client_blocked.labels(client=client_name).set(blocked_total)
            g_client_blocked_ratio.labels(client=client_name).set(ratio)

        g_querylog_entries_total.set(len(entries))
        g_querylog_blocked_detected_total.set(blocked_detected)
        g_querylog_nonblocked_detected_total.set(nonblocked_detected)
        g_querylog_unknown_blocked_state_total.set(unknown_detected)
        g_querylog_up.set(1)
    except Exception:
        g_querylog_up.set(0)

    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)


@app.route("/")
def index():
    return "ok\n"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9911)
