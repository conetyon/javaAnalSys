# Archive: Refactor Evaluation Framework

## Status: COMPLETED

**Archived**: 2026-02-07
**Duration**: 2026-02-04 to 2026-02-07

## Summary

成功将评估框架从循环验证（Ground Truth 自动生成）重构为分级规则评估体系。

## Key Achievements

1. **分级规则体系**：56 条 KP 规则，支持 Grade 0/1/2 三级判断
2. **评估指标**：Binary Precision 98.0%，Graded Precision 58.4%，nDCG 0.874
3. **权重优化**：基于消融实验优化权重 AST=0.2, KW=0.7, DIFF=0.1
4. **代码清理**：删除旧评估文件，简化项目结构

## Files Changed

### Added
- `experiments/evaluation/rules.py` - 56 条分级规则
- `config/matching.yaml` - 权重配置文件

### Modified
- `scripts/_internal/run_evaluation.py` - 分级评估脚本
- `experiments/evaluation/__init__.py` - 模块导出

### Deleted
- `experiments/evaluation/metrics.py`
- `experiments/evaluation/experiment.py`
- `experiments/evaluation/labeler.py`
- `experiments/datasets/ground_truth/codesearchnet_v7.0-final.json`

## Learnings

1. **Keyword 是核心特征**：单独达到 97.7% Binary Precision
2. **AST 权重应降低**：单独只有 55.8%，但辅助排序有价值
3. **分级评估更客观**：避免循环验证问题，规则与算法独立

## Next Steps

- 持续扩展 KP 规则覆盖度
- 优化低精度 KP（LinkedHashMap、Stream Sorted/Distinct 等）
- 考虑引入更多评估维度（如代码质量）
