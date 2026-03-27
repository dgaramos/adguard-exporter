from __future__ import annotations

import importlib

import pytest

from adguard_exporter.observability import get_telemetry
from adguard_exporter.state.store import QuerylogState

app_module = importlib.import_module("adguard_exporter.app")
app = app_module.app


class InMemoryStateStore:
    def __init__(self) -> None:
        self.state = QuerylogState()

    def load_querylog_state(self) -> QuerylogState:
        return self.state

    def save_querylog_state(self, state: QuerylogState) -> None:
        self.state = state


class FakeAdGuardClient:
    def get_stats(self):
        return {
            "num_dns_queries": 100,
            "num_blocked_filtering": 25,
            "avg_processing_time": 0.015,
            "dns_queries": [10, 20],
            "blocked_filtering": [3, 4],
            "top_queried_domains": [{"example.com": 12}],
            "top_clients": [{"phone": 30}],
            "top_blocked_domains": [{"ads.example": 8}],
            "top_upstreams_responses": [{"1.1.1.1": 50}],
            "top_upstreams_avg_time": [{"1.1.1.1": 0.01}],
        }

    def get_clients(self):
        return {
            "clients": [
                {"name": "dan-phone", "ids": ["192.168.1.10"]},
            ],
            "auto_clients": [],
        }

    def get_querylog(self, limit):
        assert limit == 1000
        return {
            "data": [
                {"time": 1710000000, "client_ip": "192.168.1.10", "reason": "FilteredBlackList", "question": {"host": "ads.example"}},
                {"time": 1710000001, "client_ip": "192.168.1.10", "reason": "NotFilteredAllowList", "question": {"host": "example.com"}},
                {"time": 1710000002, "client": "tablet", "reason": "FilteredSafeBrowsing", "question": {"host": "tracking.example"}},
            ]
        }


class QuerylogWithoutClientsClient(FakeAdGuardClient):
    def get_clients(self):
        raise RuntimeError("clients unavailable")


class FailingStatsClient:
    def get_stats(self):
        raise RuntimeError("stats unavailable")

    def get_querylog(self, limit):
        raise AssertionError("querylog should not be called when stats fails")


@pytest.fixture(autouse=True)
def reset_telemetry():
    get_telemetry().reset()
    yield
    get_telemetry().reset()


def test_index_route_returns_ok():
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.data == b"ok\n"


def test_metrics_route_exposes_expected_metrics(monkeypatch):
    monkeypatch.setattr(app_module, "client", FakeAdGuardClient())
    monkeypatch.setattr(app_module, "state_store", InMemoryStateStore())

    response = app.test_client().get("/metrics")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'adguard_exporter_up 1.0' in body
    assert 'adguard_querylog_up 1.0' in body
    assert 'adguard_num_dns_queries 100.0' in body
    assert 'adguard_num_blocked_filtering 25.0' in body
    assert 'adguard_blocked_ratio 0.25' in body

    assert 'adguard_client_queries_total{client="dan-phone"} 2.0' in body
    assert 'adguard_client_blocked_total{client="dan-phone"} 1.0' in body
    assert 'adguard_client_blocked_ratio{client="dan-phone"} 0.5' in body

    assert 'adguard_client_queries_processed_total{client="dan-phone"} 2.0' in body
    assert 'adguard_client_blocked_processed_total{client="dan-phone"} 1.0' in body
    assert 'adguard_client_blocked_processed_ratio{client="dan-phone"} 0.5' in body

    assert 'adguard_querylog_entries_total 3.0' in body
    assert 'adguard_querylog_entries_processed_total 3.0' in body
    assert 'adguard_querylog_unknown_blocked_state_total 0.0' in body
    assert 'adguard_exporter_last_scrape_duration_seconds ' in body
    assert 'adguard_exporter_last_stats_duration_seconds ' in body
    assert 'adguard_exporter_last_querylog_duration_seconds ' in body
    assert 'adguard_exporter_api_request_failures_total{endpoint="stats"} 0.0' in body
    assert 'adguard_exporter_processing_failures_total{stage="querylog"} 0.0' in body
    assert 'adguard_exporter_state_operation_failures_total{operation="load"} 0.0' in body


def test_metrics_route_keeps_cumulative_counts_across_duplicate_snapshots(monkeypatch):
    monkeypatch.setattr(app_module, "client", FakeAdGuardClient())
    monkeypatch.setattr(app_module, "state_store", InMemoryStateStore())

    first_response = app.test_client().get("/metrics")
    second_response = app.test_client().get("/metrics")

    first_body = first_response.get_data(as_text=True)
    second_body = second_response.get_data(as_text=True)

    assert 'adguard_client_queries_total{client="dan-phone"} 2.0' in first_body
    assert 'adguard_client_queries_total{client="dan-phone"} 2.0' in second_body
    assert 'adguard_client_queries_processed_total{client="dan-phone"} 2.0' in second_body
    assert 'adguard_querylog_entries_total 3.0' in second_body
    assert 'adguard_querylog_entries_processed_total 3.0' in second_body


def test_metrics_route_falls_back_without_clients_mapping(monkeypatch):
    monkeypatch.setattr(app_module, "client", QuerylogWithoutClientsClient())
    monkeypatch.setattr(app_module, "state_store", InMemoryStateStore())

    response = app.test_client().get("/metrics")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'adguard_querylog_up 1.0' in body
    assert 'adguard_client_queries_total{client="192.168.1.10"} 2.0' in body
    assert 'adguard_client_queries_processed_total{client="192.168.1.10"} 2.0' in body


def test_metrics_route_reports_exporter_down_when_stats_fail(monkeypatch):
    monkeypatch.setattr(app_module, "client", FailingStatsClient())
    monkeypatch.setattr(app_module, "state_store", InMemoryStateStore())

    response = app.test_client().get("/metrics")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'adguard_exporter_up 0.0' in body
    assert 'adguard_num_dns_queries 0.0' in body
    assert 'adguard_num_blocked_filtering 0.0' in body
    assert 'adguard_exporter_processing_failures_total{stage="stats"} 1.0' in body
