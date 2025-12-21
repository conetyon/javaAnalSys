import tree_sitter_java
from tree_sitter import Language, Parser
from .constants import JAVA_KEYWORDS, COMPLEXITY_NODES
from .utils import find_nodes_by_type, extract_ast_types


class JavaAnalyzer:
    def __init__(self):
        # 初始化 Parser
        self.language = Language(tree_sitter_java.language())
        self.parser = Parser(self.language)
        self.keywords = JAVA_KEYWORDS

    def analyze_file(self, java_code: str):
        code_bytes = java_code.encode("utf8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node
        snippets = []

        methods = find_nodes_by_type(root, "method_declaration")

        for method_node in methods:
            start = method_node.start_point[0]
            end = method_node.end_point[0]

            # 使用 bytes 切片后解码
            content = code_bytes[method_node.start_byte: method_node.end_byte].decode("utf8")

            ast_types = extract_ast_types(method_node)
            keywords_found = self._extract_keywords(method_node, code_bytes)

            difficulty = self._calculate_complexity(
                ast_types,
                method_node.end_point[0] - method_node.start_point[0]
            )

            snippets.append({
                "start_line": start + 1,
                "end_line": end + 1,
                "content": content,
                "ast_features": list(set(ast_types)),
                "keywords": list(keywords_found),
                "difficulty": difficulty
            })

        return snippets

    def _extract_keywords(self, node, full_code_bytes):
        found = set()

        # 定义内部递归函数
        def traverse(n):
            if len(n.children) == 0:
                text = full_code_bytes[n.start_byte: n.end_byte].decode("utf8")
                if text in self.keywords:
                    found.add(text)
            else:
                for child in n.children:
                    traverse(child)

        traverse(node)
        return found

    def _calculate_complexity(self, ast_types, lines):
        cc = 1
        for t in ast_types:
            if t in COMPLEXITY_NODES:
                cc += 1
        norm_score = min(1.0, (cc * 0.5 + lines * 0.1) / 10.0)
        return round(norm_score, 2)
