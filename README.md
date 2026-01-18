# Java 知识点匹配系统

> For graduation-design-2026, BUPT
> **Version**: v1.2.4

一个基于 AST 分析和关键词匹配的 Java 代码知识点匹配系统。采用混合打分策略（AST 结构 + 关键词语义 + 难度评估），支持单点匹配和综合知识点匹配。

## 核心特性

- 🌲 **精确 AST 解析**：基于 tree-sitter-java 的方法级代码分析
- 🎯 **领域锚点约束**：防止集合类型等领域相关知识点的跨类型误匹配
- ⚖️ **三维度混合打分**：结构（AST）+ 语义（关键词）+ 难度
- 🔍 **灵活匹配模式**：支持单知识点、批量、综合匹配
- 🛡️ **智能兜底逻辑**：自动降低阈值重试，尽量不返回空结果
- 🔄 **幂等化设计**：数据库初始化和代码分析安全可重复执行

## 评估结果概览

基于 **19 个测试用例、30 个代码片段** 的标注数据集：

### 消融实验（关键发现）

| 配置 | Top-1 Accuracy | Precision@10 | MRR | 说明 |
|------|----------------|--------------|-----|------|
| **AST + Keyword** | **100.00%** | 56.93% | 1.0000 | ✅ **最优语义匹配配置** |
| Full (AST+KW+DIFF) | 94.74% | 57.46% | 0.9737 | 生产推荐配置 |
| Keyword Only | 94.74% | 56.93% | 0.9737 | 关键词是核心 |
| AST Only | 68.42% | 52.72% | 0.7675 | 结构匹配不足 |

**关键洞察**：
- ✅ AST+Keyword 组合达到 100% 准确率（19/19 全部正确）
- ✅ Difficulty 参数导致准确率下降 5.26% **符合设计预期**（见 [报告 3.2 节](tests/evaluation_results/report.md#32-difficulty参数对准确率的影响分析)）
- ✅ Difficulty 为实际应用提供**用户个性化难度适配**，是合理的工程权衡

### 基线对比

| 方法 | Top-1 Accuracy | MRR | 提升幅度 |
|------|----------------|-----|----------|
| **Hybrid (本系统)** | **94.74%** | **0.9737** | - |
| TF-IDF | 73.68% | 0.8158 | +21.06% |
| Pure AST | 63.16% | 0.7342 | +31.58% |
| Random | 31.58% | 0.3642 | +63.16% |

📊 **完整评估报告**: [tests/evaluation_results/report.md](tests/evaluation_results/report.md)

### 实验现象说明（FAQ）

#### Q1: 为什么消融实验日志中有大量"领域锚点约束未满足"？

**答**：这是**正常现象**，说明保护机制在工作。

系统采用两阶段匹配：
1. **召回阶段**：用数据库查询找候选（宽松，追求高召回率）
2. **排序阶段**：用领域锚点过滤（严格，追求高精准度）

例如查询"ArrayList basics"时：
- 召回阶段：找到22个包含`new XXX()`的代码
- 排序阶段：过滤掉19个不含ArrayList/List关键词的代码（如new HashSet(), new TreeMap()）
- 最终返回：3个真正使用ArrayList的代码

**这保证了ArrayList知识点不会匹配到HashMap代码，提高系统准确性。**

#### Q2: 为什么部分知识点在Keyword Only模式下得分为0？

**答**：揭示了Java知识点的**异质性**，这是有价值的发现。

4个知识点得分为0（但不影响整体94.74%准确率）：
- **Primitive types**（基本类型）：int, double等类型名称不在关键词提取范围内
- **Class declaration**（类声明）："class", "declaration"是元级别描述词，不是代码中的实际标识符
- **Lambda expression**（Lambda表达式）："lambda"不在语言关键字中
- **Fields and methods**（字段方法）：描述性词汇，非代码实际token

**深层原因**：Java知识点分为两类
- **行为性知识点**（80%）：通过方法调用、操作关键词识别 → Keyword匹配有效
- **结构性知识点**（20%）：本质是语法结构 → 必须依赖AST识别

**实验价值**：
- ✅ 验证了混合策略（AST+Keyword）的必要性
- ✅ 单一维度无法覆盖所有知识点类型
- ✅ 关键词匹配对80%的知识点有效，是核心组件

**详细分析**见评估报告中的 [3.1 消融实验现象说明](tests/evaluation_results/report.md#31-消融实验现象说明)。

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 配置数据库（编辑 config/db.yaml）
```

**数据库配置示例** (`config/db.yaml`):
```yaml
db:
  javalearningsys:
    host: localhost
    port: 3306
    user: root
    password: your_password
    db: javalearningsys
    charset: utf8mb4
    maxConn: 10
```

### 2. 初始化系统

```bash
# 方式1：运行完整流程（推荐）
python main.py

# 自动执行：
# - 创建数据库表结构
# - 导入知识点数据
# - 分析 sample_code.java
# - 运行测试场景
```

### 3. 启动 API 服务

```bash
# 默认端口 5000
python run_api.py

# 自定义配置
python run_api.py --port 8080 --host 0.0.0.0
```

### 4. 运行评估实验

```bash
# 完整评估（基线对比 + 消融实验）
python scripts/run_evaluation.py

# 快速评估（仅混合策略）
python scripts/run_evaluation.py --quick

# 仅消融实验
python scripts/run_evaluation.py --ablation-only
```

## 项目结构

```
java-ana-mvp/
├── api/                        # Flask API 层
│   ├── routes/                 # 路由：match.py, knowledge.py
│   ├── schemas/                # Pydantic 数据模型
│   └── middleware/             # 异常处理中间件
│
├── src/                        # 核心业务逻辑
│   ├── db_manager/             # 数据库管理（知识点、代码片段）
│   ├── java_analyzer/          # AST 分析器（tree-sitter）
│   ├── matching/               # 匹配策略（strategies.py）
│   └── services/               # 服务层（search_service.py）
│
├── tests/                      # 评估与测试
│   ├── fixtures/               # ground_truth.json（标注数据）
│   ├── evaluation/             # 评估框架（metrics, baselines, experiment）
│   └── evaluation_results/     # 评估报告（report.md, report.json）
│
├── scripts/                    # 离线脚本
│   ├── offline_tasks.py        # 数据库初始化、代码分析
│   └── run_evaluation.py       # 评估实验入口
│
├── lib/                        # 基础设施
│   ├── client/db.py            # MySQL 连接池
│   └── globals/                # 全局配置和日志
│
├── config/                     # 配置文件
│   ├── db.yaml                 # 数据库配置
│   └── logger.yaml             # 日志配置
│
├── main.py                     # 离线任务入口
├── run_api.py                  # API 服务入口
├── sample_code.java            # 示例代码（用于测试）
├── kp_dml.sql                  # 知识点预置数据
├── CLAUDE.md                   # 详细开发文档（给 Claude Code 的指南）
└── CHANGELOG.md                # 版本更新历史
```

## API 接口

### 匹配接口

#### 单个知识点匹配
```bash
POST /api/match
Content-Type: application/json

{
  "kp_id": 10011,
  "target_difficulty": 0.5,
  "top_k": 5,
  "ast_min_ratio": 0.4,
  "keyword_min_score": 0.4
}
```

**响应示例**:
```json
{
  "code": 200,
  "kp_id": 10011,
  "total": 3,
  "data": [
    {
      "id": 1,
      "content": "for (int i = 0; i < 10; i++) { ... }",
      "score": 0.85,
      "ast_score": 0.90,
      "keyword_score": 0.75,
      "difficulty": 0.55
    }
  ]
}
```

#### 综合知识点匹配
```bash
POST /api/match/composite
Content-Type: application/json

{
  "kp_ids": [10011, 10012, 10034],
  "score_aggregation": "average"  # 或 "min", "sum"
}
```

**其他接口**:
- `GET /api/knowledge/tree` - 获取知识点树状结构
- `GET /api/knowledge/{id}` - 获取知识点详情
- `POST /api/match/batch` - 批量知识点匹配
- `GET /api/match/health` - 服务健康检查

## 核心匹配算法

### 三维度混合打分

```
final_score = w_ast × ast_score + w_kw × keyword_score + w_diff × difficulty_score
```

**默认权重** (生产配置):
- AST (结构): 60%
- Keyword (语义): 30%
- Difficulty (难度): 10%

### 权重配置建议

| 场景 | 配置 | 预期效果 |
|------|------|----------|
| **纯语义检索** | `ast=0.5, kw=0.5, diff=0.0` | Top-1 Acc: 100% |
| **平衡配置** ✅ | `ast=0.6, kw=0.3, diff=0.1` | Top-1 Acc: 94.74% + 难度适配 |
| **教学平台** | `ast=0.5, kw=0.3, diff=0.2` | 强化难度分层 |

### 关键技术

1. **领域锚点 (Domain Anchors)**
   - 当知识点包含集合类型关键词（如 `arraylist`）时
   - 代码必须命中至少一个锚点，否则得分为 0
   - 防止 ArrayList 知识点匹配到 HashMap 代码

2. **别名归一化 (Canonical Aliases)**
   - `System.out.println` → `println`
   - `Arrays.asList` → `asList`
   - 确保静态导入和全限定名的一致性

3. **智能兜底机制**
   - 首次查询返回 0 结果时
   - 自动降低阈值 50% 重试一次
   - 提升用户体验，减少空结果

## 离线任务使用

`main.py` 支持通过**注释/取消注释**选择测试场景（无需命令行参数）：

```python
if __name__ == "__main__":
    # 步骤1: 自动初始化数据库
    # 步骤2: 自动分析 sample_code.java
    # 步骤3: 选择场景（取消注释其中一个）

    # run_single_test()        # 场景1: 单知识点匹配
    # run_multiple_test()      # 场景2: 综合知识点匹配
    # run_utility_functions()  # 工具: 查看知识点树、分析其他文件
```

**示例知识点 ID**:
- `10010, 10011` - 循环相关
- `10031, 10034` - 异常处理
- `10037, 10038` - 集合框架

## 依赖说明

| 依赖 | 用途 |
|------|------|
| Flask + flask-cors | Web 框架和跨域支持 |
| Pydantic | API 数据校验 |
| mysql-connector-python | MySQL 驱动（含连接池） |
| tree-sitter + tree-sitter-java | Java AST 解析 |
| PyYAML | 配置文件解析 |
| scikit-learn | TF-IDF 基线方法（评估用） |

## 开发指南

### 添加新的匹配算法

1. 在 `src/matching/strategies.py` 中添加新函数
2. 更新 `calculate_match_score()` 调用新函数
3. 在 `api/schemas/match.py` 中添加新参数
4. 运行评估验证效果：`python scripts/run_evaluation.py`

### 运行单元测试

```bash
# 测试匹配策略
python tests/test_matching_strategies.py

# 覆盖：AST 得分、关键词匹配、领域锚点、端到端场景
```

### 添加新知识点

1. 在 `kp_dml.sql` 中添加知识点数据
2. 定义 `ast_template.required_nodes` 和 `keywords`
3. 运行 `python main.py` 重新初始化
4. 准备对应的代码样例并分析

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.2.4 | 2026-01-18 | 兜底逻辑优化、权重 fix、评估报告完善 |
| v1.2.3 | 2026-01-03 | 匹配策略优化、领域锚点 bugfix、AST 兜底 |
| v1.2.2 | 2025-12-28 | 关键词权重调优、过滤阈值优化 |
| v1.2.0 | 2025-12-27 | 完整评估框架、消融实验 |

详细变更记录见 [CHANGELOG.md](CHANGELOG.md)

## 文档说明

- **README.md** (本文件) - 快速入门和核心功能概览
- **CLAUDE.md** - 详细开发文档，包含架构设计、数据流、常见工作流
- **tests/evaluation_results/report.md** - 完整实验评估报告
- **CHANGELOG.md** - 版本更新历史

## 常见问题

**Q: 为什么添加 Difficulty 参数后准确率下降？**
A: 这是符合预期的设计权衡。Difficulty 是为用户个性化而设计的，评估数据集仅标注语义相关性，无法体现其价值。详见 [评估报告 3.2 节](tests/evaluation_results/report.md#32-difficulty参数对准确率的影响分析)。

**Q: 如何提高匹配准确率？**
A: 使用 `weights = {"ast": 0.5, "keyword": 0.5, "difficulty": 0.0}` 可达 100% Top-1 准确率（在当前评估数据集上）。

**Q: API 调用时如何禁用 Difficulty？**
A: 在请求中设置 `w_difficulty: 0.0` 或不传 `target_difficulty` 参数。

**Q: 数据库初始化失败怎么办？**
A: 检查 `config/db.yaml` 配置，确保数据库已创建且权限正确。系统使用 `CREATE TABLE IF NOT EXISTS`，可安全重复执行。

## 许可证

MIT License

---

