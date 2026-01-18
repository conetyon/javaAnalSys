# main.py
"""
离线任务测试脚本
通过注释/取消注释选择测试场景

使用方法：
1. 取消注释想要运行的场景
2. 修改 kp_ids 参数测试不同知识点
3. 运行: python main.py

自动化流程：
- 步骤 1: 初始化数据库（创建表结构、插入知识点数据）
- 步骤 2: 分析示例代码（提取代码片段特征并存入数据库）
- 步骤 3: 运行测试场景（匹配知识点）

注意：
- 所有步骤都是幂等操作，可重复执行
- 会自动分析 ./sample_code.java 文件

可用的知识点 ID（示例）:
- 10010, 10011, 10031, 10034, 10083 (print 相关)
- 具体知识点体系可运行 print_knowledge_tree() 查看
"""

from scripts.offline_tasks import (
    init_database,
    analyze_code_file,
    run_matching_test,
    run_composite_matching_test,
    print_knowledge_tree,
)


def run_single_test():
    """
    场景 1: 单个知识点匹配
    用途: 为单个知识点查找最匹配的代码片段
    """
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
    """
    场景 2: 综合知识点匹配
    用途: 查找同时涉及多个知识点的代码片段
    score_aggregation 可选值:
      - "average": 平均得分（推荐，均衡包含各知识点）
      - "min": 最小得分（必须同时满足所有知识点）
      - "sum": 求和得分（偏好覆盖更多知识点）
    """
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


def run_utility_functions():
    """
    工具函数场景
    用途: 查看知识点体系、分析代码文件等辅助功能
    """
    # ------------------------------------------------------------
    # 查看知识点树结构
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("知识点树结构")
    print("=" * 60)
    print_knowledge_tree()

    # ------------------------------------------------------------
    # 分析指定 Java 文件
    # ------------------------------------------------------------
    # file_path = "./sample_code.java"
    # print(f"\n分析文件: {file_path}")
    # snippets = analyze_code_file(file_path, save_to_db=True)
    # print(f"检测到 {len(snippets)} 个代码片段")
    # for i, snippet in enumerate(snippets, 1):
    #     print(f"  [{i}] 行 {snippet['start_line']}-{snippet['end_line']}, "
    #           f"难度: {snippet['difficulty']:.2f}")


if __name__ == "__main__":
    try:
        # ========================================
        # 1. 自动初始化数据库（幂等操作）
        # ========================================
        print("\n" + "=" * 60)
        print("步骤 1: 初始化数据库...")
        print("=" * 60)
        success = init_database()
        if not success:
            print("[WARNING] 数据库初始化失败，但继续执行测试")
        else:
            print("[SUCCESS] 数据库已就绪")

        # ========================================
        # 2. 自动分析示例代码并提取特征
        # ========================================
        print("\n" + "=" * 60)
        print("步骤 2: 分析示例代码...")
        print("=" * 60)
        sample_file = "./sample_code.java"
        try:
            snippets = analyze_code_file(sample_file, save_to_db=True)
            print(f"[SUCCESS] 检测到 {len(snippets)} 个代码片段")
            for i, snippet in enumerate(snippets[:3], 1):  # 只显示前3个
                print(f"  [{i}] 行 {snippet['start_line']}-{snippet['end_line']}, "
                      f"难度: {snippet['difficulty']:.2f}, "
                      f"关键词: {len(snippet['keywords'])} 个")
            if len(snippets) > 3:
                print(f"  ... 还有 {len(snippets) - 3} 个片段")
        except FileNotFoundError:
            print(f"[WARNING] 未找到示例文件: {sample_file}")
            print("[INFO] 跳过代码分析，直接运行测试（可能无匹配结果）")
        except Exception as e:
            print(f"[WARNING] 代码分析失败: {e}")
            print("[INFO] 继续运行测试（可能无匹配结果）")

        # ========================================
        # 3. 运行测试场景（取消注释其中一个）
        # ========================================
        print("\n" + "=" * 60)
        print("步骤 3: 运行测试场景")
        print("=" * 60)

        run_single_test()          # 场景 1: 单个知识点匹配
        run_multiple_test()          # 场景 2: 综合知识点匹配
        # run_utility_functions()    # 工具函数: 查看知识点树等，在日志中

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
