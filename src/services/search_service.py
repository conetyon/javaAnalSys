# src/services/search_service.py
from src.db_manager import KnowledgePointManager, CodeLibraryManager
from src.matching.utils import safe_read_json, tokenize_to_set
from src.matching.strategies import (
    extract_required_nodes,
    calculate_ast_score,
    calculate_keyword_score,
    calculate_difficulty_score
)


class SearchService:
    def __init__(self, db_name):
        self.kp_mgr = KnowledgePointManager(db_name)
        self.code_mgr = CodeLibraryManager(db_name)

    def search(self, kp_id, target_difficulty=0.5, top_k=5):
        # 1. 获取知识点
        kp = self.kp_mgr.get_by_id(kp_id)
        if not kp:
            print(f"Knowledge point {kp_id} not found.")
            return []

        # 2. 准备匹配条件
        ast_tpl = safe_read_json(kp.get('ast_template'), {})
        kp_kws = tokenize_to_set(safe_read_json(kp.get('keywords'), []))
        kp_name = kp.get('name')
        need_nodes = extract_required_nodes(ast_tpl)

        # 3. 获取并打分
        snippets = self.code_mgr.get_all_snippets()
        results = []

        for snip in snippets:
            # 数据预处理
            snip_ast = tokenize_to_set(safe_read_json(snip.get('ast_features'), []))
            snip_kws = tokenize_to_set(safe_read_json(snip.get('keywords'), []))
            snip_diff = snip.get('complexity_score')

            # 核心打分 (调用 pure functions)
            ast_s, ast_cov = calculate_ast_score(need_nodes, snip_ast)
            kw_s, kw_hit, kw_total = calculate_keyword_score(kp_kws, snip_kws, kp_name)
            diff_s = calculate_difficulty_score(snip_diff, target_difficulty)

            # 综合算分
            final = 0.5 * ast_s + 0.3 * kw_s + 0.2 * diff_s

            results.append({
                "id": snip.get('id'),
                "content": snip.get('content', ''),
                "score": round(final, 3),
                "details": f"ast:{ast_s:.2f}, kw:{kw_s:.2f}, diff:{diff_s:.2f}"
            })

        # 4. 排序与截取
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
