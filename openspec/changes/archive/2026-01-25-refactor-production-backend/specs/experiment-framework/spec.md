# Specification: Experiment Framework

**Capability**: `experiment-framework`
**Change Type**: MODIFIED
**Related Capabilities**: `performance-benchmarks`

---

## MODIFIED Requirements

### Requirement: CodeSearchNet Dataset Integration

The system SHALL support loading and preprocessing CodeSearchNet Java subset.

**Rationale**: Current evaluation uses 19 test cases (30 snippets). Production system requires ≥1000 samples for robust validation.

#### Scenario: Developer downloads CodeSearchNet dataset

**Given**: System has internet connection
**When**: Developer runs `python experiments/datasets/download_codesearchnet.py`
**Then**:
- Script downloads Java subset from official source
- Dataset is saved to `experiments/datasets/cache/codesearchnet/`
- Log shows "Downloaded CodeSearchNet Java: 164K methods, 2.3GB"
- Metadata file `dataset_info.json` is created with download timestamp

#### Scenario: Preprocessing CodeSearchNet for knowledge point matching

**Given**: Raw CodeSearchNet dataset is downloaded
**When**: Developer runs `python experiments/datasets/preprocess_codesearchnet.py`
**Then**:
- Script extracts method-level snippets
- For each method, extracts:
  - Code content
  - Docstring (for heuristic labeling)
  - Repository metadata
- Preprocessed data saved to `experiments/datasets/processed/codesearchnet_java.jsonl`
- Log shows "Preprocessed 164K methods → 164K samples"

#### Scenario: Heuristic labeling of CodeSearchNet samples

**Given**: Preprocessed CodeSearchNet data exists
**When**: Developer runs `python experiments/datasets/label_codesearchnet.py`
**Then**:
- Script applies keyword-based heuristics to docstrings:
  - "loop" / "iterate" → For Loop (KP 10011)
  - "exception" / "try-catch" → Exception Handling (KP 10031)
  - "arraylist" / "list" → ArrayList (KP 10037)
- Labels assigned to subset of samples (confidence-based filtering)
- Output saved to `experiments/datasets/processed/codesearchnet_labeled.jsonl`
- Log shows "Labeled 5,432 samples across 15 knowledge points"

#### Scenario: Manual verification of heuristic labels

**Given**: Heuristically labeled dataset exists
**When**: Developer runs `python experiments/datasets/verify_labels.py --sample 200`
**Then**:
- Script randomly samples 200 labeled examples
- Displays each sample with proposed label for human review
- Reviewer marks as correct/incorrect
- Inter-annotator agreement computed (Cohen's Kappa)
- Corrected labels saved to `experiments/datasets/processed/codesearchnet_verified.jsonl`

---

### Requirement: Experiment Run Tracking

The system SHALL track experiment configurations, results, and artifacts.

**Rationale**: Enable reproducibility and comparison across experiments. Custom solution (no external dependencies like MLflow).

#### Scenario: Starting a new experiment run

**Given**: Developer wants to test new weight configuration
**When**: Developer runs:
```python
from experiments.tracking import ExperimentRun

run = ExperimentRun(
    name="test-weight-config-v2",
    config={
        "weights": {"ast": 0.5, "keyword": 0.4, "difficulty": 0.1},
        "dataset": "codesearchnet_verified",
        "thresholds": {"ast_min_ratio": 0.3, "keyword_min_score": 0.3}
    }
)
```
**Then**:
- New directory created: `experiments/runs/test-weight-config-v2-20260124-120000/`
- `config.json` saved with experiment parameters
- Run metadata logged to `experiment_runs` database table

#### Scenario: Logging metrics during experiment

**Given**: Experiment run is in progress
**When**: Evaluation completes and computes metrics:
```python
run.log_metric("top_1_accuracy", 0.96)
run.log_metric("precision_at_10", 0.58)
run.log_metric("mrr", 0.98)
```
**Then**:
- Metrics saved to `experiments/runs/{run_name}/metrics.json`
- Database `experiment_runs` table updated with metrics

#### Scenario: Saving raw predictions for analysis

**Given**: Experiment produced predictions for all test cases
**When**: Developer saves predictions:
```python
run.save_predictions(predictions_df)  # pandas DataFrame
```
**Then**:
- Predictions saved to `experiments/runs/{run_name}/predictions.csv`
- CSV includes columns: test_case_id, predicted_snippet_id, score, rank

#### Scenario: Generating experiment report

**Given**: Experiment run is complete with all metrics logged
**When**: Developer runs:
```python
run.generate_report()
```
**Then**:
- Markdown report created: `experiments/runs/{run_name}/report.md`
- Report includes:
  - Configuration summary
  - Key metrics table
  - Comparison to baseline (if available)
  - Link to raw predictions CSV

---

### Requirement: Baseline Method Implementations

Baseline methods SHALL be runnable on new datasets for comparison.

**Rationale**: Current baselines (TF-IDF, Pure AST, Random) hard-coded for 19-case dataset. Need generalization.

#### Scenario: Running TF-IDF baseline on CodeSearchNet

**Given**: CodeSearchNet labeled dataset exists
**When**: Developer runs:
```bash
python experiments/baselines/run_tfidf.py --dataset codesearchnet_verified
```
**Then**:
- TF-IDF vectorizer trained on code snippets
- For each test case, computes cosine similarity to candidate snippets
- Predictions saved to `experiments/runs/baseline-tfidf-{timestamp}/predictions.csv`
- Metrics computed and logged

#### Scenario: Running Pure AST baseline

**Given**: Dataset with AST features extracted
**When**: Developer runs:
```bash
python experiments/baselines/run_pure_ast.py --dataset codesearchnet_verified
```
**Then**:
- AST matching runs without keyword component
- Predictions and metrics saved to dedicated run directory

---

### Requirement: Automated Ablation Studies

Ablation studies SHALL be runnable with single command.

**Rationale**: Current manual configuration of weights for ablation is error-prone.

#### Scenario: Running full ablation study

**Given**: Dataset and system are ready
**When**: Developer runs:
```bash
python experiments/run_ablation.py --dataset codesearchnet_verified
```
**Then**:
- Script runs experiments with configurations:
  1. AST Only (ast=1.0, keyword=0, difficulty=0)
  2. Keyword Only (ast=0, keyword=1.0, difficulty=0)
  3. AST + Keyword (ast=0.6, keyword=0.4, difficulty=0)
  4. Full (ast=0.6, keyword=0.3, difficulty=0.1)
- Each configuration saves separate run directory
- Comparison report generated: `experiments/ablation_results_{timestamp}.md`

#### Scenario: Ablation report includes statistical significance

**Given**: Ablation study completed
**When**: Report is generated
**Then**: Report includes:
- Metrics table comparing all configurations
- Statistical significance tests (paired t-test on per-query scores)
- Best configuration highlighted

---

### Requirement: Dataset Versioning and Metadata

Datasets SHALL be versioned to ensure reproducibility.

**Rationale**: Prevent confusion when dataset preprocessing changes.

#### Scenario: Dataset metadata file creation

**Given**: Dataset is preprocessed and labeled
**When**: Processing completes
**Then**: Metadata file `dataset_info.json` created:
```json
{
  "name": "codesearchnet_verified",
  "version": "1.0",
  "created_at": "2026-01-24T12:00:00Z",
  "source": "CodeSearchNet Java subset",
  "samples_total": 5432,
  "samples_by_kp": {
    "10011": 432,
    "10031": 287,
    "10037": 156
  },
  "preprocessing": {
    "heuristic_labeling": true,
    "manual_verification_count": 200,
    "inter_annotator_agreement": 0.87
  }
}
```

#### Scenario: Experiment references dataset version

**Given**: Multiple dataset versions exist
**When**: Experiment run is created
**Then**: Run configuration includes dataset version:
```json
{
  "dataset": "codesearchnet_verified",
  "dataset_version": "1.0"
}
```
**And**: Experiment is linked to specific dataset version (reproducibility)

---

## ADDED Requirements

### Requirement: Experiment Comparison Tool

Users SHALL be able to compare multiple experiment runs.

**Rationale**: Understand which configuration changes improve performance.

#### Scenario: Comparing two experiment runs

**Given**: Two experiment runs exist with different configurations
**When**: Developer runs:
```bash
python experiments/compare_runs.py run1-20260124-120000 run2-20260124-130000
```
**Then**: Console output shows side-by-side comparison:
```
Metric              Run 1      Run 2      Δ
Top-1 Accuracy      94.74%     96.21%     +1.47%
Precision@10        57.46%     59.32%     +1.86%
MRR                 0.9737     0.9812     +0.0075
```
**And**: Markdown report saved: `experiments/comparison_{timestamp}.md`

#### Scenario: Comparing against baseline

**Given**: Current run and baseline run exist
**When**: Comparison tool runs
**Then**: Report shows improvement over baseline:
```
Configuration: AST+Keyword (run2-20260124-130000)
vs Baseline: TF-IDF (baseline-tfidf-20260120)

Top-1 Accuracy: +22.53% (96.21% vs 73.68%)
MRR: +16.54 points (0.9812 vs 0.8158)
```

---

### Requirement: Raw Data Export for External Analysis

Experiment results SHALL be exportable for analysis in external tools.

**Rationale**: Researchers may want to analyze in Jupyter, R, or Excel.

#### Scenario: Exporting experiment results to CSV

**Given**: Experiment run is complete
**When**: Developer runs:
```python
run.export_to_csv("results.csv")
```
**Then**: CSV file created with columns:
- test_case_id, kp_id, predicted_snippet_id, rank, score, ast_score, keyword_score, difficulty_score, ground_truth_match

#### Scenario: Exporting all runs for meta-analysis

**Given**: Multiple experiment runs exist
**When**: Developer runs:
```bash
python experiments/export_all_runs.py --format csv
```
**Then**:
- All runs exported to `experiments/exports/all_runs_{timestamp}.csv`
- Aggregated metrics CSV includes: run_name, dataset, config, top_1_accuracy, precision_at_10, mrr

---

## Implementation Notes

### Directory Structure
```
experiments/
├── datasets/
│   ├── cache/                        # Downloaded raw datasets
│   │   └── codesearchnet/
│   ├── processed/                    # Preprocessed datasets
│   │   ├── codesearchnet_java.jsonl
│   │   ├── codesearchnet_labeled.jsonl
│   │   └── codesearchnet_verified.jsonl
│   ├── download_codesearchnet.py
│   ├── preprocess_codesearchnet.py
│   ├── label_codesearchnet.py
│   └── verify_labels.py
├── runs/                             # Experiment run artifacts
│   └── {run_name}-{timestamp}/
│       ├── config.json
│       ├── metrics.json
│       ├── predictions.csv
│       └── report.md
├── baselines/
│   ├── run_tfidf.py
│   ├── run_pure_ast.py
│   └── run_random.py
├── tracking.py                       # ExperimentRun class
├── run_ablation.py                   # Automated ablation studies
├── compare_runs.py                   # Comparison tool
└── export_all_runs.py                # Data export utility
```

### Database Schema Addition

Table: `experiment_runs`
```sql
CREATE TABLE IF NOT EXISTS experiment_runs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    run_name VARCHAR(255) UNIQUE NOT NULL,
    dataset_name VARCHAR(100),
    dataset_version VARCHAR(50),
    config JSON,
    metrics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_name (run_name),
    INDEX idx_dataset (dataset_name)
);
```

### Heuristic Labeling Keywords (Initial Set)

| Knowledge Point | Keywords in Docstring |
|----------------|----------------------|
| For Loop (10011) | "loop", "iterate", "for each" |
| While Loop (10012) | "while", "until", "repeat" |
| Exception Handling (10031) | "exception", "try", "catch", "throw" |
| ArrayList (10037) | "arraylist", "list", "array" |
| HashMap (10038) | "hashmap", "map", "dictionary" |

**Note**: Keywords are case-insensitive. Require ≥2 keyword matches for high-confidence labeling.

### Testing Requirements
- Unit test: Heuristic labeling logic (mock docstrings)
- Unit test: ExperimentRun class (metrics logging, file creation)
- Integration test: Download and preprocess small dataset sample
- Integration test: Run ablation study on test dataset (5 samples)
- Integration test: Compare two experiment runs
