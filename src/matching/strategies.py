# src/matching/strategies.py
"""
Java 知识点 - 代码片段匹配策略实现（优化版）。

改动要点：
- AST：引入领域锚点（Domain Anchors）；当模板包含锚点时，必须至少命中一个锚点，否则直接判为不匹配；
       降低"没有 AST 模板"的默认分（由 0.6 -> 0.3），避免弱约束下的高分。
- 关键词：对歧义词（如 set、get）降低权重；去除平滑项（未命中 -> 0 分），提升区分度。
- 过滤阈值：默认提高 AST 覆盖率阈值为 0.4，并支持关键词最低得分阈值（默认 0.4）。当任何阶段过滤触发 -> final_score=0。
- 兼容输入：当 required_nodes/keywords 为 JSON 字符串或混合类型时，自动解析成规范集合。
- 权重：从 config/matching.yaml 加载，默认 AST 0.5 / KW 0.4 / DIFF 0.1，归一化后参与加权融合。
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .utils import tokenize_to_set, sanitize_ast_nodes, safe_read_json, split_string_to_tokens
from lib.globals import core_logger as log

# 节点映射表：根据知识点模板名称，映射到 tree-sitter-java 的真实 AST 节点类型
# 注意：此表用于补充 required_nodes，不应包含具体类名（如 arraylist），具体类名属于 keywords
NODE_MAPPING = {
    # 基本结构
    "primitivetype": {"integral_type", "floating_point_type", "boolean_type"},
    "ifstatement": {"if_statement"},
    "forstatement": {"for_statement", "enhanced_for_statement"},
    "whilestatement": {"while_statement"},
    "trycatch": {"try_statement", "catch_clause"},
    "controlflow": {"if_statement", "switch_statement", "switch_expression", "break_statement", "continue_statement"},

    # 类和接口
    "class": {"class_declaration", "type_identifier", "method_declaration"},
    "interface": {"interface_declaration"},
    "enum": {"enum_declaration"},

    # 继承和多态
    "inheritance": {"extends_clause", "superclass"},
    "polymorphism": {"method_declaration", "annotation"},

    # 异常处理
    "exception": {"try_statement", "catch_clause", "throw_statement", "throws", "finally_clause"},

    # 函数式编程
    "lambda": {"lambda_expression"},
    "stream": {"method_invocation", "method_reference"},

    # 集合声明（仅结构性节点，具体类名在keywords中）
    "declare<list>": {"type_identifier", "object_creation_expression", "method_invocation"},
    "declare<set>": {"type_identifier", "object_creation_expression", "method_invocation"},
    "declare<map>": {"type_identifier", "object_creation_expression", "method_invocation"},

    # === 新增：泛型相关 ===
    "generic": {"type_arguments", "type_parameter", "wildcard", "type_bound"},
    "genericclass": {"type_parameter", "class_declaration"},
    "genericmethod": {"type_parameter", "method_declaration"},
    "wildcard": {"wildcard", "type_argument"},
    "typebound": {"type_bound", "extends_clause", "super"},  # extends T 或 super T

    # === 新增：注解相关 ===
    "annotation": {"annotation", "marker_annotation", "annotation_type_declaration"},
    "annotationdeclaration": {"annotation_type_declaration", "annotation_type_body"},

    # === 新增：构造器和初始化 ===
    "constructor": {"constructor_declaration", "constructor_body"},
    "staticinitializer": {"static_initializer"},

    # === 新增：字符串和字面量 ===
    "string": {"string_literal", "text_block"},  # text_block 是 Java 15+ 的多行字符串

    # === 新增：访问操作 ===
    "access": {"field_access", "array_access", "method_invocation"},
    "fieldaccess": {"field_access"},
    "arrayaccess": {"array_access"},

    # === 新增：内部类和匿名类 ===
    "innerclass": {"class_declaration", "class_body"},
    "anonymousclass": {"anonymous_class_declaration", "object_creation_expression"},

    # === 新增：同步和并发 ===
    "synchronized": {"synchronized_statement"},
    "volatile": {"field_declaration", "modifiers"},

    # === 新增：模块系统 (Java 9+) ===
    "module": {"module_declaration", "requires_directive", "exports_directive"},

    # === 新增：switch 表达式 (Java 14+) ===
    "switchexpression": {"switch_expression", "switch_block", "switch_rule"},
}

# 领域锚点：当模板包含这些词时，必须至少命中一个（或其父类型/子类型）
DOMAIN_ANCHORS = {
    # 集合
    "list", "arraylist", "linkedlist",
    "set", "hashset", "treeset", "linkedhashset",
    "map", "hashmap", "treemap", "linkedhashmap",
    "queue", "deque", "arraydeque", "priorityqueue",
    # 工具类
    "stringbuilder", "stringbuffer", "string",
    "arrays", "collections", "objects",
    # Stream API
    "stream", "optional",
    # 并发类
    "future", "completablefuture", "reentrantlock", "countdownlatch",
}

# 类型层级图：支持继承关系的松弛匹配
# 格式：子类型 -> [父类型列表]
# 用于锚点匹配时，允许父类型匹配子类型（如：要求 "list"，代码用 "arraylist" 也可以）
TYPE_HIERARCHY = {
    # List 层级
    "arraylist": ["list", "collection"],
    "linkedlist": ["list", "collection", "deque", "queue"],
    "copyonwritearraylist": ["list", "collection"],
    "vector": ["list", "collection"],
    "stack": ["vector", "list", "collection"],

    # Set 层级
    "hashset": ["set", "collection"],
    "linkedhashset": ["set", "collection"],
    "treeset": ["set", "sortedset", "navigableset", "collection"],
    "concurrentskiplistset": ["set", "sortedset", "navigableset", "collection"],
    "enumset": ["set", "collection"],

    # Map 层级
    "hashmap": ["map"],
    "linkedhashmap": ["map"],
    "treemap": ["map", "sortedmap", "navigablemap"],
    "concurrenthashmap": ["map", "concurrentmap"],
    "hashtable": ["map"],
    "weakhashmap": ["map"],
    "identityhashmap": ["map"],

    # Queue/Deque 层级
    "arraydeque": ["deque", "queue", "collection"],
    "priorityqueue": ["queue", "collection"],
    "linkedblockingqueue": ["blockingqueue", "queue", "collection"],
    "concurrentlinkedqueue": ["queue", "collection"],

    # 其他容器
    "list": ["collection"],
    "set": ["collection"],
    "queue": ["collection"],
    "deque": ["queue", "collection"],
}

# Java 核心关键字（权重大），用于关键词匹配加权
JAVA_CORE_KEYWORDS = {
    "extends", "implements", "synchronized", "volatile",
    "throws", "throw", "try", "catch", "finally",
    "abstract", "static", "final", "enum", "interface",
    "@override", "@deprecated"
}

# 歧义度较高的常见词，降低权重（例如 set/get/data/process 等）
# 注意：set/get 等词在集合类型中很重要，不应过度降权
AMBIGUOUS_KEYWORDS = {
    "data", "value", "item", "process", "handle", "read", "write", "text", "name", "id"
}

CORE_KEYWORD_WEIGHT = 2.0
GENERAL_KEYWORD_WEIGHT = 1.0
AMBIGUOUS_KEYWORD_WEIGHT = 0.7  # 从0.5提高到0.7，减少过度降权
NAME_KEYWORD_WEIGHT = 0.8  # 从名称拆出的词，略低于显式关键字

# 特定 API 类名权重（提高以增强识别度）
# 这些类名对于识别特定 API 至关重要
API_CLASS_KEYWORDS = {
    # 集合类
    "arraylist", "linkedlist", "vector", "stack",
    "hashset", "treeset", "linkedhashset",
    "hashmap", "treemap", "linkedhashmap", "hashtable",
    "arraydeque", "priorityqueue",
    # 工具类
    "stringbuilder", "stringbuffer",
    "arrays", "collections", "objects",
    # Stream & Optional
    "stream", "optional",
    # 并发类
    "future", "completablefuture", "executor", "executorservice",
    "reentrantlock", "reentrantreadwritelock", "countdownlatch", "cyclicbarrier",
    "semaphore", "phaser",
}
API_CLASS_WEIGHT = 1.8  # 介于 CORE 和 GENERAL 之间，强调 API 特异性

# 统一默认权重 - 从 config/matching.yaml 加载
# 评估实验可通过 search() 的 w_ast/w_keyword/w_difficulty 参数覆盖这些默认值
def _load_weight_defaults() -> Dict[str, float]:
    """
    从 config/matching.yaml 加载默认权重配置。
    如果加载失败，使用硬编码的回退值。
    """
    try:
        from lib.utils.matching_config import get_matching_config
        cfg = get_matching_config('default')
        weights = {
            "ast": float(cfg.get('w_ast', 0.5)),
            "keyword": float(cfg.get('w_keyword', 0.4)),
            "difficulty": float(cfg.get('w_difficulty', 0.1)),
        }
        log.debug("[strategies] 从 matching.yaml 加载权重: %s", weights)
        return weights
    except Exception as e:
        log.warning("[strategies] 无法加载 matching.yaml，使用回退值: %s", e)
        return {"ast": 0.5, "keyword": 0.4, "difficulty": 0.1}

# 延迟加载，避免循环导入
_weight_defaults_cache: Optional[Dict[str, float]] = None

def get_weight_defaults() -> Dict[str, float]:
    """获取默认权重（带缓存，从 matching.yaml 加载）"""
    global _weight_defaults_cache
    if _weight_defaults_cache is None:
        _weight_defaults_cache = _load_weight_defaults()
    return _weight_defaults_cache.copy()


def _split_name_tokens(name: Optional[str]) -> List[str]:
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


def _normalize_input_tokens(tokens: Any) -> Set[str]:
    """
    将输入（可能为 JSON 字符串、普通字符串或集合）规范为小写去重集合。
    - 若是 JSON 字符串（以 [ 开头、以 ] 结尾），使用 safe_read_json 解析；
    - 若是普通字符串，按非字母数字分隔符拆分（split_string_to_tokens）；
    - 若是可迭代对象，逐个元素归一化。
    """
    if tokens is None:
        return set()
    if isinstance(tokens, (bytes, bytearray)):
        try:
            tokens = tokens.decode("utf-8", errors="ignore")
        except Exception:
            tokens = str(tokens)
    if isinstance(tokens, str):
        s = tokens.strip()
        if s.startswith("[") and s.endswith("]"):
            parsed = safe_read_json(s, default=[])
            tokens = parsed if isinstance(parsed, list) else [s]
        else:
            tokens = split_string_to_tokens(s)
    return {str(t).strip().lower() for t in (tokens if isinstance(tokens, (list, set, tuple)) else [tokens]) if str(t).strip()}


def _is_type_compatible(required_type: str, provided_type: str) -> bool:
    """
    检查 provided_type 是否与 required_type 兼容（考虑继承关系）。

    规则：
    1. 精确匹配：required_type == provided_type → True
    2. 子类型匹配：provided_type 是 required_type 的子类 → True
       例如：required="list", provided="arraylist" → True（因为 ArrayList extends List）
    3. 父类型匹配：provided_type 是 required_type 的父类 → True
       例如：required="arraylist", provided="list" → True（反向匹配，宽松策略）

    参数:
        required_type: 知识点要求的类型（锚点）
        provided_type: 代码片段中提供的类型

    返回:
        bool: 是否兼容
    """
    # 1. 精确匹配
    if required_type == provided_type:
        return True

    # 2. provided_type 是 required_type 的子类
    # 例如：required="list", provided="arraylist"
    if provided_type in TYPE_HIERARCHY:
        parents = TYPE_HIERARCHY[provided_type]
        if required_type in parents:
            log.debug(f"[Type Hierarchy] {provided_type} 是 {required_type} 的子类 ✓")
            return True

    # 3. required_type 是 provided_type 的子类（反向匹配）
    # 例如：required="arraylist", provided="list"
    if required_type in TYPE_HIERARCHY:
        parents = TYPE_HIERARCHY[required_type]
        if provided_type in parents:
            log.debug(f"[Type Hierarchy] {required_type} 是 {provided_type} 的子类（反向匹配）✓")
            return True

    return False


def _check_domain_anchors_relaxed(required_anchors: Set[str], provided_tokens: Set[str]) -> bool:
    """
    松弛的领域锚点检查（支持类型层级匹配）。

    当知识点要求某个领域锚点时，代码片段可以使用该类型或其父类型/子类型。

    例如：
    - 知识点要求 "arraylist"，代码使用 "list" → 匹配（ArrayList 实现 List）
    - 知识点要求 "list"，代码使用 "arraylist" → 匹配（ArrayList 是 List 的实现）
    - 知识点要求 "hashset"，代码使用 "set" → 匹配

    参数:
        required_anchors: 知识点要求的锚点集合（可能包含多个）
        provided_tokens: 代码片段的关键词集合

    返回:
        bool: 是否至少命中一个锚点（考虑类型层级）
    """
    for req_anchor in required_anchors:
        for prov_token in provided_tokens:
            if _is_type_compatible(req_anchor, prov_token):
                log.debug(f"[Domain Anchor] 松弛匹配成功: 要求={req_anchor}, 提供={prov_token} ✓")
                return True

    return False


def extract_required_nodes(ast_tpl: Any) -> Set[str]:
    """
    从知识点 AST 模板配置中提取需要匹配的节点集合（全部小写）。

    策略（改进版，合并模式）：
        1. 从 required_nodes 或 template_nodes 获取显式节点
        2. 根据 template 名称从 NODE_MAPPING 获取标准节点（补充）
        3. 合并两者，确保既有显式定义，又有标准结构节点

    这样可以弥补 kp_dml.sql 中 required_nodes 的不完整性。
    """
    if not isinstance(ast_tpl, dict):
        return set()

    # 1. 显式节点列表
    nodes = ast_tpl.get("required_nodes") or ast_tpl.get("template_nodes")
    explicit_nodes = _normalize_input_tokens(nodes)

    # 2. 基于模板名称的标准节点映射
    template_name = (ast_tpl.get("template") or "").strip().lower()
    standard_nodes = set(NODE_MAPPING.get(template_name, set()))

    # 3. 合并（而不是替代）
    all_nodes = explicit_nodes.union(standard_nodes)

    # 4. 可选：合并 details 作为额外约束
    details = _normalize_input_tokens(ast_tpl.get("details"))
    all_nodes = all_nodes.union(details)

    return all_nodes


def calculate_ast_score(need_nodes: Iterable[str], have_nodes: Iterable[str], min_ratio: float = 0.4, no_need_default: float = 0.3) -> Tuple[float, float]:
    """
    计算 AST 模式匹配得分（纯结构匹配，不含领域锚点）。

    注意：领域锚点检查已移至 calculate_keyword_score，因为锚点是领域特定词（如arraylist、hashset），
    属于关键词范畴，不是AST节点类型。

    参数:
        need_nodes: 知识点要求的 AST 节点集合（set / list / 其他可迭代）
        have_nodes: 代码片段包含的 AST 节点集合（set / list / 其他可迭代）
        min_ratio: 视为"结构类似"的最低覆盖率，低于此值得分很低（默认 0.4）
        no_need_default: 知识点未定义 AST 模板时的默认得分（默认 0.3）

    返回:
        (score, coverage_ratio)
        - score ∈ [0, 1]
        - coverage_ratio: need_nodes 被覆盖的比例

    规则：
        - 若 need 为空：返回较低的默认分（0.3）
        - 覆盖率过低：score 近 0；覆盖率 >= 0.99：score=1.0
    """
    need = tokenize_to_set(need_nodes)
    if not need:
        # 知识点未显式给 AST 模板，给一个更低的中性分
        log.debug("[AST] 知识点未定义 AST 模板，返回默认分 %.2f", no_need_default)
        return float(no_need_default), 0.0

    have = sanitize_ast_nodes(have_nodes)
    log.debug("[AST] 需求节点=%s, 片段节点=%s", need, have)

    if not have:
        log.debug("[AST] 片段无 AST 节点，得分=0")
        return 0.0, 0.0

    inter = need.intersection(have)
    if not inter:
        log.debug("[AST] 无交集，得分=0")
        return 0.0, 0.0

    coverage = len(inter) / len(need)
    log.debug("[AST] 匹配节点=%s, 覆盖率=%.2f (%d/%d)", inter, coverage, len(inter), len(need))

    # 覆盖率过低，视作结构不相似
    if coverage < min_ratio:
        score = 0.2 * coverage
        log.debug("[AST] 覆盖率过低(< %.2f)，得分=%.3f", min_ratio, score)
        return score, coverage

    # 完全覆盖
    if coverage >= 0.99:
        log.debug("[AST] 完全覆盖，得分=1.0")
        return 1.0, coverage

    # 大部分覆盖：score ∈ [0.7, 0.9]
    if coverage >= 0.7:
        score = 0.7 + (coverage - 0.7) * (0.2 / 0.29)
        score = max(0.0, min(1.0, score))
        log.debug("[AST] 大部分覆盖(>=0.7)，得分=%.3f", score)
        return score, coverage

    # 一般覆盖：score ∈ [0.5, 0.7)
    score = 0.5 + (coverage - min_ratio) * (0.2 / (0.7 - min_ratio))
    score = max(0.0, min(1.0, score))
    log.debug("[AST] 一般覆盖，得分=%.3f", score)
    return score, coverage


def calculate_keyword_score(kp_kws: Any, snip_kws: Any, kp_name: Optional[str] = None) -> Tuple[float, int, int]:
    """
    计算关键词匹配得分（支持核心关键字/歧义词加权 + 领域锚点约束）。

    改动（v2优化）：
        - **领域锚点约束**：当知识点关键词包含领域锚点（如arraylist、hashset）时，
          代码片段必须命中至少一个锚点，否则得分=0（防止误匹配）
        - 去掉平滑项：未命中关键词 -> 0 分，提升区分度
        - 对歧义词（如 set/get）降低权重，减少伪命中影响
        - 兼容：当 kp_kws/snip_kws 为 JSON 字符串或普通字符串时可自动解析

    参数:
        kp_kws: 知识点配置的关键词列表/集合/字符串
        snip_kws: 代码片段抽取出的关键词集合/字符串
        kp_name: 知识点名称，会被拆成若干 token 一并参与匹配

    返回:
        (score, hit_count, base_count)
        - score ∈ [0, 1]，加权后的匹配度
        - hit_count：未加权的命中关键词个数
        - base_count：未加权的目标关键词总数
    """
    kp_tokens = _normalize_input_tokens(kp_kws)
    name_tokens = set(_split_name_tokens(kp_name)) if kp_name else set()
    base_tokens = kp_tokens.union(name_tokens)

    snip_tokens = _normalize_input_tokens(snip_kws)

    log.debug("[KW] kp_tokens=%s, name_tokens=%s, snip_tokens=%s", kp_tokens, name_tokens, snip_tokens)

    if not base_tokens:
        # 知识点没有定义关键词，给一个中性分（降低到 0.5）
        log.debug("[KW] 知识点无关键词定义，返回默认分 0.5")
        return 0.5, 0, 0

    # === 领域锚点约束（软约束版本：降低得分而非归零）===
    # 当知识点关键词包含领域特定词（如arraylist, hashset）时，代码片段应尽量命中锚点
    # 改进：使用乘数惩罚（0.3x）而不是直接归零，保证系统在召回阶段不会过度过滤
    anchor_penalty = 1.0  # 默认无惩罚
    kp_anchors = base_tokens.intersection(DOMAIN_ANCHORS)
    if kp_anchors:
        # 使用松弛检查：支持类型层级匹配（ArrayList → List, HashSet → Set）
        if not _check_domain_anchors_relaxed(kp_anchors, snip_tokens):
            anchor_penalty = 0.3  # 未满足锚点：降低到30%
            log.debug("[KW] 领域锚点约束未满足（软惩罚）: 需要锚点=%s, 应用惩罚系数=%.1f", kp_anchors, anchor_penalty)
        else:
            log.debug("[KW] 领域锚点约束满足: 需要锚点=%s ✓", kp_anchors)

    weighted_total = 0.0
    weighted_hit = 0.0
    hit_details = []

    for token in base_tokens:
        if token in JAVA_CORE_KEYWORDS:
            w = CORE_KEYWORD_WEIGHT
        elif token in API_CLASS_KEYWORDS:
            w = API_CLASS_WEIGHT  # 特定 API 类名获得更高权重
        elif token in AMBIGUOUS_KEYWORDS:
            w = AMBIGUOUS_KEYWORD_WEIGHT
        elif token in name_tokens:
            w = NAME_KEYWORD_WEIGHT
        else:
            w = GENERAL_KEYWORD_WEIGHT

        weighted_total += w
        if token in snip_tokens:
            weighted_hit += w
            hit_details.append(f"{token}(w={w})")

    # 未命中 -> 0 分
    if weighted_hit <= 0.0 or weighted_total <= 0.0:
        score = 0.0
    else:
        score = weighted_hit / weighted_total

    # 应用领域锚点惩罚（如果有）
    score = score * anchor_penalty

    plain_inter = len(base_tokens.intersection(snip_tokens))
    plain_total = len(base_tokens)

    log.debug("[KW] 命中详情: %s, 基础得分=%.3f (%.2f/%.2f), 锚点惩罚=%.1f, 最终=%.3f, 简单命中=%d/%d",
              hit_details, weighted_hit/weighted_total if weighted_total > 0 else 0,
              weighted_hit, weighted_total, anchor_penalty, score, plain_inter, plain_total)

    return max(0.0, min(1.0, score)), plain_inter, plain_total


def calculate_difficulty_score(snip_diff: Any, target: Any, mode: str = "relaxed", tolerance: float = 0.2) -> float:
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
    kp_ast_nodes: Any,
    snip_ast_nodes: Any,
    kp_keywords: Any,
    snip_keywords: Any,
    kp_name: Optional[str] = None,
    snip_difficulty: Any = None,
    target_difficulty: Any = None,
    difficulty_mode: str = "relaxed",
    weights: Optional[Dict[str, float]] = None,
    ast_min_ratio: float = 0.4,  # 统一默认值：与API Schema一致
    keyword_min_score: float = 0.4,  # 统一默认值：与API Schema一致
) -> Dict[str, Any]:
    """
    综合计算"知识点-代码片段"的最终匹配得分。

    多阶段机制：
        1. AST 快速过滤（结构不相似直接淘汰）
        2. 关键词验证（含领域锚点约束）
        3. 难度过滤（严格/宽松）
        4. 加权融合打分

    参数:
        kp_ast_nodes: 知识点 AST 模板节点集合
        snip_ast_nodes: 代码片段 AST 节点集合
        kp_keywords: 知识点关键词列表/集合/字符串
        snip_keywords: 代码片段关键词集合/字符串
        kp_name: 知识点名称
        snip_difficulty: 代码片段难度
        target_difficulty: 用户期望难度
        difficulty_mode: "strict" / "relaxed"
        weights: dict，可覆盖默认权重
        ast_min_ratio: AST 覆盖率低于此值时视作结构不匹配（默认 0.4）
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
            "filtered": bool,
        }
    """
    log.debug("[MATCH] ===== 开始匹配计算 =====")
    log.debug("[MATCH] 知识点: %s", kp_name)
    log.debug("[MATCH] 阈值配置: ast_min_ratio=%.2f, keyword_min_score=%.2f, difficulty_mode=%s",
              ast_min_ratio, keyword_min_score, difficulty_mode)
    log.debug("[MATCH] AST节点: KP=%s, Snippet=%s", kp_ast_nodes, snip_ast_nodes)
    log.debug("[MATCH] 关键词: KP=%s, Snippet=%s", kp_keywords, snip_keywords)
    log.debug("[MATCH] 难度: Snippet=%.2f, Target=%.2f, Mode=%s",
              float(snip_difficulty) if snip_difficulty else 0,
              float(target_difficulty) if target_difficulty else 0,
              difficulty_mode)

    # 权重 - 使用动态加载的配置
    default_weights = get_weight_defaults()
    weights = weights or default_weights
    w_ast = float(weights.get("ast", default_weights["ast"]))
    w_kw = float(weights.get("keyword", default_weights["keyword"]))
    w_diff = float(weights.get("difficulty", default_weights["difficulty"]))

    total_w = w_ast + w_kw + w_diff
    if total_w <= 0:
        w_ast, w_kw, w_diff = 1.0, 0.0, 0.0
    else:
        w_ast /= total_w
        w_kw /= total_w
        w_diff /= total_w

    log.debug("[MATCH] 权重配置: AST=%.1f%%, 关键词=%.1f%%, 难度=%.1f%%",
             w_ast*100, w_kw*100, w_diff*100)

    # 1. AST 结构匹配（兼容 JSON/字符串）
    need_empty = (len(tokenize_to_set(kp_ast_nodes)) == 0)
    ast_score, ast_cov = calculate_ast_score(kp_ast_nodes, snip_ast_nodes, min_ratio=ast_min_ratio)

    filtered = False
    filter_reason = []
    
    # 当存在 AST 模板时才启用 AST 覆盖率过滤
    if not need_empty and ast_cov < ast_min_ratio:
        filtered = True
        filter_reason.append(f"AST覆盖率过低({ast_cov:.2f} < {ast_min_ratio})")

    # 2. 关键词验证（兼容 JSON/字符串）
    kw_score, kw_hit, kw_total = calculate_keyword_score(kp_keywords, snip_keywords, kp_name=kp_name)
    if kw_total > 0 and kw_score < keyword_min_score:
        filtered = True
        filter_reason.append(f"关键词得分过低({kw_score:.2f} < {keyword_min_score})")

    # 3. 难度过滤
    diff_score = calculate_difficulty_score(
        snip_difficulty,
        target_difficulty,
        mode=difficulty_mode,
    )
    if difficulty_mode == "strict" and diff_score <= 0.0:
        filtered = True
        filter_reason.append("难度严格模式不匹配")

    # === 日志：各维度得分 ===
    log.debug("[MATCH] 得分明细: AST=%.2f(覆盖%.2f) | 关键词=%.2f(%d/%d) | 难度=%.2f",
             ast_score, ast_cov, kw_score, kw_hit, kw_total, diff_score)

    # 4. 加权融合
    if filtered:
        final_score = 0.0
        log.debug("[MATCH] ❌ 被过滤: %s", " | ".join(filter_reason))
    else:
        final_score = w_ast * ast_score + w_kw * kw_score + w_diff * diff_score
        if final_score < 0.0:
            final_score = 0.0
        if final_score > 1.0:
            final_score = 1.0
        log.debug("[MATCH] ✓ 最终得分: %.3f (%.0f%% x %.2f + %.0f%% x %.2f + %.0f%% x %.2f)",
                 final_score, w_ast*100, ast_score, w_kw*100, kw_score, w_diff*100, diff_score)

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


# === 辅助：批量匹配并输出 TopN（确保过滤生效） ===
def select_top_matches(
    kp_name: str,
    kp_ast_nodes: Any,
    kp_keywords: Any,
    snippets: List[Dict[str, Any]],
    target_difficulty: Optional[float] = None,
    difficulty_mode: str = "relaxed",
    weights: Optional[Dict[str, float]] = None,
    ast_min_ratio: float = 0.4,
    keyword_min_score: float = 0.4,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    对给定代码片段列表执行匹配，返回过滤后 TopN。

    snippets 每项至少包含：
        {
            "code": str,
            "ast_nodes": Iterable[str],
            "keywords": Iterable[str] 或 字符串,
            "difficulty": float,
            ... 其他字段可选
        }
    """
    results = []
    for sn in snippets:
        r = calculate_match_score(
            kp_ast_nodes=kp_ast_nodes,
            snip_ast_nodes=sn.get("ast_nodes"),
            kp_keywords=kp_keywords,
            snip_keywords=sn.get("keywords"),
            kp_name=kp_name,
            snip_difficulty=sn.get("difficulty"),
            target_difficulty=target_difficulty,
            difficulty_mode=difficulty_mode,
            weights=weights or get_weight_defaults(),
            ast_min_ratio=ast_min_ratio,
            keyword_min_score=keyword_min_score,
        )
        # 合并必要上下文
        r.update({
            "code": sn.get("code"),
            "snippet_id": sn.get("id"),
        })
        # 仅保留未过滤的结果
        if not r["filtered"]:
            results.append(r)

    # 排序：按 final_score 下降；若相同，再按 ast_coverage、keyword_score 辅助
    results.sort(key=lambda x: (x["final_score"], x["ast_coverage"], x["keyword_score"]), reverse=True)

    # 截取 TopN
    return results[:max(1, int(top_n))]
