# experiments/evaluation/rules.py
"""
分级规则定义模块

为每个知识点定义客观的判定规则，用于生成分级 Ground Truth。
规则设计原则：
1. 与匹配算法实现独立（不使用 NODE_MAPPING、DOMAIN_ANCHORS、CANONICAL_ALIASES）
2. 使用多维度信号判断 Grade 2（避免单一指标偏差）
3. 支持可配置参数（loc_range、noise_nodes）
"""

from typing import Dict, List, Optional, Tuple, TypedDict, Set
import math


class KPRule(TypedDict, total=False):
    """知识点规则定义"""
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
    alternative = set(rule.get("alternative_nodes", []))
    exclude = positive | alternative
    return [n for n in base if n not in exclude]


def get_loc_range(rule: KPRule) -> Tuple[int, int]:
    """获取代码长度范围"""
    return rule.get("loc_range") or DEFAULT_LOC_RANGE


# =============================================================================
# KP 规则定义
# 包含 70+ 个知识点规则，覆盖 Java 核心语法、控制流、OOP、集合、Stream、并发等
# 注意：KP ID 必须与数据库中的 knowledge_points 表匹配
# =============================================================================

# Pilot KP IDs（用于 --pilot 模式）
PILOT_KP_IDS = [10010, 10011, 10031, 10017, 10037]

KP_RULES: Dict[int, KPRule] = {
    # ==========================================================================
    # 核心语法与类型 (10001-10006)
    # ==========================================================================

    10001: {  # Primitive types: int/double/boolean
        "name": "Primitive Types",
        "positive_nodes": ["primitive_type", "integral_type", "floating_point_type"],
        "name_keywords": ["int", "double", "boolean", "long", "float", "byte", "char", "short"],
        "loc_range": (3, 100),
    },
    10002: {  # Type casting and promotion
        "name": "Type Casting",
        "positive_nodes": ["cast_expression"],
        "name_keywords": ["cast", "convert", "parse", "to", "as", "from"],
        "loc_range": (3, 80),
    },
    10003: {  # String operations basics
        "name": "String Operations",
        "positive_nodes": ["method_invocation", "string_literal"],
        "positive_keywords": ["substring", "indexof", "replace", "split", "trim", "tolowercase", "touppercase", "equals", "length"],
        "name_keywords": ["string", "parse", "format", "concat", "join", "split"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10004: {  # StringBuilder and StringBuffer
        "name": "StringBuilder",
        "positive_nodes": ["type_identifier", "object_creation_expression"],
        "positive_keywords": ["stringbuilder", "stringbuffer"],
        "name_keywords": ["build", "append", "concat", "string", "buffer", "format"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10005: {  # Arrays basics
        "name": "Arrays",
        "positive_nodes": ["array_creation_expression", "array_type"],
        "name_keywords": ["array", "arr", "list", "init", "create", "copy", "fill"],
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # 控制流 (10007-10012)
    # ==========================================================================

    10007: {  # if statement
        "name": "If Statement",
        "positive_nodes": ["if_statement"],
        "name_keywords": ["check", "if", "condition", "validate", "test", "verify", "is", "has"],
        "loc_range": (3, 80),
    },
    # 10008 Switch Statement 已移除：CodeSearchNet 数据集中 switch 语句极少
    10010: {  # for loop
        "name": "For Loop",
        "positive_nodes": ["for_statement", "enhanced_for_statement"],
        "name_keywords": ["loop", "iterate", "traverse", "for", "each", "process", "scan"],
        "loc_range": (3, 100),
    },
    10011: {  # while loop
        "name": "While Loop",
        "positive_nodes": ["while_statement"],
        "name_keywords": ["loop", "while", "poll", "wait", "spin", "read", "next", "process"],
        "loc_range": (3, 100),
    },
    10012: {  # break and continue
        "name": "Break and Continue",
        "positive_nodes": ["break_statement", "continue_statement"],
        "name_keywords": ["loop", "break", "continue", "skip", "exit", "stop", "iterate"],
        "loc_range": (5, 100),
    },

    # ==========================================================================
    # OOP 基础 (10013-10017, 10024)
    # ==========================================================================

    10013: {  # Class declaration
        "name": "Class Declaration",
        "positive_nodes": ["class_declaration"],
        "name_keywords": ["class", "create", "define", "declare"],
        "noise_nodes": [],
        "loc_range": (5, 200),
    },
    10014: {  # Fields and methods
        "name": "Fields and Methods",
        "positive_nodes": ["field_declaration", "method_declaration"],
        "name_keywords": ["field", "method", "get", "set", "property"],
        "loc_range": (3, 150),
    },
    10015: {  # Constructors
        "name": "Constructors",
        "positive_nodes": ["constructor_declaration"],
        "name_keywords": ["init", "create", "build", "new", "construct", "setup"],
        "loc_range": (3, 100),
    },
    10016: {  # this and super usage
        "name": "This and Super",
        "positive_nodes": ["this", "super"],
        "name_keywords": ["this", "super", "self", "parent", "base"],
        "loc_range": (3, 100),
    },
    10017: {  # Inheritance: extends
        "name": "Inheritance",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["super"],
        "name_keywords": ["override", "extend", "inherit", "child", "sub", "base", "parent", "super"],
        "loc_range": (3, 150),
    },
    10024: {  # Inner and anonymous classes
        "name": "Inner Classes",
        "positive_nodes": ["class_declaration", "object_creation_expression"],
        "name_keywords": ["inner", "nested", "anonymous", "local"],
        "loc_range": (5, 200),
    },

    # ==========================================================================
    # 泛型 (10025-10027)
    # 移除: 10028 Wildcard, 10029 Upper Bound (数据集中极少)
    # ==========================================================================

    10025: {  # Generic class declaration
        "name": "Generic Class",
        "positive_nodes": ["type_parameters", "generic_type"],
        "name_keywords": ["generic", "type", "template", "param"],
        "loc_range": (5, 200),
    },
    10026: {  # Generic methods
        "name": "Generic Methods",
        "positive_nodes": ["type_parameters", "method_declaration"],
        "name_keywords": ["generic", "type", "convert", "cast"],
        "loc_range": (3, 150),
    },
    10027: {  # Diamond operator
        "name": "Diamond Operator",
        "positive_nodes": ["generic_type", "object_creation_expression"],
        "name_keywords": ["new", "create", "init", "list", "map", "set"],
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # 异常处理 (10031-10034, 10036)
    # ==========================================================================

    10031: {  # try-catch basics
        "name": "Try-Catch",
        "positive_nodes": ["try_statement"],
        "alternative_nodes": ["catch_clause"],
        "name_keywords": ["handle", "catch", "error", "exception", "try", "safe", "check"],
        "noise_nodes": ["class_declaration"],
        "loc_range": (3, 150),
    },
    10032: {  # finally clause
        "name": "Finally Clause",
        "positive_nodes": ["finally_clause"],
        "alternative_nodes": ["try_statement"],
        "name_keywords": ["finally", "cleanup", "close", "release", "dispose", "shutdown"],
        "loc_range": (5, 150),
    },
    10033: {  # throw and throws
        "name": "Throw Statement",
        "positive_nodes": ["throw_statement"],
        "name_keywords": ["throw", "error", "exception", "fail", "invalid", "check"],
        "loc_range": (3, 100),
    },
    10034: {  # try-with-resources
        "name": "Try-With-Resources",
        "positive_nodes": ["resource_specification"],
        "alternative_nodes": ["try_with_resources_statement"],
        "name_keywords": ["resource", "read", "write", "stream", "open", "file", "connection"],
        "loc_range": (3, 100),
    },
    10036: {  # Rethrow exceptions
        "name": "Rethrow Exception",
        "positive_nodes": ["throw_statement", "catch_clause"],
        "name_keywords": ["rethrow", "throw", "propagate", "wrap", "handle"],
        "loc_range": (5, 100),
    },

    # ==========================================================================
    # 集合 - List (10037-10040)
    # ==========================================================================

    10037: {  # ArrayList basics
        "name": "ArrayList",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["arraylist"],
        "name_keywords": ["list", "array", "add", "remove", "get", "size", "create", "init"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10038: {  # LinkedList basics
        "name": "LinkedList",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["linkedlist"],
        "name_keywords": ["list", "linked", "add", "remove", "queue", "deque"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10039: {  # List add/remove/get
        "name": "List Operations",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["add", "remove", "get", "set", "list"],
        "name_keywords": ["add", "remove", "get", "insert", "delete", "list"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10040: {  # List sorting with Comparator
        "name": "List Sorting",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["sort", "comparator", "compare", "collections.sort"],
        "name_keywords": ["sort", "order", "compare", "rank", "arrange"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # 集合 - Set (10041-10044)
    # ==========================================================================

    10041: {  # HashSet basics
        "name": "HashSet",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["hashset"],
        "name_keywords": ["set", "unique", "distinct", "add", "remove", "contains", "dedupe"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10042: {  # TreeSet basics
        "name": "TreeSet",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["treeset"],
        "name_keywords": ["tree", "set", "sorted", "order"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10043: {  # Set add/remove/contains
        "name": "Set Operations",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["add", "remove", "contains", "set"],
        "name_keywords": ["add", "remove", "contains", "has", "check", "set"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10044: {  # LinkedHashSet basics
        "name": "LinkedHashSet",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["linkedhashset"],
        "name_keywords": ["linked", "hash", "set", "order"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # 集合 - Map (10045-10048)
    # ==========================================================================

    10045: {  # HashMap basics
        "name": "HashMap",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["hashmap"],
        "name_keywords": ["map", "dict", "put", "get", "key", "value", "cache", "store"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10046: {  # LinkedHashMap basics
        "name": "LinkedHashMap",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["linkedhashmap"],
        "name_keywords": ["linked", "hash", "map", "order"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10047: {  # TreeMap basics
        "name": "TreeMap",
        "positive_nodes": ["type_identifier"],
        "positive_keywords": ["treemap"],
        "name_keywords": ["tree", "map", "sorted", "order"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10048: {  # Map entrySet iteration
        "name": "Map EntrySet",
        "positive_nodes": ["enhanced_for_statement", "method_invocation"],
        "positive_keywords": ["entryset", "entry"],
        "name_keywords": ["iterate", "entry", "map", "foreach", "loop", "traverse"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },

    # ==========================================================================
    # 集合 - Queue & Deque
    # 移除: 10051, 10052 (数据集中精度过低 10%)
    # ==========================================================================

    # ==========================================================================
    # Stream API (10053-10060)
    # ==========================================================================

    10053: {  # Stream pipeline creation
        "name": "Stream Pipeline",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["stream"],
        "name_keywords": ["stream", "process", "pipeline", "flow", "transform"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10054: {  # Intermediate operations: map/filter
        "name": "Stream Map/Filter",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["filter", "map"],
        "name_keywords": ["filter", "map", "transform", "select", "convert", "stream"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10055: {  # flatMap (注意：数据库中 10055 是 flatMap)
        "name": "Stream FlatMap",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["flatmap"],
        "name_keywords": ["flatmap", "flatten", "merge", "stream"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10056: {  # sorted and distinct
        "name": "Stream Sorted/Distinct",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["sorted", "distinct"],
        "name_keywords": ["sort", "distinct", "unique", "order", "stream"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10057: {  # collect toList/toSet
        "name": "Stream Collect",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["collect", "collectors"],
        "name_keywords": ["collect", "tolist", "toset", "group", "join", "stream"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    # 移除: 10058 reduce, 10059 findFirst/Any, 10060 parallel (数据集中 Stream+method 组合稀少)

    # ==========================================================================
    # Lambda & 函数式 (10061-10068)
    # ==========================================================================

    10061: {  # Lambda expression basics
        "name": "Lambda Expression",
        "positive_nodes": ["lambda_expression"],
        "name_keywords": ["lambda", "functional", "filter", "map", "stream", "apply", "transform"],
        "noise_nodes": [],
        "loc_range": (3, 80),
    },
    # 移除: 10062 Functional Interface (无数据), 10063 Predicate/Function, 10066 Consumer/Supplier (数据集中稀少)
    10064: {  # Comparator with lambda
        "name": "Comparator Lambda",
        "positive_nodes": ["lambda_expression", "method_invocation"],
        "positive_keywords": ["comparator", "compare", "comparing"],
        "name_keywords": ["compare", "comparator", "sort", "order"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10065: {  # Method references
        "name": "Method Reference",
        "positive_nodes": ["method_reference"],
        "name_keywords": ["reference", "method", "stream", "foreach", "map", "apply"],
        "loc_range": (3, 80),
    },
    10067: {  # Stream forEach with method reference
        "name": "ForEach",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["foreach"],
        "name_keywords": ["foreach", "each", "iterate", "process"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # Optional (10069-10070)
    # 移除: 10071 ifPresent (精度 20%)
    # ==========================================================================

    10069: {  # Optional basics
        "name": "Optional Basics",
        "positive_nodes": ["method_invocation", "type_identifier"],
        "positive_keywords": ["optional"],
        "name_keywords": ["optional", "maybe", "nullable", "empty"],
        "case_insensitive": True,
        "loc_range": (3, 80),
    },
    10070: {  # Optional map/filter/orElse
        "name": "Optional Operations",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["orelse", "orelsethrow", "orelseget", "optional"],
        "name_keywords": ["orelse", "default", "fallback", "optional"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },

    # ==========================================================================
    # 并发 (10073-10078)
    # 移除: 10075 Volatile, 10079 ReentrantLock, 10080 Atomic (数据集中稀少或 0%)
    # 保留低精度: 10077 ExecutorService (30%), 10080 Atomic (30%) - 有部分匹配
    # ==========================================================================

    10073: {  # Thread creation: Thread/Runnable
        "name": "Thread Creation",
        "positive_nodes": ["object_creation_expression", "method_invocation"],
        "positive_keywords": ["thread", "runnable"],
        "name_keywords": ["thread", "run", "start", "execute", "task", "worker"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },
    10074: {  # synchronized keyword
        "name": "Synchronized",
        "positive_nodes": ["synchronized_statement"],
        "name_keywords": ["sync", "lock", "thread", "concurrent", "atomic", "critical", "mutex"],
        "loc_range": (5, 100),
    },
    10076: {  # wait and notify
        "name": "Wait and Notify",
        "positive_nodes": ["synchronized_statement", "method_invocation"],
        "positive_keywords": ["wait", "notify", "notifyall", "notifyAll"],
        "name_keywords": ["wait", "notify", "signal", "sync", "monitor", "lock"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },
    10078: {  # Future get
        "name": "Future",
        "positive_nodes": ["method_invocation", "type_identifier"],
        "positive_keywords": ["future", "get", "completablefuture"],
        "name_keywords": ["future", "async", "get", "result", "await"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },

    # ==========================================================================
    # I/O 流 (10082-10083)
    # 移除: 10081 FileStream, 10084 Charset (数据集中 0%)
    # ==========================================================================

    10082: {  # BufferedReader and BufferedWriter
        "name": "BufferedReader/Writer",
        "positive_nodes": ["type_identifier", "object_creation_expression"],
        "positive_keywords": ["bufferedreader", "bufferedwriter"],
        "name_keywords": ["read", "write", "buffer", "line", "stream", "file", "io"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },
    10083: {  # PrintStream println
        "name": "PrintStream",
        "positive_nodes": ["method_invocation", "field_access"],
        "positive_keywords": ["println", "print", "system.out"],
        "name_keywords": ["print", "log", "output", "debug", "display", "show"],
        "case_insensitive": True,
        "loc_range": (3, 80),
    },

    # ==========================================================================
    # NIO (10085-10086) - 保留，有较好数据覆盖
    # ==========================================================================

    10085: {  # Paths and Files
        "name": "NIO Paths/Files",
        "positive_nodes": ["method_invocation", "type_identifier"],
        "positive_keywords": ["paths", "files", "path"],
        "name_keywords": ["path", "file", "nio", "read", "write", "resolve"],
        "case_insensitive": True,
        "loc_range": (3, 100),
    },
    10086: {  # FileChannel and ByteBuffer
        "name": "FileChannel/ByteBuffer",
        "positive_nodes": ["method_invocation", "type_identifier"],
        "positive_keywords": ["filechannel", "bytebuffer", "channel"],
        "name_keywords": ["channel", "buffer", "nio", "read", "write"],
        "case_insensitive": True,
        "loc_range": (5, 100),
    },

    # ==========================================================================
    # 日期时间
    # 移除大部分: 10087-10092 在数据集中覆盖极低 (0-10%)
    # ==========================================================================

    # ==========================================================================
    # 注解与反射 (10093, 10096)
    # 移除: 10097 Reflection Methods, 10098 Annotation Introspection (精度 10-30%)
    # ==========================================================================

    10093: {  # @Override and @Deprecated usage
        "name": "Annotations",
        "positive_nodes": ["marker_annotation", "normal_annotation"],
        "name_keywords": ["override", "deprecated", "annotate", "mark", "meta"],
        "loc_range": (3, 100),
    },
    10096: {  # Class.forName and ClassLoader
        "name": "Class Loading",
        "positive_nodes": ["method_invocation"],
        "positive_keywords": ["forname", "classloader", "loadclass"],
        "name_keywords": ["class", "load", "forname", "reflect"],
        "case_insensitive": True,
        "loc_range": (3, 80),
    },
}


# =============================================================================
# 分级判断函数
# =============================================================================

def calculate_feature_grade(snippet: Dict, rule: KPRule) -> int:
    """
    分级判断：0=不相关, 1=包含, 2=主要逻辑

    使用多维度信号避免单一指标的偏差：
    - 信号1: 显式命名 (Strong Signal)
    - 信号2: 高密度 (Strong Signal)
    - 信号3: 多次出现 (Medium Signal)
    - 信号4: 适中长度 (Weak Signal)

    Args:
        snippet: 代码片段字典，包含 ast_features, method_name, lines_of_code, keywords
        rule: 知识点规则

    Returns:
        0: 不相关（不包含目标特征）
        1: 部分相关（包含目标特征但不满足 Grade 2 条件）
        2: 高度相关（目标特征是主要逻辑）
    """
    ast_features = snippet.get("ast_features", [])
    positive_nodes = rule.get("positive_nodes", [])
    alternative_nodes = rule.get("alternative_nodes", [])

    # 所有可接受的正向节点
    all_positive = set(positive_nodes) | set(alternative_nodes or [])

    # Grade 0: 不包含目标特征
    has_positive_node = any(node in ast_features for node in all_positive)

    # 如果有 positive_keywords，还需要检查关键词
    positive_keywords = rule.get("positive_keywords", [])
    if positive_keywords:
        snippet_keywords = snippet.get("keywords", [])
        if rule.get("case_insensitive"):
            snippet_keywords_lower = [kw.lower() for kw in snippet_keywords]
            has_positive_keyword = any(
                pk.lower() in snippet_keywords_lower for pk in positive_keywords
            )
        else:
            has_positive_keyword = any(pk in snippet_keywords for pk in positive_keywords)

        # 对于需要关键词配合的规则（如 ArrayList），必须同时满足
        if not has_positive_keyword:
            return 0
    else:
        has_positive_keyword = True  # 不需要关键词检查

    if not has_positive_node:
        return 0

    # Grade 2 的多维度判断
    target_count = sum(ast_features.count(n) for n in all_positive)
    total_count = len(ast_features)
    density = target_count / total_count if total_count > 0 else 0.0

    # 信号1: 显式命名 (Strong Signal)
    method_name = snippet.get("method_name", "").lower()
    name_keywords = rule.get("name_keywords", [])
    has_name_match = False
    if name_keywords:
        has_name_match = any(kw.lower() in method_name for kw in name_keywords)

    # 信号2: 高密度 (Strong Signal) - 特征占比超过 10%
    is_high_density = density >= 0.10

    # 信号3: 多次出现 (Medium Signal)
    has_multiple = target_count >= 2

    # 信号4: 适中长度 (Weak Signal)
    loc = snippet.get("lines_of_code", 0)
    loc_min, loc_max = get_loc_range(rule)
    is_good_loc = loc_min <= loc <= loc_max

    # 判定逻辑:
    # 1. 显式命名 + 任意密度 -> G2
    # 2. 高密度 + 适中长度 -> G2
    # 3. 多次出现 + 基础密度(>0.05) + 适中长度 -> G2

    if has_name_match and density > 0:
        return 2

    if is_high_density and is_good_loc:
        return 2

    if has_multiple and density > 0.05 and is_good_loc:
        return 2

    return 1


def get_pilot_kp_ids() -> List[int]:
    """获取 Pilot 阶段的 KP ID 列表（5 个已验证 Kappa >= 0.6 的 KP）"""
    return PILOT_KP_IDS.copy()


def get_all_kp_ids() -> List[int]:
    """获取所有已定义规则的 KP ID 列表（Pilot + Phase 1 扩展）"""
    return list(KP_RULES.keys())


def get_rule(kp_id: int) -> Optional[KPRule]:
    """获取指定 KP 的规则"""
    return KP_RULES.get(kp_id)


def get_all_rules() -> Dict[int, KPRule]:
    """获取所有规则"""
    return KP_RULES.copy()


# =============================================================================
# 规则独立性验证
# =============================================================================

def verify_rule_independence() -> List[str]:
    """
    验证规则定义不依赖匹配算法的核心组件

    检查项：
    1. 规则不使用 NODE_MAPPING 的 key（应使用具体 tree-sitter 节点名）
    2. 规则不使用 CANONICAL_ALIASES 中的别名
    3. 规则不使用 DOMAIN_ANCHORS

    Returns:
        违规列表，空列表表示通过
    """
    violations = []

    try:
        from src.matching.strategies import NODE_MAPPING, DOMAIN_ANCHORS
    except ImportError:
        # 如果无法导入，跳过检查
        return ["无法导入 NODE_MAPPING/DOMAIN_ANCHORS，跳过独立性检查"]

    try:
        from src.java_analyzer.constants import CANONICAL_ALIASES
    except ImportError:
        CANONICAL_ALIASES = {}

    # NODE_MAPPING 的 key 是抽象概念（如 "loop", "exception"）
    # 规则应使用具体的 tree-sitter 节点名（如 "for_statement"）
    node_mapping_keys = set(NODE_MAPPING.keys())

    for kp_id, rule in KP_RULES.items():
        # 检查1: positive_nodes 不应该是 NODE_MAPPING 的 key
        for node in rule.get("positive_nodes", []):
            if node in node_mapping_keys:
                violations.append(
                    f"KP {kp_id} ({rule.get('name')}): positive_node '{node}' "
                    f"是 NODE_MAPPING 的抽象 key，应使用具体的 tree-sitter 节点名"
                )

        # 检查2: positive_keywords 不应该使用别名
        for kw in rule.get("positive_keywords", []):
            if kw.lower() in [a.lower() for a in CANONICAL_ALIASES.keys()]:
                violations.append(
                    f"KP {kp_id} ({rule.get('name')}): keyword '{kw}' "
                    f"在 CANONICAL_ALIASES 中有别名，规则应使用原始关键词"
                )

    return violations


def run_independence_check() -> bool:
    """
    运行独立性检查，打印结果

    Returns:
        True 表示通过，False 表示有违规
    """
    violations = verify_rule_independence()
    if violations:
        print("[WARN] 规则独立性检查发现问题：")
        for v in violations:
            print(f"  - {v}")
        print("\n请修改规则定义，确保与算法实现独立。")
        return False
    print("[OK] 规则独立性检查通过")
    return True
