from __future__ import annotations

from flask import Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

from adguard_exporter.clients.adguard import AdGuardClient
from adguard_exporter.collectors.querylog import process_querylog_incrementally
from adguard_exporter.services.client_mapping import build_client_name_map
from adguard_exporter.state.store import StateStore


def _set_top_map(metric: Gauge, items: list[dict[str, int]]) -> None:
    metric.clear()
    for item in items:
        for key, value in item.items():
            metric.labels(name=key).set(value)


def _set_top_map_custom_label(metric: Gauge, items: list[dict[str, float | int]], label_name: str) -> None:
    metric.clear()
    for item in items:
        for key, value in item.items():
            metric.labels(**{label_name: key}).set(value)


def build_metrics_response(
    client: AdGuardClient,
    querylog_limit: int,
    state_store: StateStore,
    recent_fingerprints_limit: int,
) -> Response:
    registry = CollectorRegistry()

    g_num_dns_queries = Gauge("adguard_num_dns_queries", "Total DNS queries", registry=registry)
    g_num_blocked = Gauge("adguard_num_blocked_filtering", "Total blocked DNS queries", registry=registry)
    g_avg_processing = Gauge("adguard_avg_processing_time_seconds", "Average DNS processing time in seconds", registry=registry)
    g_blocked_ratio = Gauge("adguard_blocked_ratio", "Blocked DNS ratio (0..1)", registry=registry)

    g_dns_queries_hour = Gauge("adguard_dns_queries_hour", "DNS queries by hour", ["hour"], registry=registry)
    g_blocked_hour = Gauge("adguard_blocked_filtering_hour", "Blocked DNS queries by hour", ["hour"], registry=registry)

    g_top_domain = Gauge("adguard_top_queried_domain_queries", "Top queried domains", ["name"], registry=registry)
    g_top_client = Gauge("adguard_top_client_queries", "Top clients", ["name"], registry=registry)
    g_top_blocked = Gauge("adguard_top_blocked_domain_queries", "Top blocked domains", ["name"], registry=registry)

    g_top_upstream_responses = Gauge("adguard_top_upstream_responses", "Top upstream responses", ["upstream"], registry=registry)
    g_top_upstream_avg_time = Gauge("adguard_top_upstream_avg_time_seconds", "Upstream avg time", ["upstream"], registry=registry)

    g_client_queries = Gauge(
        "adguard_client_queries_total",
        "Compatibility alias for processed queries per client from querylog",
        ["client"],
        registry=registry,
    )
    g_client_blocked = Gauge(
        "adguard_client_blocked_total",
        "Compatibility alias for processed blocked queries per client from querylog",
        ["client"],
        registry=registry,
    )
    g_client_blocked_ratio = Gauge(
        "adguard_client_blocked_ratio",
        "Compatibility alias for processed blocked ratio per client from querylog",
        ["client"],
        registry=registry,
    )

    g_client_queries_processed = Gauge(
        "adguard_client_queries_processed_total",
        "Queries per client processed from querylog",
        ["client"],
        registry=registry,
    )
    g_client_blocked_processed = Gauge(
        "adguard_client_blocked_processed_total",
        "Blocked queries per client processed from querylog",
        ["client"],
        registry=registry,
    )
    g_client_blocked_ratio_processed = Gauge(
        "adguard_client_blocked_processed_ratio",
        "Blocked ratio per client from processed querylog entries",
        ["client"],
        registry=registry,
    )

    g_exporter_up = Gauge("adguard_exporter_up", "Exporter status", registry=registry)
    g_querylog_up = Gauge("adguard_querylog_up", "Querylog collection status", registry=registry)
    g_querylog_entries_total = Gauge(
        "adguard_querylog_entries_total",
        "Compatibility alias for total processed querylog entries",
        registry=registry,
    )
    g_querylog_entries_processed = Gauge(
        "adguard_querylog_entries_processed_total",
        "Total querylog entries processed incrementally",
        registry=registry,
    )
    g_querylog_blocked_detected_total = Gauge("adguard_querylog_blocked_detected_total", "Entries confidently detected as blocked", registry=registry)
    g_querylog_nonblocked_detected_total = Gauge("adguard_querylog_nonblocked_detected_total", "Entries confidently detected as non-blocked", registry=registry)
    g_querylog_unknown_blocked_state_total = Gauge("adguard_querylog_unknown_blocked_state_total", "Entries where blocked state could not be determined", registry=registry)

    try:
        stats = client.get_stats()

        num_dns_queries = float(stats.get("num_dns_queries", 0))
        num_blocked = float(stats.get("num_blocked_filtering", 0))
        avg_processing_time = float(stats.get("avg_processing_time", 0))

        g_num_dns_queries.set(num_dns_queries)
        g_num_blocked.set(num_blocked)
        g_avg_processing.set(avg_processing_time)
        g_blocked_ratio.set((num_blocked / num_dns_queries) if num_dns_queries > 0 else 0)

        for idx, value in enumerate(stats.get("dns_queries", [])):
            g_dns_queries_hour.labels(hour=str(idx)).set(value)

        for idx, value in enumerate(stats.get("blocked_filtering", [])):
            g_blocked_hour.labels(hour=str(idx)).set(value)

        _set_top_map(g_top_domain, stats.get("top_queried_domains", []))
        _set_top_map(g_top_client, stats.get("top_clients", []))
        _set_top_map(g_top_blocked, stats.get("top_blocked_domains", []))
        _set_top_map_custom_label(g_top_upstream_responses, stats.get("top_upstreams_responses", []), "upstream")
        _set_top_map_custom_label(g_top_upstream_avg_time, stats.get("top_upstreams_avg_time", []), "upstream")

        g_exporter_up.set(1)
    except Exception:
        g_exporter_up.set(0)
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    try:
        client_name_map: dict[str, str] = {}
        try:
            client_name_map = build_client_name_map(client.get_clients())
        except Exception:
            client_name_map = {}

        querylog = client.get_querylog(limit=querylog_limit)
        entries = querylog.get("data", [])

        current_state = state_store.load_querylog_state()
        next_state = process_querylog_incrementally(
            entries=entries,
            state=current_state,
            client_name_map=client_name_map,
            recent_fingerprints_limit=recent_fingerprints_limit,
        )
        state_store.save_querylog_state(next_state)

        g_client_queries.clear()
        g_client_blocked.clear()
        g_client_blocked_ratio.clear()
        g_client_queries_processed.clear()
        g_client_blocked_processed.clear()
        g_client_blocked_ratio_processed.clear()

        for client_name, total in next_state.client_counts.items():
            blocked_total = next_state.client_blocked_counts.get(client_name, 0)
            classified_total = next_state.client_classified_counts.get(client_name, 0)
            ratio = (blocked_total / classified_total) if classified_total > 0 else 0

            g_client_queries.labels(client=client_name).set(total)
            g_client_blocked.labels(client=client_name).set(blocked_total)
            g_client_blocked_ratio.labels(client=client_name).set(ratio)

            g_client_queries_processed.labels(client=client_name).set(total)
            g_client_blocked_processed.labels(client=client_name).set(blocked_total)
            g_client_blocked_ratio_processed.labels(client=client_name).set(ratio)

        g_querylog_entries_total.set(next_state.total_entries)
        g_querylog_entries_processed.set(next_state.total_entries)
        g_querylog_blocked_detected_total.set(next_state.blocked_detected)
        g_querylog_nonblocked_detected_total.set(next_state.nonblocked_detected)
        g_querylog_unknown_blocked_state_total.set(next_state.unknown_detected)
        g_querylog_up.set(1)
    except Exception:
        g_querylog_up.set(0)

    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)
