# Evaluation Framework Capability

## Purpose
Comprehensive testing and evaluation system for measuring matching algorithm performance using ground truth datasets, multiple metrics, and ablation studies.

## Requirements

### Requirement: Ground Truth Dataset Management
The system SHALL maintain a curated dataset with manually annotated code snippet relevance for knowledge point evaluation.

#### Scenario: Load ground truth dataset
- **WHEN** evaluation script loads ground truth from JSON file
- **THEN** dataset contains test cases with kp_id, kp_name, and relevant_snippet_ids
- **AND** relevant snippet IDs reference actual snippets in the code library

#### Scenario: Validate ground truth integrity
- **WHEN** ground truth dataset is loaded
- **THEN** system verifies all referenced snippet IDs exist in database
- **AND** system reports any missing or invalid references

### Requirement: Top-1 Accuracy Metric
The system SHALL calculate Top-1 Accuracy as the percentage of queries where the most relevant snippet is ranked first.

#### Scenario: Calculate Top-1 with all correct
- **WHEN** all test queries return a relevant snippet as rank 1
- **THEN** Top-1 Accuracy is 100%

#### Scenario: Calculate Top-1 with some incorrect
- **WHEN** 96 out of 99 test queries return relevant snippet as rank 1
- **THEN** Top-1 Accuracy is 96.97%

#### Scenario: Calculate Top-1 with none correct
- **WHEN** no test queries return relevant snippet as rank 1
- **THEN** Top-1 Accuracy is 0.00%

### Requirement: Precision@K Metric
The system SHALL calculate Precision@K as the proportion of relevant snippets among the top-K results.

#### Scenario: Calculate Precision@5
- **WHEN** top-5 results contain 3 relevant snippets out of 5
- **THEN** Precision@5 is 0.60 (60%)

#### Scenario: Calculate Precision@10
- **WHEN** top-10 results contain 5 relevant snippets out of 10
- **THEN** Precision@10 is 0.50 (50%)

### Requirement: Recall@K Metric
The system SHALL calculate Recall@K as the proportion of relevant snippets retrieved among all relevant snippets.

#### Scenario: Calculate Recall@10 with full retrieval
- **WHEN** ground truth has 5 relevant snippets AND all 5 appear in top-10
- **THEN** Recall@10 is 1.00 (100%)

#### Scenario: Calculate Recall@10 with partial retrieval
- **WHEN** ground truth has 5 relevant snippets AND 3 appear in top-10
- **THEN** Recall@10 is 0.60 (60%)

### Requirement: F1@K Metric
The system SHALL calculate F1@K as the harmonic mean of Precision@K and Recall@K.

#### Scenario: Calculate F1@10
- **WHEN** Precision@10 is 0.50 AND Recall@10 is 1.00
- **THEN** F1@10 is 2 × (0.50 × 1.00) / (0.50 + 1.00) = 0.6667 (66.67%)

### Requirement: Mean Reciprocal Rank (MRR)
The system SHALL calculate MRR as the average of reciprocal ranks of the first relevant snippet across all queries.

#### Scenario: Calculate MRR with first-rank matches
- **WHEN** 3 queries have first relevant snippet at ranks [1, 1, 1]
- **THEN** MRR is (1/1 + 1/1 + 1/1) / 3 = 1.00

#### Scenario: Calculate MRR with varied ranks
- **WHEN** 3 queries have first relevant snippet at ranks [1, 2, 3]
- **THEN** MRR is (1/1 + 1/2 + 1/3) / 3 = 0.6111

#### Scenario: Calculate MRR with no relevant results
- **WHEN** query returns no relevant snippets
- **THEN** reciprocal rank for that query is 0

### Requirement: Mean Average Precision (MAP)
The system SHALL calculate MAP as the mean of Average Precision scores across all queries.

#### Scenario: Calculate MAP
- **WHEN** Query 1 has AP=0.8 AND Query 2 has AP=0.6
- **THEN** MAP is (0.8 + 0.6) / 2 = 0.70

### Requirement: Ablation Study - Component Isolation
The system SHALL support ablation studies testing individual and combined matching components.

#### Scenario: Test AST-only configuration
- **WHEN** weights are set to `w_ast=1.0, w_keyword=0.0, w_difficulty=0.0`
- **THEN** system evaluates matching performance using only AST features

#### Scenario: Test Keyword-only configuration
- **WHEN** weights are set to `w_ast=0.0, w_keyword=1.0, w_difficulty=0.0`
- **THEN** system evaluates matching performance using only keywords

#### Scenario: Test AST+Keyword configuration
- **WHEN** weights are set to `w_ast=0.7, w_keyword=0.3, w_difficulty=0.0`
- **THEN** system evaluates combined AST and keyword matching without difficulty

#### Scenario: Test Full configuration
- **WHEN** weights are set to `w_ast=0.5, w_keyword=0.4, w_difficulty=0.1`
- **THEN** system evaluates complete hybrid strategy

### Requirement: Evaluation Report Generation
The system SHALL generate comprehensive evaluation reports in both Markdown and JSON formats.

#### Scenario: Generate Markdown report
- **WHEN** evaluation completes
- **THEN** report is saved to `experiments/results/report.md`
- **AND** report includes sections for each ablation configuration
- **AND** report includes performance comparison tables

#### Scenario: Generate JSON report
- **WHEN** evaluation completes
- **THEN** report is saved to `experiments/results/report.json`
- **AND** report contains machine-readable metrics for all configurations

### Requirement: Quick Evaluation Mode
The system SHALL support a quick evaluation mode that skips ablation studies.

#### Scenario: Run quick evaluation
- **WHEN** script is run with `--quick` flag
- **THEN** only hybrid strategy with default weights is evaluated
- **AND** execution completes in <5 minutes

### Requirement: Selective Evaluation Modes
The system SHALL support running only ablation studies via command-line flags.

#### Scenario: Run ablation-only evaluation
- **WHEN** script is run with `--ablation-only` flag
- **THEN** only ablation configurations are evaluated

### Requirement: Dataset Version Management
The system SHALL use content-based hashing to ensure stable snippet identification across dataset versions.

#### Scenario: Identify snippet by content hash
- **WHEN** ground truth references snippet by content_hash
- **THEN** system looks up snippet using hash value
- **AND** snippet is correctly retrieved regardless of snippet_id changes

#### Scenario: Handle hash collisions
- **WHEN** multiple snippets have identical content (rare)
- **THEN** system uses first matching snippet or reports ambiguity

## Implementation Details

### Evaluation Scripts
- Main evaluation runner: scripts/run_experiments.py:1
- Internal evaluation: scripts/_internal/run_evaluation.py:1
- Experiment orchestrator: experiments/evaluation/experiment.py:1

### Metrics Implementation
- All metrics: experiments/evaluation/metrics.py:1
- Functions: `calculate_precision_at_k()`, `calculate_recall_at_k()`, `calculate_f1_at_k()`, `calculate_mrr()`, `calculate_map()`

### Experiment Orchestration
- Experiment runner: experiments/evaluation/experiment.py:1
- Configuration management: Supports weight tuning and ablation studies

### Ground Truth Dataset
- Location: experiments/datasets/ground_truth/codesearchnet_v7.0-final.json
- Format:
  ```json
  [
    {
      "kp_id": 10011,
      "kp_name": "For loop",
      "relevant_snippet_ids": [1, 5, 8, 12, 15]
    }
  ]
  ```
- Current dataset: 99 test cases, 495 annotated snippets, 20,022 total snippets

### Results Storage
- Markdown reports: experiments/results/report.md
- JSON reports: experiments/results/report.json
- Evaluation history: Timestamped reports for trend analysis

## Current Performance Benchmarks (v1.3.4, 2026-02-07)

### Hybrid Strategy (Default)
- **Top-1 Accuracy**: 96.97%
- **MRR**: 0.9832
- **Precision@10**: 49.91%
- **Recall@10**: 99.39%
- **F1@10**: 66.49%

### Ablation Study Results
- **AST-only**: 0.00% Top-1 Accuracy
- **Keyword-only**: 53.54% Top-1 Accuracy
- **AST + Keyword**: 63.64% Top-1 Accuracy
- **Full (AST + Keyword + Difficulty)**: 96.97% Top-1 Accuracy

### Key Insights
- **Keyword is most important feature**: 53.54% standalone performance
- **Difficulty contributes +33.33 percentage points**: From 63.64% to 96.97%
- **AST requires combination**: 0.00% standalone but essential in combination
- **P@10 ≈ 50% is near-optimal**: Ground truth averages 5 relevant snippets per KP (theoretical max 50%)

## Command-Line Usage

### Run Complete Evaluation
```bash
python scripts/run_experiments.py
```

### Run Quick Evaluation (Hybrid Only)
```bash
python scripts/run_experiments.py --quick
```

### Run Ablation Study Only
```bash
python scripts/run_experiments.py --ablation-only
```

## Dependencies
- Ground truth dataset: experiments/datasets/ground_truth/codesearchnet_v7.0-final.json
- Code library: MySQL database with code_snippets table
- Matching strategy: src/matching/strategies.py
- Search service: src/services/search_service.py
