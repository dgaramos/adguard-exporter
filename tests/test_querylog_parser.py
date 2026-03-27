from __future__ import annotations

import pytest

from adguard_exporter.parsers.querylog import extract_blocked, extract_client, summarize_querylog
from adguard_exporter.parsers.reason import classify_reason
from adguard_exporter.services.client_mapping import build_client_name_map


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("FilteredBlackList", True),
        ("FilteredSafeBrowsing", True),
        ("NotFilteredAllowList", False),
        ("NotFilteredNotFound", False),
        ("Rewrite", False),
        ("RewriteEtcHosts", False),
        ("", None),
        (None, None),
        ("SomethingElse", None),
    ],
)
def test_classify_reason(reason, expected):
    assert classify_reason(reason) is expected


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


def test_extract_client_uses_friendly_name_map():
    client_name_map = {"192.168.1.40": "living-room-tv"}

    assert extract_client({"client_ip": "192.168.1.40"}, client_name_map=client_name_map) == "living-room-tv"


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"blocked": True}, True),
        ({"blocked": False}, False),
        ({"result": {"is_filtered": True}}, True),
        ({"result": {"is_filtered": False}}, False),
        ({"reason": "FilteredBlackList"}, True),
        ({"reason": "NotFilteredAllowList"}, False),
        ({"reason": "Rewrite"}, False),
        ({"status": "blocked"}, True),
        ({"status": "success"}, False),
        ({"reason": "weird-value", "status": "mystery"}, None),
    ],
)
def test_extract_blocked(entry, expected):
    assert extract_blocked(entry) is expected


def test_build_client_name_map_supports_static_and_auto_clients():
    clients_payload = {
        "clients": [
            {"name": "phone", "ids": ["192.168.1.10", "aa:bb:cc"]},
        ],
        "auto_clients": [
            {"name": "tv", "ids": ["192.168.1.20"]},
        ],
    }

    assert build_client_name_map(clients_payload) == {
        "192.168.1.10": "phone",
        "aa:bb:cc": "phone",
        "192.168.1.20": "tv",
    }


def test_summarize_querylog_counts_clients_and_classification_states():
    entries = [
        {"client": "phone", "blocked": True},
        {"client": "phone", "blocked": False},
        {"client": "phone", "reason": "odd"},
        {"client_info": {"name": "tv"}, "reason": "FilteredSafeBrowsing"},
        {"client_ip": "192.168.1.50", "reason": "NotFilteredNotFound"},
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


def test_summarize_querylog_uses_client_mapping():
    summary = summarize_querylog(
        [
            {"client_ip": "192.168.1.10", "reason": "FilteredBlackList"},
            {"client_ip": "192.168.1.10", "reason": "NotFilteredAllowList"},
        ],
        client_name_map={"192.168.1.10": "dan-phone"},
    )

    assert summary.client_counts == {"dan-phone": 2}
    assert summary.client_blocked_counts == {"dan-phone": 1}
