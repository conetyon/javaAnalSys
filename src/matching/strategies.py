# src/matching/strategies.py
from .utils import tokenize_to_set

# 节点映射表
NODE_MAPPING = {
    "primitivetype": {"integral_type", "floating_point_type", "boolean_type", "int", "double"},
    "ifstatement": {"if_statement"},
    "forstatement": {"for_statement"},
    "whilestatement": {"while_statement"},
    "trycatch": {"try_statement", "catch_clause"},
    "declare<list>": {"type_identifier", "object_creation_expression", "new", "arraylist", "list"},
}

def extract_required_nodes(ast_tpl):
    if not isinstance(ast_tpl, dict):
        return set()
    # 1. 优先检查显式列表
    nodes = ast_tpl.get("required_nodes") or ast_tpl.get("template_nodes")
    if isinstance(nodes, list) and nodes:
        return tokenize_to_set(nodes)
    # 2. 检查模板名称映射
    name = (ast_tpl.get("template") or "").strip().lower()
    details = ast_tpl.get("details", [])
    base = NODE_MAPPING.get(name, set())
    return set(base).union(tokenize_to_set(details))

def calculate_ast_score(need_nodes, have_nodes):
    if not need_nodes:
        return 0.6, 0.0
    if not isinstance(have_nodes, set):
        have_nodes = set(have_nodes)
    inter = need_nodes.intersection(have_nodes)
    ratio = len(inter) / len(need_nodes)
    score = 0.2 + 0.8 * ratio
    return score, ratio

def calculate_keyword_score(kp_kws, snip_kws, kp_name=None):
    name_set = tokenize_to_set([kp_name]) if kp_name else set()
    base = set(kp_kws).union(name_set)
    if not base:
        return 0.6, 0, 0
    inter = base.intersection(snip_kws)
    score = (len(inter) + 0.5) / (len(base) + 0.5)
    return score, len(inter), len(base)

def calculate_difficulty_score(snip_diff, target):
    if snip_diff is None: snip_diff = 0.0
    if target is None: target = 0.5
    val = 1.0 - abs(snip_diff - target)
    return max(0.0, min(1.0, val))
