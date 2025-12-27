# src/matching/strategies.py
"""
Java 知识点 - 代码片段匹配策略实现（优化版）。

改动要点：
- AST：引入领域锚点（Domain Anchors），当模板包含锚点时，必须至少命中一个锚点，否则直接判为不匹配；
       降低“没有 AST 模板”的默认分（由 0.6 -> 0.3），避免弱约束下的高分。
- 关键词：对歧义词（如 set、get）降低权重；去除平滑项（未命中 -> 0 分），提升区分度。
- 过滤阈值：默认提高 AST 覆盖率阈值为 0.4，并支持关键词最低得分阈值（默认 0.4）。
- 映射：补充 Declare<Set> 的节点映射为领域词（set/hashset/treeset/linkedhashset），避免“new/类型标识符”等通用节点导致误匹配。
"""

import re
from .utils import tokenize_to_set, sanitize_ast_nodes

# 节点映射表：根据知识点模板名称，映射到 tree-sitter-java 的若干节点/标识符
NODE_MAPPING = {
    # === 原有映射 ===
    "primitivetype": {"integral_type", "floating_point_type", "boolean_type", "int", "double"},
    "ifstatement": {"if_statement"},
    "forstatement": {"for_statement"},
    "whilestatement": {"while_statement"},
    "trycatch": {"try_statement", "catch_clause"},
    # 保留原 List 映射（可根据需求改为更严格的领域词）
    "declare<list>": {"type_identifier", "object_creation_expression", "new", "arraylist", "list"},

    # === Java 相关扩展映射（示例，可根据知识点体系扩展或覆盖） ===
    "class": {"class_declaration", "normal_class_declaration", "class"},
    "interface": {"interface_declaration", "interface"},
    "enum": {"enum_declaration", "enum"},
    "inheritance": {"extends_clause", "superclass", "extends"},
    "polymorphism": {"method_declaration", "override", "@override"},
    "exception": {"try_statement", "catch_clause", "throw_statement", "throws"},
    "lambda": {"lambda_expression"},
    "stream": {"method_invocation", "stream"},

    # === 新增：Set 的声明/使用（仅保留领域锚点，避免通用节点导致误匹配） ===
    "declare<set>": {"set", "hashset", "treeset", "linkedhashset"},
}

# 领域锚点：当模板包含这些词时，必须至少命中一个
DOMAIN_ANCHORS = {
    # 集合
    "list", "arraylist", "linkedlist",
    "set", "hashset", "treeset", "linkedhashset",
    "map", "hashmap", "treemap", "linkedhashmap",
    "queue", "deque",
}

# Java 核心关键字（权重大），用于关键词匹配加权
JAVA_CORE_KEYWORDS = {
    "extends", "implements", "synchronized", "volatile",
    "throws", "throw", "try", "catch", "finally",
    "abstract", "static", "final", "enum", "interface",
    "@override", "@deprecated"
}

# 歧义度较高的常见词，降低权重（例如 set/get/data/process 等）
AMBIGUOUS_KEYWORDS = {
    "set", "get", "data", "value", "item", "process", "handle", "read", "write"
}

CORE_KEYWORD_WEIGHT = 2.0
GENERAL_KEYWORD_WEIGHT = 1.0
AMBIGUOUS_KEYWORD_WEIGHT = 0.5
NAME_KEYWORD_WEIGHT = 0.8  # 从名称拆出的词，略低于显式关键字


def _split_name_tokens(name):
    """
    将知识点名称拆成若干 token，用于参与关键词匹配。
    支持：
    - 空格/下划线/符号分词
    - 简单的 camelCase / PascalCase 拆分
    """
    if not name or not isinstance(name, str):
        return []

    cleaned = re.sub(r"[^0-9a-zA-Z_]+", " ", name)
    parts = re.split(r"\s+", cleaned)

    tokens = []
    for part in parts:
        if not part:
            continue
        # 按 camelCase / PascalCase 切分
        sub_tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", part)
        if sub_tokens:
            tokens.extend(sub_tokens)
        else:
            tokens.append(part)

    return [t.lower() for t in tokens if t]


def extract_required_nodes(ast_tpl):
    """
    从知识点 AST 模板配置中提取需要匹配的节点集合（全部小写）。

    优先级：
        1. ast_tpl["required_nodes"]
        2. ast_tpl["template_nodes"]（兼容旧数据）
        3. 根据 ast_tpl["template"] 名称在 NODE_MAPPING 中查找
           并合并 ast_tpl["details"] 作为补充节点
    """
    if not isinstance(ast_tpl, dict):
        return set()

    # 1. 显式节点列表（最高优先级）
    nodes = ast_tpl.get("required_nodes") or ast_tpl.get("template_nodes")
    required = tokenize_to_set(nodes)
    if required:
        return required

    # 2. 基于模板名称的节点映射
    name = (ast_tpl.get("template") or "").strip().lower()
    base = NODE_MAPPING.get(name, set())

    # 3. 结合 details 作为补充约束
    details = tokenize_to_set(ast_tpl.get("details"))
    return set(base).union(details)


def calculate_ast_score(need_nodes, have_nodes, min_ratio=0.4, no_need_default=0.3):
    """
    计算 AST 模式匹配得分（带领域锚点约束）。

    参数:
        need_nodes: 知识点要求的 AST 节点集合（set / list / 其他可迭代）
        have_nodes: 代码片段包含的 AST 节点集合（set / list / 其他可迭代）
        min_ratio: 视为“结构类似”的最低覆盖率，低于此值得分很低（默认 0.4）
        no_need_default: 知识点未定义 AST 模板时的默认得分（默认 0.3）

    返回:
        (score, coverage_ratio)
        - score ∈ [0, 1]
        - coverage_ratio: need_nodes 被覆盖的比例

    规则（与优化方案对齐）：
        - 若 need 为空：返回较低的默认分（0.3）
        - 若 need 包含领域锚点，但 have 未命中任一锚点：score=0.0（强过滤）
        - 完全匹配：score ≈ 1.0
        - 大部分匹配 (coverage >= 0.7)：score ∈ [0.7, 0.9]
        - 一般匹配 (min_ratio <= coverage < 0.7)：score ∈ [0.5, 0.7)
        - 覆盖率过低：score 近 0
    """
    need = tokenize_to_set(need_nodes)
    if not need:
        # 知识点未显式给 AST 模板，给一个更低的中性分
        return float(no_need_default), 0.0

    have = sanitize_ast_nodes(have_nodes)
    if not have:
        return 0.0, 0.0

    # 领域锚点约束：如果模板包含锚点，则必须至少命中一个
    anchors = need.intersection(DOMAIN_ANCHORS)
    if anchors:
        if not have.intersection(anchors):
            return 0.0, 0.0

    inter = need.intersection(have)
    if not inter:
        return 0.0, 0.0

    coverage = len(inter) / len(need)

    # 覆盖率过低，视作结构不相似
    if coverage < min_ratio:
        return 0.2 * coverage, coverage

    # 完全覆盖
    if coverage >= 0.99:
        return 1.0, coverage

    # 大部分覆盖：score ∈ [0.7, 0.9]
    if coverage >= 0.7:
        score = 0.7 + (coverage - 0.7) * (0.2 / 0.29)
        return max(0.0, min(1.0, score)), coverage

    # 一般覆盖：score ∈ [0.5, 0.7)
    score = 0.5 + (coverage - min_ratio) * (0.2 / (0.7 - min_ratio))
    return max(0.0, min(1.0, score)), coverage


def calculate_keyword_score(kp_kws, snip_kws, kp_name=None):
    """
    计算关键词匹配得分（支持核心关键字/歧义词加权）。

    改动：
        - 去掉平滑项：未命中关键词 -> 0 分，提升区分度
        - 对歧义词（如 set/get）降低权重，减少伪命中影响

    参数:
        kp_kws: 知识点配置的关键词列表或集合
        snip_kws: 代码片段抽取出的关键词集合
        kp_name: 知识点名称，会被拆成若干 token 一并参与匹配

    返回:
        (score, hit_count, base_count)
        - score ∈ [0, 1]，加权后的匹配度
        - hit_count：未加权的命中关键词个数
        - base_count：未加权的目标关键词总数
    """
    kp_tokens = tokenize_to_set(kp_kws)
    name_tokens = tokenize_to_set(_split_name_tokens(kp_name)) if kp_name else set()
    base_tokens = kp_tokens.union(name_tokens)

    snip_tokens = tokenize_to_set(snip_kws)

    if not base_tokens:
        # 知识点没有定义关键词，给一个中性分（降低到 0.5）
        return 0.5, 0, 0

    weighted_total = 0.0
    weighted_hit = 0.0

    for token in base_tokens:
        if token in JAVA_CORE_KEYWORDS:
            w = CORE_KEYWORD_WEIGHT
        elif token in AMBIGUOUS_KEYWORDS:
            w = AMBIGUOUS_KEYWORD_WEIGHT
        elif token in name_tokens:
            w = NAME_KEYWORD_WEIGHT
        else:
            w = GENERAL_KEYWORD_WEIGHT

        weighted_total += w
        if token in snip_tokens:
            weighted_hit += w

    # 未命中 -> 0 分
    if weighted_hit <= 0.0 or weighted_total <= 0.0:
        score = 0.0
    else:
        score = weighted_hit / weighted_total

    plain_inter = len(base_tokens.intersection(snip_tokens))
    plain_total = len(base_tokens)

    return max(0.0, min(1.0, score)), plain_inter, plain_total


def calculate_difficulty_score(snip_diff, target, mode="relaxed", tolerance=0.2):
    """
    计算难度匹配得分。

    参数:
        snip_diff: 代码片段难度（可以是 0~1 的浮点值，也可以是整数档位）
        target: 用户或知识点期望的难度
        mode:
            - "strict": 硬性匹配
                * 若为整数档位，允许 ±1 档
                * 若为浮点值，允许差值 <= tolerance
            - "relaxed": 连续得分，1 - |snip_diff - target|
        tolerance: 宽松模式下的最大误差，或浮点难度的严格匹配容差
    """
    if snip_diff is None:
        snip_diff = 0.0
    if target is None:
        target = 0.5

    try:
        diff = float(snip_diff)
        tgt = float(target)
    except Exception:
        return 0.0

    if mode == "strict":
        if isinstance(snip_diff, int) and isinstance(target, int):
            return 1.0 if abs(snip_diff - target) <= 1 else 0.0
        return 1.0 if abs(diff - tgt) <= float(tolerance) else 0.0

    val = 1.0 - abs(diff - tgt)
    if val < 0.0:
        val = 0.0
    if val > 1.0:
        val = 1.0
    return val


def calculate_match_score(
    kp_ast_nodes,
    snip_ast_nodes,
    kp_keywords,
    snip_keywords,
    kp_name=None,
    snip_difficulty=None,
    target_difficulty=None,
    difficulty_mode="relaxed",
    weights=None,
    ast_min_ratio=0.4,
    keyword_min_score=0.4,
):
    """
    综合计算“知识点-代码片段”的最终匹配得分。

    多阶段机制：
        1. AST 快速过滤（结构不相似直接淘汰；当模板含锚点时必须命中锚点）
        2. 关键词验证（控制最低关键词得分）
        3. 难度过滤（严格/宽松）
        4. 加权融合打分

    参数:
        kp_ast_nodes: 知识点 AST 模板节点集合（list / set / 其他可迭代）
        snip_ast_nodes: 代码片段 AST 节点集合
        kp_keywords: 知识点关键词列表/集合
        snip_keywords: 代码片段关键词集合
        kp_name: 知识点名称
        snip_difficulty: 代码片段难度（数值或档位）
        target_difficulty: 用户期望难度
        difficulty_mode: "strict" / "relaxed"
        weights: dict，可覆盖默认权重，例如：
                 {"ast": 0.6, "keyword": 0.3, "difficulty": 0.1}
        ast_min_ratio: AST 覆盖率低于此值时，视作结构不匹配（默认 0.4）
        keyword_min_score: 关键词得分低于此值时视作弱相关（默认 0.4）

    返回:
        {
            "final_score": float,
            "ast_score": float,
            "ast_coverage": float,
            "keyword_score": float,
            "keyword_hit": int,
            "keyword_total": int,
            "difficulty_score": float,
            "filtered": bool,   # True 表示在某一阶段被过滤
        }
    """
    # 权重
    weights = weights or {}
    w_ast = float(weights.get("ast", 0.6))
    w_kw = float(weights.get("keyword", 0.3))
    w_diff = float(weights.get("difficulty", 0.1))

    total_w = w_ast + w_kw + w_diff
    if total_w <= 0:
        w_ast, w_kw, w_diff = 1.0, 0.0, 0.0
    else:
        w_ast /= total_w
        w_kw /= total_w
        w_diff /= total_w

    # 1. AST 结构匹配
    need_empty = (len(tokenize_to_set(kp_ast_nodes)) == 0)
    ast_score, ast_cov = calculate_ast_score(kp_ast_nodes, snip_ast_nodes, min_ratio=ast_min_ratio)

    filtered = False
    # 当存在 AST 模板时才启用 AST 覆盖率过滤
    if not need_empty and ast_cov < ast_min_ratio:
        filtered = True

    # 2. 关键词验证
    kw_score, kw_hit, kw_total = calculate_keyword_score(kp_keywords, snip_keywords, kp_name=kp_name)
    if kw_total > 0 and kw_score < keyword_min_score:
        filtered = True

    # 3. 难度过滤
    diff_score = calculate_difficulty_score(
        snip_difficulty,
        target_difficulty,
        mode=difficulty_mode,
    )
    if difficulty_mode == "strict" and diff_score <= 0.0:
        filtered = True

    # 4. 加权融合
    if filtered:
        final_score = 0.0
    else:
        final_score = w_ast * ast_score + w_kw * kw_score + w_diff * diff_score
        if final_score < 0.0:
            final_score = 0.0
        if final_score > 1.0:
            final_score = 1.0

    return {
        "final_score": final_score,
        "ast_score": ast_score,
        "ast_coverage": ast_cov,
        "keyword_score": kw_score,
        "keyword_hit": kw_hit,
        "keyword_total": kw_total,
        "difficulty_score": diff_score,
        "filtered": filtered,
    }

