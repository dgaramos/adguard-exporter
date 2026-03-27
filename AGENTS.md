# AGENTS.md

## Mission
Maintain `adguard_exporter` as a small, pragmatic Prometheus exporter for AdGuard Home.

The codebase should stay easy to reason about, easy to operate, and useful for Grafana dashboards without drifting into a large analytics system.

## Service Summary
The exporter:
- authenticates to the AdGuard Home API
- reads `/control/stats`
- reads `/control/querylog`
- reads `/control/clients`
- persists local querylog processing state
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
- `adguard_exporter/parsers/reason.py`: explicit reason-based classification
- `adguard_exporter/collectors/querylog.py`: incremental querylog processing and deduplication
- `adguard_exporter/services/client_mapping.py`: friendly device name mapping
- `adguard_exporter/state/`: persisted querylog state
- `adguard_exporter/metrics/exporter.py`: Prometheus metric construction and rendering
- `dashboards/grafana/`: shipped Grafana dashboards for overview and device-level visibility
- `app.py`: thin root entrypoint for runtime compatibility
- `tests/`: parser, state, and HTTP endpoint tests

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
- Be careful with `_total` naming for values that are not true counters.
- New metrics must have clear Grafana or alerting value.
- Querylog-derived metrics are now exporter-processed cumulative values, not raw snapshot counters.

## Querylog Rules
- AdGuard querylog schema may vary by version.
- Parse defensively.
- Blocked-state classification may return `True`, `False`, or `None`.
- Do not hide uncertainty; expose it in debug metrics.
- Prefer deterministic heuristics over opaque logic.
- Treat `/control/querylog` as a rolling snapshot source and use persisted state for cumulative metrics.

## State Rules
- Querylog-derived counters depend on persisted local state.
- State resets must be treated as semantic counter resets.
- Deduplication should remain bounded and simple.
- Do not introduce heavy storage systems unless there is a strong operational reason.

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
- incremental deduplication behavior
- persisted state loading/saving
- `/metrics` behavior with fake clients and fake state stores

## Current Priorities
1. Improve querylog parsing robustness across AdGuard versions.
2. Improve error handling and internal observability.
3. Keep the package layout clean and maintainable.
4. Add more tests before changing metric semantics.
5. Revisit metric naming and docs now that querylog-derived values are stateful.

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
