import tree_sitter_java
from tree_sitter import Language, Parser
import os
import json

JAVA_LANGUAGE = Language(tree_sitter_java.language())
parser = Parser(JAVA_LANGUAGE)


class CodeAnalyzer:
    def __init__(self):
        # 常见Java关键字列表用于过滤
        self.java_keywords = set(["public", "private", "protected", "class", "void", "static", "final",
                                  "try", "catch", "throw", "if", "else", "for", "while", "return", "new", "import"])

    def analyze_file(self, java_code: str):
        """
        输入完整的Java文件代码，返回切割后的片段及其特征
        """
        tree = parser.parse(bytes(java_code, "utf8"))
        root = tree.root_node
        snippets = []

        # 遍历根节点，寻找所有的方法声明 (method_declaration)
        # 策略：以 Method 为粒度切割代码
        methods = self._find_nodes_by_type(root, "method_declaration")

        for method_node in methods:
            # 1. 获取代码内容和位置
            start = method_node.start_point[0]
            end = method_node.end_point[0]
            content = java_code[method_node.start_byte: method_node.end_byte]

            # 2. 提取AST特征 (该片段包含哪些类型的节点)
            # 展平树结构，获取所有节点类型列表
            ast_types = self._extract_ast_types(method_node)

            # 3. 提取关键字
            keywords = self._extract_keywords(method_node, java_code)

            # 4. 计算难度 (简单模型：圈复杂度近似值)
            difficulty = self._calculate_complexity(ast_types, method_node.end_point[0] - method_node.start_point[0])

            snippets.append({
                "start_line": start + 1,
                "end_line": end + 1,
                "content": content,
                "ast_features": list(set(ast_types)),  # 去重存储
                "keywords": list(keywords),
                "difficulty": difficulty
            })

        return snippets

    def _find_nodes_by_type(self, node, type_name):
        found = []
        if node.type == type_name:
            found.append(node)
        for child in node.children:
            found.extend(self._find_nodes_by_type(child, type_name))
        return found

    def _extract_ast_types(self, node):
        types = [node.type]
        for child in node.children:
            types.extend(self._extract_ast_types(child))
        return types

    def _extract_keywords(self, node, full_code):
        # 简单实现：提取叶子节点中的文本，如果是关键字则保留
        keywords = set()

        def traverse(n):
            if len(n.children) == 0:  # 叶子节点
                text = full_code[n.start_byte: n.end_byte]
                if text in self.java_keywords:
                    keywords.add(text)
            else:
                for child in n.children:
                    traverse(child)

        traverse(node)
        return keywords

    def _calculate_complexity(self, ast_types, lines):
        # 简单的圈复杂度计算：起步1分 + 分支循环节点数
        complexity_nodes = ['if_statement', 'for_statement', 'while_statement', 'case_label', 'catch_clause',
                            'binary_expression']
        cc = 1
        for t in ast_types:
            if t in complexity_nodes:
                cc += 1

        # 归一化难度到 0.0 - 1.0 (假设 CC>10 或 行数>50 为满分)
        norm_score = min(1.0, (cc * 0.5 + lines * 0.1) / 10.0)
        return round(norm_score, 2)

