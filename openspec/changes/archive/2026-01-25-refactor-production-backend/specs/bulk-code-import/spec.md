# Specification: Bulk Code Import

**Capability**: `bulk-code-import`
**Change Type**: ADDED
**Related Capabilities**: `api-service`, `data-initialization`

---

## ADDED Requirements

### Requirement: Directory-Based Repository Discovery

The system SHALL discover Java projects placed in a designated directory.

**Rationale**: Enable batch import of multiple projects without manual configuration per project.

#### Scenario: User places Java project in staging directory

**Given**: `code_repos/` directory exists
**When**: User copies project `spring-petclinic/` into `code_repos/`
**Then**: Directory structure is:
```
code_repos/
└── spring-petclinic/
    ├── src/
    │   └── main/
    │       └── java/
    │           └── *.java
    └── pom.xml
```
**And**: System can discover this project

#### Scenario: System scans for Java files in repository

**Given**: Repository contains Java files and non-Java files
**When**: Import script scans `code_repos/spring-petclinic/`
**Then**: Script identifies all `.java` files recursively
**And**: Excludes common non-source directories:
- `target/` (Maven build output)
- `build/` (Gradle build output)
- `test/` (test code, optional exclusion)
- `.git/` (version control)
- `node_modules/` (if mixed project)

---

### Requirement: Idempotent Code Import

Importing the same code multiple times SHALL NOT create duplicates.

**Rationale**: Users may re-run import after adding new files to repository.

#### Scenario: First-time import of repository

**Given**: Repository has 100 Java files
**When**: User runs `python scripts/batch_import/import_code_repos.py --repo code_repos/spring-petclinic`
**Then**:
- All 100 files are analyzed
- Method-level snippets are extracted (e.g., 500 snippets total)
- Each snippet is saved to `code_snippets` table with content hash
- Log shows "Imported 500 snippets from 100 files"

#### Scenario: Re-importing same repository (no changes)

**Given**: Repository already imported, no files changed
**When**: User runs import command again
**Then**:
- Script computes content hash for each snippet
- Uses `REPLACE INTO` based on content_hash
- All snippets replaced with identical data (deterministic state)
- Log shows "Replaced 500 snippets (no changes detected)"
- Database state is identical to previous run

**Note**: Strong idempotency - same input = same database state.

#### Scenario: Re-importing repository with new files

**Given**: Repository previously imported, user added 10 new Java files
**When**: User runs import command
**Then**:
- Script analyzes all files (old + new)
- Uses `REPLACE INTO` for all snippets
- 500 existing snippets replaced (unchanged)
- 50 new snippets inserted
- Log shows "Replaced 500 existing, inserted 50 new snippets"
- Final database state is deterministic

---

### Requirement: Progress Tracking During Import

Long-running imports SHALL show progress to user.

**Rationale**: Importing large repositories (1000+ files) may take minutes; users need feedback.

#### Scenario: Console output during import

**Given**: Importing repository with 100 files
**When**: Import script is running
**Then**: Console shows progress updates:
```
[1/100] Analyzing src/main/java/com/example/Main.java
[2/100] Analyzing src/main/java/com/example/Service.java
...
[50/100] Analyzing src/main/java/com/example/Controller.java
...
[100/100] Analyzing src/main/java/com/example/Utils.java
Import complete: 500 snippets from 100 files
```

#### Scenario: Progress tracking via API

**Given**: Import job started via API endpoint
**When**: User polls `GET /api/bulk-import/{job_id}`
**Then**: Response shows real-time progress:
```json
{
  "job_id": "bulk-import-abc123",
  "status": "running",
  "progress": 50,
  "total_files": 100,
  "current_file": "src/main/java/com/example/Controller.java"
}
```

---

### Requirement: Error Handling and Partial Imports

Import SHALL continue even if individual files fail to parse.

**Rationale**: Large repositories may have malformed Java files (e.g., generated code, syntax errors).

#### Scenario: Import encounters unparseable file

**Given**: Repository contains file with syntax error
**When**: Import script processes this file
**Then**:
- Tree-sitter parser fails for this file
- Error is logged with file path and error message
- Script continues to next file (does not abort)
- Final summary shows: "Imported 490 snippets, failed 10 files"

#### Scenario: Import job logs errors for review

**Given**: Import completed with some failures
**When**: User checks job details via API
**Then**: Response includes error list:
```json
{
  "job_id": "bulk-import-abc123",
  "status": "completed",
  "snippets_imported": 490,
  "errors": [
    {
      "file": "src/main/java/com/example/Generated.java",
      "error": "Syntax error at line 42"
    }
  ]
}
```

---

### Requirement: Bulk Import via Command-Line Interface

Users SHALL be able to trigger imports from command line.

**Rationale**: Enable manual imports and automation via shell scripts.

#### Scenario: Import single repository

**Given**: Repository exists at `code_repos/spring-petclinic/`
**When**: User runs:
```bash
python scripts/batch_import/import_code_repos.py --repo code_repos/spring-petclinic
```
**Then**:
- Script imports all Java files from specified repository
- Progress is shown in console
- Exit code is 0 on success

#### Scenario: Import all repositories in staging directory

**Given**: Multiple repositories in `code_repos/`:
```
code_repos/
├── spring-petclinic/
├── guava/
└── commons-lang/
```
**When**: User runs:
```bash
python scripts/batch_import/import_code_repos.py --all
```
**Then**:
- Script discovers all subdirectories in `code_repos/`
- Imports each repository sequentially
- Final summary shows total snippets imported across all repos

---

### Requirement: Async Job Queue for API-Triggered Imports

API-triggered imports SHALL run asynchronously without blocking requests.

**Rationale**: Code parsing and feature extraction are slow (5-30 minutes for large repos). API must remain responsive. Users can test in Apifox and poll for progress.

**Related Capability**: `api-service`

#### Scenario: API request queues import job

**Given**: API service is running
**When**: User posts to `/api/bulk-import` from Apifox:
```json
{"repo_path": "code_repos/spring-boot"}
```
**Then**:
- API immediately returns job ID (<100ms response time)
- Job is added to background queue (Python queue.Queue)
- Worker thread processes job asynchronously
- API remains responsive for other requests

#### Scenario: Multiple concurrent import jobs

**Given**: Three import jobs are queued via API
**When**: Background worker processes jobs
**Then**:
- Jobs are processed sequentially (one at a time, avoids resource contention)
- Each job updates its status in `bulk_import_jobs` table
- Users can poll status of all jobs independently via API

#### Scenario: Job fails and updates status

**Given**: Import job encounters database error
**When**: Exception occurs during processing
**Then**:
- Job status updated to "failed" in database
- Error message stored in `errors` field (JSON)
- API returns failure status when polled
- Worker thread continues processing next job

---

## Implementation Notes

### Directory Structure
```
scripts/
├── batch_import/
│   ├── __init__.py
│   ├── import_code_repos.py     # Main import script
│   ├── file_discovery.py        # Recursive .java file finder
│   └── job_queue.py             # Background job queue (for API)
```

### Staging Directory
```
code_repos/
├── .gitkeep                     # Keep directory in git
├── README.md                    # Instructions for users
└── <user-provided-repos>/       # User copies projects here
```

### Content Hash Calculation
```python
import hashlib

def compute_snippet_hash(file_path: str, snippet_content: str) -> str:
    """
    Hash includes file path (for uniqueness) + content.
    Ensures snippets from different files don't collide.
    """
    data = f"{file_path}::{snippet_content}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

### Database Schema Changes

Add `content_hash` column to `code_snippets` (if not exists):
```sql
-- Migration: scripts/migrations/002_add_content_hash.sql
ALTER TABLE code_snippets
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64) UNIQUE,
ADD INDEX IF NOT EXISTS idx_content_hash (content_hash);

-- Backfill existing rows
UPDATE code_snippets
SET content_hash = SHA2(CONCAT(file_path, '::', content), 256)
WHERE content_hash IS NULL;
```

Add `bulk_import_jobs` table:
```sql
-- Migration: scripts/migrations/003_add_bulk_import_jobs.sql
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

**Import Logic** (Strong Idempotency):
```sql
REPLACE INTO code_snippets (content_hash, file_path, content, ...)
VALUES (?, ?, ?, ...);
```

### Background Job Queue Implementation

**Lightweight async implementation** (no Redis/Celery):
```python
# lib/background_jobs.py
import queue
import threading
from typing import Callable

job_queue = queue.Queue()

class ImportJob:
    def __init__(self, job_id: str, repo_path: str):
        self.job_id = job_id
        self.repo_path = repo_path

    def execute(self):
        """Run import, update progress in DB"""
        # Implementation in scripts/batch_import/import_code_repos.py
        pass

    def mark_completed(self):
        # UPDATE bulk_import_jobs SET status='completed'
        pass

    def mark_failed(self, error: str):
        # UPDATE bulk_import_jobs SET status='failed', errors=?
        pass

def worker():
    """Background worker thread"""
    while True:
        job = job_queue.get()
        try:
            job.execute()
            job.mark_completed()
        except Exception as e:
            job.mark_failed(str(e))
        finally:
            job_queue.task_done()

# Start worker thread on API startup
def start_worker():
    threading.Thread(target=worker, daemon=True).start()
```

**API Integration**:
```python
# api/routes/bulk_import.py
from lib.background_jobs import job_queue, ImportJob

@app.post('/api/bulk-import')
def start_bulk_import(request):
    job = ImportJob(
        job_id=f"import-{timestamp}-{uuid}",
        repo_path=request.json['repo_path']
    )
    job_queue.put(job)
    return {"job_id": job.job_id, "status": "queued"}
```

### Testing Requirements
- Unit test: File discovery logic (mock filesystem)
- Unit test: Content hash computation (verify uniqueness and determinism)
- Integration test: Import small repository (5 files)
- Integration test: Re-import same repository (verify idempotency - identical DB state)
- Integration test: Import with syntax errors (verify error handling)
- **API integration tests**:
  - Trigger import via POST /api/bulk-import (test in Apifox)
  - Poll status via GET /api/bulk-import/{job_id}
  - Verify job completion and database state
  - Test concurrent job queueing
