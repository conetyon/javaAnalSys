# Design: Rule-Based Objective Evaluation Framework (Revised)

## Context

当前评估系统存在循环验证问题。本修订版基于社区反馈，解决了以下核心缺陷：
1. Layer 1 的循环论证风险
2. Layer 2 指标不合理
3. 验收标准过于乐观

**核心改进**：从二元判断改为分级判断，引入人工校准作为规则质量的硬性门槛。

## Goals / Non-Goals

### Goals
- 消除循环验证，实现客观评估
- 分级判断（0/1/2）替代二元判断
- 人工校准验证规则质量（Kappa ≥ 0.6）
- 务实的验收标准（Precision ≥ 75%）
- 评估过程完全幂等

### Non-Goals
- 不追求 95%+ 的虚高指标
- 不完全自动化（承认 Layer 3 人工必要性）
- 不修改匹配算法本身

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     修订后评估框架架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │  KP_RULES       │     │  Database       │                   │
│  │  (分级规则)      │     │  (Read-Only)    │                   │
│  └────────┬────────┘     └────────┬────────┘                   │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌─────────────────────────────────────────┐                   │
│  │      GradedLabeler (分级标注器)          │                   │
│  │   - calculate_feature_grade() → 0/1/2   │                   │
│  │   - 多维度信号判断                       │                   │
│  └────────────────────┬────────────────────┘                   │
│                       │                                         │
│                       ▼  (内存中，不持久化)                      │
│  ┌─────────────────────────────────────────┐                   │
│  │      Graded Ground Truth                │                   │
│  │   Dict[kp_id, Dict[hash, grade]]        │                   │
│  │   grade: 0=不相关, 1=包含, 2=主要逻辑    │                   │
│  └────────────────────┬────────────────────┘                   │
│                       │                                         │
│           ┌───────────┼───────────┐                            │
│           ▼           ▼           ▼                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │  Layer 1    │ │  Layer 2    │ │  Layer 3    │              │
│  │ 分级        │ │  nDCG@K     │ │ 人工校准    │              │
│  │ Precision   │ │             │ │ (Kappa)     │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Decisions

### Decision 1: 分级判断替代二元判断

**问题**：二元规则（满足/不满足）无法区分"包含特征"和"主要演示"。

**解决**：三级评分体系
- **Grade 0**：不包含目标特征（不相关）
- **Grade 1**：包含目标特征（部分相关）
- **Grade 2**：目标特征是主要逻辑（高度相关）

```python
def calculate_feature_grade(snippet: Dict, rule: Dict) -> int:
    """
    分级判断：0=不相关, 1=包含, 2=主要逻辑

    使用多维度信号避免单一指标的偏差
    """
    ast_features = snippet.get("ast_features", [])
    positive_nodes = rule.get("positive_nodes", [])

    # Grade 0: 不包含目标特征
    if not any(node in ast_features for node in positive_nodes):
        return 0

    # Grade 2 的多维度判断
    signals = []

    # 信号1: 特征密度 > 15%
    target_count = sum(ast_features.count(n) for n in positive_nodes)
    total_count = len(ast_features)
    if total_count > 0:
        signals.append(target_count / total_count > 0.15)

    # 信号2: 方法名包含相关关键词
    method_name = snippet.get("method_name", "").lower()
    name_keywords = rule.get("name_keywords", [])
    signals.append(any(kw in method_name for kw in name_keywords))

    # 信号3: 代码长度在规则指定范围内（可配置）
    loc = snippet.get("lines_of_code", 0)
    loc_min, loc_max = get_loc_range(rule)
    signals.append(loc_min <= loc <= loc_max)

    # 信号4: 噪声特征少（使用规则特定或默认噪声节点）
    noise_nodes = get_noise_nodes(rule)
    noise_count = sum(ast_features.count(n) for n in noise_nodes)
    signals.append(noise_count < target_count)

    # 满足 >= 2 个信号 → Grade 2
    return 2 if sum(signals) >= 2 else 1
```

### Decision 2: Layer 1 改用分级 Precision

**问题**：原设计的"必要条件满足率"只验证二元存在性，不验证相关性质量。

**解决**：分级 Precision 计算

```python
def calculate_graded_precision(predictions: List[str],
                                grades: Dict[str, int],
                                k: int) -> float:
    """
    分级 Precision@K

    公式: (2×count_grade2 + 1×count_grade1) / (2×K)
    - 满分 1.0 = 全部是 Grade 2
    - 0.5 = 全部是 Grade 1
    - 0.0 = 全部是 Grade 0
    """
    top_k = predictions[:k]
    score = sum(grades.get(p, 0) for p in top_k)
    max_score = 2 * k
    return score / max_score if max_score > 0 else 0.0
```

### Decision 3: Layer 2 改用 nDCG

**问题**：原设计的 Spearman 相关性只验证"算法按预期工作"，不验证"排序正确"。

**解决**：使用 nDCG 评估排序质量

```python
def calculate_ndcg(predictions: List[str],
                   grades: Dict[str, int],
                   k: int) -> float:
    """
    Normalized Discounted Cumulative Gain

    衡量：高相关代码（Grade 2）是否排在前面
    """
    def dcg(relevances: List[int]) -> float:
        return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))

    top_k = predictions[:k]
    actual_rels = [grades.get(p, 0) for p in top_k]
    ideal_rels = sorted(grades.values(), reverse=True)[:k]

    dcg_actual = dcg(actual_rels)
    dcg_ideal = dcg(ideal_rels)

    return dcg_actual / dcg_ideal if dcg_ideal > 0 else 0.0
```

### Decision 4: Layer 3 人工校准流程

**必要性**：规则质量无法完全自动验证，人工校准是硬性门槛。

**标注一致性方案**：
```
选项 A（资源充足）：
├── 2 人独立标注全部 60 样本
├── 计算 inter-rater Kappa（标注者间一致性）
├── Kappa ≥ 0.6 才使用标注结果
└── 分歧样本讨论后决定

选项 B（资源有限，推荐）：
├── 1 人标注全部 60 样本
├── 另 1 人复核 20%（12 样本）
├── 复核一致率 ≥ 80% 视为可接受
└── 不一致样本讨论后修正

选项 C（最小资源）：
├── 1 人标注全部样本
├── 事后抽查 10% 检验
└── 用规则 Grade vs 人工 Grade 计算"规则-人工一致性"
```

**推荐选项 B**：平衡成本与质量，复核机制确保标注质量。

**流程**：

```
1. 分层抽样
   ├── 每个知识点类别至少 3 个 KP
   ├── 随机选择，避免挑选偏差
   └── 共抽取 20 个 KP

2. 生成标注文件
   ├── 每个 KP 输出 Top-3 结果
   ├── 包含代码预览、规则 Grade
   └── 输出到 experiments/results/human_review.json

3. 主标注（1 人）
   ├── 标注员为每个样本打分 (0/1/2)
   └── 共 60 个样本

4. 复核（另 1 人，20%）
   ├── 随机抽取 12 个样本复核
   ├── 计算一致率
   └── 一致率 < 80% 需讨论校准

5. 计算 Kappa
   ├── 规则 Grade vs 人工 Grade
   ├── 目标：Kappa ≥ 0.6
   └── 输出分歧分析报告

6. 迭代改进
   ├── Kappa < 0.6 → 分析分歧样本
   ├── 修订规则定义
   └── 重新抽样验证
```

**标注输出格式**：

```json
{
  "kp_id": 10011,
  "kp_name": "For Loop",
  "samples": [
    {
      "rank": 1,
      "content_hash": "abc123...",
      "code_preview": "public void example() {\n  for(int i=0; i<10; i++) {\n    ...\n  }\n}",
      "rule_grade": 2,
      "human_grade": null
    }
  ]
}
```

### Decision 5: 小规模 Pilot 先行

**必要性**：避免规则设计的系统性问题导致大量返工。

**Pilot 流程**：
1. 选择 5 个知识点（覆盖不同类别）
2. 手写规则，运行三层评估
3. 人工校准 15 个样本
4. 验证 Kappa ≥ 0.6
5. 通过后再扩展到全部知识点

## Rules Definition Schema (Revised)

```python
# experiments/evaluation/rules.py

from typing import TypedDict, List, Optional, Tuple

class KPRule(TypedDict):
    name: str                                    # 知识点名称
    positive_nodes: List[str]                    # 必须包含的 AST 节点
    alternative_nodes: Optional[List[str]]       # 可替代的节点
    name_keywords: Optional[List[str]]           # 方法名关键词（用于 Grade 2 判断）
    noise_nodes: Optional[List[str]]             # 规则特定噪声节点（覆盖默认）
    loc_range: Optional[Tuple[int, int]]         # 代码长度范围（默认 5-30）
    positive_keywords: Optional[List[str]]       # 类型名关键词（集合类用）
    case_insensitive: Optional[bool]             # 关键词大小写不敏感

# 默认噪声节点（可被规则覆盖）
DEFAULT_NOISE_NODES = ["class_declaration", "lambda_expression"]

# 默认代码长度范围
DEFAULT_LOC_RANGE = (5, 30)

def get_noise_nodes(rule: KPRule) -> List[str]:
    """获取规则特定的噪声节点，自动排除规则本身需要的节点"""
    base = rule.get("noise_nodes") or DEFAULT_NOISE_NODES
    positive = set(rule.get("positive_nodes", []))
    return [n for n in base if n not in positive]

def get_loc_range(rule: KPRule) -> Tuple[int, int]:
    """获取代码长度范围"""
    return rule.get("loc_range") or DEFAULT_LOC_RANGE

KP_RULES: Dict[int, KPRule] = {
    # ===== 控制流 =====
    10011: {
        "name": "For Loop",
        "positive_nodes": ["for_statement"],
        "alternative_nodes": ["enhanced_for_statement"],
        "name_keywords": ["loop", "iterate", "traverse", "for"],
        # 不指定 noise_nodes，使用默认值
    },
    10012: {
        "name": "While Loop",
        "positive_nodes": ["while_statement"],
        "name_keywords": ["loop", "while", "poll", "wait"],
    },
    10021: {
        "name": "Try-Catch",
        "positive_nodes": ["try_statement", "catch_clause"],
        "name_keywords": ["handle", "catch", "error", "exception"],
        "noise_nodes": ["class_declaration"],  # lambda 可能与异常处理组合
    },

    # ===== 面向对象 =====
    10031: {
        "name": "Inheritance",
        "positive_nodes": ["superclass"],
        "name_keywords": ["extend", "inherit", "child", "sub"],
        "loc_range": (3, 50),  # 继承类可能较长
    },
    10032: {
        "name": "Interface Implementation",
        "positive_nodes": ["super_interfaces"],
        "name_keywords": ["impl", "implement", "interface"],
        "loc_range": (3, 50),
    },

    # ===== 集合类 =====
    10083: {
        "name": "ArrayList",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["arraylist"],
        "name_keywords": ["list", "array", "add", "remove"],
        "case_insensitive": True,
        "loc_range": (3, 40),  # 集合操作可能较短
    },
}
```

## Acceptance Criteria (Revised)

| 指标 | 阈值 | 说明 |
|------|------|------|
| **分级 Precision@10** | ≥ 0.75 | 务实阈值，承认规则不完美 |
| **nDCG@10** | ≥ 0.70 | 排序质量 |
| **规则覆盖度** | ≥ 70% | 已定义规则的 KP 占比 |
| **人工校准 Kappa** | ≥ 0.60 | **硬性门槛**，规则质量验证 |
| **Pilot 通过** | 5 KP | 先验证流程可行性 |

## Risks / Trade-offs

### Risk 1: Grade 2 判断仍可能与算法趋同
- **缓解**：多维度信号（方法名、代码长度、噪声特征）与算法使用的特征不同
- **验证**：Layer 3 人工校准

### Risk 2: 人工校准成本
- **缓解**：仅需 60 样本 + 12 样本复核
- **收益**：作为规则质量的"锚点"，长期复用

### Risk 3: Kappa < 0.6 导致无法通过验收
- **缓解**：迭代改进规则
- **回退**：如果多次迭代仍无法达标，说明规则化方法本身有局限，需考虑其他方案

### Trade-off: 指标降低 vs 真实性
- **选择**：从 95% 降到 75%
- **理由**：务实的 75% 比虚假的 95% 更有价值

## Rule Independence Verification

**目的**：确保评估规则与匹配算法实现相互独立，防止隐性过拟合。

### 验证方法

```python
def verify_rule_independence():
    """
    验证规则定义不依赖匹配算法的核心组件

    检查项：
    1. 规则不使用 NODE_MAPPING（算法的节点映射表）
    2. 规则不使用 DOMAIN_ANCHORS（算法的领域锚点）
    3. 规则不使用 CANONICAL_ALIASES（算法的别名规范化）
    4. 规则不使用加权计算（算法的评分权重）
    """
    from src.matching.strategies import NODE_MAPPING, DOMAIN_ANCHORS
    from src.java_analyzer.constants import CANONICAL_ALIASES
    from experiments.evaluation.rules import KP_RULES

    violations = []

    for kp_id, rule in KP_RULES.items():
        # 检查1: 规则的 positive_nodes 是否直接使用了 NODE_MAPPING 的 key
        for node in rule.get("positive_nodes", []):
            if node in NODE_MAPPING:
                violations.append(
                    f"KP {kp_id}: positive_node '{node}' 是 NODE_MAPPING 的 key，"
                    f"应使用具体的 tree-sitter 节点名"
                )

        # 检查2: 规则的关键词是否使用了别名
        for kw in rule.get("positive_keywords", []):
            if kw in CANONICAL_ALIASES:
                violations.append(
                    f"KP {kp_id}: keyword '{kw}' 在 CANONICAL_ALIASES 中，"
                    f"规则应使用原始关键词"
                )

    return violations

# 在评估启动时自动运行
def run_independence_check():
    violations = verify_rule_independence()
    if violations:
        print("⚠️ 规则独立性检查发现问题：")
        for v in violations:
            print(f"  - {v}")
        print("\n请修改规则定义，确保与算法实现独立。")
        return False
    print("✅ 规则独立性检查通过")
    return True
```

### 独立性原则

| 组件 | 规则可用 | 规则禁用 | 原因 |
|------|---------|---------|------|
| tree-sitter 节点名 | ✅ | - | 原始 AST 节点，客观事实 |
| NODE_MAPPING keys | - | ❌ | 算法抽象层，会导致耦合 |
| 原始关键词 | ✅ | - | 代码中实际出现的词 |
| CANONICAL_ALIASES | - | ❌ | 算法的规范化逻辑 |
| DOMAIN_ANCHORS | - | ❌ | 算法的过滤逻辑 |
| 代码行数 | ✅ | - | 客观事实 |
| 方法名 | ✅ | - | 客观事实 |

## Migration Plan

### Phase 0: Pilot (先行验证)
- 选择 5 个知识点：for循环、while循环、try-catch、继承、ArrayList
- 实现最小可用版本
- 完成人工校准，验证 Kappa ≥ 0.6
- **Gate**: Pilot 不通过则暂停，分析原因

### Phase 1: 规则扩展
- 扩展规则到全部主要知识点（~30 个）
- 再次人工校准（扩大样本）
- 验证整体指标

### Phase 2: 切换默认
- 新方式成为默认
- 保留 `--legacy` 标志

### Phase 3: 文档更新
- 更新 CLAUDE.md
- 归档 openspec 提案

## Open Questions

1. **规则维护**：谁负责规则的持续更新？
   - 建议：随代码库变化时检查覆盖度

2. **人工校准频率**：每次评估都需要人工校准吗？
   - 建议：规则变更时重新校准，否则复用

3. **跨项目复用**：规则能否用于其他 Java 项目？
   - 待验证：可能需要针对项目特点调整
