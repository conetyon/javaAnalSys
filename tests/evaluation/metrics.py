# src/evaluation/metrics.py
"""
评估指标计算模块

实现常用的信息检索和推荐系统评估指标：
- Top-1 Accuracy: 首位结果准确率（主要指标）
- Precision@K: 前 K 个结果的精确率
- Recall@K: 前 K 个结果的召回率
- MRR (Mean Reciprocal Rank): 平均倒数排名
- nDCG (Normalized Discounted Cumulative Gain): 归一化折损累积增益
- MAP (Mean Average Precision): 平均精度均值
"""

import math
from typing import List, Set, Dict, Any, Tuple
from lib.globals import core_logger as log


def calculate_top1_accuracy(predictions: List[List[int]], ground_truths: List[Set[int]]) -> float:
    """
    计算 Top-1 准确率（首位结果准确率）

    Args:
        predictions: 每个查询的预测结果列表（snippet_id），按得分降序排列
                     格式：[[snippet_id1, snippet_id2, ...], [snippet_id3, ...], ...]
        ground_truths: 每个查询的正确答案集合
                      格式：[{correct_id1, correct_id2}, {correct_id3}, ...]

    Returns:
        float: Top-1 准确率，范围 [0, 1]

    示例：
        predictions = [[5, 3, 7], [2, 8], [1, 9, 4]]
        ground_truths = [{5, 7}, {8}, {9}]
        # 第1个查询：首位是5，正确 ✓
        # 第2个查询：首位是2，错误（正确答案是8）✗
        # 第3个查询：首位是1，错误（正确答案是9）✗
        # Top-1 Accuracy = 1/3 = 0.333
    """
    if not predictions or not ground_truths:
        log.warning("[Top-1 Accuracy] 输入为空，返回 0.0")
        return 0.0

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    correct_count = 0
    total_count = len(predictions)

    for i, (pred_list, gt_set) in enumerate(zip(predictions, ground_truths)):
        if not pred_list:
            log.debug(f"[Top-1 Accuracy] 查询 {i}: 无预测结果")
            continue

        top1_id = pred_list[0]
        if top1_id in gt_set:
            correct_count += 1
            log.debug(f"[Top-1 Accuracy] 查询 {i}: 首位 {top1_id} 正确 ✓")
        else:
            log.debug(f"[Top-1 Accuracy] 查询 {i}: 首位 {top1_id} 错误，期望 {gt_set} ✗")

    accuracy = correct_count / total_count if total_count > 0 else 0.0
    log.info(f"[Top-1 Accuracy] {correct_count}/{total_count} = {accuracy:.2%}")
    return accuracy


def calculate_precision_at_k(predictions: List[List[int]], ground_truths: List[Set[int]], k: int = 10) -> Tuple[float, List[float]]:
    """
    计算 Precision@K（前 K 个结果的精确率）

    精确率 = 前K个结果中正确的数量 / K

    Args:
        predictions: 预测结果列表
        ground_truths: 正确答案集合
        k: 截断位置

    Returns:
        (average_precision, per_query_precisions)
        - average_precision: 所有查询的平均精确率
        - per_query_precisions: 每个查询的精确率列表

    示例：
        predictions = [[5, 3, 7, 2, 9], ...]
        ground_truths = [{5, 7, 9}, ...]
        k = 3
        # 前3个结果: [5, 3, 7]
        # 正确的: [5, 7]
        # Precision@3 = 2/3 = 0.667
    """
    if not predictions or not ground_truths:
        return 0.0, []

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    per_query_precisions = []

    for pred_list, gt_set in zip(predictions, ground_truths):
        topk = pred_list[:k]
        if not topk:
            per_query_precisions.append(0.0)
            continue

        correct_in_topk = sum(1 for pid in topk if pid in gt_set)
        precision = correct_in_topk / len(topk)
        per_query_precisions.append(precision)

    avg_precision = sum(per_query_precisions) / len(per_query_precisions) if per_query_precisions else 0.0
    log.info(f"[Precision@{k}] 平均精确率: {avg_precision:.2%}")
    return avg_precision, per_query_precisions


def calculate_recall_at_k(predictions: List[List[int]], ground_truths: List[Set[int]], k: int = 10) -> Tuple[float, List[float]]:
    """
    计算 Recall@K（前 K 个结果的召回率）

    召回率 = 前K个结果中正确的数量 / 所有正确答案的数量

    Args:
        predictions: 预测结果列表
        ground_truths: 正确答案集合
        k: 截断位置

    Returns:
        (average_recall, per_query_recalls)

    示例：
        predictions = [[5, 3, 7], ...]
        ground_truths = [{5, 7, 9, 11}, ...]
        k = 3
        # 前3个结果: [5, 3, 7]
        # 正确的: [5, 7] (2个)
        # 总共应该找到: {5, 7, 9, 11} (4个)
        # Recall@3 = 2/4 = 0.5
    """
    if not predictions or not ground_truths:
        return 0.0, []

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    per_query_recalls = []

    for pred_list, gt_set in zip(predictions, ground_truths):
        if not gt_set:
            # 没有正确答案，召回率定义为 1.0（无需召回）
            per_query_recalls.append(1.0)
            continue

        topk = pred_list[:k]
        correct_in_topk = sum(1 for pid in topk if pid in gt_set)
        recall = correct_in_topk / len(gt_set)
        per_query_recalls.append(recall)

    avg_recall = sum(per_query_recalls) / len(per_query_recalls) if per_query_recalls else 0.0
    log.info(f"[Recall@{k}] 平均召回率: {avg_recall:.2%}")
    return avg_recall, per_query_recalls


def calculate_mrr(predictions: List[List[int]], ground_truths: List[Set[int]]) -> Tuple[float, List[float]]:
    """
    计算 MRR (Mean Reciprocal Rank) - 平均倒数排名

    对每个查询，找到第一个正确结果的位置 rank，倒数 1/rank 作为得分。
    所有查询的得分平均值即为 MRR。

    Args:
        predictions: 预测结果列表
        ground_truths: 正确答案集合

    Returns:
        (mrr, per_query_rr)
        - mrr: 平均倒数排名
        - per_query_rr: 每个查询的倒数排名列表

    示例：
        predictions = [[3, 5, 7], [2, 8, 1], [9]]
        ground_truths = [{5}, {8}, {9}]
        # 查询1: 第一个正确结果是5（位置2），RR = 1/2 = 0.5
        # 查询2: 第一个正确结果是8（位置2），RR = 1/2 = 0.5
        # 查询3: 第一个正确结果是9（位置1），RR = 1/1 = 1.0
        # MRR = (0.5 + 0.5 + 1.0) / 3 = 0.667
    """
    if not predictions or not ground_truths:
        return 0.0, []

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    per_query_rr = []

    for pred_list, gt_set in zip(predictions, ground_truths):
        rr = 0.0
        for rank, pid in enumerate(pred_list, start=1):
            if pid in gt_set:
                rr = 1.0 / rank
                log.debug(f"[MRR] 首个正确结果位置: {rank}, RR = {rr:.3f}")
                break
        per_query_rr.append(rr)

    mrr = sum(per_query_rr) / len(per_query_rr) if per_query_rr else 0.0
    log.info(f"[MRR] 平均倒数排名: {mrr:.3f}")
    return mrr, per_query_rr


def calculate_ndcg(predictions: List[List[int]], ground_truths: List[Dict[int, float]], k: int = 10) -> Tuple[float, List[float]]:
    """
    计算 nDCG (Normalized Discounted Cumulative Gain) - 归一化折损累积增益

    考虑排序质量和相关性分级的评估指标。位置越靠前的相关文档权重越高。

    Args:
        predictions: 预测结果列表
        ground_truths: 正确答案及其相关性得分
                      格式：[{snippet_id: relevance_score, ...}, ...]
                      relevance_score 一般为 [0, 5] 整数，5 表示高度相关

    Returns:
        (average_ndcg, per_query_ndcg)

    计算公式：
        DCG@K = sum_{i=1}^{K} (2^{rel_i} - 1) / log2(i + 1)
        IDCG@K = 理想情况下的 DCG（按相关性降序排列）
        nDCG@K = DCG@K / IDCG@K

    示例：
        predictions = [[5, 3, 7, 2]]
        ground_truths = [{5: 3, 7: 2, 2: 1}]  # 5高度相关(3分)，7中度相关(2分)，2低度相关(1分)
        k = 3
        # 预测排序: [5, 3, 7]
        # 相关性: [3, 0, 2]
        # DCG = (2^3-1)/log2(2) + (2^0-1)/log2(3) + (2^2-1)/log2(4)
        #     = 7/1 + 0/1.585 + 3/2 = 7 + 0 + 1.5 = 8.5
        # 理想排序: [5, 7, 2] (按相关性降序)
        # IDCG = 7/1 + 3/1.585 + 1/2 = 7 + 1.89 + 0.5 = 9.39
        # nDCG = 8.5 / 9.39 = 0.905
    """
    if not predictions or not ground_truths:
        return 0.0, []

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    per_query_ndcg = []

    for pred_list, gt_dict in zip(predictions, ground_truths):
        topk = pred_list[:k]
        if not topk or not gt_dict:
            per_query_ndcg.append(0.0)
            continue

        # 计算 DCG@K
        dcg = 0.0
        for i, pid in enumerate(topk, start=1):
            relevance = gt_dict.get(pid, 0)
            dcg += (2 ** relevance - 1) / math.log2(i + 1)

        # 计算 IDCG@K（理想情况：按相关性降序排列）
        ideal_relevances = sorted(gt_dict.values(), reverse=True)[:k]
        idcg = sum((2 ** rel - 1) / math.log2(i + 1) for i, rel in enumerate(ideal_relevances, start=1))

        # 计算 nDCG
        ndcg = dcg / idcg if idcg > 0 else 0.0
        per_query_ndcg.append(ndcg)

    avg_ndcg = sum(per_query_ndcg) / len(per_query_ndcg) if per_query_ndcg else 0.0
    log.info(f"[nDCG@{k}] 平均归一化折损累积增益: {avg_ndcg:.3f}")
    return avg_ndcg, per_query_ndcg


def calculate_map(predictions: List[List[int]], ground_truths: List[Set[int]]) -> Tuple[float, List[float]]:
    """
    计算 MAP (Mean Average Precision) - 平均精度均值

    对每个查询，在每个相关文档出现的位置计算精确率，然后取平均。
    所有查询的 AP 平均值即为 MAP。

    Args:
        predictions: 预测结果列表
        ground_truths: 正确答案集合

    Returns:
        (map_score, per_query_ap)

    计算公式：
        AP = (1 / |相关文档数|) * sum_{k=1}^{n} (Precision@k * rel(k))
        其中 rel(k) 是指示函数，当第k个文档相关时为1，否则为0

    示例：
        predictions = [[5, 3, 7, 2, 9]]
        ground_truths = [{5, 7, 9}]
        # 位置1: 5 相关，P@1 = 1/1 = 1.0
        # 位置2: 3 不相关
        # 位置3: 7 相关，P@3 = 2/3 = 0.667
        # 位置4: 2 不相关
        # 位置5: 9 相关，P@5 = 3/5 = 0.6
        # AP = (1.0 + 0.667 + 0.6) / 3 = 0.756
    """
    if not predictions or not ground_truths:
        return 0.0, []

    if len(predictions) != len(ground_truths):
        raise ValueError(f"预测结果数量({len(predictions)})与真实答案数量({len(ground_truths)})不匹配")

    per_query_ap = []

    for pred_list, gt_set in zip(predictions, ground_truths):
        if not gt_set:
            per_query_ap.append(1.0)  # 没有相关文档，定义为1.0
            continue

        num_relevant = len(gt_set)
        num_hits = 0
        sum_precisions = 0.0

        for k, pid in enumerate(pred_list, start=1):
            if pid in gt_set:
                num_hits += 1
                precision_at_k = num_hits / k
                sum_precisions += precision_at_k

        ap = sum_precisions / num_relevant if num_relevant > 0 else 0.0
        per_query_ap.append(ap)

    map_score = sum(per_query_ap) / len(per_query_ap) if per_query_ap else 0.0
    log.info(f"[MAP] 平均精度均值: {map_score:.3f}")
    return map_score, per_query_ap


def calculate_f1_score(precision: float, recall: float) -> float:
    """
    计算 F1 分数（精确率和召回率的调和平均）

    Args:
        precision: 精确率
        recall: 召回率

    Returns:
        float: F1 分数

    公式：
        F1 = 2 * (precision * recall) / (precision + recall)
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)
