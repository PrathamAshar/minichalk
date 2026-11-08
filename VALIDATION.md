# Validation record

Measured in the supplied WSL workspace on 2026-11-07 with Python 3.14.7. Backend tests and benchmarks ran outside the restricted sandbox: an isolated in-memory aiosqlite connection hangs in that sandbox because its worker-thread callback cannot wake the loop.

## Backend

16 tests passed in 4.25s. Starlette emitted one dependency deprecation warning about its TestClient's httpx integration. No paid services or remote data sources are used.

## Benchmarks

20 measured iterations per mode, excluding HTTP and trace persistence. Full raw results: [benchmarks/results.json](benchmarks/results.json).

| Workload | Mode | Median | P95 | Executed features/query | Cache hit rate |
| --- | --- | ---: | ---: | ---: | ---: |
| Artificial 120ms I/O | Sequential, cold | 250.221 ms | 253.492 ms | 9 | 0% |
| Artificial 120ms I/O | Concurrent, cold | 125.949 ms | 126.915 ms | 9 | 0% |
| Artificial 120ms I/O | Concurrent, warm | 0.244 ms | 0.295 ms | 0 | 100% |
| Local SQLite, no artificial delay | Sequential, cold | 7.040 ms | 9.402 ms | 9 | 0% |
| Local SQLite, no artificial delay | Concurrent, cold | 5.008 ms | 5.714 ms | 9 | 0% |
| Local SQLite, no artificial delay | Concurrent, warm | 0.124 ms | 0.180 ms | 0 | 100% |

Cold concurrency speedup: 1.99× with artificial I/O, 1.41× for this local SQLite workload. These results demonstrate behavior on one machine, not production service latency.

## Frontend and integration

- Strict TypeScript check: passed.
- ESLint: passed without warnings after fixing the PostCSS export.
- Next.js production build: passed with Webpack; all four console routes prerendered successfully.
- npm audit: zero vulnerabilities after a scoped override of the ESLint toolchain's minimatch dependency.
- Chrome desktop (1440 × 1000) and mobile (390 × 844) smoke workflow: passed, with no browser exceptions or mobile document overflow.
- Browser workflow verified all four pages, cache invalidation, cold/warm/bypassed queries, actual I/O overlap, multiple outputs, lower score for the normal entity, feature search, and trace timelines.
- Observed browser workflow values: Nova 95.7, Ada 5.82; cold engine duration 145.21 ms, warm 0.412 ms. These individual observations are separate from the benchmark sample.

Screenshots are saved in [docs/screenshots](docs/screenshots). The optional reusable browser driver is `frontend/scripts/smoke.mjs`.

The documented `make check`, `make types`, and `make dev` commands were verified directly in the repository. The full smoke workflow also passed against `make dev`; its additional observation was 141.43 ms cold and 0.290 ms warm. Development mode can emit a React Flow size warning as a graph unmounts during navigation; screenshots and the mobile overflow check passed.
