# Phase 5: Evaluation Framework Fix

**Date**: 2026-01-24
**Status**: In Progress
**Priority**: Critical

---

## Problem Statement

Evaluation accuracy is only 31.58% (target: 95%+) due to **ground truth mismatch**:

- **Database**: Contains 20,022 CodeSearchNet snippets
- **Ground Truth**: References old sample_code.java snippets (ID 1-30)
- **Impact**: Evaluation framework comparing against non-existent data

## Root Cause Analysis

```
tests/fixtures/ground_truth.json
  → References snippet IDs: [2, 5, 10, 3, 6, 7, ...]
  → These IDs from sample_code.java (deleted in refactor)

Database (javalearningsys.code_snippets)
  → Contains 20,022 CodeSearchNet snippets
  → IDs start from 1, but content is completely different
```

## Solution Approach

### Option A: Create New Ground Truth for CodeSearchNet
**Pros**: Uses production data, realistic evaluation
**Cons**: Requires manual labeling (labor-intensive)

### Option B: Restore sample_code.java Evaluation
**Pros**: Quick fix, existing labels work
**Cons**: Not representative of production data

### **Selected**: Hybrid Approach
1. Keep sample_code.java snippets for quick validation (30 snippets)
2. Create small CodeSearchNet ground truth (50-100 snippets, high quality)
3. Use both for comprehensive evaluation

---

## Implementation Plan

### Step 1: Database Query Optimization ✅
**Issue**: Current queries inefficient for 20K+ snippets
**Fix**: Add candidate filtering in SearchService

### Step 2: Sample Ground Truth Creation
**Target**: 50 hand-labeled test cases from CodeSearchNet
**Coverage**:
- Control flow: for, while, if, switch (10 cases)
- Collections: ArrayList, HashMap, HashSet (10 cases)
- Exception handling: try-catch, try-with-resources (10 cases)
- Streams & Lambda: Stream API, lambda expressions (10 cases)
- Concurrency: synchronized, Lock, volatile (10 cases)

### Step 3: Automated Ground Truth Expansion
**Strategy**: Use keyword + AST exact matching to find high-confidence matches
```python
# Pseudo-code
for kp in knowledge_points:
    candidates = find_snippets_with_exact_keywords(kp.keywords)
    manual_verify_top_10(candidates)  # Human in the loop
    add_to_ground_truth(verified_snippets)
```

### Step 4: Evaluation Framework Update
- Separate eval configs: `ground_truth_sample.json`, `ground_truth_codesearchnet.json`
- Weighted scoring: sample (30%) + CodeSearchNet (70%)
- Report both metrics independently

---

## Current Status

### Completed
- [x] Diagnosed ground truth mismatch issue
- [x] Analyzed evaluation framework failures
- [x] Identified matching algorithm issues (AST-only performs best at 52.63%)

### In Progress
- [ ] Create CodeSearchNet ground truth (manual labeling)
- [ ] Optimize matching weights (AST=0.8, Keyword=0.2, Difficulty=0.0)
- [ ] Implement candidate filtering for large datasets

### Blocked
- Manual labeling requires domain expert time (~4 hours estimated)

---

## Metrics & Goals

| Metric | Current | Target | Strategy |
|--------|---------|--------|----------|
| Top-1 Accuracy | 31.58% | 95%+ | Fix ground truth + optimize weights |
| Precision@10 | 19.47% | 80%+ | Improve keyword matching |
| MRR | 0.4150 | 0.90+ | Better AST template coverage |

---

## Technical Findings

### Matching Algorithm Performance (on mismatched data)
| Configuration | Top-1 Accuracy | Notes |
|---------------|----------------|-------|
| AST Only | 52.63% | Best performing - reliable structure matching |
| Keyword Only | 36.84% | Noisy due to generic keywords (loop, condition) |
| AST + Keyword (0.8/0.2) | 31.58% | Current config |
| AST + Keyword (0.6/0.4) | 31.58% | Keyword adds noise |
| Full (AST+KW+DIFF) | 31.58% | Difficulty doesn't help |

**Key Insight**: AST matching is most reliable. Keyword matching needs improvement (remove generic terms, keep specific APIs).

### Recommended Configuration
```python
WEIGHT_DEFAULTS = {"ast": 0.9, "keyword": 0.1, "difficulty": 0.0}
```

---

## Next Actions

1. **Immediate** (Today):
   - [ ] Create minimal ground truth for smoke test (10 cases)
   - [ ] Run quick validation with corrected ground truth
   - [ ] Verify matching algorithm works correctly

2. **Short-term** (This week):
   - [ ] Complete 50-case CodeSearchNet ground truth
   - [ ] Optimize keyword extraction (remove generic words)
   - [ ] Achieve 95%+ accuracy on validated dataset

3. **Long-term** (Next sprint):
   - [ ] Automate ground truth expansion using ML
   - [ ] Build ground truth editor UI for stakeholders
   - [ ] Continuous evaluation on growing dataset

---

## Open Questions

1. **Labeling Strategy**: Manual vs. semi-automated?
   - **Answer**: Start manual (50 cases), then semi-auto

2. **Evaluation Split**: How to handle sample_code.java vs CodeSearchNet?
   - **Answer**: Keep both, report separately

3. **Performance**: Can we maintain <500ms latency with 20K snippets?
   - **Answer**: Need candidate filtering (implemented in SearchService._fetch_candidates)

---

## References

- Phase 5 Spec: `openspec/changes/refactor-production-backend/specs/experiment-framework/spec.md`
- Evaluation Code: `tests/evaluation/experiment.py`
- Ground Truth: `tests/fixtures/ground_truth.json`
- Matching Logic: `src/matching/strategies.py`

---

**Last Updated**: 2026-01-24
**Owner**: Claude Code Agent
**Review Status**: Pending stakeholder review
