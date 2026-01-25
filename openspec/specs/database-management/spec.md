# Database Management Capability

## Purpose
Manages MySQL database schema, connection pooling, and CRUD operations for knowledge points, code files, and code snippets. Supports both auto-commit single operations and transactional multi-statement operations.

## Requirements

### Requirement: Database Schema Initialization
The system SHALL create required database tables using `CREATE TABLE IF NOT EXISTS` statements to support idempotent initialization.

#### Scenario: Initialize fresh database
- **WHEN** initialization is run on an empty database
- **THEN** tables `knowledge_points`, `code_files`, and `code_snippets` are created

#### Scenario: Initialize existing database
- **WHEN** initialization is run on a database with existing tables
- **THEN** no error occurs and existing tables remain unchanged
- **AND** no data is lost

### Requirement: Knowledge Point Management
The system SHALL support CRUD operations for knowledge points with hierarchical relationships and JSON-encoded features.

#### Scenario: Insert knowledge point
- **WHEN** a new knowledge point is created with name, parent_id, AST template, and keywords
- **THEN** the knowledge point is stored with auto-generated kp_id
- **AND** AST template and keywords are stored as JSON in TEXT fields

#### Scenario: Query knowledge point by ID
- **WHEN** querying knowledge point with kp_id=10011
- **THEN** system returns complete knowledge point data including JSON features

#### Scenario: Query child knowledge points
- **WHEN** querying children of parent_id=100
- **THEN** system returns all knowledge points where parent_id=100
- **AND** results are ordered by kp_id

#### Scenario: Build knowledge point tree
- **WHEN** building a hierarchical tree structure
- **THEN** system recursively fetches parent-child relationships
- **AND** returns nested tree with all three levels (L1→L2→L3)

### Requirement: Code Library Management
The system SHALL manage code files and extracted code snippets with their analyzed features.

#### Scenario: Insert code file
- **WHEN** a Java source file is imported
- **THEN** file metadata is stored in `code_files` table
- **AND** file content is stored as TEXT

#### Scenario: Insert code snippets
- **WHEN** code snippets are extracted from a file
- **THEN** each snippet is stored with its file_id, content, line range, AST features, keywords, and difficulty
- **AND** AST features and keywords are stored as JSON in TEXT fields

#### Scenario: Query snippets by file
- **WHEN** querying snippets for file_id=5
- **THEN** system returns all snippets belonging to that file
- **AND** snippets are ordered by start_line

### Requirement: Connection Pooling
The system SHALL maintain a connection pool to efficiently handle concurrent database operations.

#### Scenario: Initialize connection pool
- **WHEN** MySQL client is first instantiated
- **THEN** a connection pool is created with configured pool size (default 10)
- **AND** connection parameters are loaded from config/db.yaml

#### Scenario: Reuse pooled connections
- **WHEN** multiple database queries are executed
- **THEN** connections are acquired from the pool
- **AND** connections are returned to the pool after use
- **AND** no new connections are created if pool limit is not reached

#### Scenario: Handle connection pool exhaustion
- **WHEN** all pool connections are in use
- **AND** a new query is requested
- **THEN** the query waits for an available connection
- **OR** times out with appropriate error message

### Requirement: Transaction Support
The system SHALL support multi-statement transactions with commit/rollback capability.

#### Scenario: Execute transaction with commit
- **WHEN** multiple INSERT/UPDATE statements are executed in a transaction block
- **AND** all statements succeed
- **THEN** transaction is committed
- **AND** all changes are persisted to database

#### Scenario: Execute transaction with rollback
- **WHEN** multiple statements are executed in a transaction block
- **AND** any statement fails
- **THEN** transaction is rolled back
- **AND** no changes are persisted to database

### Requirement: Auto-Commit Mode
The system SHALL support single-operation auto-commit mode for simple queries.

#### Scenario: Execute single SELECT query
- **WHEN** a SELECT query is executed via `fetch_one()` or `fetch_all()`
- **THEN** query executes in auto-commit mode
- **AND** connection is returned to pool immediately after result is fetched

#### Scenario: Execute single INSERT query
- **WHEN** an INSERT query is executed via `execute()`
- **THEN** query executes and commits automatically
- **AND** connection is returned to pool immediately

### Requirement: Idempotent Data Loading
The system SHALL support loading knowledge points from SQL files without creating duplicates.

#### Scenario: Load knowledge points first time
- **WHEN** knowledge points are loaded from kp_dml.sql
- **THEN** all knowledge points are inserted into the database

#### Scenario: Load knowledge points again
- **WHEN** knowledge points are loaded a second time
- **THEN** duplicate key errors are ignored
- **AND** existing knowledge points remain unchanged

### Requirement: JSON Feature Storage
The system SHALL store AST templates and keyword lists as JSON-encoded TEXT fields for MySQL compatibility.

#### Scenario: Store AST template
- **WHEN** knowledge point has AST template `{"required_nodes": ["if_statement", "for_statement"]}`
- **THEN** template is stored as JSON TEXT in `ast_template` column
- **AND** can be retrieved and parsed back to Python dict

#### Scenario: Store keywords
- **WHEN** code snippet has keywords `["if", "for", "println", "ArrayList"]`
- **THEN** keywords are stored as JSON TEXT in `keywords` column
- **AND** can be retrieved and parsed back to Python list

## Implementation Details

### Database Schema
- Schema initialization: src/db_manager/database.py:20 (`DatabaseInitializer._init_tables()`)
- Tables:
  - `knowledge_points`: kp_id, parent_id, name, description, level, ast_template (TEXT), keywords (TEXT), difficulty, created_at
  - `code_files`: file_id, file_name, file_path, file_type, created_at
  - `code_snippets`: snippet_id, file_id, content, content_hash, start_line, end_line, ast_features (TEXT), keywords (TEXT), difficulty, created_at

### Manager Classes
- Knowledge point operations: src/db_manager/knowledge_point_manager.py:1
- Code library operations: src/db_manager/code_library_manager.py:1
- Database initialization: src/db_manager/database.py:1

### MySQL Client
- Connection pooling: lib/client/db.py:1
- Methods:
  - `fetch_one(sql, params)`: Single row query
  - `fetch_all(sql, params)`: Multi-row query
  - `execute(sql, params)`: Single statement (auto-commit)
  - `execute_transaction(statements)`: Multi-statement transaction

### Configuration
- Database config: config/db.yaml
- Config loader: lib/globals/__init__.py:1
- Settings parser: lib/utils/settings.py:1

## Database Schema

### knowledge_points table
```sql
CREATE TABLE IF NOT EXISTS knowledge_points (
    kp_id INT PRIMARY KEY AUTO_INCREMENT,
    parent_id INT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    level INT NOT NULL,
    ast_template TEXT,
    keywords TEXT,
    difficulty VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### code_files table
```sql
CREATE TABLE IF NOT EXISTS code_files (
    file_id INT PRIMARY KEY AUTO_INCREMENT,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT,
    file_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### code_snippets table
```sql
CREATE TABLE IF NOT EXISTS code_snippets (
    snippet_id INT PRIMARY KEY AUTO_INCREMENT,
    file_id INT NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64),
    start_line INT,
    end_line INT,
    ast_features TEXT,
    keywords TEXT,
    difficulty VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES code_files(file_id)
);
```

## Dependencies
- mysql-connector-python: MySQL driver with native connection pooling
- PyYAML: Configuration file parsing
- Python 3.8+: Core language
