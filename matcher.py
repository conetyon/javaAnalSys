# matcher.py
import json
from db_manager import KnowledgePointManager, CodeLibraryManager


def read_json(raw, default):
    if raw is None:
        return default
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode('utf-8', errors='ignore')
        return json.loads(raw)
    except Exception:
        return default


def to_words(tokens):
    out = set()
    for t in (tokens or []):
        if isinstance(t, str):
            s = t.strip().lower()
            if s:
                out.add(s)
    return out


def make_need_nodes(ast_tpl):
    """
    从知识点模板里抽出需要的AST节点集合（尽量简单）。
    支持：
    - required_nodes / template_nodes
    - template + details 的简单映射
    """
    if not isinstance(ast_tpl, dict):
        return set()

    # 1) 直接给的节点列表
    nodes = ast_tpl.get("required_nodes")
    if not nodes:
        nodes = ast_tpl.get("template_nodes")
    if isinstance(nodes, list) and nodes:
        return to_words(nodes)

    # 2) 名称映射（只做几个常用的）
    name = (ast_tpl.get("template") or "").strip().lower()
    details = ast_tpl.get("details", [])
    details_set = to_words(details)

    mapping = {
        "primitivetype": {"integral_type", "floating_point_type", "boolean_type", "int", "double", "boolean"},
        "ifstatement": {"if_statement"},
        "forstatement": {"for_statement"},
        "whilestatement": {"while_statement"},
        "trycatch": {"try_statement", "catch_clause", "finally_clause"},
        "declare<list>": {"type_identifier", "object_creation_expression", "new", "arraylist", "list"},
        "declare<set>": {"type_identifier", "object_creation_expression", "new", "hashset", "set"},
    }
    base = mapping.get(name, set())
    return set(base).union(details_set)


def score_ast(need_nodes, have_nodes):
    """
    AST 得分：更宽松
    - 没有要求节点：给友好基准分 0.6
    - 有要求：用覆盖率算分，最低 0.2，最高 1.0
    """
    if not need_nodes:
        return 0.6, 0.0
    inter = need_nodes.intersection(have_nodes)
    ratio = len(inter) / len(need_nodes) if need_nodes else 0.0
    score = 0.2 + 0.8 * ratio
    return score, ratio


def score_kw(kp_kws, snip_kws, kp_name=None):
    """
    关键词得分：简单可懂，带平滑，尽量不为0
    - 把知识点名称也当作一个关键词参与（尽量“能匹配一点是一点”）
    - 公式： (交集个数 + 0.5) / (知识点关键词数 + 0.5)
    """
    name_set = to_words([kp_name]) if kp_name else set()
    base = set(kp_kws).union(name_set)

    if not base:
        return 0.6, 0, 0  # 没有关键词要求，给友好基准分

    inter = base.intersection(snip_kws)
    score = (len(inter) + 0.5) / (len(base) + 0.5)  # 平滑，避免0分
    return score, len(inter), len(base)


def score_diff(snip_diff, target):
    """
    难度得分：1 - 差值，限制在[0,1]
    不做硬过滤，只参与加分。
    """
    if snip_diff is None:
        snip_diff = 0.0
    if target is None:
        target = 0.5
    val = 1.0 - abs(snip_diff - target)
    return max(0.0, min(1.0, val))


class Matcher:
    def __init__(self, db_name=None):
        self.kp_mgr = KnowledgePointManager(db_name)
        self.code_mgr = CodeLibraryManager(db_name)

    def search(self, knowledge_point_id, target_difficulty=0.5, top_k=5):
        # 1) 取知识点
        kp = self.kp_mgr.get_by_id(knowledge_point_id)
        if not kp:
            print(f"Knowledge point {knowledge_point_id} not found.")
            return []

        ast_tpl = read_json(kp.get('ast_template'), {})
        kp_kws = to_words(read_json(kp.get('keywords'), []))
        kp_name = kp.get('name') or ""

        need_nodes = make_need_nodes(ast_tpl)

        # 2) 取所有代码片段
        snippets = self.code_mgr.get_all_snippets()

        results = []
        for snip in snippets:
            snip_ast = to_words(read_json(snip.get('ast_features'), []))
            snip_kws = to_words(read_json(snip.get('keywords'), []))
            snip_diff = snip.get('complexity_score') or 0.0

            ast_s, ast_cov = score_ast(need_nodes, snip_ast)
            kw_s, kw_hit, kw_total = score_kw(kp_kws, snip_kws, kp_name=kp_name)
            diff_s = score_diff(snip_diff, target_difficulty)

            # 简单加权，保证易读
            final = 0.5 * ast_s + 0.3 * kw_s + 0.2 * diff_s

            results.append({
                "id": snip.get('id'),
                "content": snip.get('content', ''),
                "score": round(final, 3),
                "details": f"ast:{ast_s:.2f}(cov={ast_cov:.2f}), kw:{kw_s:.2f}({kw_hit}/{kw_total}), diff:{diff_s:.2f}"
            })

        # 基于分数排序
        results.sort(key=lambda x: x['score'], reverse=True)

        # 设一个很宽松的阈值，尽量保留结果
        keep = [r for r in results if r['score'] >= 0.2][:top_k]

        # 兜底：如果不够，就按“难度接近度”补齐
        if len(keep) < top_k:
            already = {r['id'] for r in keep}
            others = []
            for snip in snippets:
                if snip.get('id') in already:
                    continue
                snip_diff = snip.get('complexity_score') or 0.0
                d = score_diff(snip_diff, target_difficulty)
                fallback_score = round(0.2 + 0.8 * d, 3)  # 也给个直观分
                others.append({
                    "id": snip.get('id'),
                    "content": snip.get('content', ''),
                    "score": fallback_score,
                    "details": f"fallback_by_diff:{d:.2f}"
                })
            others.sort(key=lambda x: x['score'], reverse=True)
            need_more = top_k - len(keep)
            keep.extend(others[:need_more])

        return keep
