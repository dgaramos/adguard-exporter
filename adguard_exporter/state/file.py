from __future__ import annotations

import json
import os
from pathlib import Path

from adguard_exporter.state.store import QuerylogState


class FileStateStore:
    def __init__(self, path: str, recent_fingerprints_limit: int = 5000) -> None:
        self.path = Path(path)
        self.recent_fingerprints_limit = max(recent_fingerprints_limit, 1)

    def load_querylog_state(self) -> QuerylogState:
        if not self.path.exists():
            return QuerylogState()

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return QuerylogState()

        state = QuerylogState.from_dict(payload)
        if len(state.recent_fingerprints) > self.recent_fingerprints_limit:
            state.recent_fingerprints = state.recent_fingerprints[-self.recent_fingerprints_limit :]
        return state

    def save_querylog_state(self, state: QuerylogState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = state.to_dict()
        payload["recent_fingerprints"] = state.recent_fingerprints[-self.recent_fingerprints_limit :]

        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
        os.replace(temp_path, self.path)
