# src/evaluation/baselines.py
"""
基线方法实现

用于对比实验的基线匹配算法：
1. TF-IDF 匹配器：纯基于关键词的 TF-IDF 相似度
2. Pure AST 匹配器：纯基于 AST 节点相似度
3. Random 匹配器：随机排序（最差基线）
"""

import math
import random
from collections import Counter
from typing import List, Dict, Any, Tuple
from lib.globals import core_logger as log


class TFIDFMatcher:
    """
    TF-IDF 关键词匹配器（基线方法）

    使用经典的 TF-IDF 算法计算查询关键词与代码片段关键词的相似度。
    不考虑 AST 结构，纯关键词匹配。
    """

    def __init__(self):
        self.idf_cache = {}

    def calculate_idf(self, all_snippets: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算所有关键词的 IDF 值

        IDF(term) = log(N / df(term))
        其中 N 是文档总数，df(term) 是包含该词的文档数

        Args:
            all_snippets: 所有代码片段列表

        Returns:
            Dict[str, float]: {keyword: idf_value}
        """
        N = len(all_snippets)
        df = Counter()

        for snippet in all_snippets:
            keywords = snippet.get("keywords", [])
            if isinstance(keywords, str):
                import json
                try:
                    keywords = json.loads(keywords)
                except:
                    keywords = []

            unique_kws = set(kw.lower() for kw in keywords if kw)
            for kw in unique_kws:
                df[kw] += 1

        idf = {}
        for term, doc_freq in df.items():
            idf[term] = math.log(N / doc_freq) if doc_freq > 0 else 0.0

        self.idf_cache = idf
        log.info(f"[TF-IDF] 计算完成，词汇表大小: {len(idf)}")
        return idf

    def match(self, kp_keywords: List[str], all_snippets: List[Dict[str, Any]], top_k: int = 10) -> List[int]:
        """
        使用 TF-IDF 匹配代码片段

        Args:
            kp_keywords: 知识点关键词列表
            all_snippets: 所有候选代码片段
            top_k: 返回前 K 个结果

        Returns:
            List[int]: 按相似度降序排列的 snippet_id 列表
        """
        if not self.idf_cache:
            self.calculate_idf(all_snippets)

        query_kws = set(kw.lower() for kw in kp_keywords if kw)
        scores = []

        for snippet in all_snippets:
            snippet_id = snippet.get("id")
            snippet_kws_raw = snippet.get("keywords", [])

            if isinstance(snippet_kws_raw, str):
                import json
                try:
                    snippet_kws_raw = json.loads(snippet_kws_raw)
                except:
                    snippet_kws_raw = []

            snippet_kws = [kw.lower() for kw in snippet_kws_raw if kw]
            snippet_kw_counts = Counter(snippet_kws)

            # 计算 TF-IDF 余弦相似度
            score = 0.0
            for kw in query_kws:
                if kw in snippet_kw_counts:
                    tf = snippet_kw_counts[kw] / len(snippet_kws) if snippet_kws else 0
                    idf = self.idf_cache.get(kw, 0)
                    score += tf * idf

            scores.append((snippet_id, score))

        # 按得分降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        result_ids = [sid for sid, _ in scores[:top_k]]

        log.debug(f"[TF-IDF Matcher] Top-{top_k} 结果: {result_ids[:5]}...")
        return result_ids


class PureASTMatcher:
    """
    纯 AST 匹配器（基线方法）

    只考虑 AST 节点的 Jaccard 相似度，不考虑关键词。
    """

    def match(self, kp_ast_nodes: List[str], all_snippets: List[Dict[str, Any]], top_k: int = 10) -> List[int]:
        """
        使用 AST 节点集合计算 Jaccard 相似度

        Jaccard(A, B) = |A ∩ B| / |A ∪ B|

        Args:
            kp_ast_nodes: 知识点要求的 AST 节点列表
            all_snippets: 所有候选代码片段
            top_k: 返回前 K 个结果

        Returns:
            List[int]: 按相似度降序排列的 snippet_id 列表
        """
        query_nodes = set(node.lower() for node in kp_ast_nodes if node)
        scores = []

        for snippet in all_snippets:
            snippet_id = snippet.get("id")
            snippet_ast_raw = snippet.get("ast_features", [])

            if isinstance(snippet_ast_raw, str):
                import json
                try:
                    snippet_ast_raw = json.loads(snippet_ast_raw)
                except:
                    snippet_ast_raw = []

            snippet_nodes = set(node.lower() for node in snippet_ast_raw if node)

            # 计算 Jaccard 相似度
            if not query_nodes or not snippet_nodes:
                score = 0.0
            else:
                intersection = len(query_nodes & snippet_nodes)
                union = len(query_nodes | snippet_nodes)
                score = intersection / union if union > 0 else 0.0

            scores.append((snippet_id, score))

        # 按得分降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        result_ids = [sid for sid, _ in scores[:top_k]]

        log.debug(f"[Pure AST Matcher] Top-{top_k} 结果: {result_ids[:5]}...")
        return result_ids


class RandomMatcher:
    """
    随机匹配器（最差基线）

    随机排序所有代码片段，用于验证其他方法是否优于随机。
    """

    def match(self, all_snippets: List[Dict[str, Any]], top_k: int = 10) -> List[int]:
        """
        随机排序代码片段

        Args:
            all_snippets: 所有候选代码片段
            top_k: 返回前 K 个结果

        Returns:
            List[int]: 随机排序的 snippet_id 列表
        """
        snippet_ids = [s.get("id") for s in all_snippets if s.get("id")]
        random.shuffle(snippet_ids)
        result_ids = snippet_ids[:top_k]

        log.debug(f"[Random Matcher] Top-{top_k} 结果: {result_ids[:5]}...")
        return result_ids
