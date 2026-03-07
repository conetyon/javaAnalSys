# src/services/search_service.py
# 说明：
# - 引入关键词归一化（CANONICAL_ALIASES）：对 KP 与片段关键词统一小写与别名映射，缓解 println vs System.out.println 等不一致
# - 尝试用"候选检索"避免全库遍历：若 CodeLibraryManager 实现 find_snippet_candidates，则优先使用；否则回退到 get_all_snippets
# - 其它逻辑兼容既有 calculate_match_score 与阈值过滤

import re
from typing import List, Dict, Any, Tuple

from src.db_manager import KnowledgePointManager, CodeLibraryManager
from src.matching.utils import safe_read_json
from lib.globals import core_logger as log
from src.matching.strategies import (
    extract_required_nodes,
    calculate_match_score,
    get_weight_defaults,
)
from src.services.highlight_service import get_highlight_service


def _extract_method_info(content: str) -> Tuple[str, int]:
    """
    从代码内容中提取方法名和代码行数

    Args:
        content: 代码片段内容

    Returns:
        (method_name, lines_of_code) 元组
    """
    if not content:
        return "", 0

    # 计算非空行数
    lines = content.split('\n')
    lines_of_code = len([l for l in lines if l.strip()])

    # 提取方法名：查找 method_name( 模式
    method_match = re.search(r'\b(\w+)\s*\([^)]*\)\s*(?:throws|{|$)', content)
    method_name = method_match.group(1) if method_match else ""

    return method_name, lines_of_code


class KnowledgePointNotFoundError(Exception):
    """知识点不存在异常"""
    def __init__(self, kp_id: int):
        self.kp_id = kp_id
        super().__init__(f"Knowledge point not found: {kp_id}")


class NonLeafKnowledgePointError(Exception):
    """非叶子节点不支持匹配异常"""
    def __init__(self, kp_id: int, level: int, name: str = ""):
        self.kp_id = kp_id
        self.level = level
        self.name = name
        super().__init__(f"Knowledge point {kp_id} ('{name}') is not a leaf node (level={level}). Only leaf nodes (level=3) support matching.")

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
        self.highlight_service = get_highlight_service()
        log.info("[SearchService] 初始化完成, db=%s, candidate_limit=%d", db_name, self.candidate_limit)

    def search(
        self,
        kp_id: int,
        target_difficulty: float = 0.5,
        top_k: int = 5,
        ast_min_ratio: float = 0.4,  # 统一默认值：与API Schema一致
        keyword_min_score: float = 0.4,  # 统一默认值：与API Schema一致
        difficulty_mode: str = "relaxed",
        w_ast: float = None,  # 可选：自定义AST权重（用于消融实验）
        w_keyword: float = None,  # 可选：自定义关键词权重
        w_difficulty: float = None,  # 可选：自定义难度权重
        source: str = None,  # 可选：数据来源过滤 ('codesearchnet', 'manual', None=全部)
    ) -> List[Dict[str, Any]]:
        """
        使用新策略进行匹配与过滤：
          - 统一权重：默认 WEIGHT_DEFAULTS（可在 strategies 配置中调整）
          - 启用过滤：AST 覆盖率、关键词最低得分、难度模式
          - 关键词归一化：统一大小写与别名
          - 候选检索：若底层支持则避免全库遍历

        阈值说明：
          - ast_min_ratio: AST覆盖率最低阈值，低于此值的候选被过滤（默认0.4）
          - keyword_min_score: 关键词得分最低阈值，低于此值的候选被过滤（默认0.4）
          - 评估实验时可设为0.0以测试最大召回能力
        """
        log.info("[SearchService.search] 开始搜索: kp_id=%d, target_diff=%.2f, top_k=%d, ast_min=%.2f, kw_min=%.2f, diff_mode=%s, source=%s",
                 kp_id, target_difficulty, top_k, ast_min_ratio, keyword_min_score, difficulty_mode, source or 'all')
        log.info("[SearchService.search] 参数验证 - 接收到的阈值: ast_min_ratio=%.2f, keyword_min_score=%.2f",
                 ast_min_ratio, keyword_min_score)
        
        # 1. 获取知识点
        kp_row = self.kp_mgr.get_by_id(kp_id)
        if not kp_row:
            log.warning("[SearchService.search] 知识点不存在: kp_id=%d", kp_id)
            raise KnowledgePointNotFoundError(kp_id)

        # 校验：只有叶子节点（level=3）才支持匹配
        kp_level = kp_row.get("level")
        if kp_level != 3:
            log.warning("[SearchService.search] 非叶子节点不支持匹配: kp_id=%d, level=%s", kp_id, kp_level)
            raise NonLeafKnowledgePointError(kp_id, kp_level, kp_row.get("name", ""))

        log.debug("[SearchService.search] 知识点原始数据: %s", kp_row)

        # 2. 解析知识点配置
        kp_cfg = self.kp_mgr.parse_kp_config(kp_row)
        need_nodes = extract_required_nodes(kp_cfg.get("ast"))
        if not need_nodes and kp_cfg.get("required_nodes"):
            need_nodes = set(kp_cfg["required_nodes"])

        # 显式必需节点（用于硬性过滤，不使用 NODE_MAPPING 扩展）
        ast_tpl = kp_cfg.get("ast") or {}
        explicit_required_nodes = set()
        if isinstance(ast_tpl, dict):
            explicit_nodes = ast_tpl.get("required_nodes") or ast_tpl.get("template_nodes") or []
            if isinstance(explicit_nodes, list):
                explicit_required_nodes = {str(n).lower() for n in explicit_nodes}

        # 归一化知识点关键词
        kp_keywords_norm = normalize_keywords_list(kp_cfg.get("keywords", []))

        log.info("[SearchService.search] 知识点配置: name=%s, need_nodes=%s, explicit_required=%s, keywords=%s",
                 kp_cfg.get("name"), need_nodes, explicit_required_nodes, kp_keywords_norm)

        # 3. 候选检索（如不可用则回退到全表）
        candidates = self._fetch_candidates(kp_keywords_norm, need_nodes, limit=self.candidate_limit, source=source)
        log.info("[SearchService.search] 获取候选片段数量: %d", len(candidates))

        # 预先构建自定义权重（移到循环外，避免 fallback 时未定义）
        custom_weights = get_weight_defaults()
        if w_ast is not None:
            custom_weights["ast"] = w_ast
        if w_keyword is not None:
            custom_weights["keyword"] = w_keyword
        if w_difficulty is not None:
            custom_weights["difficulty"] = w_difficulty

        results = []
        filtered_count = 0
        for idx, snip in enumerate(candidates):
            snip_id = snip.get("id", idx)

            # === 过滤测试/示例数据（可选）===
            # 在评估模式下，可以通过 file_path 过滤特定数据源
            # 例如：跳过 sample_code.java 等示例文件
            file_path = snip.get("file_path", snip.get("source_path", ""))
            if file_path and "sample_code.java" in file_path:
                log.debug("[SearchService.search] 跳过示例文件片段 #%s (sample_code.java)", snip_id)
                continue

            # AST
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            # === 硬性过滤：必须包含至少一个显式必需 AST 节点 ===
            # 这是结构相关性的最低要求，即使 ast_min_ratio=0.0 也强制执行
            # 使用 explicit_required_nodes（不含 NODE_MAPPING 扩展）
            if explicit_required_nodes:
                snip_ast_set = set(n.lower() if isinstance(n, str) else str(n).lower() for n in snip_ast_nodes)
                has_required_node = bool(explicit_required_nodes & snip_ast_set)
                if not has_required_node:
                    filtered_count += 1
                    log.debug("[SearchService.search] 片段 #%s 不含必需 AST 节点，跳过 (need=%s, has=%s)",
                              snip_id, explicit_required_nodes, snip_ast_set)
                    continue

            # 关键词（归一化）
            kws_raw = snip.get("keywords")
            snip_keywords_norm = normalize_keywords_list(kws_raw)

            # 难度（兼容老字段名）
            snip_difficulty = snip.get("complexity_score")
            if snip_difficulty is None:
                snip_difficulty = snip.get("difficulty")
            
            log.debug("[SearchService.search] 处理片段 #%s: ast=%s, kw=%s, diff=%s",
                      snip_id, snip_ast_nodes, snip_keywords_norm, snip_difficulty)

            # 4. 打分（第一个片段时输出权重配置）
            if idx == 0:
                total_w = custom_weights["ast"] + custom_weights["keyword"] + custom_weights["difficulty"]
                w_ast_pct = custom_weights["ast"] / total_w * 100 if total_w > 0 else 0
                w_kw_pct = custom_weights["keyword"] / total_w * 100 if total_w > 0 else 0
                w_diff_pct = custom_weights["difficulty"] / total_w * 100 if total_w > 0 else 0
                log.info("[SearchService.search] 权重配置: AST=%.0f%%, 关键词=%.0f%%, 难度=%.0f%%",
                         w_ast_pct, w_kw_pct, w_diff_pct)

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

            # 从 content 提取 method_name 和 lines_of_code (数据库无此列)
            snip_content = snip.get("content", "")
            snip_method_name, snip_loc = _extract_method_info(snip_content)

            results.append({
                "id": snip.get("id"),
                "content_hash": snip.get("content_hash"),  # 添加稳定标识符
                "content": snip_content,
                "score": round(r["final_score"], 3),

                # 用于分级评估的原始字段
                "ast_features": snip_ast_nodes,
                "keywords": snip_keywords_norm,
                "method_name": snip_method_name,
                "lines_of_code": snip_loc,

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

        # 为最终结果计算 highlight_ranges（只对top_k结果计算，节省性能）
        kp_ast_for_highlight = kp_cfg.get("ast") or {}
        kp_keywords_for_highlight = kp_cfg.get("keywords", [])
        for res in final_results:
            try:
                highlights = self.highlight_service.compute_highlights(
                    res["content"],
                    kp_ast_for_highlight,
                    kp_keywords_for_highlight
                )
                res["highlight_ranges"] = highlights
            except Exception as e:
                log.warning("[SearchService.search] 计算高亮失败: %s", e)
                res["highlight_ranges"] = []

        log.info("[SearchService.search] 搜索完成: 候选=%d, 过滤=%d, 通过=%d, 返回=%d",
                 len(candidates), filtered_count, len(results), len(final_results))

        # === 兜底逻辑：如果没有结果，降低阈值重试（仅重试一次）===
        if not final_results and candidates and (ast_min_ratio > 0.0 or keyword_min_score > 0.0):
            log.warning("[SearchService.search] 未找到匹配结果，启用兜底逻辑（降低阈值重试）")
            fallback_ast_ratio = max(0.0, ast_min_ratio * 0.5)  # 降低50%
            fallback_kw_score = max(0.0, keyword_min_score * 0.5)  # 降低50%
            log.info("[SearchService.search] 兜底阈值: ast_min=%.2f (原%.2f), kw_min=%.2f (原%.2f)",
                     fallback_ast_ratio, ast_min_ratio, fallback_kw_score, keyword_min_score)

            fallback_results = []
            for idx, snip in enumerate(candidates):
                snip_id = snip.get("id", idx)
                ast_raw = snip.get("ast_features")
                if isinstance(ast_raw, (str, bytes, bytearray)):
                    snip_ast_nodes = safe_read_json(ast_raw, default=[])
                else:
                    snip_ast_nodes = ast_raw or []

                snip_keywords_norm = normalize_keywords_list(snip.get("keywords"))
                snip_difficulty = snip.get("complexity_score") or snip.get("difficulty")

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
                    ast_min_ratio=fallback_ast_ratio,
                    keyword_min_score=fallback_kw_score,
                )

                if not r.get("filtered"):
                    # 从 content 提取 method_name 和 lines_of_code (数据库无此列)
                    fb_content = snip.get("content", "")
                    fb_method_name, fb_loc = _extract_method_info(fb_content)

                    fallback_results.append({
                        "id": snip.get("id"),
                        "content_hash": snip.get("content_hash"),  # 添加稳定标识符
                        "content": fb_content,
                        "score": round(r["final_score"], 3),

                        # 用于分级评估的原始字段
                        "ast_features": snip_ast_nodes,
                        "keywords": snip_keywords_norm,
                        "method_name": fb_method_name,
                        "lines_of_code": fb_loc,

                        "ast_ratio": round(r["ast_score"], 2),
                        "ast_coverage": round(r["ast_coverage"], 2),
                        "keyword_score": round(r["keyword_score"], 2),
                        "keyword_hit": r.get("keyword_hit", 0),
                        "keyword_total": r.get("keyword_total", 0),
                        "difficulty": round(r["difficulty_score"], 2),
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
                        "file_path": snip.get("file_path") or snip.get("source_path"),
                    })

            fallback_results.sort(key=lambda x: (-x["score"], x["id"]))
            final_results = fallback_results[:max(1, int(top_k))]

            # 为兜底结果也计算 highlight_ranges
            for res in final_results:
                try:
                    highlights = self.highlight_service.compute_highlights(
                        res["content"],
                        kp_ast_for_highlight,
                        kp_keywords_for_highlight
                    )
                    res["highlight_ranges"] = highlights
                except Exception as e:
                    log.warning("[SearchService.search] 兜底结果计算高亮失败: %s", e)
                    res["highlight_ranges"] = []

            log.info("[SearchService.search] 兜底结果: 通过=%d, 返回=%d", len(fallback_results), len(final_results))

        if final_results:
            log.info("[SearchService.search] Top结果: %s",
                     [(r["id"], r["score"]) for r in final_results[:3]])
        else:
            log.warning("[SearchService.search] 最终无匹配结果（候选数=%d）", len(candidates))

        return final_results

    def composite_search(
        self,
        kp_ids: List[int],
        target_difficulty: float = 0.5,
        top_k: int = 5,
        ast_min_ratio: float = 0.4,  # 统一默认值：与API Schema一致
        keyword_min_score: float = 0.4,  # 统一默认值：与API Schema一致
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
                raise KnowledgePointNotFoundError(kp_id)

            # 校验：只有叶子节点（level=3）才支持匹配
            kp_level = kp_row.get("level")
            if kp_level != 3:
                log.warning("[SearchService.composite_search] 非叶子节点不支持匹配: kp_id=%d, level=%s", kp_id, kp_level)
                raise NonLeafKnowledgePointError(kp_id, kp_level, kp_row.get("name", ""))

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
            # 防御性检查：正常情况下不会到达这里（空 kp_ids 已在上面处理，无效 kp_id 会抛异常）
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
                    weights=get_weight_defaults(),
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

            # 过滤：综合得分过低，跳过
            if composite_score < 0.1:
                continue

            # 判断是否所有 KP 都有匹配（严格模式条件）
            all_kp_matched = all(s > 0 for s in kp_scores)

            log.debug("[SearchService.composite_search] 片段 #%s: composite=%.3f, kp_scores=%s, all_matched=%s",
                      snip_id, composite_score, [round(s, 2) for s in kp_scores], all_kp_matched)

            results.append({
                "id": snip.get("id"),
                "content": snip.get("content", ""),
                "composite_score": round(composite_score, 3),
                "kp_count": len(kp_configs),
                "kp_details": kp_details,
                "score_aggregation": score_aggregation,
                "file_path": snip.get("file_path") or snip.get("source_path"),
                "_all_kp_matched": all_kp_matched,  # 内部标记，用于分层过滤
            })

        # 分层过滤：优先返回严格匹配结果，无结果时降级到宽松模式
        strict_results = [r for r in results if r.get("_all_kp_matched")]

        if strict_results:
            # 严格模式有结果
            final_pool = strict_results
            fallback_used = False
            log.info("[SearchService.composite_search] 严格模式: %d 个片段与所有 KP 都匹配", len(strict_results))
        else:
            # 降级到宽松模式
            final_pool = results
            fallback_used = True
            log.warning("[SearchService.composite_search] 严格模式无结果，降级到宽松模式（部分 KP 匹配）: %d 个候选", len(results))

        # 清理内部标记
        for r in final_pool:
            r.pop("_all_kp_matched", None)
            if fallback_used:
                r["partial_match"] = True  # 标记为部分匹配

        # 排序并返回 top-k
        final_pool.sort(key=lambda x: x["composite_score"], reverse=True)
        final_results = final_pool[:max(1, int(top_k))]

        log.info("[SearchService.composite_search] 综合匹配完成: 候选=%d, 严格=%d, 宽松=%d, 返回=%d",
                 len(candidates), len(strict_results), len(results), len(final_results))

        # 为最终结果计算 highlight_ranges（使用所有 KP 的模板）
        if kp_configs:
            # 收集所有 KP 的高亮配置
            all_kp_highlight_configs = []
            for kp_cfg in kp_configs:
                kp_row = self.kp_mgr.get_by_id(kp_cfg["id"])
                if kp_row:
                    parsed_cfg = self.kp_mgr.parse_kp_config(kp_row)
                    all_kp_highlight_configs.append((
                        parsed_cfg.get("ast") or {},
                        parsed_cfg.get("keywords", []),
                        kp_cfg["name"]
                    ))

            for res in final_results:
                try:
                    highlights = self.highlight_service.compute_highlights_multi(
                        res["content"],
                        all_kp_highlight_configs
                    )
                    res["highlight_ranges"] = highlights
                except Exception as e:
                    log.warning("[SearchService.composite_search] 计算高亮失败: %s", e)
                    res["highlight_ranges"] = []

        if final_results:
            log.info("[SearchService.composite_search] Top结果: %s",
                     [(r["id"], r["composite_score"]) for r in final_results[:3]])

        return final_results

    # ---------------- internal helpers ----------------

    def _fetch_candidates(self, kp_keywords_norm, need_nodes, *, limit: int, source: str = None):
        """
        候选检索优先调用索引方法；不存在则回退到全量。
        约定优先级：
          - CodeLibraryManager.find_snippet_candidates(keywords, ast_nodes, limit, source) [已实现]
          - CodeLibraryManager.get_all_snippets(limit, source) [安全回退]
        """
        log.debug("[SearchService._fetch_candidates] 开始检索候选, keywords=%s, nodes=%s, limit=%d, source=%s",
                  kp_keywords_norm, need_nodes, limit, source or 'all')

        # 优先使用预筛选检索（已实现）
        if hasattr(self.code_mgr, "find_snippet_candidates"):
            try:
                log.debug("[SearchService._fetch_candidates] 使用 find_snippet_candidates 预筛选")
                result = self.code_mgr.find_snippet_candidates(kp_keywords_norm, list(need_nodes or []), limit=limit, source=source)
                log.info("[SearchService._fetch_candidates] 预筛选获取 %d 条候选 (source=%s)", len(result), source or 'all')
                return result
            except Exception as e:
                log.error("[SearchService._fetch_candidates] find_snippet_candidates 失败: %s，回退到全量检索", e, exc_info=True)

        # 回退：全量检索（带 LIMIT 安全网）
        fallback_limit = min(limit * 2, 5000)  # 最多 5000 条，避免 OOM
        log.warning("[SearchService._fetch_candidates] 回退到全量检索 get_all_snippets (limit=%d, source=%s)", fallback_limit, source or 'all')
        result = self.code_mgr.get_all_snippets(limit=fallback_limit, source=source)
        log.info("[SearchService._fetch_candidates] 全量检索获取 %d 条", len(result))
        return result

    # ---------------- 矩阵匹配模式 ----------------

    # 默认难度分级边界
    DEFAULT_DIFFICULTY_LEVELS = [
        {"name": "easy", "min_val": 0.0, "max_val": 0.33},
        {"name": "medium", "min_val": 0.33, "max_val": 0.66},
        {"name": "hard", "min_val": 0.66, "max_val": 1.01},  # 1.01 确保 1.0 被包含
    ]

    def _get_difficulty_bucket(self, difficulty: float) -> str:
        """根据难度值返回对应的难度级别名称"""
        for level in self.DEFAULT_DIFFICULTY_LEVELS:
            if level["min_val"] <= difficulty < level["max_val"]:
                return level["name"]
        return "hard"  # 默认归入 hard

    def _get_matrix_weights(self) -> dict:
        """获取矩阵模式的归一化权重（移除难度权重）"""
        # 基于生产配置 0.2/0.7 归一化
        # 0.2 / (0.2 + 0.7) = 0.222...
        # 0.7 / (0.2 + 0.7) = 0.778...
        return {
            "ast": 0.22,
            "keyword": 0.78,
            "difficulty": 0.0
        }

    def matrix_search(
        self,
        kp_id: int,
        per_level: int = 5,
        ast_min_ratio: float = 0.4,
        keyword_min_score: float = 0.4,
        source: str = None,
    ) -> Dict[str, Any]:
        """
        矩阵匹配：按难度分级返回匹配结果

        与 search() 的区别：
        1. 难度作为分类维度（行标签），不参与打分
        2. 使用归一化权重：w_ast=0.22, w_keyword=0.78, w_difficulty=0.0
        3. 返回格式为矩阵：{level_name: [snippets]}

        :param kp_id: 知识点 ID
        :param per_level: 每个难度级别返回的片段数量
        :param ast_min_ratio: AST 最低阈值
        :param keyword_min_score: 关键词最低得分
        :param source: 数据来源过滤
        :return: 矩阵结构结果
        """
        log.info("[SearchService.matrix_search] 开始矩阵搜索: kp_id=%d, per_level=%d",
                 kp_id, per_level)

        # 1. 获取知识点
        kp_row = self.kp_mgr.get_by_id(kp_id)
        if not kp_row:
            log.warning("[SearchService.matrix_search] 知识点不存在: kp_id=%d", kp_id)
            raise KnowledgePointNotFoundError(kp_id)

        kp_level = kp_row.get("level")
        if kp_level != 3:
            raise NonLeafKnowledgePointError(kp_id, kp_level, kp_row.get("name", ""))

        # 2. 解析知识点配置
        kp_cfg = self.kp_mgr.parse_kp_config(kp_row)
        need_nodes = extract_required_nodes(kp_cfg.get("ast"))
        if not need_nodes and kp_cfg.get("required_nodes"):
            need_nodes = set(kp_cfg["required_nodes"])

        kp_keywords_norm = normalize_keywords_list(kp_cfg.get("keywords", []))

        # 3. 获取候选片段
        candidates = self._fetch_candidates(kp_keywords_norm, need_nodes, limit=self.candidate_limit, source=source)
        log.info("[SearchService.matrix_search] 获取候选片段数量: %d", len(candidates))

        # 4. 使用矩阵模式权重打分
        matrix_weights = self._get_matrix_weights()
        log.info("[SearchService.matrix_search] 矩阵模式权重: AST=%.0f%%, 关键词=%.0f%%, 难度=%.0f%%",
                 matrix_weights["ast"]*100, matrix_weights["keyword"]*100, matrix_weights["difficulty"]*100)

        # 按难度分桶
        buckets = {level["name"]: [] for level in self.DEFAULT_DIFFICULTY_LEVELS}

        for snip in candidates:
            snip_id = snip.get("id")

            # 解析特征
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            snip_keywords_norm = normalize_keywords_list(snip.get("keywords"))
            snip_difficulty = snip.get("complexity_score") or snip.get("difficulty") or 0.5

            # 打分（不含难度权重）
            r = calculate_match_score(
                kp_ast_nodes=need_nodes,
                snip_ast_nodes=snip_ast_nodes,
                kp_keywords=kp_keywords_norm,
                snip_keywords=snip_keywords_norm,
                kp_name=kp_cfg.get("name"),
                snip_difficulty=snip_difficulty,
                target_difficulty=0.5,  # 矩阵模式下不使用目标难度
                difficulty_mode="relaxed",
                weights=matrix_weights,
                ast_min_ratio=ast_min_ratio,
                keyword_min_score=keyword_min_score,
            )

            if r.get("filtered"):
                continue

            # 确定难度桶
            bucket_name = self._get_difficulty_bucket(snip_difficulty)

            # 从 content 提取 method_name 和 lines_of_code
            snip_content = snip.get("content", "")
            snip_method_name, snip_loc = _extract_method_info(snip_content)

            buckets[bucket_name].append({
                "id": snip.get("id"),
                "content_hash": snip.get("content_hash"),
                "content": snip_content,
                "score": round(r["final_score"], 3),
                "ast_ratio": round(r["ast_score"], 2),
                "keyword_score": round(r["keyword_score"], 2),
                "difficulty": round(snip_difficulty, 2),
                "method_name": snip_method_name,
                "lines_of_code": snip_loc,
                "file_path": snip.get("file_path") or snip.get("source_path"),
            })

        # 5. 每个桶内按得分排序并截取
        matrix = {}
        total = 0
        for level_name, items in buckets.items():
            # 按得分降序，ID 升序（稳定排序）
            items.sort(key=lambda x: (-x["score"], x["id"]))
            matrix[level_name] = items[:per_level]
            total += len(matrix[level_name])

        levels = [level["name"] for level in self.DEFAULT_DIFFICULTY_LEVELS]
        shape = [len(levels), per_level]

        # 6. 兜底逻辑：如果结果为空，降低阈值重试
        if total == 0 and candidates and (ast_min_ratio > 0.0 or keyword_min_score > 0.0):
            log.warning("[SearchService.matrix_search] 矩阵结果为空，启用兜底逻辑（降低阈值重试）")
            fallback_ast_ratio = max(0.0, ast_min_ratio * 0.5)
            fallback_kw_score = max(0.0, keyword_min_score * 0.5)

            fallback_buckets = {level["name"]: [] for level in self.DEFAULT_DIFFICULTY_LEVELS}

            for snip in candidates:
                ast_raw = snip.get("ast_features")
                if isinstance(ast_raw, (str, bytes, bytearray)):
                    snip_ast_nodes = safe_read_json(ast_raw, default=[])
                else:
                    snip_ast_nodes = ast_raw or []

                snip_keywords_norm = normalize_keywords_list(snip.get("keywords"))
                snip_difficulty = snip.get("complexity_score") or snip.get("difficulty") or 0.5

                r = calculate_match_score(
                    kp_ast_nodes=need_nodes,
                    snip_ast_nodes=snip_ast_nodes,
                    kp_keywords=kp_keywords_norm,
                    snip_keywords=snip_keywords_norm,
                    kp_name=kp_cfg.get("name"),
                    snip_difficulty=snip_difficulty,
                    target_difficulty=0.5,
                    difficulty_mode="relaxed",
                    weights=matrix_weights,
                    ast_min_ratio=fallback_ast_ratio,
                    keyword_min_score=fallback_kw_score,
                )

                if r.get("filtered"):
                    continue

                bucket_name = self._get_difficulty_bucket(snip_difficulty)
                snip_content = snip.get("content", "")
                snip_method_name, snip_loc = _extract_method_info(snip_content)

                fallback_buckets[bucket_name].append({
                    "id": snip.get("id"),
                    "content_hash": snip.get("content_hash"),
                    "content": snip_content,
                    "score": round(r["final_score"], 3),
                    "ast_ratio": round(r["ast_score"], 2),
                    "keyword_score": round(r["keyword_score"], 2),
                    "difficulty": round(snip_difficulty, 2),
                    "method_name": snip_method_name,
                    "lines_of_code": snip_loc,
                    "file_path": snip.get("file_path") or snip.get("source_path"),
                    "fallback": True,  # 标记为兜底结果
                })

            # 重新构建矩阵
            matrix = {}
            total = 0
            for level_name, items in fallback_buckets.items():
                items.sort(key=lambda x: (-x["score"], x["id"]))
                matrix[level_name] = items[:per_level]
                total += len(matrix[level_name])

            log.info("[SearchService.matrix_search] 兜底结果: total=%d, 分布=%s",
                     total, {k: len(v) for k, v in matrix.items()})

        log.info("[SearchService.matrix_search] 矩阵搜索完成: shape=%s, total=%d, 分布=%s",
                 shape, total, {k: len(v) for k, v in matrix.items()})

        # 7. 为最终结果计算 highlight_ranges
        kp_ast_for_highlight = kp_cfg.get("ast") or {}
        kp_keywords_for_highlight = kp_cfg.get("keywords", [])
        for level_name, items in matrix.items():
            for res in items:
                try:
                    highlights = self.highlight_service.compute_highlights(
                        res["content"],
                        kp_ast_for_highlight,
                        kp_keywords_for_highlight
                    )
                    res["highlight_ranges"] = highlights
                except Exception as e:
                    log.warning("[SearchService.matrix_search] 计算高亮失败: %s", e)
                    res["highlight_ranges"] = []

        return {
            "kp_id": kp_id,
            "shape": shape,
            "levels": levels,
            "per_level": per_level,
            "matrix": matrix,
            "total": total,
        }

    def composite_matrix_search(
        self,
        kp_ids: List[int],
        per_level: int = 5,
        ast_min_ratio: float = 0.4,
        keyword_min_score: float = 0.4,
        score_aggregation: str = "average",
    ) -> Dict[str, Any]:
        """
        综合知识点矩阵匹配：找到涉及多个知识点的代码片段，按难度分级返回

        :param kp_ids: 知识点 ID 列表
        :param per_level: 每个难度级别返回的片段数量
        :param ast_min_ratio: AST 最低阈值
        :param keyword_min_score: 关键词最低得分
        :param score_aggregation: 得分聚合方式
        :return: 矩阵结构结果
        """
        log.info("[SearchService.composite_matrix_search] 开始综合矩阵搜索: kp_ids=%s, per_level=%d, agg=%s",
                 kp_ids, per_level, score_aggregation)

        if not kp_ids:
            log.warning("[SearchService.composite_matrix_search] 知识点列表为空")
            return {
                "kp_ids": [],
                "shape": [3, per_level],
                "levels": [l["name"] for l in self.DEFAULT_DIFFICULTY_LEVELS],
                "per_level": per_level,
                "matrix": {l["name"]: [] for l in self.DEFAULT_DIFFICULTY_LEVELS},
                "total": 0,
            }

        # 1. 获取所有知识点配置
        kp_configs = []
        all_kp_keywords = set()
        all_kp_nodes = set()

        for kp_id in kp_ids:
            kp_row = self.kp_mgr.get_by_id(kp_id)
            if not kp_row:
                raise KnowledgePointNotFoundError(kp_id)

            kp_level = kp_row.get("level")
            if kp_level != 3:
                raise NonLeafKnowledgePointError(kp_id, kp_level, kp_row.get("name", ""))

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

        # 2. 获取候选片段
        candidates = self._fetch_candidates(list(all_kp_keywords), all_kp_nodes, limit=self.candidate_limit)
        log.info("[SearchService.composite_matrix_search] 获取候选片段数量: %d", len(candidates))

        # 3. 使用矩阵模式权重
        matrix_weights = self._get_matrix_weights()

        # 按难度分桶
        buckets = {level["name"]: [] for level in self.DEFAULT_DIFFICULTY_LEVELS}

        for snip in candidates:
            snip_id = snip.get("id")

            # 解析特征
            ast_raw = snip.get("ast_features")
            if isinstance(ast_raw, (str, bytes, bytearray)):
                snip_ast_nodes = safe_read_json(ast_raw, default=[])
            else:
                snip_ast_nodes = ast_raw or []

            snip_keywords_norm = normalize_keywords_list(snip.get("keywords"))
            snip_difficulty = snip.get("complexity_score") or snip.get("difficulty") or 0.5

            # 计算每个知识点的得分
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
                    target_difficulty=0.5,
                    difficulty_mode="relaxed",
                    weights=matrix_weights,
                    ast_min_ratio=ast_min_ratio,
                    keyword_min_score=keyword_min_score,
                )

                if r.get("filtered"):
                    kp_scores.append(0.0)
                else:
                    kp_scores.append(r["final_score"])

                kp_details.append({
                    "kp_id": kp_cfg["id"],
                    "kp_name": kp_cfg["name"],
                    "score": round(kp_scores[-1], 3),
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

            if composite_score < 0.1:
                continue

            # 标记是否满足所有知识点
            all_kp_matched = all(s > 0 for s in kp_scores)

            # 确定难度桶
            bucket_name = self._get_difficulty_bucket(snip_difficulty)

            buckets[bucket_name].append({
                "id": snip.get("id"),
                "content": snip.get("content", ""),
                "composite_score": round(composite_score, 3),
                "difficulty": round(snip_difficulty, 2),
                "kp_count": len(kp_configs),
                "kp_details": kp_details,
                "score_aggregation": score_aggregation,
                "file_path": snip.get("file_path") or snip.get("source_path"),
                "_all_kp_matched": all_kp_matched,  # 内部标记
            })

        # 4. 分层过滤：每个桶内优先严格匹配，无结果时降级到宽松模式
        matrix = {}
        total = 0
        fallback_used = False

        for level_name, items in buckets.items():
            # 分离严格匹配和宽松匹配
            strict_items = [it for it in items if it.get("_all_kp_matched")]

            if strict_items:
                # 有严格匹配结果
                final_items = strict_items
            else:
                # 降级到宽松模式
                final_items = items
                if items:
                    fallback_used = True
                    log.warning("[SearchService.composite_matrix_search] %s 级别无严格匹配，降级到宽松模式", level_name)

            # 排序并截取
            final_items.sort(key=lambda x: (-x["composite_score"], x["id"]))
            final_items = final_items[:per_level]

            # 清理内部标记，标记部分匹配
            for it in final_items:
                is_partial = not it.pop("_all_kp_matched", True)
                if is_partial:
                    it["partial_match"] = True

            matrix[level_name] = final_items
            total += len(final_items)

        levels = [level["name"] for level in self.DEFAULT_DIFFICULTY_LEVELS]
        shape = [len(levels), per_level]

        log.info("[SearchService.composite_matrix_search] 综合矩阵搜索完成: shape=%s, total=%d, 分布=%s, 降级=%s",
                 shape, total, {k: len(v) for k, v in matrix.items()}, fallback_used)

        # 为最终结果计算 highlight_ranges（使用所有 KP 的模板）
        if kp_configs:
            # 收集所有 KP 的高亮配置
            all_kp_highlight_configs = []
            for kp_cfg in kp_configs:
                kp_row = self.kp_mgr.get_by_id(kp_cfg["id"])
                if kp_row:
                    parsed_cfg = self.kp_mgr.parse_kp_config(kp_row)
                    all_kp_highlight_configs.append((
                        parsed_cfg.get("ast") or {},
                        parsed_cfg.get("keywords", []),
                        kp_cfg["name"]
                    ))

            for level_name, items in matrix.items():
                for res in items:
                    try:
                        highlights = self.highlight_service.compute_highlights_multi(
                            res["content"],
                            all_kp_highlight_configs
                        )
                        res["highlight_ranges"] = highlights
                    except Exception as e:
                        log.warning("[SearchService.composite_matrix_search] 计算高亮失败: %s", e)
                        res["highlight_ranges"] = []

        return {
            "kp_ids": kp_ids,
            "shape": shape,
            "levels": levels,
            "per_level": per_level,
            "matrix": matrix,
            "total": total,
        }
