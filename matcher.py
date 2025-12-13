import pymysql
import json
# 假设 DB_CONFIG 在同一个包中可访问，或者需要在这里重新定义
# 这里为了代码独立性，我们重新引用配置，实际项目中建议导入
from db_manager.database import DB_CONFIG


class Matcher:
    def __init__(self, db_name=None):
        # db_name 参数保留以兼容接口，但实际连接使用 DB_CONFIG
        pass

    def search(self, knowledge_point_id, target_difficulty=0.5):
        # 使用 DictCursor 以便像字典一样访问结果 (row['field'])
        conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        c = conn.cursor()

        # 1. 获取知识点详情 (使用 %s)
        c.execute("SELECT * FROM knowledge_points WHERE id=%s", (knowledge_point_id,))
        kp = c.fetchone()

        if not kp:
            print("Knowledge point not found.")
            conn.close()
            return []

        kp_ast_tpl = json.loads(kp['ast_template'])
        kp_keywords = set(json.loads(kp['keywords']))
        required_nodes = set(kp_ast_tpl.get("required_nodes", []))

        # 2. 获取所有代码片段
        c.execute("SELECT * FROM code_snippets")
        snippets = c.fetchall()

        conn.close()

        results = []

        for snip in snippets:
            snip_ast_features = set(json.loads(snip['ast_features']))
            snip_keywords = set(json.loads(snip['keywords']))
            snip_diff = snip['complexity_score']

            # --- 算法核心部分 (未变动) ---

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
