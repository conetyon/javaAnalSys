## MODIFIED Requirements

### Requirement: Ground Truth Dataset Management
The system SHALL dynamically generate graded ground truth from code snippets using rule-based labeling, without persisting to database.

#### Scenario: Generate graded ground truth
- **WHEN** evaluation starts
- **THEN** system scans all code snippets from database (read-only)
- **AND** applies grading rules to each snippet for each knowledge point
- **AND** stores graded labels in memory (not persisted)

#### Scenario: Graded labeling
- **WHEN** a snippet is evaluated against a knowledge point rule
- **THEN** system assigns Grade 0 if snippet lacks required AST nodes
- **AND** assigns Grade 1 if snippet contains required nodes but fails Grade 2 signals
- **AND** assigns Grade 2 if snippet satisfies >= 2 quality signals (feature density, method name keywords, appropriate length, low noise)

#### Scenario: Idempotent evaluation
- **WHEN** evaluation runs multiple times with same codebase and rules
- **THEN** graded ground truth is identical each time
- **AND** no database writes occur

## ADDED Requirements

### Requirement: Graded Precision Metric
The system SHALL calculate Graded Precision@K using weighted scoring based on relevance grades.

#### Scenario: Calculate graded precision
- **WHEN** Top-10 results contain 5 Grade-2, 3 Grade-1, and 2 Grade-0 snippets
- **THEN** Graded Precision@10 is (5×2 + 3×1 + 2×0) / (10×2) = 0.65

#### Scenario: Perfect graded precision
- **WHEN** all Top-K results are Grade 2
- **THEN** Graded Precision@K is 1.0

### Requirement: nDCG Metric
The system SHALL calculate Normalized Discounted Cumulative Gain to evaluate ranking quality.

#### Scenario: Calculate nDCG with ideal ranking
- **WHEN** Top-K results are sorted with all Grade-2 first, then Grade-1, then Grade-0
- **THEN** nDCG@K is 1.0

#### Scenario: Calculate nDCG with suboptimal ranking
- **WHEN** Grade-0 snippet appears before Grade-2 snippet in results
- **THEN** nDCG@K is less than 1.0
- **AND** penalty increases with position difference

### Requirement: Human Calibration with Cohen's Kappa
The system SHALL support human calibration to validate rule quality using Cohen's Kappa coefficient.

#### Scenario: Generate human review samples
- **WHEN** evaluation runs with `--generate-review` flag
- **THEN** system outputs Top-3 results for sampled KPs to JSON file
- **AND** includes code preview, rule grade, and placeholder for human grade

#### Scenario: Calculate Kappa coefficient
- **WHEN** human grades are provided for review samples
- **THEN** system calculates Cohen's Kappa between rule grades and human grades
- **AND** Kappa >= 0.6 indicates acceptable rule quality

#### Scenario: Kappa below threshold
- **WHEN** Kappa < 0.6
- **THEN** system flags rule quality issue
- **AND** outputs disagreement analysis for rule improvement

### Requirement: Graded Rule Definition
The system SHALL define knowledge point rules with multi-dimensional signals for Grade 2 determination.

#### Scenario: Rule with AST nodes only
- **WHEN** rule specifies `positive_nodes: ["for_statement"]`
- **THEN** snippet must contain for_statement to achieve Grade >= 1

#### Scenario: Rule with name keywords
- **WHEN** rule specifies `name_keywords: ["loop", "iterate"]`
- **AND** snippet method name contains "loop"
- **THEN** this contributes as one positive signal for Grade 2

#### Scenario: Rule with noise detection
- **WHEN** rule specifies `noise_nodes: ["try_statement", "lambda_expression"]`
- **AND** snippet contains more noise nodes than target nodes
- **THEN** this contributes as negative signal (fails noise check)

### Requirement: Pilot Evaluation Mode
The system SHALL support pilot mode to validate evaluation framework with subset of knowledge points.

#### Scenario: Run pilot evaluation
- **WHEN** script runs with `--pilot` flag
- **THEN** only 5 predefined KPs are evaluated (for, while, try-catch, inheritance, ArrayList)
- **AND** human review samples are generated for these KPs

#### Scenario: Pilot gate check
- **WHEN** pilot Kappa < 0.6
- **THEN** system recommends rule revision before full evaluation
- **AND** does not proceed to full evaluation automatically

## MODIFIED Requirements

### Requirement: Evaluation Report Generation
The system SHALL generate comprehensive evaluation reports including three-layer metrics.

#### Scenario: Generate graded evaluation report
- **WHEN** graded evaluation completes
- **THEN** report includes Graded Precision@K for each KP
- **AND** report includes nDCG@K for each KP
- **AND** report includes rule coverage statistics
- **AND** report includes path to human review samples file

#### Scenario: Generate JSON report with grades
- **WHEN** evaluation completes
- **THEN** JSON report contains graded ground truth for each KP
- **AND** JSON report contains per-KP metrics
- **AND** JSON report contains overall Kappa if human grades provided

### Requirement: Quick Evaluation Mode
The system SHALL support quick evaluation mode that runs only Layer 1 and Layer 2 metrics.

#### Scenario: Run quick graded evaluation
- **WHEN** script runs with `--quick --graded` flags
- **THEN** only Graded Precision and nDCG are calculated
- **AND** human review samples are not generated
- **AND** Kappa calculation is skipped

### Requirement: Selective Evaluation Modes
The system SHALL support legacy mode for backward compatibility.

#### Scenario: Run legacy evaluation
- **WHEN** script runs with `--legacy` flag
- **THEN** original evaluation logic is used
- **AND** static ground truth JSON is loaded
- **AND** original metrics (Top-1 Accuracy, MRR) are calculated

## REMOVED Requirements

### Requirement: Top-1 Accuracy Metric
**Reason**: Replaced by Graded Precision which provides more nuanced assessment
**Migration**: Use Graded Precision@K instead; Top-1 can be derived from Grade distribution

### Requirement: Static Ground Truth Loading
**Reason**: Replaced by dynamic graded labeling
**Migration**: Ground truth is now generated at runtime; static JSON files deprecated
