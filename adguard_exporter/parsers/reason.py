from __future__ import annotations


def classify_reason(reason: object) -> bool | None:
    normalized = str(reason or "").strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    if lowered.startswith("filtered"):
        return True
    if lowered.startswith("notfiltered"):
        return False
    if lowered.startswith("rewrite"):
        return False

    return None
