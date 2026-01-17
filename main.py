# main.py
"""
离线任务测试脚本
通过注释/取消注释选择测试场景

使用方法：
1. 取消注释想要运行的场景
2. 修改 kp_ids 参数测试不同知识点
3. 运行: python main.py

可用的知识点 ID（示例）:
- 10010, 10011, 10031, 10034, 10083 (print 相关)
- 具体知识点体系可运行 print_knowledge_tree() 查看
"""

from scripts.offline_tasks import (
    run_matching_test,
    run_composite_matching_test,
)


def run_single_test():
    """
    测试场景选择
    取消注释其中一个场景运行
    """

    # ------------------------------------------------------------
    # 场景 1: 单个知识点匹配
    # 用途: 为单个知识点查找最匹配的代码片段
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("场景 1: 单个知识点匹配")
    print("=" * 60)

    kp_id = 10011  # 可选: 10010, 10011, 10031, 10034, 10083

    results = run_matching_test(
        kp_ids=[kp_id],
        target_difficulty=0.5,
        top_k=5
    )

    for kp_id, matches in results.items():
        print(f"\n知识点 {kp_id}: 找到 {len(matches)} 条匹配")
        for i, m in enumerate(matches, 1):
            print(f"  [{i}] score={m.get('score'):.3f}, "
                  f"ast={m.get('ast_ratio'):.2f}, "
                  f"kw={m.get('keyword_score'):.2f}, "
                  f"diff={m.get('difficulty'):.2f}")
            code_preview = m.get('content', '')[:100].replace('\n', ' ')
            print(f"      {code_preview}...")

def run_multiple_test():
    # ------------------------------------------------------------
    # 场景 2: 综合知识点匹配
    # 用途: 查找同时涉及多个知识点的代码片段
    # score_aggregation 可选值:
    #   - "average": 平均得分（推荐，均衡包含各知识点）
    #   - "min": 最小得分（必须同时满足所有知识点）
    #   - "sum": 求和得分（偏好覆盖更多知识点）
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("场景 2: 综合知识点匹配")
    print("=" * 60)

    # 选择多个知识点组合
    kp_ids = [10011, 10012, 10034]  # 可选: 10010, 10011, 10031, 10034, 10083

    results = run_composite_matching_test(
        kp_ids=kp_ids,
        target_difficulty=0.5,
        top_k=5,
        score_aggregation="average"  # 可选: average, min, sum
    )

    print(f"\n找到 {len(results)} 条综合匹配")
    for i, match in enumerate(results, 1):
        print(f"\n[{i}] 综合得分: {match.get('composite_score'):.3f}")
        print(f"    各知识点得分:")
        for kp_detail in match.get('kp_details', []):
            print(f"      - KP {kp_detail.get('kp_id')} ({kp_detail.get('kp_name')}): "
                  f"{kp_detail.get('score'):.3f}")
        code_preview = match.get('content', '')[:100].replace('\n', ' ')
        print(f"    代码: {code_preview}...")


if __name__ == "__main__":
    try:
        # run_single_test()
        run_multiple_test()
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
