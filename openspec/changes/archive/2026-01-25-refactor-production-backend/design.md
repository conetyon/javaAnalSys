# Design Document: Production Backend Refactoring

**Change ID**: `refactor-production-backend`
**Version**: 1.0
**Last Updated**: 2026-01-24

## 1. Architecture Overview

### 1.1 Current State Analysis

**Keep (Good Parts)**:
- Service layer (`src/services/`) - solid business logic
- Matching algorithms (`src/matching/`) - proven accuracy (94.74%)
- Java analyzer (`src/java_analyzer/`) - tree-sitter integration works well
- Connection pooling via MySQLClient
- Evaluation framework structure (metrics, baselines)

**Replace Completely (Design Flaws)**:
- Entry points (main.py, run_api.py) - will be rewritten from scratch
- Scripts (offline_tasks.py) - delete and replace with modular design
- Experiment tracking - current markdown-only approach lacks structure

**Design Constraint from Stakeholder**:
- **No legacy preservation required** - prioritize clean design over compatibility
- **Database must be deterministic** - same input = same database state every time
- **System must be runnable** - no broken states, no manual fixes needed

### 1.2 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Entry Points                          │
│  run_api.py (API)  │  init_data.sh  │  run_experiments.py  │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼──────────┐
│   API Module    │  │  Init Scripts  │  │   Experiments    │
│   (api/)        │  │  (scripts/     │  │   (experiments/) │
│                 │  │   init_data/)  │  │                  │
│ • Routes        │  │                │  │ • Dataset loader │
│ • Schemas       │  │ • load_kp.py   │  │ • Tracking       │
│ • Middleware    │  │ • import_code  │  │ • Baselines      │
└────────┬────────┘  └───────┬────────┘  └───────┬──────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Service Layer   │
                    │   (src/services/) │
                    │                   │
                    │ • SearchService   │
                    │ • KnowledgeServ.  │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼──────────┐
│  DB Manager     │  │ Java Analyzer  │  │ Matching Engine  │
│  (src/db_mgr/)  │  │ (src/java_ana) │  │ (src/matching/)  │
└─────────────────┘  └────────────────┘  └──────────────────┘
```

### 1.3 Key Design Decisions

#### Decision 1: Scripts Directory Reorganization

**Current**: `scripts/offline_tasks.py` (monolithic, 400+ lines)

**Proposed**:
```
scripts/
├── init_data/
│   ├── load_knowledge_points.py    # Load kp_dml.sql
│   ├── import_sample_code.py       # Analyze sample_code.java
│   └── run_all.py                  # Orchestrator
├── batch_import/
│   ├── import_code_repos.py        # Bulk Java project import
│   └── config.yaml                 # Import settings
└── experiments/
    ├── run_evaluation.py           # Moved from scripts/
    └── baselines.py                # Extracted baselines
```

**Rationale**:
- Clear separation of concerns (init vs batch vs experiments)
- Each script < 200 lines, single responsibility
- Easier to maintain and test independently

#### Decision 2: Configuration Unification

**Current**:
- `config.py` (root): Extracts DB name from YAML
- `config/db.yaml`: Database connection params
- `config/logger.yaml`: Logging config
- `lib/globals/__init__.py`: Lazy-loads into `Cfg` singleton

**Proposed**: Keep current structure (no changes needed)

**Rationale**:
- Current design already follows best practices
- `lib/globals/` provides clean singleton access
- No benefit to changing (would be refactoring for refactoring's sake)

#### Decision 3: Bulk Code Import Design

**Requirements**:
1. User drops multiple Java projects into `code_repos/`
2. Single command imports all projects
3. Idempotent (safe to re-run)
4. Progress tracking (console output)

**Implementation Approach**:
```python
# scripts/batch_import/import_code_repos.py
def import_projects(root_dir: str):
    """
    Scans root_dir for .java files, analyzes each,
    saves to code_snippets table.
    """
    projects = discover_java_projects(root_dir)
    for project in projects:
        java_files = find_java_files(project)
        for file in java_files:
            # Reuse existing analyzer
            snippets = analyze_code_file(file)
            save_snippets_to_db(snippets)
```

**File Discovery Strategy**:
- Walk directory tree, find `.java` files
- Skip `test/`, `target/`, `.git/` directories
- Log skipped files (e.g., compile errors)

**Idempotency** (Strong Requirement from Stakeholder):
- Hash file content + file path as unique key
- Use `REPLACE INTO` based on content_hash (deterministic: same files = same DB state)
- Every script run produces identical database state (critical requirement)

#### Decision 4: Experiment Framework Enhancement

**Current State**:
- Ground truth: 19 test cases, 30 snippets (tests/fixtures/ground_truth.json)
- Baselines: TF-IDF, Pure AST, Random (tests/evaluation/baselines.py)
- Metrics: P@K, R@K, MRR, Top-1 Acc (tests/evaluation/metrics.py)
- Output: Markdown report (tests/evaluation_results/report.md)

**Proposed Enhancements**:

1. **Dataset Integration**:
   ```
   experiments/
   ├── datasets/
   │   ├── loaders/
   │   │   ├── codesearchnet.py
   │   │   └── codexglue.py
   │   ├── cache/                    # Downloaded datasets
   │   └── processed/                # Preprocessed for system
   ```

2. **Experiment Tracking**:
   ```python
   # experiments/tracking.py
   class ExperimentRun:
       def __init__(self, name, config):
           self.name = name
           self.config = config
           self.metrics = {}

       def log_metric(self, name, value):
           self.metrics[name] = value

       def save(self):
           # Save to experiments/runs/{name}/
           # - config.json
           # - metrics.json
           # - predictions.csv
   ```

3. **Report Generation**:
   - Keep markdown output (human-readable)
   - Add JSON export (machine-readable)
   - Add CSV raw predictions (for analysis)

**Dataset Choice**: Start with **CodeSearchNet Java subset**
- Reason: Well-documented, widely used, ~164K Java methods
- Preprocessing needed: Extract method-level snippets → knowledge point labels
- Labeling strategy: Use existing ground truth as seed, expand with heuristics

#### Decision 5: API Versioning Strategy

**Requirement**: Support future frontend integration without breaking existing clients

**Chosen Approach**: **No explicit versioning** - maintain backward compatibility through careful API design

**Rationale**:
- Graduation project scope - single major release cycle
- API is new (v1.2.4), no legacy clients to support
- Easier to maintain single API surface
- Can introduce versioning later if needed

**Backward Compatibility Guidelines**:
- Never remove fields from responses (only add)
- Optional request parameters only (never require new fields)
- Keep existing endpoint paths unchanged (`/api/match`, `/api/knowledge/tree`)
- New features use new endpoints (`/api/bulk-import`, not `/api/import-v2`)

#### Decision 6: Performance Benchmarking

**Targets to Define**:

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| QPS (single KP match) | TBD | Locust load test |
| P99 latency | TBD | Percentile from load test |
| Throughput (bulk import) | TBD | Time to import 1000 files |
| Memory usage (API) | TBD | Docker stats during load |

**Benchmarking Approach**:
1. Create `tests/performance/` directory
2. Use Locust (Python load testing) for API benchmarks
3. Measure before/after refactoring (regression detection)
4. Document results in `docs/performance.md`

**Realistic Target Estimation**:
- Tree-sitter parsing: ~5-10ms per file (empirical)
- Database query: ~1-5ms (local MySQL)
- Matching algorithm: ~2-10ms (depends on candidate count)
- **Estimated QPS**: 50-100 req/s (single worker, single KP match)
- **Estimated P99 latency**: <100ms (95% confidence target)

#### Decision 7: Sync vs Async Task Scheduling

**Decision**: **Async for slow operations, sync for fast queries**

**Rationale** (Stakeholder confirmed: slow operations need async):
- Code parsing/feature extraction is slow: ~5-10ms per file
- Large repos (1000+ files) take 10+ minutes
- Without async: API timeout, poor UX
- With async: Immediate response, poll for progress
- Thresholds: Use async for operations >30 seconds

| Task Type | Estimated Time | Mode | Interface |
|-----------|---------------|------|-----------|
| Single KP match | <100ms | Sync | API: `/api/match` |
| Batch match (5 KPs) | <500ms | Sync | API: `/api/match/batch` |
| **Bulk code import** | **5-30 minutes** | **Async** | **API: `/api/bulk-import` + CLI** |
| Experiment evaluation | 1-60 minutes | CLI only | `experiments/run_evaluation.py` |

**Async Implementation** (Lightweight):
```python
# lib/background_jobs.py
import threading
import queue

job_queue = queue.Queue()

def worker():
    while True:
        job = job_queue.get()
        try:
            job.execute()  # Run import in background
            job.mark_completed()
        except Exception as e:
            job.mark_failed(str(e))
        finally:
            job_queue.task_done()

# Start single worker thread on app startup
threading.Thread(target=worker, daemon=True).start()
```

**Benefits**:
- ✅ API remains responsive (no timeout)
- ✅ Can test in Apifox (start job, poll status)
- ✅ Progress tracking visible
- ✅ Lightweight (1 worker thread, no Redis/Celery)
- ✅ Both CLI and API supported

## 2. Data Model Changes

### 2.1 New Table: experiment_runs (Simplified)

```sql
CREATE TABLE IF NOT EXISTS experiment_runs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    run_name VARCHAR(255) UNIQUE NOT NULL,
    dataset_name VARCHAR(100),
    config JSON,
    metrics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dataset (dataset_name)
);
```

**Purpose**: Track experiment configurations and results for reproducibility.

**Rationale**: Minimal schema - only essential fields for experiment tracking.

### 2.2 Modify Table: code_snippets (Add Idempotency Key)

```sql
ALTER TABLE code_snippets
ADD COLUMN content_hash VARCHAR(64) UNIQUE,
ADD INDEX idx_content_hash (content_hash);
```

**Purpose**: Enable idempotent imports via `REPLACE INTO` based on hash.

**Migration Strategy**:
1. Add column (nullable initially)
2. Compute hash for existing rows: `UPDATE code_snippets SET content_hash = SHA2(CONCAT(file_path, '::', content), 256)`
3. Add UNIQUE constraint after backfill

### 2.3 New Table: bulk_import_jobs (Simplified for Async Operations)

```sql
CREATE TABLE IF NOT EXISTS bulk_import_jobs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    repo_path VARCHAR(500),
    status ENUM('queued', 'running', 'completed', 'failed') DEFAULT 'queued',
    progress INT DEFAULT 0,
    total_files INT DEFAULT 0,
    snippets_imported INT DEFAULT 0,
    errors JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_job_id (job_id),
    INDEX idx_status (status)
);
```

**Purpose**: Track async bulk import jobs for API endpoints. Essential because code parsing and feature extraction are slow operations (minutes for large repos).

**Rationale**:
- Code library import is slow (tree-sitter parsing ~5-10ms per file)
- 1000 files = ~10 minutes processing time
- Without async: API requests timeout, poor user experience
- With async: Immediate response, poll for progress

**Total New Tables**: 2 (experiment_runs, bulk_import_jobs)
**Total Modified Tables**: 1 (code_snippets - add content_hash)

## 3. API Design Changes

### 3.1 New Endpoints

#### Health Check
```
GET /api/health
Response: {
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-01-24T12:00:00Z"
}
```

#### Performance Metrics
```
GET /api/metrics
Response: {
  "uptime_seconds": 3600,
  "requests_total": 1523,
  "avg_latency_ms": 23.5
}
```

#### Bulk Import (Async)
```
POST /api/bulk-import
Request: {"repo_path": "code_repos/spring-boot"}
Response: {"job_id": "import-20260124-abc123", "status": "queued"}

GET /api/bulk-import/{job_id}
Response: {
  "job_id": "import-20260124-abc123",
  "status": "running",
  "progress": 450,
  "total_files": 1000,
  "snippets_imported": 2340,
  "errors": []
}
```

**Rationale**: Code import is slow (5-30 minutes for large repos), async is necessary.

### 3.2 Existing Endpoints (No Changes)

All existing endpoints remain unchanged:
- `/api/match` - single KP matching
- `/api/match/batch` - batch matching
- `/api/match/composite` - composite matching
- `/api/knowledge/tree` - knowledge tree
- `/api/knowledge/{id}` - KP details

**No API versioning** (per earlier decision)

## 4. Testing Strategy

### 4.1 Unit Tests (Existing)
- Keep `tests/test_matching_strategies.py` (no changes)

### 4.2 Integration Tests (New)
```
tests/integration/
├── test_api_endpoints.py        # Test all v1 endpoints
├── test_bulk_import.py           # Test import workflow
└── test_idempotency.py           # Verify safe re-runs
```

### 4.3 Performance Tests (New)
```
tests/performance/
├── locustfile.py                 # Load test scenarios
└── benchmark_results.json        # Baseline measurements
```

## 5. Migration Plan

### Phase 1: Preparation (No Breaking Changes)
1. Add new database tables (experiment_runs, bulk_import_jobs)
2. Add content_hash to code_snippets
3. Create directory structure (code_repos/, experiments/)

### Phase 2: Script Reorganization
1. **Delete** offline_tasks.py and main.py (no preservation needed)
2. Create clean init_data/ modules from scratch
3. Create batch_import/import_code_repos.py (CLI only)
4. Move run_evaluation.py to experiments/

### Phase 3: API Enhancement
1. Add health check endpoint
2. Add metrics endpoint
3. Add bulk import API endpoints (async)
4. Implement background job queue
5. Improve error handling in run_api.py

### Phase 4: Experiment Framework
1. Integrate CodeSearchNet loader
2. Implement experiment tracking
3. Enhance report generation

### Phase 5: Performance Benchmarking
1. Create Locust load tests
2. Measure baseline performance
3. Document targets in docs/

## 6. Open Questions & Decisions Needed

### Q1: Dataset Selection ✅ DECIDED

**Decision**: **CodeSearchNet Java subset**

**Labeling Strategy**: Hybrid approach
- Heuristic labeling using keyword matching on docstrings
- Manual verification of 200 samples for quality assessment
- Compute inter-annotator agreement (Cohen's Kappa)
- Target: ≥1000 labeled samples across 10-15 knowledge points

### Q2: Experiment Tracking Library ✅ DECIDED

**Decision**: **Custom solution** (JSON-based tracking)

**Implementation**:
- Experiment runs stored in `experiments/runs/{run_name}/`
- Metadata in MySQL `experiment_runs` table
- Artifacts: config.json, metrics.json, predictions.csv, report.md
- No external dependencies (MLflow/WandB rejected)
- Simple Python class: `ExperimentRun` with log/save/report methods

### Q3: Async Implementation ✅ DECIDED

**Decision**: **Simple thread pool** (Python `queue.Queue` + threading)

**Rationale**:
- No external dependencies (no Redis, no Celery)
- Sufficient for graduation project (single instance)
- Easy to debug and maintain
- Can upgrade to Celery later if distributed workers needed

### Q4: Performance Targets

**Question**: What are realistic QPS/latency targets?

**Need**: Run baseline benchmark to set targets

**Action Items**:
1. Create simple Locust test
2. Measure current system (before refactoring)
3. Set targets based on measurements (not guesses)

## 7. Risk Mitigation

### Risk 1: Breaking Existing Clients
**Mitigation**: Keep old URLs as aliases, deprecation warnings in v1.1

### Risk 2: Dataset Labeling Quality
**Mitigation**: Start with manual verification of 200 samples, measure inter-annotator agreement

### Risk 3: Performance Regression
**Mitigation**: Benchmark before/after, automated regression tests in CI

### Risk 4: Scope Creep
**Mitigation**: Follow OpenSpec "straightforward, minimal" guardrail, defer non-critical features

## 8. Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| API backward compat | 100% old URLs work | Integration tests |
| Bulk import speed | >10 files/sec | Performance test |
| Experiment dataset size | ≥1000 samples | Count in dataset loader |
| Matching accuracy | ≥95% | Evaluation on new dataset |
| Documentation coverage | 100% new features | Manual review |

## 9. Documentation Updates Needed

1. **README.md**: Update quickstart, add bulk import section
2. **CLAUDE.md**: Update architecture section, add async scheduling guide
3. **docs/api.md** (NEW): OpenAPI spec for v1 endpoints
4. **docs/performance.md** (NEW): Benchmark results and targets
5. **docs/experiments.md** (NEW): How to run experiments, dataset info

## 10. Timeline Estimate

**Note**: Per project guidelines, no specific time estimates provided. Work breakdown:

- **Script reorganization**: Straightforward refactoring
- **Bulk import**: Medium complexity (file discovery + idempotency)
- **API versioning**: Simple (Flask blueprints)
- **Dataset integration**: Complex (download + preprocessing + labeling)
- **Experiment tracking**: Medium (custom JSON-based solution)
- **Performance benchmarking**: Simple (Locust setup + measurement)

**Sequencing**: Can parallelize (1) script reorg, (2) API versioning, (3) bulk import. Dataset work is independent and can start anytime.
