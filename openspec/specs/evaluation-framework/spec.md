# Evaluation Framework Capability

## Purpose
Graded rule-based evaluation system for measuring matching algorithm performance using defined rules, multiple metrics, and ablation studies.

## Requirements

### Requirement: Graded Rule-Based Evaluation
The system SHALL use rule-based grading (Grade 0/1/2) instead of manual Ground Truth annotation.

#### Scenario: Grade calculation based on rules
- **WHEN** a code snippet is evaluated against a KP rule
- **THEN** system assigns Grade 2 (highly relevant), Grade 1 (partially relevant), or Grade 0 (not relevant)
- **AND** grading uses AST features, keywords, method names, and code length

#### Scenario: Grade 2 determination
- **WHEN** snippet has explicit naming match OR high density (≥10%) OR multiple occurrences
- **AND** snippet is within acceptable length range
- **THEN** snippet is graded as Grade 2 (highly relevant)

#### Scenario: Grade 1 determination
- **WHEN** snippet contains required AST nodes and keywords
- **BUT** doesn't meet Grade 2 criteria
- **THEN** snippet is graded as Grade 1 (partially relevant)

#### Scenario: Grade 0 determination
- **WHEN** snippet lacks required AST nodes OR required keywords
- **THEN** snippet is graded as Grade 0 (not relevant)

### Requirement: Binary Precision Metric
The system SHALL calculate Binary Precision as the proportion of relevant results (G1+G2) among all results.

#### Scenario: Calculate Binary Precision
- **WHEN** top-10 results contain 9 relevant snippets (G1 or G2) and 1 irrelevant (G0)
- **THEN** Binary Precision is 90%

#### Scenario: Perfect Binary Precision
- **WHEN** all results are G1 or G2 (no G0)
- **THEN** Binary Precision is 100%

### Requirement: Graded Precision Metric
The system SHALL calculate Graded Precision as (2×G2 + G1) / (2×K).

#### Scenario: Calculate Graded Precision with mixed grades
- **WHEN** top-10 results contain G2=2, G1=7, G0=1
- **THEN** Graded Precision is (2×2 + 7) / (2×10) = 11/20 = 55%

#### Scenario: Calculate Graded Precision with all G2
- **WHEN** all 10 results are Grade 2
- **THEN** Graded Precision is (2×10 + 0) / (2×10) = 100%

#### Scenario: Calculate Graded Precision with all G1
- **WHEN** all 10 results are Grade 1
- **THEN** Graded Precision is (2×0 + 10) / (2×10) = 50%

### Requirement: nDCG@K Metric
The system SHALL calculate nDCG@K to measure ranking quality with graded relevance.

#### Scenario: Calculate nDCG@10
- **WHEN** results have grades [2, 2, 1, 1, 1, 1, 1, 0, 0, 0]
- **THEN** system calculates DCG and ideal DCG
- **AND** nDCG = DCG / IDCG

#### Scenario: Perfect ranking
- **WHEN** all G2 results are ranked before G1, all G1 before G0
- **THEN** nDCG is 1.0

### Requirement: Ablation Study - Weight Configurations
The system SHALL support ablation studies testing different weight configurations.

#### Scenario: Test Full configuration
- **WHEN** weights are `w_ast=0.2, w_keyword=0.7, w_difficulty=0.1`
- **THEN** system evaluates with production configuration

#### Scenario: Test AST + Keyword configuration
- **WHEN** weights are `w_ast=0.3, w_keyword=0.7, w_difficulty=0.0`
- **THEN** system evaluates without difficulty component

#### Scenario: Test Keyword + Difficulty configuration
- **WHEN** weights are `w_ast=0.0, w_keyword=0.9, w_difficulty=0.1`
- **THEN** system evaluates without AST component

#### Scenario: Test AST Only configuration
- **WHEN** weights are `w_ast=1.0, w_keyword=0.0, w_difficulty=0.0`
- **THEN** system evaluates structural matching only

#### Scenario: Test Keyword Only configuration
- **WHEN** weights are `w_ast=0.0, w_keyword=1.0, w_difficulty=0.0`
- **THEN** system evaluates semantic matching only

### Requirement: Evaluation Report Generation
The system SHALL generate comprehensive evaluation reports in both Markdown and JSON formats.

#### Scenario: Generate Markdown report
- **WHEN** evaluation completes
- **THEN** report is saved to `experiments/results/report.md`
- **AND** report includes Binary Precision, Graded Precision, nDCG
- **AND** report includes grade distribution (G2, G1, G0 counts)

#### Scenario: Generate JSON report
- **WHEN** evaluation completes
- **THEN** report is saved to `experiments/results/report.json`
- **AND** report contains per-KP metrics and ablation results

#### Scenario: Save to database
- **WHEN** evaluation completes
- **THEN** results are saved to `experiment_runs` table
- **AND** results include config, metrics, and timestamp

### Requirement: Quick Evaluation Mode
The system SHALL support a quick evaluation mode that skips ablation studies.

#### Scenario: Run quick evaluation
- **WHEN** script is run with `--quick` flag
- **THEN** only main evaluation is run (no ablation)
- **AND** execution completes faster

### Requirement: Pilot Evaluation Mode
The system SHALL support evaluating only Pilot KPs for rapid testing.

#### Scenario: Run pilot evaluation
- **WHEN** script is run with `--pilot` flag
- **THEN** only 5 Pilot KPs are evaluated
- **AND** results validate rule definitions

## Implementation Details

### Evaluation Scripts
- Main entry: `scripts/run_experiments.py`
- Internal runner: `scripts/_internal/run_evaluation.py`

### Rules Implementation
- Rule definitions: `experiments/evaluation/rules.py`
- 56 KP rules with Grade 0/1/2 criteria
- Functions: `calculate_feature_grade()`, `get_all_kp_ids()`, `KP_RULES`

### Configuration
- Weight configuration: `config/matching.yaml`
- Default weights: AST=0.2, Keyword=0.7, Difficulty=0.1

### Results Storage
- Markdown reports: `experiments/results/report.md`
- JSON reports: `experiments/results/report.json`
- Database: `experiment_runs` table

## Current Performance Benchmarks (v1.3.4, 2026-02-07)

### Production Configuration (AST=0.2, KW=0.7, DIFF=0.1)
- **Binary Precision**: 98.0%
- **Graded Precision**: 58.4%
- **nDCG@10**: 0.874
- **G0 (Irrelevant)**: 2.0% (11/554)

### Grade Distribution
- **G2 (Highly Relevant)**: 18.8% (104 snippets)
- **G1 (Partially Relevant)**: 79.2% (439 snippets)
- **G0 (Not Relevant)**: 2.0% (11 snippets)

### Ablation Study Results
| Config | Binary P | Graded P | G2 | G1 | G0 |
|--------|----------|----------|----|----|-----|
| Full (AST+KW+DIFF) | 98.0% | 58.4% | 104 | 439 | 11 |
| AST + Keyword | 98.0% | 58.5% | 105 | 438 | 11 |
| Keyword + Difficulty | 97.5% | 57.8% | 100 | 440 | 14 |
| Keyword Only | 97.7% | 59.2% | 115 | 426 | 13 |
| AST + Difficulty | 57.4% | 32.4% | 41 | 277 | 236 |
| AST Only | 55.8% | 32.3% | 49 | 260 | 245 |

### Key Insights
- **Keyword is most important feature**: 97.7% Binary Precision standalone
- **AST adds limited value alone**: 55.8% Binary Precision
- **Full config stable**: 98.0% with good ranking quality (nDCG=0.874)

## Command-Line Usage

### Run Complete Evaluation
```bash
python scripts/_internal/run_evaluation.py
```

### Run Quick Evaluation (Skip Ablation)
```bash
python scripts/_internal/run_evaluation.py --quick
```

### Run Pilot Evaluation (5 KPs Only)
```bash
python scripts/_internal/run_evaluation.py --pilot
```

## Dependencies
- Rules: `experiments/evaluation/rules.py`
- Code library: MySQL database with `code_snippets` table
- Matching strategy: `src/matching/strategies.py`
- Search service: `src/services/search_service.py`
