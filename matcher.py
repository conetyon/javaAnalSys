import sqlite3
import json


class Matcher:
    def __init__(self, db_path):
        self.db_path = db_path

    def search(self, knowledge_point_id, target_difficulty=0.5):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 1. 获取知识点详情
        kp = c.execute("SELECT * FROM knowledge_points WHERE id=?", (knowledge_point_id,)).fetchone()
        if not kp:
            print("Knowledge point not found.")
            return []

        kp_ast_tpl = json.loads(kp['ast_template'])
        kp_keywords = set(json.loads(kp['keywords']))
        required_nodes = set(kp_ast_tpl.get("required_nodes", []))

        # 2. 获取所有代码片段 (实际生产中会先基于关键字粗筛，这里全量遍历)
        snippets = c.execute("SELECT * FROM code_snippets").fetchall()

        results = []

        for snip in snippets:
            snip_ast_features = set(json.loads(snip['ast_features']))
            snip_keywords = set(json.loads(snip['keywords']))
            snip_diff = snip['complexity_score']

            # --- 算法核心部分 ---

            # A. AST 结构匹配得分 (权重 0.5)
            # 检查 snippet 是否包含知识点要求的所有节点 (如 try_statement AND catch_clause)
            if required_nodes.issubset(snip_ast_features):
                ast_score = 1.0
            else:
                # 简单计算重合度
                intersection = required_nodes.intersection(snip_ast_features)
                ast_score = len(intersection) / len(required_nodes) if required_nodes else 0

            # 如果关键结构完全不对，直接得0分或过滤（这里给个软惩罚）
            if ast_score < 0.5:
                match_score = 0
                continue

            # B. 关键字匹配得分 (权重 0.3)
            # Jaccard 相似系数
            if len(kp_keywords) > 0:
                common = snip_keywords.intersection(kp_keywords)
                kw_score = len(common) / len(kp_keywords.union(snip_keywords))
            else:
                kw_score = 0.5

            # C. 难度匹配得分 (权重 0.2)
            # 距离越近分越高
            diff_score = 1.0 - abs(snip_diff - target_difficulty)

            # 加权求和
            final_score = (0.5 * ast_score) + (0.3 * kw_score) + (0.2 * diff_score)

            if final_score > 0.4:  # 阈值过滤
                results.append({
                    "id": snip['id'],
                    "content": snip['content'],
                    "score": round(final_score, 3),
                    "details": f"AST:{ast_score:.1f}, KW:{kw_score:.1f}, Diff:{diff_score:.1f}"
                })

        # 排序返回Top-K
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]

