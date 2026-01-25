# Tasks: Production Backend Refactoring

**Change ID**: `refactor-production-backend`
**Total Tasks**: 28 (optimized for async operations)

**Design Principles** (from Stakeholder Review):
1. **Delete old code** - no preservation of offline_tasks.py or main.py
2. **Simplify database** - only 2 new tables (experiment_runs, bulk_import_jobs)
3. **Strong idempotency** - every script run = identical database state
4. **System must work** - no broken states, runnable at every phase
5. **Async for slow ops** - code import takes 5-30 minutes, needs async + progress tracking

---

## Phase 1: Foundation & Database Changes (Parallel)

### Task 1.1: Create database migration scripts ⚡
**Type**: Database Migration
**Validation**: Migrations run cleanly on fresh database

Steps:
1. Create `scripts/migrations/001_add_experiment_runs.sql`:
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
2. Create `scripts/migrations/002_add_content_hash.sql`:
   ```sql
   ALTER TABLE code_snippets
   ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64) UNIQUE,
   ADD INDEX IF NOT EXISTS idx_content_hash (content_hash);

   UPDATE code_snippets
   SET content_hash = SHA2(CONCAT(file_path, '::', content), 256)
   WHERE content_hash IS NULL;
   ```
3. Create `scripts/migrations/003_add_bulk_import_jobs.sql`:
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
4. Test migrations on test database
5. Verify idempotency (re-run should not fail)

**Deliverable**: 3 migration SQL files

---

### Task 1.2: Create directory structure ⚡
**Type**: Setup
**Validation**: All directories exist

Steps:
1. Create `scripts/init_data/`
2. Create `scripts/batch_import/`
3. Create `scripts/migrations/`
4. Create `experiments/datasets/cache/`
5. Create `experiments/datasets/processed/`
6. Create `experiments/runs/`
7. Create `experiments/baselines/`
8. Create `code_repos/` with README.md
9. Create `docs/`
10. Create `tests/performance/`
11. **Delete** `scripts/offline_tasks.py` (no preservation needed)
12. **Delete** `main.py` (will be replaced)

**Deliverable**: Clean directory structure, old files removed

---

## Phase 2: Data Initialization Module (Sequential)

### Task 2.1: Create schema initialization script
**Type**: New Implementation
**Dependencies**: Task 1.1, 1.2
**Validation**: Creates all tables on fresh database, idempotent

Steps:
1. Create `scripts/init_data/init_schema.py` (from scratch, no code reuse)
2. Run migration files from `scripts/migrations/`
3. Create tables: knowledge_points, code_files, code_snippets (if not exist)
4. Create new tables: experiment_runs (from migration)
5. Log each operation clearly
6. Test on fresh MySQL database
7. Test idempotency: re-run must succeed without errors

**Deliverable**: `scripts/init_data/init_schema.py` with tests

---

### Task 2.2: Create knowledge point loader
**Type**: New Implementation
**Dependencies**: Task 2.1
**Validation**: Loads KPs deterministically, every run = same state

Steps:
1. Create `scripts/init_data/load_knowledge_points.py` (from scratch)
2. Parse `kp_dml.sql` to extract INSERT statements
3. **Use `REPLACE INTO` for all knowledge points** (not INSERT IGNORE)
4. Log count: "Replaced X knowledge points"
5. Test: run twice, verify database state identical both times
6. Update `kp_dml.sql` if needed to include all current KPs

**Key Requirement**: Strong idempotency - same KP data every run

**Deliverable**: `scripts/init_data/load_knowledge_points.py` + updated kp_dml.sql

---

### Task 2.3: Create sample code analyzer
**Type**: New Implementation
**Dependencies**: Task 2.2
**Validation**: Analyzes sample code deterministically

Steps:
1. Create `scripts/init_data/analyze_sample_code.py` (from scratch)
2. Use existing `src/java_analyzer/` for parsing
3. Compute content_hash for each snippet: `SHA256(file_path + '::' + content)`
4. **Use `REPLACE INTO` based on content_hash** (not INSERT IGNORE)
5. Log count: "Replaced X snippets"
6. Test: analyze same file twice, verify identical DB state

**Key Requirement**: Same file = same database state (deterministic)

**Deliverable**: `scripts/init_data/analyze_sample_code.py`

---

### Task 2.4: Create status checker
**Type**: Utility
**Dependencies**: Task 2.3
**Validation**: Correctly reports initialization state

Steps:
1. Create `scripts/init_data/check_status.py`
2. Check table existence (run `SHOW TABLES`)
3. Check KP count (SELECT COUNT(*) FROM knowledge_points)
4. Check snippet count (SELECT COUNT(*) FROM code_snippets)
5. Print colored output (✓ / ✗)
6. Exit code 0 if fully initialized, 1 otherwise

**Deliverable**: `scripts/init_data/check_status.py`

---

### Task 2.5: Create master orchestrator
**Type**: Integration
**Dependencies**: Task 2.4
**Validation**: Single command initializes entire system

Steps:
1. Create `scripts/init_data/run_all.py`
2. Call scripts in sequence:
   - init_schema.py
   - load_knowledge_points.py
   - analyze_sample_code.py
3. Print progress for each step
4. Handle errors gracefully (fail-fast on critical errors)
5. Final status: call check_status.py
6. Test end-to-end on fresh database
7. Test idempotency: run twice, verify same state

**Deliverable**: `scripts/init_data/run_all.py` with integration test

---

## Phase 3: Bulk Code Import (CLI Only)

### Task 3.1: Implement file discovery
**Type**: New Feature
**Dependencies**: Task 1.2
**Validation**: Finds Java files, excludes build dirs

Steps:
1. Create `scripts/batch_import/file_discovery.py`
2. Recursive directory walker
3. Filter: `*.java` files only
4. Exclude: `target/`, `build/`, `.git/`, `node_modules/`, `test/` (optional)
5. Return list of absolute file paths
6. Unit test with mock filesystem (tempfile)

**Deliverable**: `scripts/batch_import/file_discovery.py` with tests

---

### Task 3.2: Implement content hash utility
**Type**: Utility
**Dependencies**: None
**Validation**: Hash is deterministic and unique

Steps:
1. Create `scripts/batch_import/hash_utils.py`
2. Function: `compute_snippet_hash(file_path, content) -> str`
3. Implementation: `SHA256(f"{file_path}::{content}")`
4. Unit tests: verify determinism (same input = same hash)

**Deliverable**: `scripts/batch_import/hash_utils.py` with tests

---

### Task 3.3: Implement bulk import script
**Type**: New Feature
**Dependencies**: Task 3.1, 3.2
**Validation**: Imports projects idempotently

Steps:
1. Create `scripts/batch_import/import_code_repos.py` (from scratch)
2. CLI args: `--repo <path>` or `--all` (scan code_repos/)
3. For each Java file:
   - Parse with tree-sitter (reuse `src/java_analyzer/`)
   - Extract method-level snippets
   - Compute content_hash
   - **Use `REPLACE INTO code_snippets`** (not INSERT IGNORE)
4. Progress bar (tqdm or simple counter)
5. Error handling: log unparseable files, continue processing
6. Final summary: "Replaced X snippets, inserted Y new, Z errors"
7. Test with small project (5-10 files)
8. Test idempotency: import twice, verify identical DB state

**Key Requirement**: Same files = same database state (strong idempotency)

**Deliverable**: `scripts/batch_import/import_code_repos.py` with tests

---

### Task 3.4: Create code_repos README
**Type**: Documentation
**Dependencies**: Task 3.3
**Validation**: Clear user instructions

Steps:
1. Create `code_repos/README.md`
2. Explain directory purpose
3. Instructions: copy Java projects into subdirectories
4. Example command: `python scripts/batch_import/import_code_repos.py --all`
5. Explain expected output

**Deliverable**: `code_repos/README.md`

---

### Task 3.5: Implement background job queue
**Type**: Infrastructure
**Dependencies**: Task 1.1 (bulk_import_jobs table)
**Validation**: Jobs execute asynchronously without blocking

Steps:
1. Create `lib/background_jobs.py`
2. Implement job queue using Python `queue.Queue` (no external dependencies)
3. Create `ImportJob` class with methods:
   - `execute()` - run import logic
   - `mark_completed()` - update DB status to 'completed'
   - `mark_failed(error)` - update DB status to 'failed'
4. Implement worker thread function (runs continuously)
5. Add `start_worker()` function to initialize on app startup
6. Update job progress in `bulk_import_jobs` table during execution
7. Test with mock import job (verify status updates)

**Key Design**:
- Single worker thread (sequential processing)
- Lightweight (no Redis/Celery)
- Jobs update status in database for API polling

**Deliverable**: `lib/background_jobs.py` with unit tests

---

### Task 3.6: Add bulk import API endpoints
**Type**: API Enhancement
**Dependencies**: Task 3.5
**Validation**: Can start job via Apifox, poll status

Steps:
1. Create `api/routes/bulk_import.py`
2. Implement `POST /api/bulk-import`:
   - Validate request (repo_path exists)
   - Generate job_id (timestamp + UUID)
   - Insert job record to `bulk_import_jobs` table
   - Add job to queue
   - Return job_id immediately (<100ms)
3. Implement `GET /api/bulk-import/{job_id}`:
   - Query `bulk_import_jobs` table
   - Return status, progress, errors
4. Add request/response schemas in `api/schemas/bulk_import.py`
5. Register routes in `api/routes/__init__.py`
6. Start worker thread in `api/__init__.py` (create_app)
7. Integration test: start job via Apifox, poll until completed

**Deliverable**: API endpoints testable in Apifox

---

## Phase 4: API Service Enhancements

### Task 4.1: Add health check endpoint
**Type**: API Enhancement
**Dependencies**: None
**Validation**: Returns 200 with database status

Steps:
1. Create `api/routes/system.py` (new file)
2. Route: `GET /api/health`
3. Check database connection (simple query: SELECT 1)
4. Response: `{"status": "healthy", "database": "connected", "timestamp": "..."}`
5. If DB fails: return 503 Service Unavailable
6. Unit test with mock database

**Deliverable**: `/api/health` endpoint with tests

---

### Task 4.2: Add metrics endpoint
**Type**: API Enhancement
**Dependencies**: None
**Validation**: Returns runtime metrics

Steps:
1. Create `api/middleware/metrics.py`
2. Track requests using Flask hooks (before_request, after_request)
3. Metrics: request count per endpoint, avg response time
4. Route: `GET /api/metrics` in system.py
5. Response: `{"uptime_seconds": ..., "requests_total": ..., "avg_latency_ms": ...}`
6. Integration test: make requests, verify metrics update

**Deliverable**: `/api/metrics` endpoint with middleware

---

### Task 4.3: Improve startup validation
**Type**: Code Quality
**Dependencies**: None
**Validation**: Clear errors on config failure

Steps:
1. **Rewrite `run_api.py` from scratch** (no preservation of old code)
2. Validate config file exists before starting
3. Test database connection during startup (fail-fast)
4. Clear error messages with troubleshooting hints
5. Exit with non-zero code on failure
6. Test: missing config file
7. Test: wrong database credentials

**Deliverable**: New `run_api.py` with validation

---

### Task 4.4: Add request logging
**Type**: Observability
**Dependencies**: None
**Validation**: All requests logged

Steps:
1. Create `api/middleware/request_logger.py`
2. Log before request: timestamp, method, path, IP
3. Log after request: status code, response time
4. Use `api_logger` from `lib/globals/`
5. Register in `api/__init__.py` (create_app)
6. Unit test: verify log entries

**Deliverable**: Request logging middleware

---

### Task 4.5: Update API documentation
**Type**: Documentation
**Dependencies**: Task 3.6, 4.1, 4.2
**Validation**: All endpoints documented

Steps:
1. Update README.md API section
2. Add `/api/health`, `/api/metrics`, `/api/bulk-import` docs
3. Include Apifox testing examples
4. Update CLAUDE.md architecture section
5. Document new entry points (run_api.py, scripts/init_data/run_all.py)
6. Document async job workflow

**Deliverable**: Updated README.md and CLAUDE.md

---

## Phase 5: Experiment Framework

### Task 5.1: Implement CodeSearchNet downloader
**Type**: Dataset Integration
**Dependencies**: Task 1.1
**Validation**: Dataset downloaded successfully

Steps:
1. Create `experiments/datasets/download_codesearchnet.py`
2. Use `requests` or `urllib` to download Java subset
3. Save to `experiments/datasets/cache/codesearchnet/`
4. Create metadata: `dataset_info.json` (download time, size, file count)
5. Progress bar (tqdm)
6. Test with small subset for CI

**Note**: ~2.3GB download, may take time

**Deliverable**: `experiments/datasets/download_codesearchnet.py`

---

### Task 5.2: Implement preprocessor
**Type**: Data Processing
**Dependencies**: Task 5.1
**Validation**: JSONL format output

Steps:
1. Create `experiments/datasets/preprocess_codesearchnet.py`
2. Read raw CodeSearchNet JSON files
3. Extract method code, docstring, metadata
4. Save to `experiments/datasets/processed/codesearchnet_java.jsonl`
5. Log progress and final count

**Deliverable**: `experiments/datasets/preprocess_codesearchnet.py`

---

### Task 5.3: Implement heuristic labeling
**Type**: Data Labeling
**Dependencies**: Task 5.2
**Validation**: Labels assigned

Steps:
1. Create `experiments/datasets/label_codesearchnet.py`
2. Define keyword-to-KP mappings (config file or hardcoded)
3. Parse docstrings, match keywords (case-insensitive)
4. Require ≥2 keyword matches for label
5. Save to `experiments/datasets/processed/codesearchnet_labeled.jsonl`
6. Log label distribution

**Deliverable**: `experiments/datasets/label_codesearchnet.py`

---

### Task 5.4: Create verification tool
**Type**: Data Quality
**Dependencies**: Task 5.3
**Validation**: Interactive label review

Steps:
1. Create `experiments/datasets/verify_labels.py`
2. Sample N examples (CLI arg, default 200)
3. Display code + proposed label
4. Prompt: "Correct? (y/n/skip)"
5. Save corrections to `codesearchnet_verified.jsonl`
6. Compute Cohen's Kappa (if multiple reviewers)

**Deliverable**: `experiments/datasets/verify_labels.py`

---

### Task 5.5: Implement ExperimentRun class
**Type**: Infrastructure
**Dependencies**: Task 1.1
**Validation**: Tracks runs to DB and filesystem

Steps:
1. Create `experiments/tracking.py`
2. Class `ExperimentRun`:
   - `__init__(name, config)`
   - `log_metric(name, value)`
   - `save_predictions(df)`
   - `generate_report()`
3. Save config.json, metrics.json to `experiments/runs/{name}/`
4. Insert metadata to `experiment_runs` table
5. Unit tests (mock filesystem and DB)

**Deliverable**: `experiments/tracking.py` with tests

---

### Task 5.6: Refactor evaluation script
**Type**: Code Refactoring
**Dependencies**: Task 5.5
**Validation**: Works with ExperimentRun tracking

Steps:
1. Move `scripts/run_evaluation.py` to `experiments/run_evaluation.py`
2. Use `ExperimentRun` class for tracking
3. Replace manual report generation
4. Test: run evaluation, verify artifacts created

**Deliverable**: `experiments/run_evaluation.py` (refactored)

---

### Task 5.7: Generalize baselines
**Type**: Code Enhancement
**Dependencies**: Task 5.4
**Validation**: Runs on new datasets

Steps:
1. Create `experiments/baselines/run_tfidf.py`
2. Create `experiments/baselines/run_pure_ast.py`
3. Create `experiments/baselines/run_random.py`
4. Add `--dataset` CLI arg to each
5. Test on both ground_truth.json and codesearchnet_verified.jsonl

**Deliverable**: 3 baseline scripts in `experiments/baselines/`

---

### Task 5.8: Implement ablation script
**Type**: Automation
**Dependencies**: Task 5.6
**Validation**: Single command runs all configs

Steps:
1. Create `experiments/run_ablation.py`
2. Define configs: AST-only, Keyword-only, AST+Keyword, Full
3. For each, create ExperimentRun and evaluate
4. Generate comparison report
5. Test on small dataset

**Deliverable**: `experiments/run_ablation.py`

---

### Task 5.9: Implement comparison tool
**Type**: Analysis
**Dependencies**: Task 5.5
**Validation**: Compares two runs

Steps:
1. Create `experiments/compare_runs.py`
2. Load two run directories (config + metrics)
3. Compute differences (absolute and percentage)
4. Print comparison table
5. Save markdown report

**Deliverable**: `experiments/compare_runs.py`

---

### Task 5.10: Implement export utility
**Type**: Data Export
**Dependencies**: Task 5.5
**Validation**: Exports to CSV

Steps:
1. Create `experiments/export_all_runs.py`
2. Query `experiment_runs` table
3. Export to CSV (run_name, dataset, config, metrics)
4. Support JSON format too (--format arg)

**Deliverable**: `experiments/export_all_runs.py`

---

## Phase 6: Performance Benchmarking

### Task 6.1: Create Locust script
**Type**: Performance Testing
**Dependencies**: Task 4.5
**Validation**: Locust runs successfully

Steps:
1. Create `tests/performance/locustfile.py`
2. Define `APIUser` with tasks (match, tree endpoints)
3. Weight tasks appropriately
4. Test locally

**Deliverable**: `tests/performance/locustfile.py`

---

### Task 6.2: Implement benchmark runner
**Type**: Automation
**Dependencies**: Task 6.1
**Validation**: Saves JSON results

Steps:
1. Create `tests/performance/run_benchmarks.py`
2. Run Locust headless (10 users, 60s duration)
3. Parse output, convert to JSON format
4. Save to `tests/performance/results/benchmark_{timestamp}.json`

**Deliverable**: `tests/performance/run_benchmarks.py`

---

### Task 6.3: Implement baseline comparison
**Type**: Regression Detection
**Dependencies**: Task 6.2
**Validation**: Detects regressions

Steps:
1. Create `tests/performance/compare_baseline.py`
2. Load current + baseline results
3. Compare QPS, P99 latency
4. Thresholds: QPS -10%, P99 +20%
5. Exit code 1 if threshold exceeded

**Deliverable**: `tests/performance/compare_baseline.py`

---

### Task 6.4: Write performance docs
**Type**: Documentation
**Dependencies**: Task 6.2
**Validation**: Comprehensive guide

Steps:
1. Create `docs/performance.md`
2. Document methodology
3. Include current targets (from actual measurements)
4. Document bottlenecks
5. Scaling recommendations

**Deliverable**: `docs/performance.md`

---

### Task 6.5: Create GitHub Actions workflow
**Type**: CI/CD
**Dependencies**: Task 6.3
**Validation**: Workflow runs on PR

Steps:
1. Create `.github/workflows/performance-tests.yml`
2. Trigger: pull_request
3. Steps: setup, start MySQL, init DB, run benchmarks
4. Compare to baseline (fail if regression)
5. Post comment on PR with results
6. Test on test branch

**Deliverable**: `.github/workflows/performance-tests.yml`

---

## Phase 7: Integration & Release

### Task 7.1: Update all documentation
**Type**: Documentation
**Dependencies**: All implementation tasks
**Validation**: Docs reflect current system

Steps:
1. Update README.md (project structure, quickstart, all features)
2. Update CLAUDE.md (architecture, new workflows)
3. Ensure all new commands documented
4. Add performance benchmarks section

**Deliverable**: Complete documentation update

---

### Task 7.2: End-to-end integration test
**Type**: Validation
**Dependencies**: All tasks
**Validation**: Full system works

Steps:
1. Fresh database setup
2. Run `python scripts/init_data/run_all.py`
3. Verify: check_status.py reports "Ready"
4. Start API: `python run_api.py`
5. Test all endpoints (health, metrics, match)
6. **Test bulk import via Apifox**:
   - POST /api/bulk-import with test repo
   - Poll GET /api/bulk-import/{job_id} until completed
   - Verify snippets imported to database
7. Test CLI import: `python scripts/batch_import/import_code_repos.py --repo test_repo`
8. Run evaluation on dataset subset
9. Run performance benchmarks
10. **Critical**: Verify database state is deterministic (re-run init, same state)

**Deliverable**: Integration test checklist (all pass)

---

### Task 7.3: Create CHANGELOG entry
**Type**: Release
**Dependencies**: Task 7.2
**Validation**: All changes documented

Steps:
1. Update CHANGELOG.md
2. Add v1.3.0 section
3. List major changes (modular scripts, bulk import, CodeSearchNet, experiments, benchmarks)
4. Note breaking changes: old scripts deleted
5. Migration guide for users

**Deliverable**: CHANGELOG.md update

---

### Task 7.4: Release v1.3.0 ⚡
**Type**: Release
**Dependencies**: Task 7.3
**Validation**: Version tagged

Steps:
1. Update version in README.md
2. Git tag: `git tag v1.3.0`
3. Push tag: `git push origin v1.3.0`
4. Create GitHub release

**Deliverable**: v1.3.0 released

---

## Task Dependencies Summary

**Phase 1** (Parallel): 1.1, 1.2

**Phase 2** (Sequential): 2.1 → 2.2 → 2.3 → 2.4 → 2.5

**Phase 3** (Sequential): 3.1 + 3.2 (parallel) → 3.3 → 3.4 + 3.5 (parallel) → 3.6

**Phase 4** (Parallel): 4.1, 4.2, 4.3, 4.4 (all parallel) → 4.5

**Phase 5** (Mixed): 5.1 → 5.2 → 5.3 → 5.4, then 5.5-5.10 can parallelize

**Phase 6** (Sequential): 6.1 → 6.2 → 6.3, 6.4 (parallel with 6.3) → 6.5

**Phase 7** (Sequential): 7.1 → 7.2 → 7.3 → 7.4

---

## Critical Success Criteria (from Stakeholder)

1. ✅ **System must work** - runnable at every phase
2. ✅ **Strong idempotency** - same input = same database state (every time)
3. ✅ **Async for slow ops** - code import (5-30 min) needs async + progress tracking
4. ✅ **Both CLI and API** - can run scripts AND test in Apifox
5. ✅ **Database simplicity** - only 2 new tables (experiment_runs, bulk_import_jobs)
6. ✅ **Clean code** - old scripts deleted, no legacy cruft
7. ✅ **DML files updated** - kp_dml.sql reflects all knowledge points

---

## Complexity Distribution

- **Simple** (⚡): 1.2, 3.4, 7.4 (3 tasks)
- **Medium**: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.5, 4.1, 4.2, 4.3, 4.4, 5.5, 5.9, 5.10, 6.1, 6.2, 6.3, 6.4, 7.1, 7.3 (22 tasks)
- **Complex**: 3.3, 3.6, 4.5, 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 5.8, 6.5, 7.2 (12 tasks)

**Total**: 28 tasks (optimized for async operations)

---

## Key Changes from Initial Review

✅ **Restored** (per stakeholder confirmation):
- Task 3.5: Background job queue (async is necessary)
- Task 3.6: Bulk import API endpoints (testable in Apifox)
- Database table: bulk_import_jobs (lightweight, 10 fields)

✅ **Kept Removed**:
- ~~API versioning~~ (not needed)
- ~~Deprecation warnings~~ (just delete old code)
- ~~Complex monitoring~~ (keep simple)
