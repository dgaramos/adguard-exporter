from __future__ import annotations

from typing import Any


def build_client_name_map(clients_data: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}

    for group_key in ("clients", "auto_clients"):
        clients = clients_data.get(group_key, [])
        if not isinstance(clients, list):
            continue

        for item in clients:
            if not isinstance(item, dict):
                continue

            name = item.get("name")
            if not isinstance(name, str) or not name:
                continue

            ids = item.get("ids", [])
            if isinstance(ids, list):
                for raw_id in ids:
                    if isinstance(raw_id, str) and raw_id:
                        mapping[raw_id] = name

            ip = item.get("ip")
            if isinstance(ip, str) and ip:
                mapping[ip] = name

    return mapping


def resolve_client_name(raw_client: str, client_name_map: dict[str, str] | None = None) -> str:
    if client_name_map and raw_client in client_name_map:
        return client_name_map[raw_client]
    return raw_client
