Adapters live here to keep the pipeline loosely coupled.
- Keep shared adapter modules (config, registries, cli/time helpers) in this folder.
- When adding a new external integration, prefer an adapter module over wiring it directly into tools.
- If you move adapters, update imports in tools/* and scripts/* accordingly.
