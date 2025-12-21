# matcher.py
import json
from db_manager import KnowledgePointManager, CodeLibraryManager


class Matcher:
    def __init__(self, db_name=None):
        """
        初始化匹配器。
        它不直接操作 SQL，而是通过 Managers 获取数据。
        """
        # 初始化 Managers
        self.kp_mgr = KnowledgePointManager(db_name)
        self.code_mgr = CodeLibraryManager(db_name)

    def search(self, knowledge_point_id, target_difficulty=0.5):
        # 1. 通过 Manager 获取知识点
        kp = self.kp_mgr.get_by_id(knowledge_point_id)

        if not kp:
            print(f"Knowledge point {knowledge_point_id} not found.")
            return []

        # 解析知识点数据
        kp_ast_tpl = json.loads(kp['ast_template'])
        kp_keywords = set(json.loads(kp['keywords']))
        required_nodes = set(kp_ast_tpl.get("required_nodes", []))

        # 2. 通过 Manager 获取所有代码片段
        snippets = self.code_mgr.get_all_snippets()

        results = []

        # --- 算法核心部分 (保持不变) ---
        for snip in snippets:
            # 数据清洗：处理可能的类型差异
            ast_feat_raw = snip['ast_features']
            keywords_raw = snip['keywords']

            # 兼容 bytes 类型 (blob) 或 str
            if isinstance(ast_feat_raw, bytes): ast_feat_raw = ast_feat_raw.decode('utf-8')
            if isinstance(keywords_raw, bytes): keywords_raw = keywords_raw.decode('utf-8')

            snip_ast_features = set(json.loads(ast_feat_raw))
            snip_keywords = set(json.loads(keywords_raw))
            snip_diff = snip['complexity_score']

            # A. AST 结构匹配得分
            if required_nodes.issubset(snip_ast_features):
                ast_score = 1.0
            else:
                intersection = required_nodes.intersection(snip_ast_features)
                ast_score = len(intersection) / len(required_nodes) if required_nodes else 0

            if ast_score < 0.5:
                continue

            # B. 关键字匹配得分
            if len(kp_keywords) > 0:
                common = snip_keywords.intersection(kp_keywords)
                kw_score = len(common) / len(kp_keywords.union(snip_keywords))
            else:
                kw_score = 0.5

            # C. 难度匹配得分
            diff_score = 1.0 - abs(snip_diff - target_difficulty)

            # 加权求和
            final_score = (0.5 * ast_score) + (0.3 * kw_score) + (0.2 * diff_score)

            if final_score > 0.4:
                results.append({
                    "id": snip['id'],
                    "content": snip['content'],
                    "score": round(final_score, 3),
                    "details": f"AST:{ast_score:.1f}, KW:{kw_score:.1f}, Diff:{diff_score:.1f}"
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]
