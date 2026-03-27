from __future__ import annotations

import pytest

from adguard_exporter.parsers.querylog import extract_blocked, extract_client, summarize_querylog


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"client": "phone"}, "phone"),
        ({"client_info": {"name": "tablet", "ip": "192.168.1.20"}}, "tablet"),
        ({"client_info": {"ip": "192.168.1.30"}}, "192.168.1.30"),
        ({"client_ip": "192.168.1.40"}, "192.168.1.40"),
        ({}, "unknown"),
    ],
)
def test_extract_client(entry, expected):
    assert extract_client(entry) == expected


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"blocked": True}, True),
        ({"blocked": False}, False),
        ({"result": {"is_filtered": True}}, True),
        ({"result": {"is_filtered": False}}, False),
        ({"reason": "filtered"}, True),
        ({"reason": "processed"}, False),
        ({"reason": "SaFeSearch"}, True),
        ({"status": "blocked"}, True),
        ({"status": "success"}, False),
        ({"reason": "weird-value", "status": "mystery"}, None),
    ],
)
def test_extract_blocked(entry, expected):
    assert extract_blocked(entry) is expected


def test_summarize_querylog_counts_clients_and_classification_states():
    entries = [
        {"client": "phone", "blocked": True},
        {"client": "phone", "blocked": False},
        {"client": "phone", "reason": "odd"},
        {"client_info": {"name": "tv"}, "result": {"is_filtered": True}},
        {"client_ip": "192.168.1.50", "status": "success"},
    ]

    summary = summarize_querylog(entries)

    assert summary.total_entries == 5
    assert summary.client_counts == {
        "phone": 3,
        "tv": 1,
        "192.168.1.50": 1,
    }
    assert summary.client_blocked_counts == {
        "phone": 1,
        "tv": 1,
    }
    assert summary.client_classified_counts == {
        "phone": 2,
        "tv": 1,
        "192.168.1.50": 1,
    }
    assert summary.blocked_detected == 2
    assert summary.nonblocked_detected == 2
    assert summary.unknown_detected == 1
