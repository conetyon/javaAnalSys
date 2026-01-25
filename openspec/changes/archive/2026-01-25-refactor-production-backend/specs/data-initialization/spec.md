# Specification: Data Initialization Module

**Capability**: `data-initialization`
**Change Type**: MODIFIED
**Related Capabilities**: None

---

## MODIFIED Requirements

### Requirement: Modular Initialization Scripts

Database initialization SHALL be split into focused, single-purpose scripts.

**Rationale**: Current `scripts/offline_tasks.py` (400+ lines) handles too many responsibilities. Modular scripts improve maintainability and testability.

#### Scenario: Developer initializes database schema

**Given**: Fresh MySQL database exists
**When**: Developer runs `python scripts/init_data/init_schema.py`
**Then**:
- Tables `knowledge_points`, `code_files`, `code_snippets` are created
- Tables `experiment_runs`, `bulk_import_jobs` are created (new)
- Script logs "Database schema initialized successfully"
- Script exits with code 0

#### Scenario: Developer re-runs schema initialization (idempotency)

**Given**: Database tables already exist
**When**: Developer runs `python scripts/init_data/init_schema.py`
**Then**:
- Script completes without errors
- No duplicate tables created (`CREATE TABLE IF NOT EXISTS`)
- Log shows "Schema already exists, skipping creation"
- Script exits with code 0

---

### Requirement: Knowledge Point Data Loading

Knowledge point data SHALL be loaded via dedicated script.

**Rationale**: Separate schema creation from data population for flexibility (e.g., load different KP sets).

#### Scenario: Developer loads baseline knowledge points

**Given**: Database schema is initialized
**When**: Developer runs `python scripts/init_data/load_knowledge_points.py`
**Then**:
- Knowledge points from `kp_dml.sql` are inserted
- Script logs count of KPs inserted (e.g., "Loaded 50 knowledge points")
- Script exits with code 0

#### Scenario: Re-loading knowledge points (idempotency)

**Given**: Knowledge points already exist in database
**When**: Developer runs `python scripts/init_data/load_knowledge_points.py`
**Then**:
- Script detects existing KPs (by checking IDs)
- No duplicate insertions
- Log shows "Knowledge points already loaded, skipping"
- Script exits with code 0

#### Scenario: Loading knowledge points with updates

**Given**: `kp_dml.sql` has been modified (e.g., updated keywords)
**When**: Developer runs `python scripts/init_data/load_knowledge_points.py`
**Then**:
- Script uses `REPLACE INTO` to ensure deterministic state
- Existing KPs are replaced with new definitions
- Log shows "Replaced 50 knowledge points"
- Script exits with code 0

**Note**: Strong idempotency requirement - every run produces identical database state.

---

### Requirement: Sample Code Analysis

Sample code analysis SHALL be executable independently.

**Rationale**: Users may want to analyze sample code without reinitializing entire database.

#### Scenario: Developer analyzes sample Java file

**Given**: Database schema and KPs are loaded
**When**: Developer runs `python scripts/init_data/analyze_sample_code.py`
**Then**:
- `sample_code.java` is parsed via tree-sitter
- Code snippets (method-level) are extracted
- Snippets are saved to `code_snippets` table
- Log shows "Analyzed sample_code.java: 15 snippets saved"
- Script exits with code 0

#### Scenario: Re-analyzing sample code (idempotency)

**Given**: Sample code snippets already exist in database
**When**: Developer runs `python scripts/init_data/analyze_sample_code.py`
**Then**:
- Script computes content hash for each snippet
- Uses `REPLACE INTO` based on content_hash
- Identical snippets replace existing records (deterministic state)
- Log shows "Replaced 15 snippets (deterministic update)"
- Script exits with code 0

**Note**: Same file analyzed multiple times = same database state (strong idempotency).

---

### Requirement: One-Command Full Initialization

A master script SHALL orchestrate all initialization steps.

**Rationale**: Simplify onboarding for new developers (single command to set up system).

#### Scenario: New developer runs full initialization

**Given**: Fresh database, no data loaded
**When**: Developer runs `python scripts/init_data/run_all.py`
**Then**:
- Script executes in order:
  1. `init_schema.py`
  2. `load_knowledge_points.py`
  3. `analyze_sample_code.py`
- Each step logs progress
- Final log shows "Initialization complete. System ready."
- Script exits with code 0

#### Scenario: Full initialization on existing database (idempotency)

**Given**: Database is already initialized
**When**: Developer runs `python scripts/init_data/run_all.py`
**Then**:
- Each sub-script detects existing data and skips
- No errors occur
- Log shows "Database already initialized"
- Script exits with code 0

---

## ADDED Requirements

### Requirement: Initialization Status Check

Users SHALL be able to check if system is initialized.

**Rationale**: Avoid running initialization unnecessarily; useful for deployment automation.

#### Scenario: Developer checks initialization status

**Given**: System may or may not be initialized
**When**: Developer runs `python scripts/init_data/check_status.py`
**Then**: Output shows:
```
Database Schema: ✓ Initialized
Knowledge Points: ✓ Loaded (50 items)
Sample Code: ✓ Analyzed (15 snippets)
Status: Ready
```
**And**: Exit code is 0

#### Scenario: System is partially initialized

**Given**: Schema exists but KPs not loaded
**When**: Developer runs `python scripts/init_data/check_status.py`
**Then**: Output shows:
```
Database Schema: ✓ Initialized
Knowledge Points: ✗ Not loaded
Sample Code: ✗ Not analyzed
Status: Incomplete
```
**And**: Exit code is 1

---

## Implementation Notes

### Directory Structure
```
scripts/
├── init_data/
│   ├── __init__.py
│   ├── init_schema.py           # Create tables
│   ├── load_knowledge_points.py # Load kp_dml.sql
│   ├── analyze_sample_code.py   # Analyze sample_code.java
│   ├── check_status.py          # Check initialization status
│   └── run_all.py               # Orchestrator
```

### Shared Utilities
- Extract common functions from `scripts/offline_tasks.py` into `scripts/init_data/utils.py`:
  - Database connection helper
  - SQL file parser
  - Logging setup

### Idempotency Implementation (Critical Requirement)
- **Schema**: Use `CREATE TABLE IF NOT EXISTS`
- **Knowledge Points**: Use `REPLACE INTO` based on `id` (primary key)
- **Code Snippets**: Use `REPLACE INTO` based on `content_hash` (unique key)
- **Goal**: Running any script multiple times produces identical database state

### DML File Management
- Keep `kp_dml.sql` updated with all knowledge point definitions
- Script `load_knowledge_points.py` parses this file and uses `REPLACE INTO`
- New migrations: `scripts/migrations/001_add_experiment_runs.sql`
- New migrations: `scripts/migrations/002_add_content_hash.sql`

### Backward Compatibility
- **Old scripts will be deleted** (no deprecation period needed per stakeholder)
- `scripts/offline_tasks.py` → delete
- `main.py` → delete and replace with new `run_api.py` and `scripts/init_data/run_all.py`

### Testing Requirements
- Unit tests for each script (isolated, mock database)
- Integration test: Full initialization on fresh database
- Integration test: Re-run initialization (verify idempotency)
