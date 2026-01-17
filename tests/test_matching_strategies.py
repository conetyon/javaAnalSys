# tests/test_matching_strategies.py
"""
匹配策略单元测试：验证特征提取和匹配逻辑的一致性
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching.strategies import (
    calculate_ast_score,
    calculate_keyword_score,
    calculate_match_score,
    extract_required_nodes,
    DOMAIN_ANCHORS
)


def test_ast_score_basic():
    """测试基本的AST节点匹配"""
    # 完全匹配
    need = ["if_statement", "for_statement"]
    have = ["if_statement", "for_statement", "method_declaration"]
    score, cov = calculate_ast_score(need, have)
    assert cov == 1.0, f"Expected coverage 1.0, got {cov}"
    assert score == 1.0, f"Expected score 1.0, got {score}"
    print("[OK] AST basic matching test passed")

    # 部分匹配
    score2, cov2 = calculate_ast_score(need, ["if_statement"])
    assert cov2 == 0.5, f"Expected coverage 0.5, got {cov2}"
    assert 0.5 <= score2 <= 0.7, f"Expected score in [0.5, 0.7], got {score2}"
    print("[OK] AST partial matching test passed")

    # 无匹配
    score3, cov3 = calculate_ast_score(need, ["method_declaration"])
    assert cov3 == 0.0, f"Expected coverage 0.0, got {cov3}"
    assert score3 == 0.0, f"Expected score 0.0, got {score3}"
    print("[OK] AST no-match test passed")


def test_keyword_score_with_anchors():
    """测试关键词匹配（含领域锚点约束）"""
    # 测试1：有锚点且命中
    kp_kw = ["arraylist", "add", "list"]  # 包含锚点 "arraylist"
    snip_kw = ["arraylist", "add", "new"]
    score, hit, total = calculate_keyword_score(kp_kw, snip_kw)
    assert score > 0, f"Anchor should be hit, score should > 0, got {score}"
    print(f"[OK] Keyword anchor hit test passed: score={score:.2f}, hit={hit}/{total}")

    # 测试2：有锚点但未命中（应该返回0分）
    kp_kw2 = ["arraylist", "add"]
    snip_kw2 = ["linkedlist", "remove"]  # 没有 "arraylist"，虽然有 "linkedlist"（另一个锚点）
    score2, hit2, total2 = calculate_keyword_score(kp_kw2, snip_kw2)
    assert score2 == 0.0, f"Anchor miss should return 0 score, got {score2}"
    print(f"[OK] Keyword anchor miss test passed: score={score2}")

    # 测试3：无锚点，普通匹配
    kp_kw3 = ["if", "else", "condition"]
    snip_kw3 = ["if", "condition", "return"]
    score3, hit3, total3 = calculate_keyword_score(kp_kw3, snip_kw3)
    assert score3 > 0, f"Normal keyword match should > 0, got {score3}"
    print(f"[OK] Keyword normal match test passed: score={score3:.2f}, hit={hit3}/{total3}")


def test_extract_required_nodes():
    """测试AST节点提取（合并模式）"""
    # 显式 + 映射合并
    ast_tpl = {
        "template": "IfStatement",
        "required_nodes": ["method_declaration"]
    }
    nodes = extract_required_nodes(ast_tpl)
    assert "if_statement" in nodes, "Should include nodes from NODE_MAPPING"
    assert "method_declaration" in nodes, "Should include explicitly defined nodes"
    print(f"[OK] AST node extraction test passed: {nodes}")


def test_full_match_scenario():
    """端到端匹配场景测试"""
    # 模拟知识点：ArrayList basics
    kp_ast = ["object_creation_expression", "method_invocation", "type_identifier"]
    kp_kw = ["arraylist", "add", "get", "list"]
    kp_name = "ArrayList basics"

    # 模拟代码片段：包含ArrayList的代码
    snip_ast = ["method_declaration", "object_creation_expression", "method_invocation", "type_identifier"]
    snip_kw = ["arraylist", "add", "new", "list", "get"]
    snip_diff = 0.5

    result = calculate_match_score(
        kp_ast_nodes=kp_ast,
        snip_ast_nodes=snip_ast,
        kp_keywords=kp_kw,
        snip_keywords=snip_kw,
        kp_name=kp_name,
        snip_difficulty=snip_diff,
        target_difficulty=0.5,
        ast_min_ratio=0.3,
        keyword_min_score=0.2
    )

    assert not result["filtered"], "Well-matched code should not be filtered"
    assert result["final_score"] > 0.5, f"Expected score > 0.5, got {result['final_score']}"
    assert result["ast_coverage"] >= 0.6, f"Expected AST coverage >= 0.6, got {result['ast_coverage']}"
    print(f"[OK] End-to-end match test passed: final_score={result['final_score']:.2f}, "
          f"ast_cov={result['ast_coverage']:.2f}, kw_score={result['keyword_score']:.2f}")


def test_anchor_filtering():
    """测试领域锚点过滤功能"""
    # 场景：查找ArrayList相关代码，但代码中只有HashMap
    kp_ast = ["object_creation_expression", "method_invocation"]
    kp_kw = ["arraylist", "list", "add"]  # 有锚点 "arraylist"

    snip_ast = ["object_creation_expression", "method_invocation", "type_identifier"]
    snip_kw = ["hashmap", "put", "map"]  # 有锚点 "hashmap"，但不是 "arraylist"

    result = calculate_match_score(
        kp_ast_nodes=kp_ast,
        snip_ast_nodes=snip_ast,
        kp_keywords=kp_kw,
        snip_keywords=snip_kw,
        kp_name="ArrayList basics",
        snip_difficulty=0.5,
        target_difficulty=0.5,
        ast_min_ratio=0.3,
        keyword_min_score=0.2
    )

    # 应该被过滤（锚点不匹配）
    assert result["filtered"] or result["final_score"] == 0.0, \
        "Anchor mismatch should lead to filtering or 0 score"
    print(f"[OK] Anchor filtering test passed: filtered={result['filtered']}, score={result['final_score']}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Running Matching Strategy Unit Tests")
    print("="*60 + "\n")

    tests = [
        ("AST scoring", test_ast_score_basic),
        ("Keyword scoring (with anchors)", test_keyword_score_with_anchors),
        ("AST node extraction", test_extract_required_nodes),
        ("End-to-end matching", test_full_match_scenario),
        ("Domain anchor filtering", test_anchor_filtering),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n[Test] {name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
