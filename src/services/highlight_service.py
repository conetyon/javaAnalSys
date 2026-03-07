"""
Highlight Service - Real-time Key Line Detection

Computes highlight ranges for code snippets based on knowledge point AST templates
and keywords. Does NOT modify the database - all computation is done at runtime.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

import json
from typing import List, Dict, Any, Set, Optional

import tree_sitter_java
from tree_sitter import Language, Parser

from src.matching.strategies import NODE_MAPPING
from lib.globals import core_logger as log


class HighlightService:
    """
    Real-time key line detection service.

    Analyzes code snippets to identify lines that are most relevant to
    a given knowledge point based on AST structure and keywords.
    """

    def __init__(self):
        self.language = Language(tree_sitter_java.language())
        self.parser = Parser(self.language)

    def compute_highlights(
        self,
        code: str,
        kp_ast_template: Optional[Dict[str, Any]],
        kp_keywords: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Compute highlight ranges for a code snippet.

        Args:
            code: Java code snippet
            kp_ast_template: Knowledge point AST template dict with 'required_nodes' key
            kp_keywords: List of keywords associated with the knowledge point

        Returns:
            List of highlight range dicts:
            [
                {
                    "start_line": 3,
                    "end_line": 6,
                    "type": "for_statement",
                    "label": "for 循环"
                }
            ]
        """
        return self.compute_highlights_multi(code, [(kp_ast_template, kp_keywords, None)])

    def compute_highlights_multi(
        self,
        code: str,
        kp_configs: List[tuple]  # List of (ast_template, keywords, kp_name)
    ) -> List[Dict[str, Any]]:
        """
        Compute highlight ranges for multiple knowledge points.

        Args:
            code: Java code snippet
            kp_configs: List of (ast_template, keywords, kp_name) tuples

        Returns:
            List of highlight range dicts with kp_name in label
        """
        if not code:
            return []

        code_bytes = code.encode('utf-8')
        try:
            tree = self.parser.parse(code_bytes)
        except Exception as e:
            log.warning(f"[HighlightService] Failed to parse code: {e}")
            return []

        root = tree.root_node
        highlights = []
        seen_ranges = set()

        for kp_ast_template, kp_keywords, kp_name in kp_configs:
            # Extract required node types from AST template
            target_node_types = self._extract_target_node_types(kp_ast_template)

            # Normalize keywords to lowercase set
            target_keywords = self._normalize_keywords(kp_keywords)

            # Label prefix for this KP
            label_prefix = f"[{kp_name}] " if kp_name else ""

            # Find nodes matching target types
            if target_node_types:
                matches = self._find_matching_nodes(root, target_node_types)
                for node, matched_type in matches:
                    range_key = (node.start_point[0], node.end_point[0], matched_type)
                    if range_key not in seen_ranges:
                        seen_ranges.add(range_key)
                        highlights.append({
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                            "type": node.type,
                            "label": label_prefix + self._get_label_for_type(matched_type)
                        })

            # Find lines containing keywords
            if target_keywords:
                keyword_lines = self._find_keyword_lines(code, target_keywords)
                for line_num, keyword in keyword_lines:
                    range_key = (line_num - 1, line_num - 1, f"kw_{keyword}")
                    if range_key not in seen_ranges:
                        seen_ranges.add(range_key)
                        highlights.append({
                            "start_line": line_num,
                            "end_line": line_num,
                            "type": "keyword_match",
                            "label": label_prefix + f"关键词: {keyword}"
                        })

        # Sort by start line
        highlights.sort(key=lambda x: x["start_line"])

        return highlights

    def _extract_target_node_types(
        self,
        ast_template: Optional[Dict[str, Any]]
    ) -> Set[str]:
        """Extract target tree-sitter node types from AST template."""
        if not ast_template:
            return set()

        required_nodes = ast_template.get("required_nodes", [])

        # Handle JSON string
        if isinstance(required_nodes, str):
            try:
                required_nodes = json.loads(required_nodes)
            except json.JSONDecodeError:
                required_nodes = [n.strip() for n in required_nodes.split(",") if n.strip()]

        target_types = set()
        for node_name in required_nodes:
            if not node_name:
                continue

            node_name_lower = node_name.lower().strip()

            # Check NODE_MAPPING for expanded types
            if node_name_lower in NODE_MAPPING:
                target_types.update(NODE_MAPPING[node_name_lower])
            else:
                # Use the node name directly (it might be a tree-sitter type)
                target_types.add(node_name_lower)
                # Also try without underscores
                target_types.add(node_name_lower.replace("_", ""))

        return target_types

    def _normalize_keywords(
        self,
        keywords: Optional[List[str]]
    ) -> Set[str]:
        """Normalize keywords to lowercase set."""
        if not keywords:
            return set()

        # Handle JSON string
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except json.JSONDecodeError:
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        return {k.lower().strip() for k in keywords if k}

    def _find_matching_nodes(
        self,
        root,
        target_types: Set[str]
    ) -> List[tuple]:
        """
        Find all nodes matching target types.

        Returns:
            List of (node, matched_type) tuples
        """
        matches = []
        stack = [root]

        while stack:
            node = stack.pop()
            node_type_lower = node.type.lower()

            if node_type_lower in target_types or node.type in target_types:
                matches.append((node, node.type))

            stack.extend(node.children)

        return matches

    def _find_keyword_lines(
        self,
        code: str,
        keywords: Set[str]
    ) -> List[tuple]:
        """
        Find lines containing keywords.

        Returns:
            List of (line_number, keyword) tuples (1-indexed)
        """
        matches = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower:
                    matches.append((i, keyword))
                    break  # Only one match per line

        return matches

    def _get_label_for_type(self, node_type: str) -> str:
        """Get Chinese label for a node type."""
        labels = {
            # Control flow
            "if_statement": "条件判断",
            "for_statement": "for 循环",
            "enhanced_for_statement": "增强 for 循环",
            "while_statement": "while 循环",
            "do_statement": "do-while 循环",
            "switch_statement": "switch 语句",
            "switch_expression": "switch 表达式",
            "break_statement": "break 语句",
            "continue_statement": "continue 语句",
            "return_statement": "return 语句",

            # Exception handling
            "try_statement": "try-catch 块",
            "catch_clause": "异常捕获",
            "finally_clause": "finally 块",
            "throw_statement": "抛出异常",
            "throws": "throws 声明",

            # Class structure
            "class_declaration": "类声明",
            "interface_declaration": "接口声明",
            "enum_declaration": "枚举声明",
            "method_declaration": "方法声明",
            "constructor_declaration": "构造方法",
            "field_declaration": "字段声明",

            # OOP
            "extends_clause": "继承",
            "superclass": "父类",
            "implements_clause": "实现接口",

            # Functional
            "lambda_expression": "Lambda 表达式",
            "method_reference": "方法引用",

            # Generics
            "type_arguments": "泛型参数",
            "type_parameter": "类型参数",
            "wildcard": "通配符",

            # Annotations
            "annotation": "注解",
            "marker_annotation": "标记注解",

            # Creation
            "object_creation_expression": "对象创建",
            "array_creation_expression": "数组创建",

            # Invocation
            "method_invocation": "方法调用",
            "field_access": "字段访问",
            "array_access": "数组访问",

            # Synchronization
            "synchronized_statement": "同步块",
        }
        return labels.get(node_type, node_type.replace("_", " ").title())


# Singleton instance
_highlight_service: Optional[HighlightService] = None


def get_highlight_service() -> HighlightService:
    """Get singleton HighlightService instance."""
    global _highlight_service
    if _highlight_service is None:
        _highlight_service = HighlightService()
    return _highlight_service
