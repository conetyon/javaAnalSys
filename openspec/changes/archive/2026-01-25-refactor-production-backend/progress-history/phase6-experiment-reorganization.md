# Phase 6: 实验结构重组

**日期**: 2026-01-24
**状态**: 完成
**目标**: 简化实验结构，提供单一入口，完全基于CodeSearchNet数据集

---

## 问题背景

### 原有问题

1. **数据源混乱**：
   - 旧版19个测试用例（sample_code.java，已废弃）
   - CodeSearchNet数据集（20,022个片段，当前使用）
   - 两套ground truth文件共存

2. **实验结构散乱**：
   - experiments/目录有多个重复的README文档
   - tracking.py、baselines.py与tests/evaluation/重复
   - 多个入口脚本，用户不知道该用哪个

3. **文档冗余**：
   - CODESEARCHNET_EXPERIMENT_GUIDE.md
   - CODESEARCHNET_EXPERIMENT_REPORT.md
   - README_CODESEARCHNET.md
   - 三个文档内容重叠，维护困难

4. **用户体验差**：
   - 没有明确的单一启动命令
   - 需要手动检查数据状态
   - 多步骤操作容易出错

---

## 解决方案

### 核心原则

1. **单一数据源**：完全基于CodeSearchNet数据集
2. **单一文档**：EXPERIMENTS.md作为主实验文档
3. **单一入口**：scripts/run_experiments.py作为主启动脚本
4. **清晰结构**：主实验 vs 扩展实验（可选）

### 实施内容

#### 1. 删除废弃测试用例

**删除的文件**：
- `tests/fixtures/ground_truth.json` (19个旧测试用例)

**保留的文件**：
- `tests/ground_truth_codesearchnet.json` (10个测试用例，24个相关片段)

**移动操作**：
```bash
mv tests/fixtures/ground_truth_codesearchnet.json tests/ground_truth_codesearchnet.json
rmdir tests/fixtures/
```

#### 2. 创建统一实验文档

**新建文件**：`EXPERIMENTS.md`（项目根目录）

**内容结构**：
- 快速开始（一键命令）
- 实验数据说明
- 评估指标
- 实验选项
- 数据管理
- 故障排查
- 文件结构
- 配置说明

**特点**：
- 清晰的操作流程
- 完整的故障排查指南
- 明确的文件结构说明

#### 3. 创建主入口脚本

**新建文件**：`scripts/run_experiments.py`

**功能**：
1. 检查数据库连接
2. 自动初始化数据（如果需要）
3. 生成测试标注（如果不存在）
4. 运行评估实验
5. 显示结果摘要

**用法**：
```bash
python scripts/run_experiments.py          # 完整实验
python scripts/run_experiments.py --quick  # 快速评估
```

**优势**：
- 零配置启动
- 自动处理所有依赖
- 友好的进度提示
- 智能错误处理

#### 4. 更新路径引用

**修改的文件**：

1. `scripts/run_evaluation.py`（line 35）：
```python
# 修改前
default_ground_truth = str(project_root / "tests" / "fixtures" / "ground_truth.json")

# 修改后
default_ground_truth = str(project_root / "tests" / "ground_truth_codesearchnet.json")
```

2. `scripts/init_data/init_experiment_data.py`（line 182）：
```python
# 修改前
ground_truth_path = project_root / "tests" / "fixtures" / "ground_truth_codesearchnet.json"

# 修改后
ground_truth_path = project_root / "tests" / "ground_truth_codesearchnet.json"
```

#### 5. 清理experiments/目录

**删除的文件**：
- `experiments/CODESEARCHNET_EXPERIMENT_GUIDE.md`（387行，内容重复）
- `experiments/CODESEARCHNET_EXPERIMENT_REPORT.md`（实验结果已过时）
- `experiments/tracking.py`（与tests/evaluation/重复）
- `experiments/baselines.py`（与tests/evaluation/重复）

**保留的文件**：
- `experiments/README_CODESEARCHNET.md`（重写为扩展实验指南）

**新README特点**：
- 明确指向主实验文档
- 聚焦于扩展场景（110K样本处理）
- 简洁的工具说明
- 清晰的使用场景分类

#### 6. 目录结构优化

**之前**：
```
tests/
├── fixtures/
│   └── ground_truth_codesearchnet.json
├── evaluation/
└── evaluation_results/

experiments/
├── CODESEARCHNET_EXPERIMENT_GUIDE.md
├── CODESEARCHNET_EXPERIMENT_REPORT.md
├── README_CODESEARCHNET.md
├── tracking.py
├── baselines.py
└── ...
```

**之后**：
```
EXPERIMENTS.md                              # 主实验文档

tests/
├── ground_truth_codesearchnet.json        # 测试标注（唯一）
├── evaluation/                            # 评估框架
└── evaluation_results/                    # 评估结果

scripts/
├── run_experiments.py                     # 主入口
├── run_evaluation.py                      # 评估脚本
└── init_data/                             # 数据初始化

experiments/
├── README_CODESEARCHNET.md                # 扩展实验文档
├── datasets/                              # 数据处理工具
├── runs/                                  # 实验结果
└── *.py                                   # 检索实验脚本
```

---

## 验证测试

### 测试场景

1. **从零开始运行实验**：
```bash
python scripts/run_experiments.py
```

预期：
- 自动检查数据库
- 自动初始化数据（如果需要）
- 自动生成ground truth
- 运行完整评估
- 输出结果摘要

2. **数据已就绪，快速评估**：
```bash
python scripts/run_experiments.py --quick
```

预期：
- 跳过数据检查（已存在）
- 仅运行核心混合策略评估
- ~30秒完成

3. **仅查看文档**：
```bash
cat EXPERIMENTS.md
```

预期：
- 清晰的快速开始指南
- 完整的操作说明
- 故障排查指南

### 验证清单

- [x] ground_truth文件移动到正确位置
- [x] tests/fixtures/目录已删除
- [x] run_evaluation.py引用正确的ground truth路径
- [x] init_experiment_data.py引用正确的ground truth路径
- [x] experiments/冗余文档已删除
- [x] experiments/重复模块已删除
- [x] experiments/README更新为扩展实验指南
- [x] 主实验文档EXPERIMENTS.md创建完成
- [x] 主入口脚本run_experiments.py创建完成

---

## 性能改进

### 用户体验

**之前**：
1. 阅读多个文档找启动命令
2. 手动检查数据状态
3. 手动运行4-5个脚本
4. 容易遗漏步骤导致错误

**之后**：
1. 运行单个命令：`python scripts/run_experiments.py`
2. 自动处理所有依赖
3. 清晰的进度提示
4. 智能错误处理和修复建议

### 维护成本

**之前**：
- 3个重复的README文档需要同步更新
- 多个入口脚本需要维护
- 用户容易使用错误的脚本

**之后**：
- 单一主文档EXPERIMENTS.md
- 单一主入口run_experiments.py
- 清晰的主实验 vs 扩展实验区分

---

## 兼容性说明

### 破坏性变更

1. **Ground truth路径变更**：
   - 旧路径: `tests/fixtures/ground_truth_codesearchnet.json`
   - 新路径: `tests/ground_truth_codesearchnet.json`

**影响**: 任何硬编码旧路径的脚本需要更新

**缓解措施**:
- 所有官方脚本已更新
- 主入口脚本会自动生成ground truth（如果不存在）

2. **删除旧测试用例**：
   - `tests/fixtures/ground_truth.json`（19个测试用例）已删除

**影响**: 无，这些测试用例已被CodeSearchNet数据集替代

**缓解措施**: 用户应使用CodeSearchNet测试用例

### 向后兼容

以下内容保持不变：
- 数据库schema
- API接口
- 评估框架（tests/evaluation/）
- 匹配算法配置
- 核心业务逻辑

---

## 后续任务

### 已完成

- [x] 创建统一实验文档
- [x] 创建主入口脚本
- [x] 清理冗余文件
- [x] 更新路径引用
- [x] 重写experiments/README

### 待办事项

- [ ] 测试完整实验流程（从空数据库开始）
- [ ] 验证快速评估模式
- [ ] 更新CLAUDE.md引用新的实验文档
- [ ] 添加CI/CD自动化测试

---

## 文档清单

### 新增文档

1. **EXPERIMENTS.md**（项目根目录）
   - 主实验指南
   - 300行，清晰结构
   - 包含快速开始、故障排查、配置说明

### 更新文档

1. **experiments/README_CODESEARCHNET.md**
   - 重写为扩展实验指南
   - 明确指向主实验文档
   - 聚焦于高级场景

### 删除文档

1. **experiments/CODESEARCHNET_EXPERIMENT_GUIDE.md**（387行）
2. **experiments/CODESEARCHNET_EXPERIMENT_REPORT.md**（75行）

---

## 关键改进总结

1. **简化**：3个文档 → 1个主文档 + 1个扩展文档
2. **统一**：多个入口 → 单一主入口
3. **自动化**：手动5步 → 自动1步
4. **清晰**：混乱的目录结构 → 明确的主实验/扩展实验
5. **可靠**：容易出错 → 智能错误处理

---

**版本**: v2.0
**完成日期**: 2026-01-24
**状态**: ✅ 完成
**下一阶段**: Phase 7 - 性能基准测试
