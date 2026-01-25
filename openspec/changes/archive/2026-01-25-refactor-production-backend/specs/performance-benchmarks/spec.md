# Specification: Performance Benchmarks

**Capability**: `performance-benchmarks`
**Change Type**: ADDED
**Related Capabilities**: `api-service`

---

## ADDED Requirements

### Requirement: Performance Benchmark Suite

The system SHALL include automated performance tests to measure API throughput and latency.

**Rationale**: Production systems require documented performance characteristics. Benchmarks prevent regression during refactoring.

#### Scenario: Developer runs baseline performance benchmark

**Given**: API service is running with initialized database
**When**: Developer runs:
```bash
python tests/performance/run_benchmarks.py
```
**Then**:
- Script executes load tests using Locust (or equivalent)
- Tests measure:
  - Single KP match endpoint (`/api/match`)
  - Batch match endpoint (`/api/match/batch`)
  - Knowledge point tree endpoint (`/api/knowledge/tree`)
- Results saved to `tests/performance/results/benchmark_{timestamp}.json`
- Summary printed to console

#### Scenario: Benchmark measures QPS for single match endpoint

**Given**: Benchmark script configured with 10 concurrent users
**When**: Load test runs for 60 seconds
**Then**: Results include:
```json
{
  "endpoint": "/api/match",
  "duration_seconds": 60,
  "total_requests": 3420,
  "successful_requests": 3420,
  "failed_requests": 0,
  "qps": 57.0,
  "avg_response_time_ms": 175.3,
  "p50_response_time_ms": 162.0,
  "p95_response_time_ms": 238.0,
  "p99_response_time_ms": 287.0
}
```

#### Scenario: Benchmark detects performance regression

**Given**: Previous benchmark baseline exists
**When**: New benchmark runs after code changes
**Then**:
- Script compares current results to baseline
- If QPS drops >10% or P99 latency increases >20%, warning is printed:
  ```
  ⚠️ Performance regression detected:
  QPS: 57.0 → 48.3 (-15.3%)
  P99 Latency: 287ms → 356ms (+24.0%)
  ```
- Exit code is 1 (failure for CI integration)

---

### Requirement: Performance Target Documentation

Performance characteristics SHALL be documented for stakeholders.

**Rationale**: Users need to understand system limits for capacity planning.

#### Scenario: Performance documentation includes targets

**Given**: Benchmarks have been run on representative hardware
**When**: Developer generates performance documentation
**Then**: File `docs/performance.md` includes:

```markdown
# Performance Characteristics

**Test Environment**:
- Hardware: 4-core CPU, 8GB RAM
- Database: MySQL 8.0 (local)
- Dataset: 1000 code snippets, 50 knowledge points

## API Endpoints

| Endpoint | QPS | P99 Latency | Notes |
|----------|-----|-------------|-------|
| `/api/match` (single KP) | 57 req/s | <300ms | Dominant: tree-sitter parsing |
| `/api/match/batch` (5 KPs) | 12 req/s | <1200ms | Linear scaling with KP count |
| `/api/knowledge/tree` | 450 req/s | <50ms | Read-only, cache-friendly |

## Bottlenecks

1. **Tree-sitter AST parsing**: ~5-10ms per snippet
2. **Database query**: ~2-5ms per KP template fetch
3. **Matching algorithm**: ~2-10ms depending on candidate count

## Scaling Recommendations

- For >100 QPS: Add connection pooling (current: 10 max connections)
- For >1000 snippets: Consider caching parsed AST features
- For >10 concurrent bulk imports: Use dedicated worker pool
```

---

### Requirement: Load Testing with Locust

Performance tests SHALL use industry-standard load testing tools.

**Rationale**: Locust provides realistic concurrent user simulation and detailed metrics.

#### Scenario: Locust configuration for API load testing

**Given**: Developer wants to simulate realistic API usage
**When**: Locust script is configured:
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 seconds between requests

    @task(3)  # 3x weight (most common operation)
    def match_single_kp(self):
        self.client.post("/api/match", json={
            "kp_id": 10011,
            "top_k": 5
        })

    @task(1)
    def get_knowledge_tree(self):
        self.client.get("/api/knowledge/tree")
```
**Then**: Running `locust -f locustfile.py` simulates realistic traffic patterns

#### Scenario: Running Locust via command line

**Given**: API service is running
**When**: Developer runs:
```bash
locust -f tests/performance/locustfile.py --host http://localhost:5000 --users 10 --spawn-rate 2 --run-time 60s --headless
```
**Then**:
- 10 concurrent users spawned at rate of 2/second
- Test runs for 60 seconds
- Results printed to console and saved to CSV

---

### Requirement: Memory Profiling for Bulk Operations

Long-running operations SHALL be profiled for memory leaks.

**Rationale**: Bulk import of 1000+ files may reveal memory issues.

#### Scenario: Memory profiling during bulk import

**Given**: Developer wants to check memory usage
**When**: Bulk import runs with memory profiler:
```bash
python -m memory_profiler scripts/batch_import/import_code_repos.py --repo code_repos/large-project
```
**Then**:
- Console shows memory usage per line of code
- Peak memory usage logged
- Report saved to `tests/performance/memory_profile_{timestamp}.txt`

#### Scenario: Detecting memory leaks

**Given**: Bulk import processes 1000 files sequentially
**When**: Memory usage is monitored over time
**Then**:
- If memory grows linearly without plateau, leak is suspected
- Alert logged: "Potential memory leak detected: usage grew from 150MB → 800MB"

---

### Requirement: Continuous Performance Monitoring (CI Integration)

Performance benchmarks SHALL be runnable in CI for regression detection.

**Rationale**: Catch performance regressions before merging code changes.

**Note**: This requires GitHub hosting (as specified by user).

#### Scenario: GitHub Actions workflow for performance testing

**Given**: Project is hosted on GitHub
**When**: Pull request is opened
**Then**: GitHub Actions workflow runs:
```yaml
# .github/workflows/performance-tests.yml
name: Performance Tests

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start MySQL
        uses: mirromutth/mysql-action@v1.1
        with:
          mysql database: 'javalearningsys'
      - name: Initialize database
        run: python scripts/init_data/run_all.py
      - name: Start API
        run: python run_api.py &
      - name: Run benchmarks
        run: python tests/performance/run_benchmarks.py
      - name: Compare to baseline
        run: python tests/performance/compare_baseline.py
```
**And**: Workflow fails if performance regression detected

#### Scenario: Performance test results posted to PR

**Given**: Benchmark runs in CI
**When**: Workflow completes
**Then**: Bot comment added to PR:
```
## Performance Test Results

| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| QPS | 57.0 | 56.2 | -1.4% ✅ |
| P99 Latency | 287ms | 293ms | +2.1% ✅ |

No significant regression detected.
```

---

### Requirement: Performance Baseline Storage

Benchmark results SHALL be versioned for historical comparison.

**Rationale**: Track performance trends over multiple releases.

#### Scenario: Saving benchmark baseline

**Given**: Benchmarks run successfully
**When**: Results are committed as baseline:
```bash
python tests/performance/save_baseline.py tests/performance/results/benchmark_20260124.json
```
**Then**:
- Baseline copied to `tests/performance/baselines/v1.2.4.json`
- Git commit created: "Add performance baseline for v1.2.4"

#### Scenario: Comparing to historical baselines

**Given**: Multiple version baselines exist (v1.2.3, v1.2.4)
**When**: Developer runs:
```bash
python tests/performance/compare_baseline.py --all-versions
```
**Then**: Report shows performance evolution:
```
Version    QPS     P99 Latency
v1.2.3     48.2    310ms
v1.2.4     57.0    287ms       (+18.3% QPS, -7.4% latency)
v1.3.0     56.2    293ms       (-1.4% QPS, +2.1% latency)
```

---

## Implementation Notes

### Directory Structure
```
tests/
├── performance/
│   ├── locustfile.py                # Locust load test scenarios
│   ├── run_benchmarks.py            # Automated benchmark runner
│   ├── compare_baseline.py          # Regression detection
│   ├── save_baseline.py             # Baseline versioning
│   ├── results/                     # Raw benchmark results
│   │   └── benchmark_{timestamp}.json
│   ├── baselines/                   # Version baselines
│   │   ├── v1.2.4.json
│   │   └── v1.3.0.json
│   └── memory_profiles/             # Memory profiling results
```

### Benchmark Result Format

```json
{
  "timestamp": "2026-01-24T12:00:00Z",
  "version": "1.3.0",
  "environment": {
    "cpu_cores": 4,
    "memory_gb": 8,
    "database": "MySQL 8.0",
    "dataset_size": {
      "snippets": 1000,
      "knowledge_points": 50
    }
  },
  "endpoints": [
    {
      "name": "/api/match",
      "method": "POST",
      "qps": 57.0,
      "total_requests": 3420,
      "failed_requests": 0,
      "response_times": {
        "avg": 175.3,
        "p50": 162.0,
        "p95": 238.0,
        "p99": 287.0,
        "max": 456.0
      }
    }
  ]
}
```

### Performance Regression Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| QPS decrease | >10% | Fail CI |
| P99 latency increase | >20% | Fail CI |
| Memory leak | Linear growth >500MB | Warn |
| Error rate | >1% | Fail CI |

### Dependencies

- **Locust**: Load testing framework (`pip install locust`)
- **memory_profiler**: Memory usage tracking (`pip install memory-profiler`)
- **psutil**: System resource monitoring (`pip install psutil`)

### Testing Requirements

- Integration test: Run benchmark suite on test database
- Integration test: Compare baseline (verify no false positives)
- Unit test: Regression detection logic (mock benchmark results)
- CI test: Full workflow in GitHub Actions (on test branch)

### Performance Optimization Opportunities

Document known optimization opportunities for future work:

1. **AST Feature Caching**: Cache parsed AST for frequently queried snippets
2. **Database Query Optimization**: Add indexes on commonly filtered columns
3. **Connection Pool Tuning**: Increase max connections for high-QPS scenarios
4. **Async Request Handling**: Use async Flask (Quart) for I/O-bound operations
5. **Horizontal Scaling**: Load balance across multiple API instances

These should be documented in `docs/performance.md` under "Future Optimizations" section.
