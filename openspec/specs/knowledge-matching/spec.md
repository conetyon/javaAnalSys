# Knowledge Matching Capability

## Purpose
Hybrid scoring algorithm that matches code snippets to knowledge points using three weighted components: AST structure matching, keyword semantic matching, and difficulty/complexity alignment.
## Requirements
### Requirement: Hybrid Scoring Algorithm
The system SHALL calculate a final match score by combining AST score, keyword score, and difficulty score with configurable weights.

#### Scenario: Calculate final score with default weights
- **WHEN** a code snippet is matched against a knowledge point
- **THEN** the final score is computed as: `0.5 × ast_score + 0.4 × keyword_score + 0.1 × difficulty_score`

#### Scenario: Calculate final score with custom weights
- **WHEN** API request specifies `w_ast=0.5, w_keyword=0.5, w_difficulty=0.0`
- **THEN** the final score is computed using the custom weights
- **AND** difficulty matching is effectively disabled

### Requirement: AST Structure Matching
The system SHALL calculate AST similarity by mapping knowledge point templates to tree-sitter node types and computing coverage ratio.

#### Scenario: Full AST match
- **WHEN** a code snippet contains all required AST nodes from the template
- **THEN** the AST score is 1.0 (100% coverage)

#### Scenario: Partial AST match
- **WHEN** a code snippet contains 3 out of 5 required AST nodes
- **THEN** the AST score is 0.6 (60% coverage)

#### Scenario: No AST match
- **WHEN** a code snippet contains none of the required AST nodes
- **THEN** the AST score is 0.0

### Requirement: Domain Anchor Validation
The system SHALL enforce domain anchor constraints for collection-related knowledge points to prevent false positives.

#### Scenario: Domain anchor satisfied
- **WHEN** template contains collection node types AND snippet keywords include "arraylist" or "list"
- **THEN** domain anchor constraint is satisfied
- **AND** AST matching proceeds normally

#### Scenario: Domain anchor not satisfied
- **WHEN** template contains collection node types BUT snippet keywords lack any collection anchors
- **THEN** domain anchor constraint fails
- **AND** final score is set to 0.0 regardless of AST/keyword scores

#### Scenario: No domain anchor required
- **WHEN** template does not contain collection node types
- **THEN** domain anchor validation is skipped
- **AND** matching proceeds without anchor constraints

### Requirement: Keyword Semantic Matching
The system SHALL calculate keyword similarity using weighted scoring with different importance levels for different keyword types.

#### Scenario: Core keyword match
- **WHEN** snippet keywords include "extends", "implements", or "throws"
- **THEN** each core keyword contributes 2.0× weight to the keyword score

#### Scenario: General keyword match
- **WHEN** snippet keywords include "if", "for", "try", "catch"
- **THEN** each general keyword contributes 1.0× weight to the keyword score

#### Scenario: Ambiguous keyword match
- **WHEN** snippet keywords include "set", "get", "data"
- **THEN** each ambiguous keyword contributes 0.5× weight to the keyword score

#### Scenario: Name token match
- **WHEN** knowledge point name is "ArrayList basics" AND snippet contains "arraylist"
- **THEN** the name token contributes 0.8× weight to the keyword score

### Requirement: Difficulty Alignment
The system SHALL compare snippet complexity with knowledge point difficulty using exact or relaxed matching modes.

#### Scenario: Exact difficulty match
- **WHEN** snippet complexity is "intermediate" AND knowledge point difficulty is "intermediate"
- **THEN** difficulty score is 1.0

#### Scenario: Relaxed difficulty match
- **WHEN** snippet complexity is "advanced" AND knowledge point difficulty is "intermediate"
- **AND** matching mode is "relaxed"
- **THEN** difficulty score is 0.5 (partial credit)

#### Scenario: No difficulty match
- **WHEN** snippet complexity is "beginner" AND knowledge point difficulty is "advanced"
- **THEN** difficulty score is 0.0

### Requirement: Filtering Thresholds
The system SHALL filter out low-quality matches using minimum thresholds for AST ratio and keyword score.

#### Scenario: Both thresholds met
- **WHEN** snippet has AST ratio 0.6 and keyword score 0.5
- **AND** thresholds are `ast_min_ratio=0.4, keyword_min_score=0.4`
- **THEN** snippet is included in results with its calculated final score

#### Scenario: AST threshold not met
- **WHEN** snippet has AST ratio 0.3 and keyword score 0.6
- **AND** threshold is `ast_min_ratio=0.4`
- **THEN** snippet is excluded from results (final_score=0)

#### Scenario: Keyword threshold not met
- **WHEN** snippet has AST ratio 0.6 and keyword score 0.3
- **AND** threshold is `keyword_min_score=0.4`
- **THEN** snippet is excluded from results (final_score=0)

### Requirement: Automatic Fallback Logic
The system SHALL automatically retry searches with reduced thresholds when initial search returns zero results.

#### Scenario: Trigger fallback on zero results
- **WHEN** initial search with thresholds 0.4/0.4 returns 0 results
- **THEN** system automatically retries with thresholds reduced by 50% (0.2/0.2)
- **AND** logs fallback activation message

#### Scenario: No fallback on non-zero results
- **WHEN** initial search returns 1 or more results
- **THEN** fallback logic is not triggered
- **AND** original results are returned

#### Scenario: No fallback when thresholds already zero
- **WHEN** initial search uses thresholds 0.0/0.0 and returns 0 results
- **THEN** fallback logic is not triggered
- **AND** empty result set is returned

### Requirement: Single Knowledge Point Matching
The system SHALL rank and return top-K code snippets most relevant to a single knowledge point.

#### Scenario: Return top-5 matches
- **WHEN** search is performed with `top_k=5`
- **THEN** system returns up to 5 code snippets
- **AND** snippets are sorted by final score in descending order

#### Scenario: Insufficient matches
- **WHEN** only 3 snippets pass threshold filters
- **AND** `top_k=10` is requested
- **THEN** system returns only the 3 qualifying snippets

### Requirement: Composite Knowledge Point Matching
The system SHALL find code snippets demonstrating multiple knowledge points simultaneously using score aggregation strategies.

#### Scenario: Average aggregation for balanced match
- **WHEN** searching for snippets involving KPs [A, B, C]
- **AND** aggregation strategy is "average"
- **THEN** each snippet's composite score is the average of its scores against A, B, and C

#### Scenario: Min aggregation for strict match
- **WHEN** searching for snippets involving KPs [A, B, C]
- **AND** aggregation strategy is "min"
- **THEN** each snippet's composite score is the minimum of its scores against A, B, and C
- **AND** only snippets satisfying ALL knowledge points well are ranked highly

#### Scenario: Sum aggregation for coverage match
- **WHEN** searching for snippets involving KPs [A, B, C]
- **AND** aggregation strategy is "sum"
- **THEN** each snippet's composite score is the sum of its scores against A, B, and C
- **AND** snippets demonstrating more knowledge points are preferred

### Requirement: 矩阵模式打分策略

系统 SHALL 在矩阵模式下使用不同于列表模式的打分权重，移除难度权重以避免职责重叠。

#### Scenario: 矩阵模式权重归一化

- **WHEN** 使用矩阵匹配端点 (`/api/match/matrix` 或 `/api/match/composite/matrix`)
- **THEN** 系统使用归一化权重：`w_ast=0.22, w_keyword=0.78, w_difficulty=0.0`
- **AND** 难度不参与打分，仅作为分类维度

#### Scenario: 列表模式权重不变

- **WHEN** 使用列表匹配端点 (`/api/match` 或 `/api/match/composite`)
- **THEN** 系统继续使用原有权重：`w_ast=0.2, w_keyword=0.7, w_difficulty=0.1`
- **AND** 难度参与打分

### Requirement: 难度分桶逻辑

系统 SHALL 根据代码片段的难度值将其分配到对应的难度级别桶中。

#### Scenario: 默认三级分桶

- **WHEN** 片段难度值为 0.25
- **THEN** 片段被分配到 "easy" 桶（范围 [0, 0.33)）

#### Scenario: 中等难度分桶

- **WHEN** 片段难度值为 0.5
- **THEN** 片段被分配到 "medium" 桶（范围 [0.33, 0.66)）

#### Scenario: 高难度分桶

- **WHEN** 片段难度值为 0.8
- **THEN** 片段被分配到 "hard" 桶（范围 [0.66, 1.0]）

#### Scenario: 边界值处理

- **WHEN** 片段难度值恰好为 0.33
- **THEN** 片段被分配到 "medium" 桶（左闭右开区间）

### Requirement: 级别内排序

系统 SHALL 在每个难度级别内按语义相关性得分降序排列代码片段。

#### Scenario: 同一级别内按得分排序

- **WHEN** "easy" 级别有 3 个片段，得分分别为 0.8, 0.9, 0.7
- **THEN** 返回顺序为得分 0.9, 0.8, 0.7 的片段

#### Scenario: 得分相同时按 ID 排序

- **WHEN** 两个片段得分相同
- **THEN** 按片段 ID 升序排列，保证结果稳定性

## Implementation Details

### Matching Strategy
- Implementation: src/matching/strategies.py:1
- Main function: `calculate_match_score()` at src/matching/strategies.py:150
- Weights: `WEIGHT_DEFAULTS` at src/matching/strategies.py:23

### Node Mapping
- Template to tree-sitter mapping: `NODE_MAPPING` at src/matching/strategies.py:31
- Domain anchors: `DOMAIN_ANCHORS` at src/matching/strategies.py:55

### Keyword Weights
- Core keywords: `JAVA_CORE_KEYWORDS` at src/matching/strategies.py:67 (weight 2.0)
- Ambiguous keywords: `AMBIGUOUS_KEYWORDS` at src/matching/strategies.py:75 (weight 0.5)
- General keywords: Default weight 1.0
- Name tokens: Weight 0.8

### Search Service
- Single KP matching: `SearchService.search()` at src/services/search_service.py:50
- Composite matching: `SearchService.composite_search()` at src/services/search_service.py:200
- Fallback logic: src/services/search_service.py:100

## Performance Metrics

### Current Performance (v1.3.3, CodeSearchNet dataset)
- **Top-1 Accuracy**: 96.97%
- **Mean Reciprocal Rank (MRR)**: 0.9832
- **Precision@10**: 49.91%
- **Recall@10**: 99.39%
- **F1@10**: 66.49%

### Baseline Comparisons
- **vs TF-IDF**: +95.96 percentage points (1.01% → 96.97%)
- **vs Pure AST**: +96.97 percentage points (0.00% → 96.97%)
- **vs Random**: +96.97 percentage points (0.00% → 96.97%)

### Ablation Study Results
- **AST-only**: 0.00% Top-1 Accuracy
- **Keyword-only**: 53.54% Top-1 Accuracy
- **AST + Keyword**: 63.64% Top-1 Accuracy
- **Full (AST + Keyword + Difficulty)**: 96.97% Top-1 Accuracy
- **Key Insight**: Keyword is the most important feature; difficulty improves by 33.33 percentage points

## Dependencies
- tree-sitter node types for AST mapping
- Knowledge point templates from database
- Code snippet features from database
