# AGENTS.md

## Mission
Maintain `adguard_exporter` as a small, pragmatic Prometheus exporter for AdGuard Home.

The codebase should stay easy to reason about, easy to operate, and useful for Grafana dashboards without drifting into a large analytics system.

## Service Summary
The exporter:
- authenticates to the AdGuard Home API
- reads `/control/stats`
- reads `/control/querylog`
- exposes Prometheus metrics at `/metrics`

## Stack
- Python
- Flask
- `requests`
- `prometheus_client`
- Docker
- pytest for tests

## Runtime Context
- Raspberry Pi 5
- Linux
- AdGuard Home in Docker
- Prometheus scraping the exporter
- Grafana consuming Prometheus
- Loki + Alloy for logs

## Code Layout
- `adguard_exporter/app.py`: packaged Flask app
- `adguard_exporter/config.py`: environment-based configuration
- `adguard_exporter/clients/adguard.py`: AdGuard API client and session handling
- `adguard_exporter/parsers/querylog.py`: querylog parsing and blocked-state heuristics
- `adguard_exporter/metrics/exporter.py`: Prometheus metric construction and rendering
- `app.py`: thin root entrypoint for runtime compatibility
- `tests/`: parser and HTTP endpoint tests

## Primary Constraints
- Avoid overengineering.
- Prefer simple, explicit code.
- Preserve current metric compatibility when possible.
- Do not casually break dashboards.
- Treat Prometheus label cardinality as a first-class concern.
- Prefer Loki for detail and Prometheus for aggregates.

## Metric Rules
- Default to low-cardinality labels.
- Be skeptical of `client + domain` combinations.
- Do not add unbounded labels casually.
- If a metric is snapshot-based, document it clearly.
- Be careful with `_total` naming for values that are not true counters.
- New metrics must have clear Grafana or alerting value.

## Querylog Rules
- AdGuard querylog schema may vary by version.
- Parse defensively.
- Blocked-state classification may return `True`, `False`, or `None`.
- Do not hide uncertainty; expose it in debug metrics.
- Prefer deterministic heuristics over opaque logic.

## Good Change Pattern
- small refactor
- preserve behavior first
- add or update tests
- improve logging or observability when useful
- explain Prometheus and Grafana trade-offs

## Bad Change Pattern
- introducing unbounded labels
- adding complexity without operational value
- hiding parse uncertainty
- coupling future features before they are needed
- turning the exporter into a general analytics backend

## Testing Focus
Highest-value tests:
- client extraction
- blocked-state extraction
- schema variation fixtures
- querylog summarization
- `/metrics` behavior with fake clients

## Current Priorities
1. Improve querylog parsing robustness across AdGuard versions.
2. Improve error handling and internal observability.
3. Keep the package layout clean and maintainable.
4. Add more tests before changing metric semantics.
5. Revisit snapshot-derived metric naming when there is a safe migration path.

## Future Work Guidance
If adding friendly device naming:
- prefer static mapping first
- keep fallback behavior deterministic
- avoid dynamic discovery unless clearly justified

If adding top domains per client:
- keep it disabled by default
- enforce hard limits
- consider allowlists or thresholds
- document cardinality cost clearly
