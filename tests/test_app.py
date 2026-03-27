from __future__ import annotations

import adguard_exporter.app as app_module
from adguard_exporter.app import app


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

    def get_querylog(self, limit):
        assert limit == 1000
        return {
            "data": [
                {"client": "phone", "blocked": True},
                {"client": "phone", "blocked": False},
                {"client": "tablet", "status": "blocked"},
            ]
        }


class FailingStatsClient:
    def get_stats(self):
        raise RuntimeError("stats unavailable")

    def get_querylog(self, limit):
        raise AssertionError("querylog should not be called when stats fails")


def test_index_route_returns_ok():
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.data == b"ok\n"


def test_metrics_route_exposes_expected_metrics(monkeypatch):
    monkeypatch.setattr(app_module, "client", FakeAdGuardClient())

    response = app.test_client().get("/metrics")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'adguard_exporter_up 1.0' in body
    assert 'adguard_querylog_up 1.0' in body
    assert 'adguard_num_dns_queries 100.0' in body
    assert 'adguard_num_blocked_filtering 25.0' in body
    assert 'adguard_blocked_ratio 0.25' in body
    assert 'adguard_client_queries_total{client="phone"} 2.0' in body
    assert 'adguard_client_blocked_total{client="phone"} 1.0' in body
    assert 'adguard_client_blocked_ratio{client="phone"} 0.5' in body
    assert 'adguard_querylog_unknown_blocked_state_total 0.0' in body


def test_metrics_route_reports_exporter_down_when_stats_fail(monkeypatch):
    monkeypatch.setattr(app_module, "client", FailingStatsClient())

    response = app.test_client().get("/metrics")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'adguard_exporter_up 0.0' in body
    assert 'adguard_num_dns_queries' not in body
