# Java AST Analysis Capability

## Purpose
Parses Java source code into Abstract Syntax Trees (AST) using tree-sitter-java and extracts structural features, keywords, and complexity metrics at the method declaration level.

## Requirements

### Requirement: Method-Level Code Parsing
The system SHALL parse Java source files and extract individual method declarations as separate code snippets for analysis.

#### Scenario: Parse Java file with multiple methods
- **WHEN** a Java file containing 3 methods is analyzed
- **THEN** the system extracts 3 separate code snippets
- **AND** each snippet contains only one method declaration with its body

#### Scenario: Ignore non-method code
- **WHEN** a Java file contains class fields, constructors, and inner classes
- **THEN** the system only extracts method declarations
- **AND** ignores fields, constructors, and inner classes

### Requirement: AST Node Type Extraction
The system SHALL extract AST node types from parsed methods and categorize them according to the tree-sitter-java grammar.

#### Scenario: Extract control flow nodes
- **WHEN** a method contains if-else statements and for loops
- **THEN** the extracted AST features include `if_statement`, `else_clause`, and `for_statement` node types

#### Scenario: Extract exception handling nodes
- **WHEN** a method contains try-catch-finally blocks
- **THEN** the extracted AST features include `try_statement`, `catch_clause`, and `finally_clause` node types

### Requirement: Keyword Extraction
The system SHALL extract three categories of keywords from code snippets: language keywords, API/method calls, and type names.

#### Scenario: Extract language keywords
- **WHEN** a method uses `if`, `for`, `while`, `return`, `throw`
- **THEN** all reserved Java keywords are included in the keyword list

#### Scenario: Extract API calls with prefix chains
- **WHEN** a method calls `System.out.println()`, `Arrays.asList()`, `Collections.sort()`
- **THEN** method calls are extracted with their prefix chains
- **AND** prefixes are retained only if in `ALLOWED_PREFIX_PREFIXES` (System, Arrays, Collections, logger)

#### Scenario: Extract type names
- **WHEN** a method declares variables with types `ArrayList`, `HashMap`, `Exception`
- **THEN** all type names are extracted as keywords

### Requirement: Alias Normalization
The system SHALL normalize API method calls to canonical forms to handle static imports and different calling patterns.

#### Scenario: Normalize println variants
- **WHEN** code uses `System.out.println` or `println` (via static import)
- **THEN** both are normalized to the canonical form `println`

#### Scenario: Normalize collection API variants
- **WHEN** code uses `Arrays.asList` or `asList` (via static import)
- **THEN** both are normalized to the canonical form `asList`

### Requirement: Short Method Whitelist
The system SHALL extract short method names (≤3 characters) only if they appear in the `SHORT_METHOD_WHITELIST`.

#### Scenario: Extract whitelisted short methods
- **WHEN** code contains `add()`, `get()`, `set()`, `put()`, `pop()`
- **THEN** these methods are extracted because they are in the whitelist

#### Scenario: Ignore non-whitelisted short methods
- **WHEN** code contains custom short methods like `foo()`, `bar()`, `baz()`
- **THEN** these methods are excluded from keyword extraction

### Requirement: Complexity Scoring
The system SHALL calculate a complexity/difficulty score based on AST node types and line count.

#### Scenario: Calculate low complexity
- **WHEN** a method has 5 lines with only basic statements and one if-statement
- **THEN** the difficulty score is categorized as "beginner" or low numeric value

#### Scenario: Calculate high complexity
- **WHEN** a method has 50+ lines with nested loops, exception handling, and multiple conditional branches
- **THEN** the difficulty score is categorized as "advanced" or high numeric value

### Requirement: Idempotent Analysis
The system SHALL support re-analyzing the same code file multiple times without creating duplicate entries in the database.

#### Scenario: Re-analyze existing file
- **WHEN** the same Java file is analyzed twice
- **THEN** existing code snippets are updated rather than duplicated
- **AND** snippet IDs remain stable across re-analysis

## Implementation Details

### Node Type Categories
- **Control Flow**: if_statement, for_statement, while_statement, switch_statement, enhanced_for_statement
- **Exception Handling**: try_statement, catch_clause, finally_clause, throw_statement, throws
- **Collections**: Uses `DOMAIN_ANCHORS` for collection-related types (list, set, map, hashset, arraylist, hashmap)
- **Complexity Nodes**: All control flow, exception handling, lambda expressions, stream operations

### Constants Location
- `JAVA_KEYWORDS`: src/java_analyzer/constants.py:8
- `COMPLEXITY_NODES`: src/java_analyzer/constants.py:45
- `ALLOWED_PREFIX_PREFIXES`: src/java_analyzer/constants.py:73
- `SHORT_METHOD_WHITELIST`: src/java_analyzer/constants.py:76
- `CANONICAL_ALIASES`: src/java_analyzer/constants.py:82

### Core Analyzer
- Implementation: src/java_analyzer/analyzer.py:1
- Main function: `analyze_java_file()` at src/java_analyzer/analyzer.py:120

## Dependencies
- tree-sitter: Universal parsing library (MIT license)
- tree-sitter-java: Java grammar definitions
- Python 3.8+: Core language
