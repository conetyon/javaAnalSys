# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java knowledge point matching system that uses AST (Abstract Syntax Tree) analysis and keyword matching to identify Java code snippets that correspond to specific programming concepts. Built for a graduation project at BUPT (2026).

The system analyzes Java code files, extracts code snippets at the method level, and matches them against a knowledge point database using a hybrid scoring algorithm that combines:
- AST feature matching (tree-sitter-java)
- Keyword matching with alias normalization
- Complexity/difficulty scoring

## Commands

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure database in config/db.yaml
# Required fields: host, port, user, password, db, charset, maxConn
```

### Database Management

```bash
# Database and code analysis are automatically handled when running main.py
python main.py
```

**Automated Process**:
1. Database initialization (creates tables, inserts knowledge points)
2. Code analysis (extracts features from `sample_code.java` and saves to DB)
3. Both are idempotent - safe to run multiple times

**Manual operations** (if needed):
```python
from scripts.offline_tasks import init_database, analyze_code_file

# Initialize database only
init_database()

# Analyze a specific file
analyze_code_file("path/to/file.java", save_to_db=True)
```

**Note**:
- All operations use `CREATE TABLE IF NOT EXISTS` (safe to re-run)
- Knowledge points are automatically inserted by `init_database()`
- If baseline data is missing, manually import `kp_dml.sql`

### API Service

```bash
# Start Flask API server (default: http://0.0.0.0:5000)
python run_api.py

# With custom settings
python run_api.py --port 8080 --host 0.0.0.0 --debug
```

### Offline Testing (`main.py`)

**Test by commenting/uncommenting scenarios (no CLI arguments needed)**

```bash
# Run directly (complete automation pipeline)
python main.py
```

**Automated Pipeline** (runs automatically on every execution):
1. **Initialize Database** - Create table schema and insert preset knowledge points
2. **Analyze Sample Code** - Extract code snippet features from `sample_code.java` and save to database
3. **Run Test Scenario** - Execute selected matching test

**How to use**:
1. Open `main.py`
2. Find the scenario selection area in Step 3 of `if __name__ == "__main__":`
3. Uncomment the desired scenario (remove `#`)
4. Modify `kp_ids` within scenario functions to test different knowledge points
5. Run `python main.py`

**Available scenarios**:
- **Scenario 1**: `run_single_test()` - Single knowledge point matching
- **Scenario 2**: `run_multiple_test()` - Composite knowledge point matching (find code involving multiple KPs)
- **Utility Functions**: `run_utility_functions()` - View KP hierarchy, analyze other code files

**Features**:
- All steps are idempotent (safe to run multiple times)
- Fully automated pipeline, no manual initialization needed
- Analyzes `./sample_code.java` by default (can be replaced)
- Configuration: `config/db.yaml`

**Example knowledge point IDs**: `10010, 10011, 10031, 10034, 10083` (print-related)

**Utility functions** (can be imported from `scripts.offline_tasks`):
- `init_database()` - Initialize database (called automatically in Step 1)
- `analyze_code_file(path)` - Analyze Java file (called automatically for sample_code.java in Step 2)
- `print_knowledge_tree()` - View KP hierarchy (included in utility scenario)
- `run_matching_test(kp_ids)` - Single/batch matching
- `run_composite_matching_test(kp_ids)` - Composite matching

## Architecture Overview

### Layered Architecture

The codebase follows a clean separation of concerns across 4 main layers:

```
Entry Points (run_api.py, main.py)
    ↓
API Layer (api/) + Offline Scripts (scripts/)
    ↓
Service Layer (src/services/) - shared by both API and offline
    ↓
Data/Analysis Layers (src/db_manager/, src/java_analyzer/, src/matching/)
    ↓
Infrastructure (lib/) - database pooling, logging, config
```

### Key Design Patterns

1. **Factory Pattern**: Flask app creation via `create_app()` in `api/__init__.py`
2. **Connection Pooling**: MySQL connection pool managed by `MySQLClient` in `lib/client/db.py`
3. **Shared Service Layer**: `src/services/` contains business logic reused by both API endpoints and offline tasks
4. **Lazy Singleton Config**: `lib/globals/__init__.py` loads configuration once on first access

### Core Components

#### 1. Java Analyzer (`src/java_analyzer/`)

- Uses tree-sitter-java to parse Java code into AST
- Extracts three types of keywords:
  - Language keywords (if, for, while, etc.)
  - API/method calls with prefix chains (System.out.println, Arrays.asList)
  - Type and exception names
- Features **alias normalization** via `CANONICAL_ALIASES` (e.g., "System.out.println" → "println")
- Includes **short method whitelist** (`SHORT_METHOD_WHITELIST`) for methods that should always be extracted
- Operates at **method declaration** level, not class/file level
- Returns list of snippets with: content, AST features, keywords, difficulty score

#### 2. Matching Strategy (`src/matching/strategies.py`)

Hybrid scoring algorithm with three components:

**AST Matching**:
- Maps knowledge point AST templates to tree-sitter node types via `NODE_MAPPING`
- Introduces **domain anchors** (`DOMAIN_ANCHORS`) - when template contains collection types (list, set, map), at least one anchor must match
- Calculates coverage ratio (matched nodes / template nodes)
- Default weight: 0.6

**Keyword Matching**:
- Weighted scoring system:
  - Core keywords (extends, implements, throws): 2.0x weight
  - General keywords: 1.0x weight
  - Ambiguous keywords (set, get, data): 0.5x weight (reduced to prevent false positives)
  - Name tokens from KP names: 0.8x weight
- Uses alias normalization for consistency
- Default weight: 0.3

**Difficulty Matching**:
- Calculates complexity based on AST node types and line count
- Supports "exact" or "relaxed" matching modes
- Default weight: 0.1

**Filtering Thresholds**:
- `ast_min_ratio`: Minimum AST coverage (default 0.4)
- `keyword_min_score`: Minimum keyword score (default 0.4)
- Snippets below thresholds get `final_score=0`

#### 3. Service Layer (`src/services/`)

**SearchService** (`search_service.py`):
- Main entry point for knowledge point matching
- **Single KP matching** (`search()` method):
  - Fetches KP templates and code snippets from database
  - Normalizes keywords using `CANONICAL_ALIASES`
  - Applies matching strategy and filtering
  - Returns top-k results sorted by score
- **Composite KP matching** (`composite_search()` method):
  - Finds code snippets involving multiple knowledge points
  - Calculates each snippet's score against each KP
  - Aggregates scores using: `average` (balanced), `min` (strict), or `sum` (coverage)
  - Returns snippets with highest composite scores
  - Use case: Find code demonstrating multiple concepts (e.g., loops + exception handling)
- **Service singleton**: Both API and offline tasks share a single instance via `_get_search_service()` (in offline tasks) or `get_search_service()` (in API routes) to avoid recreating connection pools

**KnowledgeService** (`knowledge_service.py`):
- Queries knowledge point hierarchy
- Builds tree structures for frontend display
- Handles parent-child relationships

#### 4. Database Layer (`src/db_manager/`)

Three main tables:
- `knowledge_points`: KP hierarchy with AST templates and keywords (JSON stored as TEXT)
- `code_files`: Java source files
- `code_snippets`: Extracted method-level snippets with features

Managers:
- `DatabaseInitializer`: Creates schema (does not populate data)
- `KnowledgePointManager`: CRUD for knowledge points
- `CodeLibraryManager`: CRUD for code files and snippets

#### 5. Infrastructure (`lib/`)

**Database Client** (`lib/client/db.py`):
- `MySQLClient` wraps mysql-connector-python with connection pooling
- Supports both auto-commit (single operations) and transactional (with statement) modes
- Methods: `fetch_one()`, `fetch_all()`, `execute()`, `execute_transaction()`

**Global Configuration** (`lib/globals/__init__.py`):
- Lazy-loads configuration from `config/db.yaml` and `config/logger.yaml`
- Provides singleton `Cfg` object and logger instances:
  - `core_logger`: Business logic (src/)
  - `api_logger`: API layer (api/)
  - Root `logger`: General use

**Settings** (`lib/utils/settings.py`):
- Parses YAML configuration files
- Validates database connection parameters

### Data Flow: Matching Request

1. API route receives POST to `/api/match` with `kp_id` and parameters
2. Route validates request using Pydantic schema (`api/schemas/match.py`)
3. Calls `SearchService.search(kp_id, ...)`
4. SearchService:
   - Fetches KP template from `KnowledgePointManager`
   - Retrieves candidate snippets from `CodeLibraryManager`
   - Normalizes keywords using `CANONICAL_ALIASES`
   - For each snippet, calls `calculate_match_score()` from matching strategy
   - Filters by thresholds (AST ratio, keyword score)
   - Sorts by final score and returns top-k
5. Route formats response using Pydantic schema and returns JSON

### Configuration Management

**Database Config** (`config/db.yaml`):
```yaml
db:
  javalearningsys:  # DB name (key becomes the identifier)
    host: localhost
    port: 3306
    user: root
    password: your_password
    db: javalearningsys
    charset: utf8mb4
    maxConn: 10
```

**Config Loading**:
- `config.py` at root extracts DB name from YAML (first key under `db:`)
- `lib/globals/` loads full config into `Cfg` singleton on first import
- Use `from lib.globals import Cfg` to access configuration
- Database name is available as `config.DB_NAME` (imported from root `config.py`)

### API Routes

Knowledge Point Endpoints (READ-ONLY):
- `GET /api/knowledge/tree` - Hierarchical tree structure
- `GET /api/knowledge/list` - Flat list of all KPs
- `GET /api/knowledge/{id}` - Single KP details
- `GET /api/knowledge/{id}/children` - Child KPs

Matching Endpoints:
- `POST /api/match` - Single KP matching with parameters
- `POST /api/match/batch` - Multiple KP matching (independent)
- `POST /api/match/composite` - Composite KP matching (find code involving multiple KPs)
- `GET /api/match/health` - Service health check

### Logging Strategy

- Separate loggers by layer: `core_logger`, `api_logger`
- Log levels configured in `config/logger.yaml`
- Core logic logs to `src/logs/`, API logs to `api/logs/`
- Database client logs debug-level SQL queries

### Important Constants

**AST Analysis** (`src/java_analyzer/constants.py`):
- `JAVA_KEYWORDS`: Reserved words to extract
- `COMPLEXITY_NODES`: AST node types that increase complexity
- `ALLOWED_PREFIX_PREFIXES`: API prefixes to retain (System, Arrays, Collections, logger)
- `SHORT_METHOD_WHITELIST`: Methods always extracted despite short names
- `CANONICAL_ALIASES`: Normalization map (e.g., System.out.println → println)

**Matching** (`src/matching/strategies.py`):
- `NODE_MAPPING`: Template names → tree-sitter node types
- `DOMAIN_ANCHORS`: Collection types requiring explicit match
- `JAVA_CORE_KEYWORDS`: High-weight keywords for scoring
- `AMBIGUOUS_KEYWORDS`: Low-weight keywords to reduce false positives

## Key Architectural Decisions

### Why Service Layer is Shared
Both API endpoints and offline scripts need identical business logic (e.g., matching algorithm). Service layer (`src/services/`) centralizes this to prevent duplication and ensure consistency.

### Why Method-Level Granularity
The analyzer extracts individual method declarations rather than entire files. This provides:
- Finer-grained matching (one method may demonstrate multiple concepts)
- More accurate difficulty scoring
- Better snippet reusability

### Why Alias Normalization
Java code may reference the same API in different ways:
- `System.out.println` vs `println` (after static import)
- `Arrays.asList` vs `asList`

Alias normalization ensures these variations match the same knowledge point keywords.

### Why Domain Anchors
Generic AST nodes (e.g., `type_identifier`) can appear in any code. Domain anchors (e.g., "set", "hashset") ensure that KPs about specific concepts only match snippets explicitly using those concepts.

### Why Connection Pooling
MySQL connections are expensive. Connection pooling in `MySQLClient`:
- Reuses connections across requests
- Handles concurrent API requests efficiently
- Supports both quick single queries and multi-statement transactions

## Dependencies

Core:
- **Flask** + **flask-cors**: Web framework and CORS support
- **Pydantic**: Request/response validation and serialization
- **mysql-connector-python**: MySQL driver with native connection pooling
- **tree-sitter** + **tree-sitter-java**: AST parsing for Java
- **PyYAML**: Configuration file parsing

Windows-specific:
- **pywin32**: Required on Windows for concurrent-log-handler
- **concurrent-log-handler**: Thread-safe logging to files

## Testing Notes

This repository does not currently include automated tests. When adding tests:
- Place unit tests in `tests/` directory
- Use pytest as the test runner
- Mock database connections using `unittest.mock` or `pytest-mock`
- Test matching algorithm with known KP-snippet pairs in `tests/fixtures/`

## Common Workflows

### Adding a New Knowledge Point Matching Algorithm

1. Add new matching function to `src/matching/strategies.py`
2. Update `calculate_match_score()` to call your function
3. Add new weight parameter to `WEIGHT_DEFAULTS` if needed
4. Update API schema in `api/schemas/match.py` to accept new parameters
5. Test via offline script: Uncomment relevant scenario in `main.py` and run `python main.py`

### Adding a New API Endpoint

1. Define request/response schemas in `api/schemas/`
2. Add route function to appropriate file in `api/routes/`
3. Register route in `api/routes/__init__.py` (if new route file)
4. Business logic goes in `src/services/`, not in route handler
5. Use appropriate logger: `from lib.globals import api_logger as log`

### Modifying AST Feature Extraction

1. Update `src/java_analyzer/analyzer.py` (extraction logic)
2. Update `src/java_analyzer/constants.py` (node types, keywords, aliases)
3. Update `src/matching/strategies.py` (NODE_MAPPING if templates change)
4. Re-analyze existing code files: Use `analyze_code_file()` from `scripts.offline_tasks`

### Using Composite Knowledge Point Matching

**When to use**: Find code snippets that demonstrate multiple programming concepts simultaneously.

**Steps**:
1. Open `main.py` and uncomment Scenario 2 (Composite matching)
2. Set `kp_ids` to list of relevant KPs (e.g., `[10011, 10012, 10034]`)
3. Choose aggregation strategy:
   - `average`: Balanced match across all KPs (recommended for general use)
   - `min`: Strict match - code must satisfy ALL KPs well
   - `sum`: Prefers code with broader KP coverage
4. Run `python main.py`

**API usage**:
```bash
curl -X POST http://localhost:5000/api/match/composite \
  -H "Content-Type: application/json" \
  -d '{"kp_ids": [10011, 10012], "score_aggregation": "average"}'
```

### Database Schema Changes

1. Modify table definitions in `src/db_manager/database.py` (`_init_tables()`)
2. Update manager classes in `src/db_manager/` for new fields
3. Run `python main.py` (database auto-initialization uses `CREATE TABLE IF NOT EXISTS`, safe to re-run)
4. For destructive changes, manually drop tables first or write migration script

## Files NOT to Edit

- `venv/`: Python virtual environment
- `logs/`: Generated log files
- `__pycache__/`: Python bytecode cache
- `sample_code.java`: Example file for testing (can be replaced for testing purposes)
- `kp_dml.sql`: Pre-populated knowledge points data (modify only if changing KP structure)
