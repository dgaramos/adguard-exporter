from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class QuerylogState:
    client_counts: dict[str, int] = field(default_factory=dict)
    client_blocked_counts: dict[str, int] = field(default_factory=dict)
    client_classified_counts: dict[str, int] = field(default_factory=dict)
    blocked_detected: int = 0
    nonblocked_detected: int = 0
    unknown_detected: int = 0
    total_entries: int = 0
    recent_fingerprints: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object] | None) -> QuerylogState:
        if not isinstance(data, dict):
            return cls()

        return cls(
            client_counts=_as_int_dict(data.get("client_counts")),
            client_blocked_counts=_as_int_dict(data.get("client_blocked_counts")),
            client_classified_counts=_as_int_dict(data.get("client_classified_counts")),
            blocked_detected=_as_int(data.get("blocked_detected")),
            nonblocked_detected=_as_int(data.get("nonblocked_detected")),
            unknown_detected=_as_int(data.get("unknown_detected")),
            total_entries=_as_int(data.get("total_entries")),
            recent_fingerprints=_as_str_list(data.get("recent_fingerprints")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "client_counts": self.client_counts,
            "client_blocked_counts": self.client_blocked_counts,
            "client_classified_counts": self.client_classified_counts,
            "blocked_detected": self.blocked_detected,
            "nonblocked_detected": self.nonblocked_detected,
            "unknown_detected": self.unknown_detected,
            "total_entries": self.total_entries,
            "recent_fingerprints": self.recent_fingerprints,
        }


class StateStore(Protocol):
    def load_querylog_state(self) -> QuerylogState:
        ...

    def save_querylog_state(self, state: QuerylogState) -> None:
        ...


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _as_int_dict(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}

    result: dict[str, int] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, int) and item >= 0:
            result[key] = item
    return result


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
