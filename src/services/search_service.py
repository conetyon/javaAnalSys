# src/services/search_service.py
# 说明：
# - 引入关键词归一化（CANONICAL_ALIASES）：对 KP 与片段关键词统一小写与别名映射，缓解 println vs System.out.println 等不一致
# - 尝试用“候选检索”避免全库遍历：若 CodeLibraryManager 实现 find_snippet_candidates，则优先使用；否则回退到 get_all_snippets
# - 其它逻辑兼容既有 calculate_match_score 与阈值过滤

from typing import List, Dict, Any

from src.db_manager import KnowledgePointManager, CodeLibraryManager
from src.matching.utils import safe_read_json
from lib.globals import core_logger as log
from src.matching.strategies import (
    extract_required_nodes,
    calculate_match_score,
    WEIGHT_DEFAULTS,
)

# 优先从 java_analyzer.constants 导入别名表；若不可用，使用内置最小表
try:
    from src.java_analyzer.constants import CANONICAL_ALIASES as _CANONICAL_ALIASES
except Exception:
    _CANONICAL_ALIASES = {
        "system.out.println": "println",
        "system.err.println": "println",
        "arrays.aslist": "aslist",
        "collections.sort": "sort",
        "logger.info": "log.info",
        "logger.error": "log.error",
        "logger.debug": "log.debug",
        "printstacktrace": "printstacktrace",
    }


def normalize_token(tok: str) -> str:
    if not tok:
        return ""
    low = tok.strip().lower()
    return _CANONICAL_ALIASES.get(low, low)


def normalize_keywords_list(xs) -> List[str]:
    if xs is None:
        return []
    if isinstance(xs, (bytes, bytearray)):
        try:
            xs = xs.decode("utf-8", errors="ignore")
        except Exception:
            xs = str(xs)
    if isinstance(xs, str):
        xs_parsed = safe_read_json(xs, default=None)
        xs = xs_parsed if isinstance(xs_parsed, list) else [xs]
    # 去重保持稳定顺序（小集合场景）
    seen = set()
    out = []
    for x in xs:
        if x is None:
            continue
        nx = normalize_token(str(x))
        if nx and nx not in seen:
            seen.add(nx)
            out.append(nx)
    return out


class SearchService:
    def __init__(self, db_name: str, *, candidate_limit: int = 2000):
        self.kp_mgr = KnowledgePointManager(db_name)
        self.code_mgr = CodeLibraryManager(db_name)
        self.candidate_limit = int(candidate_limit)
        log.info("[SearchService] 初始化完成, db=%s, candidate_limit=%d", db_name, self.candidate_limit)

    def search(
        self,
        kp_id: int,
        target_difficulty: float = 0.5,
        top_k: int = 5,
        ast_min_ratio: float = 0.1,  # 生产环境默认阈值，过滤低质量结果
        keyword_min_score: float = 0.1,  # 保证推荐质量，同时保持合理召回率
        difficulty_mode: str = "relaxed",
        w_ast: float = None,  # 可选：自定义AST权重（用于消融实验）
        w_keyword: float = None,  # 可选：自定义关键词权重
        w_difficulty: float = None,  # 可选：自定义难度权重
    ) -> List[Dict[str, Any]]:
        """
        使用新策略进行匹配与过滤：
          - 统一权重：默认 WEIGHT_DEFAULTS（可在 strategies 配置中调整）
          - 启用过滤：AST 覆盖率、关键词最低得分、难度模式
          - 关键词归一化：统一大小写与别名
          - 候选检索：若底层支持则避免全库遍历

        阈值说明：
          - ast_min_ratio: AST覆盖率最低阈值，低于此值的候选被过滤
          - keyword_min_score: 关键词得分最低阈值，低于此值的候选被过滤
          - 默认0.1是生产环境推荐值，保证推荐质量
          - 评估实验时可设为0.0以测试最大召回能力
        """
        log.info("[SearchService.search] 开始搜索: kp_id=%d, target_diff=%.2f, top_k=%d, ast_min=%.2f, kw_min=%.2f, diff_mode=%s",
                 kp_id, target_difficulty, top_k, ast_min_ratio, keyword_min_score, difficulty_mode)
        
        # 1. 获取知识点
        kp_row = self.kp_mgr.get_by_id(kp_id)
        if not kp_row:
            log.warning("[SearchService.search] 知识点不存在: kp_id=%d", kp_id)
            return []
        
        log.debug("[SearchService.search] 知识点原始数据: %s", kp_row)

        # 2. 解析知识点配置
        kp_cfg = self.kp_mgr.parse_kp_config(kp_row)
        need_nodes = extract_required_nodes(kp_cfg.get("ast"))
        if not need_nodes and kp_cfg.get("required_nodes"):
            need_nodes = set(kp_cfg["required_nodes"])

        # 归一化知识点关键词
        kp_keywords_norm = normalize_keywords_list(kp_cfg.get("keywords", []))
        
        log.info("[SearchService.search] 知识点配置: name=%s, need_nodes=%s, keywords=%s",
                 kp_cfg.get("name"), need_nodes, kp_keywords_norm)

        # 3. 候选检索（如不可用则回退到全表）
        candidates = self._fetch_candidates(kp_keywords_norm, need_nodes, limit=self.candidate_limit)
        log.info("[SearchService.search] 获取候选片段数量: %d", len(candidates))

        results = []
        filtered_count = 0
        for idx, snip in enumerate(candidates):
            snip_id = snip.get("id", idx)
            
            # AST
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            # 关键词（归一化）
            kws_raw = snip.get("keywords")
            snip_keywords_norm = normalize_keywords_list(kws_raw)

            # 难度（兼容老字段名）
            snip_difficulty = snip.get("complexity_score")
            if snip_difficulty is None:
                snip_difficulty = snip.get("difficulty")
            
            log.debug("[SearchService.search] 处理片段 #%s: ast=%s, kw=%s, diff=%s",
                      snip_id, snip_ast_nodes, snip_keywords_norm, snip_difficulty)

            # 4. 打分（将归一化关键词传入策略）
            # 构建自定义权重（如果提供）
            custom_weights = WEIGHT_DEFAULTS.copy()
            if w_ast is not None:
                custom_weights["ast"] = w_ast
            if w_keyword is not None:
                custom_weights["keyword"] = w_keyword
            if w_difficulty is not None:
                custom_weights["difficulty"] = w_difficulty

            r = calculate_match_score(
                kp_ast_nodes=need_nodes,
                snip_ast_nodes=snip_ast_nodes,
                kp_keywords=kp_keywords_norm,
                snip_keywords=snip_keywords_norm,
                kp_name=kp_cfg.get("name"),
                snip_difficulty=snip_difficulty,
                target_difficulty=target_difficulty if target_difficulty is not None else kp_cfg.get("target_difficulty"),
                difficulty_mode=difficulty_mode,
                weights=custom_weights,
                ast_min_ratio=ast_min_ratio,
                keyword_min_score=keyword_min_score,
            )

            # 过滤不合格候选
            if r.get("filtered"):
                filtered_count += 1
                log.debug("[SearchService.search] 片段 #%s 被过滤", snip_id)
                continue
            
            log.debug("[SearchService.search] 片段 #%s 通过, score=%.3f", snip_id, r["final_score"])

            results.append({
                "id": snip.get("id"),
                "content": snip.get("content", ""),
                "score": round(r["final_score"], 3),

                # 结构化指标
                "ast_ratio": round(r["ast_score"], 2),
                "ast_coverage": round(r["ast_coverage"], 2),
                "keyword_score": round(r["keyword_score"], 2),
                "keyword_hit": r.get("keyword_hit", 0),
                "keyword_total": r.get("keyword_total", 0),
                "difficulty": round(r["difficulty_score"], 2),

                # 详情文本
                "details_md": (
                    f"- AST: {r['ast_score']:.2f} (coverage: {r['ast_coverage']:.2f})\n"
                    f"- KW: {r['keyword_score']:.2f} ({r.get('keyword_hit', 0)}/{r.get('keyword_total', 0)})\n"
                    f"- Diff: {r['difficulty_score']:.2f}"
                ),
                "details": (
                    f"ast:{r['ast_score']:.2f} (cov:{r['ast_coverage']:.2f}), "
                    f"kw:{r['keyword_score']:.2f} ({r.get('keyword_hit', 0)}/{r.get('keyword_total', 0)}), "
                    f"diff:{r['difficulty_score']:.2f}"
                ),

                # 源路径（如有）
                "file_path": snip.get("file_path") or snip.get("source_path"),
            })

        # 稳定排序：主排序按score降序，次要排序按ID升序（确保相同得分时结果稳定）
        results.sort(key=lambda x: (-x["score"], x["id"]))
        final_results = results[:max(1, int(top_k))]
        
        log.info("[SearchService.search] 搜索完成: 候选=%d, 过滤=%d, 通过=%d, 返回=%d",
                 len(candidates), filtered_count, len(results), len(final_results))
        
        if final_results:
            log.info("[SearchService.search] Top结果: %s",
                     [(r["id"], r["score"]) for r in final_results[:3]])
        
        return final_results

    def composite_search(
        self,
        kp_ids: List[int],
        target_difficulty: float = 0.5,
        top_k: int = 5,
        ast_min_ratio: float = 0.1,  # 生产环境默认阈值
        keyword_min_score: float = 0.1,  # 保证推荐质量
        difficulty_mode: str = "relaxed",
        score_aggregation: str = "average"
    ) -> List[Dict[str, Any]]:
        """
        综合知识点匹配：计算代码片段与多个知识点的综合匹配度

        策略：
        1. 获取所有选中知识点的模板和关键词
        2. 获取候选代码片段（合并所有知识点的候选集）
        3. 对每个片段，计算它与每个知识点的匹配分数
        4. 综合得分 = 聚合所有知识点的分数（平均值/最小值/加权和）
        5. 返回综合得分最高的 top-k 片段

        :param kp_ids: 知识点 ID 列表（例如：[10011, 10012, 10034]）
        :param target_difficulty: 目标难度
        :param top_k: 返回结果数量
        :param ast_min_ratio: AST 最低匹配率（放宽，因为要综合多个KP）
        :param keyword_min_score: 关键词最低得分（放宽）
        :param difficulty_mode: 难度模式
        :param score_aggregation: 得分聚合方式 ('average'=平均, 'min'=最小值, 'sum'=求和)
        :return: 匹配结果列表
        """
        log.info("[SearchService.composite_search] 开始综合匹配: kp_ids=%s, agg=%s, top_k=%d",
                 kp_ids, score_aggregation, top_k)

        if not kp_ids:
            log.warning("[SearchService.composite_search] 知识点列表为空")
            return []

        # 1. 获取所有知识点的配置
        kp_configs = []
        all_kp_keywords = set()
        all_kp_nodes = set()

        for kp_id in kp_ids:
            kp_row = self.kp_mgr.get_by_id(kp_id)
            if not kp_row:
                log.warning("[SearchService.composite_search] 知识点不存在: kp_id=%d", kp_id)
                continue

            kp_cfg = self.kp_mgr.parse_kp_config(kp_row)
            need_nodes = extract_required_nodes(kp_cfg.get("ast"))
            if not need_nodes and kp_cfg.get("required_nodes"):
                need_nodes = set(kp_cfg["required_nodes"])

            kp_keywords_norm = normalize_keywords_list(kp_cfg.get("keywords", []))

            kp_configs.append({
                "id": kp_id,
                "name": kp_cfg.get("name"),
                "nodes": need_nodes,
                "keywords": kp_keywords_norm
            })

            all_kp_keywords.update(kp_keywords_norm)
            all_kp_nodes.update(need_nodes)

            log.info("[SearchService.composite_search] KP %d: name=%s, nodes=%s, keywords=%s",
                     kp_id, kp_cfg.get("name"), need_nodes, kp_keywords_norm)

        if not kp_configs:
            log.warning("[SearchService.composite_search] 没有有效的知识点配置")
            return []

        # 2. 获取候选片段（合并所有知识点的候选集）
        candidates = self._fetch_candidates(list(all_kp_keywords), all_kp_nodes, limit=self.candidate_limit)
        log.info("[SearchService.composite_search] 获取候选片段数量: %d", len(candidates))

        # 3. 计算每个片段的综合得分
        results = []
        for idx, snip in enumerate(candidates):
            snip_id = snip.get("id", idx)

            # 解析片段特征
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            snip_keywords_norm = normalize_keywords_list(snip.get("keywords"))
            snip_difficulty = snip.get("complexity_score") or snip.get("difficulty")

            # 计算片段与每个知识点的匹配分数
            kp_scores = []
            kp_details = []

            for kp_cfg in kp_configs:
                r = calculate_match_score(
                    kp_ast_nodes=kp_cfg["nodes"],
                    snip_ast_nodes=snip_ast_nodes,
                    kp_keywords=kp_cfg["keywords"],
                    snip_keywords=snip_keywords_norm,
                    kp_name=kp_cfg["name"],
                    snip_difficulty=snip_difficulty,
                    target_difficulty=target_difficulty,
                    difficulty_mode=difficulty_mode,
                    weights=WEIGHT_DEFAULTS,
                    ast_min_ratio=ast_min_ratio,
                    keyword_min_score=keyword_min_score,
                )

                # 如果被过滤，记录为0分（而不是跳过）
                if r.get("filtered"):
                    kp_scores.append(0.0)
                else:
                    kp_scores.append(r["final_score"])

                kp_details.append({
                    "kp_id": kp_cfg["id"],
                    "kp_name": kp_cfg["name"],
                    "score": round(kp_scores[-1], 3),
                    "ast_ratio": round(r.get("ast_score", 0), 2),
                    "keyword_score": round(r.get("keyword_score", 0), 2),
                })

            # 聚合得分
            if score_aggregation == "average":
                composite_score = sum(kp_scores) / len(kp_scores) if kp_scores else 0
            elif score_aggregation == "min":
                composite_score = min(kp_scores) if kp_scores else 0
            elif score_aggregation == "sum":
                composite_score = sum(kp_scores)
            else:
                composite_score = sum(kp_scores) / len(kp_scores) if kp_scores else 0

            # 过滤：如果综合得分过低，跳过
            if composite_score < 0.1:
                continue

            log.debug("[SearchService.composite_search] 片段 #%s: composite=%.3f, kp_scores=%s",
                      snip_id, composite_score, [round(s, 2) for s in kp_scores])

            results.append({
                "id": snip.get("id"),
                "content": snip.get("content", ""),
                "composite_score": round(composite_score, 3),
                "kp_count": len(kp_configs),
                "kp_details": kp_details,
                "score_aggregation": score_aggregation,
                "file_path": snip.get("file_path") or snip.get("source_path"),
            })

        # 排序并返回 top-k
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        final_results = results[:max(1, int(top_k))]

        log.info("[SearchService.composite_search] 综合匹配完成: 候选=%d, 通过=%d, 返回=%d",
                 len(candidates), len(results), len(final_results))

        if final_results:
            log.info("[SearchService.composite_search] Top结果: %s",
                     [(r["id"], r["composite_score"]) for r in final_results[:3]])

        return final_results

    # ---------------- internal helpers ----------------

    def _fetch_candidates(self, kp_keywords_norm, need_nodes, *, limit: int):
        """
        候选检索优先调用索引方法；不存在则回退到全量。
        约定优先级：
          - CodeLibraryManager.find_snippet_candidates(keywords, ast_nodes, limit) [已实现]
          - CodeLibraryManager.get_all_snippets(limit) [安全回退]
        """
        log.debug("[SearchService._fetch_candidates] 开始检索候选, keywords=%s, nodes=%s, limit=%d",
                  kp_keywords_norm, need_nodes, limit)

        # 优先使用预筛选检索（已实现）
        if hasattr(self.code_mgr, "find_snippet_candidates"):
            try:
                log.debug("[SearchService._fetch_candidates] 使用 find_snippet_candidates 预筛选")
                result = self.code_mgr.find_snippet_candidates(kp_keywords_norm, list(need_nodes or []), limit=limit)
                log.info("[SearchService._fetch_candidates] 预筛选获取 %d 条候选", len(result))
                return result
            except Exception as e:
                log.error("[SearchService._fetch_candidates] find_snippet_candidates 失败: %s，回退到全量检索", e, exc_info=True)

        # 回退：全量检索（带 LIMIT 安全网）
        fallback_limit = min(limit * 2, 5000)  # 最多 5000 条，避免 OOM
        log.warning("[SearchService._fetch_candidates] 回退到全量检索 get_all_snippets (limit=%d)", fallback_limit)
        result = self.code_mgr.get_all_snippets(limit=fallback_limit)
        log.info("[SearchService._fetch_candidates] 全量检索获取 %d 条", len(result))
        return result
