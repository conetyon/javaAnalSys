<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Java knowledge point matching system that uses AST (Abstract Syntax Tree) analysis and keyword matching to identify Java code snippets that correspond to specific programming concepts. Built for a graduation project at BUPT (2026).

The system analyzes Java code files, extracts codegsnippets at the method level, and matches them against a knowledge point database using a hybrid scoring algorithm that combines:
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
# Complete database setup (recommended for first-time use)
python scripts/setup_database.py --all

# Step-by-step operations
python scripts/setup_database.py --init-schema      # Initialize tables
python scripts/setup_database.py --load-kp          # Load knowledge points
python scripts/setup_database.py --import-dataset   # Import CodeSearchNet dataset
```

**Automated Process**:
1. Database initialization (creates tables, inserts knowledge points)
2. Code analysis (extracts features from code snippets and saves to DB)
3. Both are idempotent - safe to run multiple times

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

### Evaluation and Testing

```bash
# Run complete evaluation (hybrid strategy + ablation study)
python scripts/run_experiments.py

# Quick evaluation (hybrid strategy only)
python scripts/run_experiments.py --quick

# Run only ablation study
python scripts/run_experiments.py --ablation-only

# Run unit tests for matching strategies
python tests/test_matching_strategies.py
```

**Evaluation Framework**:
- Ground truth dataset: `experiments/datasets/ground_truth/codesearchnet_v7.0-final.json` (99 test cases, 495 annotated snippets)
- Hybrid strategy: 96.97% Top-1 Accuracy
- Ablation study: Tests AST-only, Keyword-only, AST+Keyword, Full (AST+Keyword+Difficulty)
- Metrics: Top-1 Accuracy, Precision@K, Recall@K, F1@K, MRR, MAP
- Results: Saved to `experiments/results/report.md` and `report.json`
- **Key Finding**: Keyword 是最重要特征（单独 53.54%），AST 需要与其他特征组合发挥作用

**Example knowledge point IDs**: `10010, 10011, 10031, 10034, 10083` (print-related)

**Available scripts**:
- `scripts/setup_database.py` - Unified database setup entry point
- `scripts/run_experiments.py` - Run complete experiment pipeline

## Architecture Overview

### Layered Architecture

The codebase follows a clean separation of concerns across 4 main layers:

```
Entry Points (run_api.py, scripts/)
    ↓
API Layer (api/) + CLI Scripts (scripts/)
    ↓
Service Layer (src/services/) - shared by both API and scripts
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

**Automatic Fallback Logic** (v1.2.6+):
- When initial search returns 0 results with non-zero thresholds
- System automatically retries with thresholds reduced by 50% (e.g., 0.4 → 0.2)
- Fallback triggers only once per request
- Improves user experience by reducing empty results
- Logged as: `[SearchService.search] 未找到匹配结果，启用兜底逻辑（降低阈值重试）`

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
- **Matrix matching** (`matrix_search()` / `composite_matrix_search()` methods):
  - Groups matching results by difficulty level (easy/medium/hard)
  - Uses normalized weights without difficulty: `w_ast=0.22, w_keyword=0.78`
  - Difficulty is classification dimension, not scoring weight
  - Returns matrix format: `{"easy": [...], "medium": [...], "hard": [...]}`
  - Supports fallback logic and partial matching (same as list mode)
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
- `POST /api/match/matrix` - Single KP matching with difficulty-grouped matrix return
- `POST /api/match/composite/matrix` - Composite KP matching with difficulty-grouped matrix return
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

### Why Difficulty Parameter Despite Trade-off
The system includes a `difficulty` parameter (default weight 0.1) even though it may reduce pure semantic matching accuracy in some cases. This is an intentional design trade-off:
- **Current Performance**: Full (AST+KW+DIFF) = 96.97%, AST+KW = 63.64%
- **Improvement**: Difficulty 提升 33.33 个百分点，证明其有效性
- Real users have varying skill levels requiring difficulty-appropriate code examples
- Evaluation datasets only measure semantic relevance, not user preferences for code complexity
- For pure semantic matching, set `w_difficulty=0.0` in evaluation scripts or service layer calls (weights not exposed via HTTP API)
- The parameter adds valuable personalization capability for educational platforms

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

The repository includes both unit tests and a comprehensive evaluation framework:

**Unit Tests** (`tests/test_matching_strategies.py`):
- Tests AST score calculation (exact/partial/no match)
- Tests keyword scoring with domain anchors
- Tests end-to-end matching with realistic scenarios
- Run with: `python tests/test_matching_strategies.py`

**Evaluation Framework** (`experiments/evaluation/`):
- `ground_truth/codesearchnet_v7.0-final.json`: Auto-generated dataset (99 test cases, 495 snippets, using content_hash)
- `metrics.py`: Precision@K, Recall@K, F1@K, MRR, MAP, Top-1 Accuracy
- `experiment.py`: Orchestrates ablation studies and report generation

**Current Performance** (v7.0 dataset, 2026-01-25):
- **Hybrid Strategy**: 96.97% Top-1 Accuracy, 0.9832 MRR, 99.39% Recall@10
- **P@10 = 49.91%**: 接近理论最优（每个KP平均5个相关片段，上限50%）

**Adding New Tests**:
- Unit tests: Add to `tests/test_matching_strategies.py`
- Evaluation cases: Add to `experiments/ground_truth_codesearchnet.json` with format:
  ```json
  {
    "kp_id": 10011,
    "kp_name": "For loop",
    "relevant_snippet_ids": [1, 5, 8]
  }
  ```
- Mock database connections using `unittest.mock` for isolated testing

## Common Workflows

### Adding a New Knowledge Point Matching Algorithm

1. Add new matching function to `src/matching/strategies.py`
2. Update `calculate_match_score()` to call your function
3. Add new weight parameter to `WEIGHT_DEFAULTS` if needed
4. Update API schema in `api/schemas/match.py` to accept new parameters
5. Test via API: `curl -X POST http://localhost:5000/api/match -H "Content-Type: application/json" -d '{"kp_id": 10011}'`
6. Run evaluation to measure impact: `python scripts/run_experiments.py`

### Running and Validating Evaluations

1. Ensure database is initialized and CodeSearchNet dataset is imported: `python scripts/setup_database.py --import-dataset`
2. Run evaluation: `python scripts/run_experiments.py` (outputs to `experiments/results/report.md`)
3. Validate results against expected metrics (see README.md for current benchmarks)
4. Key metrics to check:
   - Top-1 Accuracy: Should be ≥95% for hybrid strategy
   - MRR: Should be ≥0.95
   - Recall@10: Should be ≥95%
   - **P@10 ≈ 50%**: 接近理论最优（Ground Truth 平均5个相关片段/KP）
5. For ablation studies, verify that Full configuration achieves ~97% Top-1 Accuracy

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
4. Re-analyze existing code files: `python scripts/setup_database.py --import-project ./code_repos`

### Using Matrix Mode Matching

**When to use**: Return results grouped by difficulty level (easy/medium/hard) for adaptive learning scenarios.

**Single KP Matrix**:
```bash
curl -X POST http://localhost:5000/api/match/matrix \
  -H "Content-Type: application/json" \
  -d '{"kp_id": 10011, "per_level": 5}'
```

**Composite KP Matrix**:
```bash
curl -X POST http://localhost:5000/api/match/composite/matrix \
  -H "Content-Type: application/json" \
  -d '{"kp_ids": [10011, 10012], "per_level": 5, "score_aggregation": "average"}'
```

**Key differences from list mode**:
- Difficulty is classification dimension, not scoring weight
- Weights normalized: `w_ast=0.22, w_keyword=0.78, w_difficulty=0.0`
- Response format: `{"matrix": {"easy": [...], "medium": [...], "hard": [...]}, "shape": [3, n]}`
- Composite matrix requires code to match ALL KPs; returns empty if no combined matches exist

### Using Composite Knowledge Point Matching

**When to use**: Find code snippets that demonstrate multiple programming concepts simultaneously.

**API usage**:
```bash
curl -X POST http://localhost:5000/api/match/composite \
  -H "Content-Type: application/json" \
  -d '{"kp_ids": [10011, 10012], "score_aggregation": "average"}'
```

**Aggregation strategies**:
- `average`: Balanced match across all KPs (recommended for general use)
- `min`: Strict match - code must satisfy ALL KPs well
- `sum`: Prefers code with broader KP coverage

### Database Schema Changes

1. Modify table definitions in `src/db_manager/database.py` (`_init_tables()`)
2. Update manager classes in `src/db_manager/` for new fields
3. Run `python scripts/setup_database.py --init-schema` to create/update tables
4. For clean reinstallation, drop the database first: `DROP DATABASE javalearningsys;`

**Note**: All table definitions include complete schema with all fields. The system uses `CREATE TABLE IF NOT EXISTS`, so it's safe to re-run initialization. For adding new fields to existing tables, consider dropping and recreating the database for experimental setups.

### Debugging Matching Issues

When matching results are unexpected:

1. **Check log levels**: Set `core_logger` to DEBUG in `config/logger.yaml` for detailed matching info
2. **Verify thresholds**: Default `ast_min_ratio=0.4, keyword_min_score=0.4` - check if fallback logic triggered
3. **Inspect domain anchors**: Look for "领域锚点约束未满足" in logs - this is normal and indicates protective filtering
4. **Validate keywords**: Check if `CANONICAL_ALIASES` in `src/java_analyzer/constants.py` includes expected method names
5. **Test without difficulty**: In evaluation scripts, set `w_difficulty=0.0` to isolate semantic matching issues (weights not configurable via HTTP API)
6. **Check AST templates**: Verify knowledge point `ast_template.required_nodes` in database match expected node types
7. **Run unit tests**: `python tests/test_matching_strategies.py` to verify core logic

### Understanding "Domain Anchor Constraint Not Met" Warnings

These warnings are **normal and expected**:
- Appear during the ranking phase when filtering candidates
- Example: Query "ArrayList basics" finds 22 candidates with `new XXX()`, but filters out 19 that don't contain "arraylist" or "list" keywords
- This prevents ArrayList knowledge points from matching HashMap/TreeMap code
- Indicates the protective mechanism is working correctly
- Does not indicate an error - only means a candidate was correctly rejected

## Files NOT to Edit

- `venv/`: Python virtual environment
- `logs/`: Generated log files
- `__pycache__/`: Python bytecode cache
- `sample_code.java`: Example file for testing (can be replaced for testing purposes)
- `kp_dml.sql`: Pre-populated knowledge points data (modify only if changing KP structure)

## Important System Defaults (v1.2.6+)

**Default Thresholds** (unified across all layers):
- `ast_min_ratio`: 0.4
- `keyword_min_score`: 0.4

**Default Weights** (production configuration):
- `w_ast`: 0.5 (AST structure matching)
- `w_keyword`: 0.4 (keyword semantic matching)
- `w_difficulty`: 0.1 (difficulty scoring)

**Note**: Weights are configured internally and NOT exposed via HTTP API:
- Service layer (`src/services/search_service.py`) - uses defaults
- Strategy layer (`src/matching/strategies.py`) - defines `WEIGHT_DEFAULTS`
- Evaluation scripts can override weights programmatically

**API-configurable parameters** (via HTTP request):
```json
{
  "kp_id": 10011,
  "target_difficulty": 0.5,
  "top_k": 10,
  "ast_min_ratio": 0.3,
  "keyword_min_score": 0.3
}
```

For experimental weight tuning, modify evaluation scripts directly:
```python
# In scripts/run_experiments.py or direct service calls
results = search_service.search(
    kp_id=10011,
    w_ast=0.5,
    w_keyword=0.5,
    w_difficulty=0.0  # Disable difficulty for pure semantic matching
)
```

## Recent Major Changes

**v1.3.5** (2026-02-24):
- **矩阵匹配模式**：新增 `/api/match/matrix` 和 `/api/match/composite/matrix` 端点
- **按难度分级返回**：easy/medium/hard 三级分桶，每级返回 top-n 结果
- **权重归一化**：矩阵模式使用 `w_ast=0.22, w_keyword=0.78`，难度不参与打分
- **OpenSpec 归档**：`2026-02-24-add-matrix-difficulty-matching`

**v1.3.3** (2026-02-07):
- **非叶子节点校验**：API 拒绝对分类节点（level!=3）进行匹配，返回明确错误信息
- **数据库备份**：DDL/DML 脚本备份
- **多知识点匹配修复**：修复 composite_search 的边界情况

**v1.3.1** (2026-01-31):
- **移除异步导入 API**：删除 `api/routes/bulk_import.py` 和 `lib/background_jobs.py`
- **简化架构**：CLI 脚本（`scripts/setup_database.py`）已足够满足项目导入需求
- **清理数据库表**：移除 `bulk_import_jobs` 表定义

**v1.3.0** (2026-01-25):
- **完整数据集评估**：使用 CodeSearchNet 子集（20,022 个片段，99 个测试用例）
- **实验结果更新**：Hybrid 96.97% Top-1 Accuracy
- **文档更新**：增加 P@10 说明

**v1.2.6** (2026-01-18):
- Added automatic fallback/retry logic when no results found
- Unified default thresholds across all layers (0.4, 0.4)
- Optimized logging output (reduced INFO logs by 70-80%)
- Added parameter validation logging for debugging

**v1.2.4** (2026-01-18):
- Completed comprehensive evaluation with 19 test cases
- Added fallback logic and weight optimization
- Achieved 94.74% Top-1 Accuracy (100% without difficulty parameter)

**v1.2.3** (2026-01-03):
- Fixed domain anchor bugs
- Added AST fallback mechanisms

See `CHANGELOG.md` for complete version history.
