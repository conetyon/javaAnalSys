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
        # 【关键修改1】先将字符串转为字节流，后续所有切片操作都基于这个字节流
        code_bytes = java_code.encode("utf8")

        # 解析时也直接传入字节流
        tree = parser.parse(code_bytes)
        root = tree.root_node
        snippets = []

        # 遍历根节点，寻找所有的方法声明 (method_declaration)
        methods = self._find_nodes_by_type(root, "method_declaration")

        for method_node in methods:
            # 1. 获取代码内容和位置
            start = method_node.start_point[0]
            end = method_node.end_point[0]

            # 【关键修改2】使用字节流切片，再解码回字符串
            # 原来的写法: content = java_code[method_node.start_byte: method_node.end_byte]
            content = code_bytes[method_node.start_byte: method_node.end_byte].decode("utf8")

            # 2. 提取AST特征
            ast_types = self._extract_ast_types(method_node)

            # 3. 提取关键字 (传入字节流)
            # 【关键修改3】传入 code_bytes 而不是 java_code
            keywords = self._extract_keywords(method_node, code_bytes)

            # 4. 计算难度
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

    def _extract_keywords(self, node, full_code_bytes):
        # 【关键修改4】参数名改为 bytes，处理逻辑也适配 bytes
        keywords = set()

        def traverse(n):
            if len(n.children) == 0:  # 叶子节点
                # 从字节流中切取
                text_bytes = full_code_bytes[n.start_byte: n.end_byte]
                # 解码为字符串
                text = text_bytes.decode("utf8")

                if text in self.java_keywords:
                    keywords.add(text)
            else:
                for child in n.children:
                    traverse(child)

        traverse(node)
        return keywords

    def _calculate_complexity(self, ast_types, lines):
        # 简单的圈复杂度计算
        complexity_nodes = ['if_statement', 'for_statement', 'while_statement', 'case_label', 'catch_clause',
                            'binary_expression']
        cc = 1
        for t in ast_types:
            if t in complexity_nodes:
                cc += 1

        norm_score = min(1.0, (cc * 0.5 + lines * 0.1) / 10.0)
        return round(norm_score, 2)
