from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class QuerylogSummary:
    client_counts: dict[str, int]
    client_blocked_counts: dict[str, int]
    client_classified_counts: dict[str, int]
    blocked_detected: int
    nonblocked_detected: int
    unknown_detected: int
    total_entries: int


def extract_client(entry: dict[str, Any]) -> str:
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


def extract_blocked(entry: dict[str, Any]) -> bool | None:
    if isinstance(entry.get("blocked"), bool):
        return entry["blocked"]

    result = entry.get("result")
    if isinstance(result, dict):
        is_filtered = result.get("is_filtered")
        if isinstance(is_filtered, bool):
            return is_filtered

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

    status = str(entry.get("status", "")).strip().lower()
    if status in {"blocked", "filtered"}:
        return True
    if status in {"processed", "ok", "success", "answered", "cached"}:
        return False

    return None


def summarize_querylog(entries: list[dict[str, Any]]) -> QuerylogSummary:
    client_counts: dict[str, int] = {}
    client_blocked_counts: dict[str, int] = {}
    client_classified_counts: dict[str, int] = {}

    blocked_detected = 0
    nonblocked_detected = 0
    unknown_detected = 0

    for entry in entries:
        client_name = extract_client(entry)
        blocked_state = extract_blocked(entry)

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

    return QuerylogSummary(
        client_counts=client_counts,
        client_blocked_counts=client_blocked_counts,
        client_classified_counts=client_classified_counts,
        blocked_detected=blocked_detected,
        nonblocked_detected=nonblocked_detected,
        unknown_detected=unknown_detected,
        total_entries=len(entries),
    )
