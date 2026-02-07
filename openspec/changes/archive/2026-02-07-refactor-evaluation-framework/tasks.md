# Tasks: Refactor Evaluation Framework (Revised)

## Phase 0: Pilot 验证（优先）

- [ ] 0.1 实现核心分级逻辑
  - 创建 `experiments/evaluation/rules.py`
  - 定义 5 个 Pilot KP 的规则（for、while、try-catch、继承、ArrayList）
  - 实现 `calculate_feature_grade()` 多维度判断
  - 支持可配置的 `loc_range` 和 `noise_nodes`

- [ ] 0.2 实现规则独立性验证
  - 实现 `verify_rule_independence()` 检查函数
  - 确保规则不使用 NODE_MAPPING、DOMAIN_ANCHORS、CANONICAL_ALIASES
  - 评估启动时自动运行检查

- [ ] 0.3 实现分级标注器
  - 创建 `experiments/evaluation/labeler.py`
  - 实现 `GradedLabeler.generate_graded_ground_truth()`
  - 确保只读数据库，结果存内存

- [ ] 0.4 实现新指标
  - 在 `metrics.py` 添加 `calculate_graded_precision()`
  - 添加 `calculate_ndcg()`
  - 添加 `calculate_cohens_kappa()`

- [ ] 0.5 生成人工校准样本
  - 实现 `extract_human_review_samples()`
  - 输出 15 样本到 `experiments/results/human_review_pilot.json`

- [ ] 0.6 **人工校准（手动，选项 B）**
  - 主标注：1 人标注 15 个样本的 human_grade (0/1/2)
  - 复核：另 1 人复核 3 个样本（20%）
  - 复核一致率 ≥ 80%
  - 计算规则-人工 Kappa
  - **Gate**: Kappa ≥ 0.6 才继续

- [ ] 0.7 Pilot 结果验证
  - 分级 Precision@10 ≥ 0.75
  - nDCG@10 ≥ 0.70
  - 如不通过，分析原因并迭代规则

## Phase 1: 规则扩展

- [ ] 1.1 扩展规则定义
  - 添加控制流：do-while、if-else、switch
  - 添加异常处理：try-finally、throws
  - 添加面向对象：interface、abstract class
  - 添加集合类：HashMap、HashSet、LinkedList
  - 共计 ~30 个 KP

- [ ] 1.2 覆盖度验证
  - 实现 `check_rule_coverage()`
  - 确保每个规则至少匹配 5 个代码片段
  - 输出覆盖度报告

- [ ] 1.3 扩展人工校准（选项 B）
  - 分层抽样 20 个 KP
  - 主标注：1 人标注 60 样本
  - 复核：另 1 人复核 12 样本（20%）
  - 复核一致率 ≥ 80%
  - 计算整体 Kappa

## Phase 2: 评估流程集成

- [ ] 2.1 修改评估入口
  - 修改 `experiment.py` 添加 `run_graded_evaluation()`
  - 集成：规则加载 → 分级标注 → 三层评估

- [ ] 2.2 更新命令行接口
  - 添加 `--graded` 标志启用新模式
  - 添加 `--legacy` 标志使用旧模式
  - 添加 `--pilot` 标志仅运行 5 KP

- [ ] 2.3 报告生成更新
  - 输出三层指标（分级 Precision、nDCG、Kappa）
  - 输出规则覆盖度统计
  - 输出人工校准样本路径

## Phase 3: 切换与文档

- [ ] 3.1 切换默认评估模式
  - 新方式成为默认
  - 旧方式保留但标记废弃

- [ ] 3.2 更新 CLAUDE.md
  - 文档化三层评估体系
  - 说明规则定义方法
  - 更新验收标准

- [ ] 3.3 更新 openspec 规范
  - 归档本提案
  - 更新 evaluation-framework/spec.md

## 验收标准（修订后）

| 指标 | 阈值 | Phase |
|------|------|-------|
| 规则独立性检查 | 通过 | Phase 0 前置 |
| Pilot 复核一致率 | ≥ 80% | Phase 0 |
| Pilot Kappa | ≥ 0.60 | Phase 0 Gate |
| 分级 Precision@10 | ≥ 0.75 | Phase 1 |
| nDCG@10 | ≥ 0.70 | Phase 1 |
| 规则覆盖度 | ≥ 70% | Phase 1 |
| 整体复核一致率 | ≥ 80% | Phase 1 |
| 整体 Kappa | ≥ 0.60 | Phase 1 |
| 幂等性验证 | 通过 | Phase 2 |
| 无 DB 写入 | 通过 | Phase 2 |

## 回退条件

- Pilot Kappa < 0.5 连续 3 次迭代 → 暂停，重新评估方案可行性
- 分级 Precision < 0.6 → 检查规则定义或算法实现
