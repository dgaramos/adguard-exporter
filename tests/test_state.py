from __future__ import annotations

from pathlib import Path

from adguard_exporter.collectors.querylog import build_querylog_fingerprint, process_querylog_incrementally
from adguard_exporter.state.file import FileStateStore
from adguard_exporter.state.store import QuerylogState


def test_build_querylog_fingerprint_uses_stable_fields():
    fingerprint = build_querylog_fingerprint(
        {
            "time": 1710000000,
            "client_ip": "192.168.1.10",
            "question": {"host": "example.com"},
            "reason": "FilteredBlackList",
            "status": "blocked",
        }
    )

    assert fingerprint == "1710000000|192.168.1.10|example.com|FilteredBlackList|blocked|"


def test_process_querylog_incrementally_skips_duplicate_snapshot_entries():
    entries = [
        {"time": 1710000000, "client_ip": "192.168.1.10", "reason": "FilteredBlackList", "question": {"host": "example.com"}},
        {"time": 1710000001, "client_ip": "192.168.1.10", "reason": "NotFilteredAllowList", "question": {"host": "example.com"}},
    ]

    first_state = process_querylog_incrementally(
        entries=entries,
        state=QuerylogState(),
        client_name_map={"192.168.1.10": "dan-phone"},
        recent_fingerprints_limit=10,
    )
    second_state = process_querylog_incrementally(
        entries=entries,
        state=first_state,
        client_name_map={"192.168.1.10": "dan-phone"},
        recent_fingerprints_limit=10,
    )

    assert first_state.client_counts == {"dan-phone": 2}
    assert first_state.client_blocked_counts == {"dan-phone": 1}
    assert first_state.client_classified_counts == {"dan-phone": 2}
    assert first_state.total_entries == 2
    assert second_state.client_counts == {"dan-phone": 2}
    assert second_state.total_entries == 2


def test_process_querylog_incrementally_accumulates_only_new_entries():
    initial_state = process_querylog_incrementally(
        entries=[
            {"time": 1710000000, "client_ip": "192.168.1.10", "reason": "FilteredBlackList", "question": {"host": "example.com"}},
        ],
        state=QuerylogState(),
        client_name_map={"192.168.1.10": "dan-phone"},
        recent_fingerprints_limit=10,
    )

    next_state = process_querylog_incrementally(
        entries=[
            {"time": 1710000000, "client_ip": "192.168.1.10", "reason": "FilteredBlackList", "question": {"host": "example.com"}},
            {"time": 1710000001, "client_ip": "192.168.1.10", "reason": "NotFilteredAllowList", "question": {"host": "example.org"}},
            {"time": 1710000002, "client": "tablet", "reason": "FilteredSafeBrowsing", "question": {"host": "ads.example"}},
        ],
        state=initial_state,
        recent_fingerprints_limit=10,
    )

    assert next_state.client_counts == {"dan-phone": 2, "tablet": 1}
    assert next_state.client_blocked_counts == {"dan-phone": 1, "tablet": 1}
    assert next_state.client_classified_counts == {"dan-phone": 2, "tablet": 1}
    assert next_state.total_entries == 3


def test_file_state_store_persists_querylog_state(tmp_path: Path):
    store = FileStateStore(str(tmp_path / "querylog-state.json"), recent_fingerprints_limit=3)
    state = QuerylogState(
        client_counts={"dan-phone": 2},
        client_blocked_counts={"dan-phone": 1},
        client_classified_counts={"dan-phone": 2},
        blocked_detected=1,
        nonblocked_detected=1,
        unknown_detected=0,
        total_entries=2,
        recent_fingerprints=["1", "2", "3", "4"],
    )

    store.save_querylog_state(state)
    loaded_state = store.load_querylog_state()

    assert loaded_state.client_counts == {"dan-phone": 2}
    assert loaded_state.client_blocked_counts == {"dan-phone": 1}
    assert loaded_state.total_entries == 2
    assert loaded_state.recent_fingerprints == ["2", "3", "4"]
