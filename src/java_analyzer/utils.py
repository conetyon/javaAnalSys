# services/search_service.py
# 结论（以注释形式放在文件顶部，便于团队同步）：
# - 不需要回滚到最早不扫描 content 的版本。保留“内容扫描兜底”但通过配置开关控制。
# - 完成 Analyzer 全量回填并验证后，将该开关关闭（或删除兜底逻辑），回到纯特征打分。
# - 不做全库遍历：通过索引/数据库先拿候选集，仅对候选做精排。兜底扫描（若开启）也只在候选上执行。

import os
import re
from typing import List, Dict, Iterable, Set, Tuple

def to_lower_set(xs: Iterable[str]) -> Set[str]:
    return {x for x in xs if x} | {x.lower() for x in xs if x}

class KnowledgePoint:
    def __init__(self, keywords: List[str], ast_requirements: List[str] = None):
        self.keywords = to_lower_set(keywords or [])
        self.ast_requirements = set(ast_requirements or [])

class CodeLibraryRepo:
    """
    Repository 抽象：
    - 应使用数据库/搜索引擎索引来返回候选集，避免全库遍历
    - 需要字段：id, content, keywords(array), ast_features(array)
    实现建议（择一）：
      1) PostgreSQL：WHERE keywords && :kw OR ast_features && :ast LIMIT :limit
      2) Elasticsearch：terms 查询 + bool should，返回 topN
      3) SQLite FTS/自建倒排：先取 ids 再批量取详情
    """
    def find_candidates_by_index(self, kw: Set[str], ast: Set[str], limit: int = 2000) -> List[Dict]:
        # TODO: 用实际索引替换，以下仅示意（应不进行全表遍历）
        raise NotImplementedError

    def get_snippets_by_ids(self, ids: List[int]) -> List[Dict]:
        # TODO: 批量取详情，字段至少包含：id, content, keywords, ast_features
        raise NotImplementedError

class SearchService:
    def __init__(self, repo: CodeLibraryRepo, config: Dict = None):
        cfg = config or {}
        # 兜底开关：默认开启，等 Analyzer 回填稳定后设为 False
        self.enable_content_scan_fallback = bool(
            cfg.get("enable_content_scan_fallback", os.getenv("ENABLE_CONTENT_SCAN_FALLBACK", "1") == "1")
        )
        # 候选集大小上限，控制精排规模
        self.candidate_limit = int(cfg.get("candidate_limit", os.getenv("CANDIDATE_LIMIT", "2000")))
        # 权重（可通过配置/实验平台调整）
        self.w_kw = float(cfg.get("weight_keywords", 0.7))
        self.w_ast = float(cfg.get("weight_ast", 0.3))

    def search(self, kp: KnowledgePoint, top_k: int = 50) -> List[Dict]:
        # 1) 索引生成候选集（避免全库遍历）
        candidates = self._get_candidates(kp)
        if not candidates:
            return []

        # 2) 对候选集精排（如启用兜底，仅对候选进行内容扫描）
        scored = []
        for s in candidates:
            score, detail = self._score_snippet(s, kp, use_fallback=self.enable_content_scan_fallback)
            if score > 0:
                s_out = dict(s)
                s_out["score"] = score
                s_out["score_detail"] = detail
                scored.append(s_out)

        # 3) 排序返回
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _get_candidates(self, kp: KnowledgePoint) -> List[Dict]:
        return self._safe_repo_call(self.repo.find_candidates_by_index, kp.keywords, kp.ast_requirements, self.candidate_limit)

    def _score_snippet(self, s: Dict, kp: KnowledgePoint, use_fallback: bool) -> Tuple[float, Dict]:
        # 关键词命中（DB 抽取）
        s_kw = to_lower_set(s.get("keywords", []))
        kw_hits_db = kp.keywords & s_kw

        # 可选兜底：对候选片段的 content 做不区分大小写的子串命中
        kw_hits_text = set()
        if use_fallback:
            content = s.get("content") or ""
            low_content = content.lower()
            for kw in kp.keywords:
                if kw and kw in low_content:
                    kw_hits_text.add(kw)

        kw_hits = kw_hits_db | kw_hits_text
        kw_score = self._score_keywords(kp.keywords, kw_hits)

        # AST 覆盖
        s_ast = set(s.get("ast_features", []))
        ast_hits = kp.ast_requirements & s_ast if kp.ast_requirements else set()
        ast_score = self._score_ast(kp.ast_requirements, ast_hits)

        score = self.w_kw * kw_score + self.w_ast * ast_score
        detail = {
            "kw_hits_db": sorted(list(kw_hits_db)),
            "kw_hits_text": sorted(list(kw_hits_text)) if use_fallback else [],
            "ast_hits": sorted(list(ast_hits)),
            "kw_score": kw_score,
            "ast_score": ast_score,
        }
        return score, detail

    def _score_keywords(self, kp_kw: Set[str], hits: Set[str]) -> float:
        if not kp_kw:
            return 0.0
        # 简单命中率；可换成加权/IDF
        return round(len(hits) / len(kp_kw), 6)

    def _score_ast(self, kp_ast: Set[str], hits: Set[str]) -> float:
        if not kp_ast:
            return 0.0
        return round(len(hits) / len(kp_ast), 6)

    # --------- utils ---------
    @property
    def repo(self) -> CodeLibraryRepo:
        return getattr(self, "_repo")

    @repo.setter
    def repo(self, r: CodeLibraryRepo):
        self._repo = r

    def _safe_repo_call(self, fn, *args, **kwargs):
        # 协助在尚未接好真实索引实现前快速发现错误
        try:
            return fn(*args, **kwargs)
        except NotImplementedError:
            # 在本地/测试环境可临时退化到空结果（不做全表遍历）
            return []
