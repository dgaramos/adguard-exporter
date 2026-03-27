from __future__ import annotations

from adguard_exporter.parsers.querylog import extract_blocked, extract_client
from adguard_exporter.state.store import QuerylogState


_FINGERPRINT_SEPARATOR = "|"


def process_querylog_incrementally(
    entries: list[dict[str, object]],
    state: QuerylogState,
    client_name_map: dict[str, str] | None = None,
    recent_fingerprints_limit: int = 5000,
) -> QuerylogState:
    recent_fingerprints_limit = max(recent_fingerprints_limit, 1)

    client_counts = dict(state.client_counts)
    client_blocked_counts = dict(state.client_blocked_counts)
    client_classified_counts = dict(state.client_classified_counts)

    blocked_detected = state.blocked_detected
    nonblocked_detected = state.nonblocked_detected
    unknown_detected = state.unknown_detected
    total_entries = state.total_entries

    recent_fingerprints = list(state.recent_fingerprints)
    recent_fingerprint_set = set(recent_fingerprints)

    for entry in entries:
        fingerprint = build_querylog_fingerprint(entry)
        if fingerprint in recent_fingerprint_set:
            continue

        recent_fingerprints.append(fingerprint)
        recent_fingerprint_set.add(fingerprint)

        while len(recent_fingerprints) > recent_fingerprints_limit:
            removed = recent_fingerprints.pop(0)
            recent_fingerprint_set.discard(removed)

        client_name = extract_client(entry, client_name_map=client_name_map)
        blocked_state = extract_blocked(entry)

        client_counts[client_name] = client_counts.get(client_name, 0) + 1
        total_entries += 1

        if blocked_state is True:
            client_blocked_counts[client_name] = client_blocked_counts.get(client_name, 0) + 1
            client_classified_counts[client_name] = client_classified_counts.get(client_name, 0) + 1
            blocked_detected += 1
        elif blocked_state is False:
            client_classified_counts[client_name] = client_classified_counts.get(client_name, 0) + 1
            nonblocked_detected += 1
        else:
            unknown_detected += 1

    return QuerylogState(
        client_counts=client_counts,
        client_blocked_counts=client_blocked_counts,
        client_classified_counts=client_classified_counts,
        blocked_detected=blocked_detected,
        nonblocked_detected=nonblocked_detected,
        unknown_detected=unknown_detected,
        total_entries=total_entries,
        recent_fingerprints=recent_fingerprints,
    )


def build_querylog_fingerprint(entry: dict[str, object]) -> str:
    timestamp = _extract_timestamp(entry)
    raw_client = extract_client(entry)
    domain = _extract_domain(entry)
    reason = _as_normalized_string(entry.get("reason"))
    status = _as_normalized_string(entry.get("status"))
    blocked = _as_normalized_string(entry.get("blocked"))

    fingerprint = _FINGERPRINT_SEPARATOR.join((timestamp, raw_client, domain, reason, status, blocked))
    if fingerprint != _FINGERPRINT_SEPARATOR.join(("", "", "", "", "", "")):
        return fingerprint
    return str(entry)


def _extract_timestamp(entry: dict[str, object]) -> str:
    for key in ("time", "timestamp", "ts"):
        value = entry.get(key)
        normalized = _as_normalized_string(value)
        if normalized:
            return normalized
    return ""


def _extract_domain(entry: dict[str, object]) -> str:
    question = entry.get("question")
    if isinstance(question, dict):
        for key in ("host", "name"):
            value = question.get(key)
            normalized = _as_normalized_string(value)
            if normalized:
                return normalized
    elif isinstance(question, str):
        normalized = _as_normalized_string(question)
        if normalized:
            return normalized

    for key in ("qhost", "domain", "host"):
        normalized = _as_normalized_string(entry.get(key))
        if normalized:
            return normalized

    return ""


def _as_normalized_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
