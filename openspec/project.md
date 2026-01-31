# Project Context

## Purpose
Java knowledge point matching system for educational purposes. The system analyzes Java code using AST (Abstract Syntax Tree) parsing and matches code snippets to specific programming concepts through a hybrid scoring algorithm. Built as a graduation project for BUPT (2026).

**Core Value Proposition**: Automatically identify which Java programming concepts (e.g., loops, exception handling, collections) are demonstrated in code snippets with 96.97% accuracy.

## Tech Stack
- **Language**: Python 3.8+
- **AST Parsing**: tree-sitter-java (Java code analysis)
- **Web Framework**: Flask + flask-cors (REST API)
- **Database**: MySQL 8.0+ with mysql-connector-python
- **Validation**: Pydantic (request/response schemas)
- **Configuration**: PyYAML (YAML-based config)
- **Logging**: concurrent-log-handler (thread-safe file logging)
- **Platform**: Cross-platform (Windows/Linux/macOS)

## Project Conventions

### Code Style
- **Python Style**: PEP 8 compliant
- **Import Order**: Standard library → Third-party → Local modules
- **Naming**:
  - Classes: PascalCase (`SearchService`, `MySQLClient`)
  - Functions/methods: snake_case (`calculate_match_score`, `get_knowledge_point`)
  - Constants: UPPER_SNAKE_CASE (`NODE_MAPPING`, `JAVA_KEYWORDS`)
  - Private methods: Leading underscore (`_init_tables`, `_get_search_service`)
- **String Formatting**: f-strings preferred for readability
- **Docstrings**: Google style for public APIs
- **Line Length**: 120 characters max (relaxed from PEP 8's 79)

### Architecture Patterns
- **Layered Architecture**:
  ```
  Entry Points (run_api.py, scripts/)
      ↓
  API Layer (api/) + CLI Scripts (scripts/)
      ↓
  Service Layer (src/services/) - shared business logic
      ↓
  Data/Analysis Layers (src/db_manager/, src/java_analyzer/, src/matching/)
      ↓
  Infrastructure (lib/) - database pooling, logging, config
  ```
- **Factory Pattern**: Flask app creation via `create_app()`
- **Connection Pooling**: Singleton MySQL client with pool management
- **Lazy Singleton**: Configuration loaded once on first access
- **Shared Service Layer**: Business logic reused by both API and offline tasks
- **Granularity**: Method-level code analysis (not class/file level)

### Testing Strategy
- **Unit Tests**: Core matching logic (`tests/test_matching_strategies.py`)
- **Evaluation Framework**: Comprehensive metrics with ground truth dataset
  - Dataset: CodeSearchNet subset (99 test cases, 495 annotated snippets, 20,022 total snippets)
  - Metrics: Top-1 Accuracy, Precision@K, Recall@K, F1@K, MRR, MAP
  - Current performance: 96.97% Top-1 Accuracy (v1.3.1)
- **Baselines**: TF-IDF (1.01%), Pure AST (0.00%), Random (0.00%)
- **Ablation Studies**: Test individual components (AST-only, Keyword-only, Full)
- **Idempotent Operations**: Database init and data loading safe to re-run

### Git Workflow
- **Main Branch**: `main` (stable, deployment-ready)
- **Commit Messages**: Imperative mood with context
  - Format: `<type>: <description>` (e.g., `fix: domain anchor validation`, `feat: add fallback logic`)
  - Include co-authorship: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`
- **Version Tags**: Semantic versioning (v1.3.0, v1.2.6, etc.)
- **Changelog**: Track changes in `CHANGELOG.md` with version sections

## Domain Context

### Knowledge Point Hierarchy
- **Three-level structure**: L1 (category) → L2 (subcategory) → L3 (specific concepts)
- Example: "Language Basics" → "Control Flow" → "For loop"
- Each knowledge point has:
  - AST template (required AST node types)
  - Keywords (method calls, language keywords, type names)
  - Difficulty score (beginner/intermediate/advanced)
  - Parent-child relationships

### Matching Algorithm (Hybrid Strategy)
**Three components with weights**:
1. **AST Matching (w_ast=0.5)**: Structural similarity
   - Maps templates to tree-sitter node types via `NODE_MAPPING`
   - Requires domain anchors for collection types (prevents false positives)
   - Calculates coverage ratio (matched nodes / template nodes)
2. **Keyword Matching (w_keyword=0.4)**: Semantic similarity
   - Weighted scoring: Core keywords (2.0x), General (1.0x), Ambiguous (0.5x)
   - Alias normalization (e.g., `System.out.println` → `println`)
   - Name tokens from KP names (0.8x weight)
3. **Difficulty Matching (w_difficulty=0.1)**: Complexity alignment
   - Calculates complexity from AST nodes and line count
   - Supports exact or relaxed matching modes

**Filtering Thresholds**:
- `ast_min_ratio=0.4`: Minimum AST coverage
- `keyword_min_score=0.4`: Minimum keyword score
- Automatic fallback: Retry with 50% reduced thresholds when no results found

### Educational Context
- **Target Audience**: Java learners (beginner to intermediate)
- **Use Case**: Find code examples demonstrating specific programming concepts
- **Composite Matching**: Find code involving multiple concepts (e.g., loops + exception handling)
- **Difficulty Personalization**: Match code complexity to learner skill level

## Important Constraints

### Technical Constraints
- **Method-Level Granularity**: Analysis operates on method declarations, not classes/files
- **MySQL Limitations**: JSON stored as TEXT (not native JSON type for compatibility)
- **AST Parser**: tree-sitter-java coverage limited to standard Java syntax
- **Short Method Whitelist**: Some methods (get, set, add) require explicit inclusion to extract
- **Alias Normalization**: Must keep `CANONICAL_ALIASES` updated with common API patterns

### Performance Constraints
- **Database Connection Pool**: Max 10 connections (configurable)
- **API Response Time**: Target <500ms for single KP matching
- **Evaluation Dataset**: 20,022 snippets for comprehensive testing
- **Concurrent Requests**: Flask development server (single-threaded)

### Data Constraints
- **Knowledge Points**: Pre-populated via `kp_dml.sql` (53 KPs in baseline)
- **Code Snippets**: Extracted at method level with features stored in DB
- **Ground Truth**: 99 test cases with 495 manually annotated snippets

## External Dependencies

### Database
- **MySQL 8.0+**: Primary data store for knowledge points and code snippets
- **Configuration**: `config/db.yaml` (host, port, credentials, pool size)
- **Schema Management**: Automatic via `DatabaseInitializer` (idempotent)

### AST Parsing
- **tree-sitter**: Universal parsing library (MIT license)
- **tree-sitter-java**: Java grammar definitions
- **Node Types**: 50+ node types mapped to templates (if_statement, for_statement, etc.)

### API Clients (Optional)
- None (no external API dependencies)
- System operates entirely offline once data is loaded

### Development Tools
- **pytest**: Unit testing framework
- **ruff**: Fast Python linter (optional)
- **mypy**: Static type checker (optional)

## File Organization

### Core Directories
- `api/` - Flask API layer (routes, schemas)
- `src/` - Core business logic (services, analyzers, matching)
- `lib/` - Infrastructure (DB client, config, logging)
- `scripts/` - Offline tasks (data init, evaluation, experiments)
- `tests/` - Unit tests
- `experiments/` - Evaluation framework and datasets
- `config/` - Configuration files (db.yaml, logger.yaml)

### Data Directories
- `experiments/datasets/` - Ground truth and processed datasets
- `experiments/results/` - Evaluation reports and metrics
- `src/logs/` - Core business logic logs
- `api/logs/` - API request/response logs

### Configuration Files
- `config/db.yaml` - Database connection settings
- `config/logger.yaml` - Logging configuration (levels, handlers, formatters)
- `requirements.txt` - Python dependencies
- `sample_code.java` - Example file for testing
- `kp_dml.sql` - Knowledge points baseline data

## Documentation References
- `CLAUDE.md` - Comprehensive developer guide for Claude Code
- `README.md` - User-facing documentation and quickstart
- `CHANGELOG.md` - Version history and release notes
- `openspec/AGENTS.md` - OpenSpec workflow for AI assistants
