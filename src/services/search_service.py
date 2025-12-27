# src/services/search_service.py
from src.db_manager import KnowledgePointManager, CodeLibraryManager
from src.matching.utils import safe_read_json
from src.matching.strategies import (
    extract_required_nodes,
    calculate_match_score,
    WEIGHT_DEFAULTS,
)


class SearchService:
    def __init__(self, db_name):
        self.kp_mgr = KnowledgePointManager(db_name)
        self.code_mgr = CodeLibraryManager(db_name)

    def search(
        self,
        kp_id,
        target_difficulty=0.5,
        top_k=5,
        ast_min_ratio=0.4,
        keyword_min_score=0.4,
        difficulty_mode="relaxed",
    ):
        """
        使用新策略进行匹配与过滤：
          - 统一权重：AST 0.6 / 关键词 0.3 / 难度 0.1
          - 启用过滤：AST 覆盖率、关键词最低得分、难度模式
        """
        # 1. 获取知识点
        kp_row = self.kp_mgr.get_by_id(kp_id)
        if not kp_row:
            print(f"Knowledge point {kp_id} not found.")
            return []

        # 2. 解析知识点配置
        kp_cfg = self.kp_mgr.parse_kp_config(kp_row)
        need_nodes = extract_required_nodes(kp_cfg.get("ast"))
        if not need_nodes and kp_cfg.get("required_nodes"):
            need_nodes = set(kp_cfg["required_nodes"])

        # 3. 获取代码片段并按策略打分
        snippets = self.code_mgr.get_all_snippets()
        results = []

        for snip in snippets:
            # 兼容 JSON/text/list
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            kws_raw = snip.get("keywords")
            snip_keywords = kws_raw if kws_raw is not None else []

            snip_difficulty = snip.get("complexity_score")

            r = calculate_match_score(
                kp_ast_nodes=need_nodes,
                snip_ast_nodes=snip_ast_nodes,
                kp_keywords=kp_cfg.get("keywords", []),
                snip_keywords=snip_keywords,
                kp_name=kp_cfg.get("name"),
                snip_difficulty=snip_difficulty,
                target_difficulty=target_difficulty if target_difficulty is not None else kp_cfg.get("target_difficulty"),
                difficulty_mode=difficulty_mode,
                weights=WEIGHT_DEFAULTS,  # 如需强制 0.6/0.3/0.1，可改成 {'ast':0.6,'keyword':0.3,'difficulty':0.1}
                ast_min_ratio=ast_min_ratio,
                keyword_min_score=keyword_min_score,
            )

            # 过滤不合格候选
            if r.get("filtered"):
                continue

            results.append({
                "id": snip.get("id"),
                "content": snip.get("content", ""),
                "score": round(r["final_score"], 3),

                # 结构化指标字段（用于非 MD 渲染或程序处理）
                "ast_ratio": round(r["ast_score"], 2),
                "ast_coverage": round(r["ast_coverage"], 2),
                "keyword_score": round(r["keyword_score"], 2),
                "keyword_hit": r.get("keyword_hit", 0),
                "keyword_total": r.get("keyword_total", 0),
                "difficulty": round(r["difficulty_score"], 2),

                # Markdown 友好的详情文本（用于直接渲染）
                "details_md": (
                    f"- AST: {r['ast_score']:.2f} (coverage: {r['ast_coverage']:.2f})\n"
                    f"- KW: {r['keyword_score']:.2f} ({r.get('keyword_hit', 0)}/{r.get('keyword_total', 0)})\n"
                    f"- Diff: {r['difficulty_score']:.2f}"
                ),

                # 兼容旧的纯文本 details（如已有打印逻辑在用）
                "details": (
                    f"ast:{r['ast_score']:.2f} (cov:{r['ast_coverage']:.2f}), "
                    f"kw:{r['keyword_score']:.2f} ({r.get('keyword_hit', 0)}/{r.get('keyword_total', 0)}), "
                    f"diff:{r['difficulty_score']:.2f}"
                ),

                # 源文件路径（如果有）
                "file_path": snip.get("file_path") or snip.get("source_path"),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max(1, int(top_k))]
