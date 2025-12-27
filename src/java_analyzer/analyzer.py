# analyzers/java_analyzer.py
# 说明：
# - 基于 AST 精准抽取三类关键词：语言保留字、API/方法调用（含可控前缀链）、类型与异常名
# - 引入别名归一化（CANONICAL_ALIASES）与短方法白名单（SHORT_METHOD_WHITELIST）
# - 对 Arrays.asList / System.out.println / logger.info / new BufferedReader / catch(IOException) 等可稳定产出关键词
# - 兼容 method_reference（如 System.out::println / String::valueOf）

import tree_sitter_java
from tree_sitter import Language, Parser
from .constants import (
    JAVA_KEYWORDS,
    COMPLEXITY_NODES,
    ALLOWED_PREFIX_PREFIXES,
    SHORT_METHOD_WHITELIST,
    CANONICAL_ALIASES,
)


class JavaAnalyzer:
    def __init__(self):
        # 初始化 Parser（按你的运行环境保持用法）
        self.language = Language(tree_sitter_java.language())
        self.parser = Parser(self.language)

        # 语言关键字与规则配置
        self.kw_lang = JAVA_KEYWORDS
        self.allowed_prefixes = ALLOWED_PREFIX_PREFIXES
        self.short_method_whitelist = SHORT_METHOD_WHITELIST
        self.aliases = CANONICAL_ALIASES

    def analyze_file(self, java_code: str):
        code_bytes = java_code.encode("utf8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node
        snippets = []

        methods = self._find_nodes_by_type(root, "method_declaration")

        for method_node in methods:
            start = method_node.start_point[0]
            end = method_node.end_point[0]

            content = code_bytes[method_node.start_byte: method_node.end_byte].decode("utf8")
            ast_types = self._extract_ast_types(method_node)
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
                "keywords": sorted(list(keywords_found)),
                "difficulty": difficulty
            })

        return snippets

    # ---------------- internal helpers ----------------

    def _extract_keywords(self, node, full_code_bytes):
        found = set()

        def text(n):
            return full_code_bytes[n.start_byte:n.end_byte].decode("utf8")

        def normalize_token(tok: str) -> str:
            """小写 + 别名归一化"""
            low = tok.lower()
            return self.aliases.get(low, low)

        def add(tok: str):
            """收集 token：原样 + 小写 + 归一化"""
            if not tok:
                return
            raw = tok.strip()
            if not raw:
                return
            low = raw.lower()
            canon = self.aliases.get(low, low)
            found.add(raw)
            found.add(low)
            found.add(canon)

        def split_chain(s: str):
            return [p for p in s.split(".") if p]

        def flatten_qualifier(n):
            """
            展开 field_access/scoped_identifier/scoped_type_identifier 为 a.b.c 形式
            """
            if n is None:
                return ""
            t = n.type
            if t == "field_access":
                obj = n.child_by_field_name("object") or (n.children[0] if n.children else None)
                fld = n.child_by_field_name("field")
                left = flatten_qualifier(obj)
                right = text(fld) if fld else ""
                return (left + "." + right) if left and right else (left or right)
            if t in ("scoped_identifier", "scoped_type_identifier"):
                scope = n.child_by_field_name("scope") or (n.children[0] if n.children else None)
                name = n.child_by_field_name("name") or (n.children[-1] if n.children else None)
                left = flatten_qualifier(scope)
                right = text(name) if name else ""
                return (left + "." + right) if left and right else (left or right)
            if t in ("identifier", "type_identifier", "this", "super"):
                return text(n)
            # 回退：拼接 identifier 子节点
            ids = [text(c) for c in n.children if c.type in ("identifier", "type_identifier")]
            return ".".join(ids) if ids else text(n)

        def should_keep_prefix(prefix_parts):
            """
            是否保留前缀（避免变量名前缀噪音）
            - 以大写开头（类型/类名）
            - 在白名单中
            - 特判 System.out / System.err
            - 容忍常见日志变量名 logger/log
            """
            if not prefix_parts:
                return False
            head = prefix_parts[0]
            if not head:
                return False
            if head[0].isupper():
                return True
            if head in self.allowed_prefixes or head.lower() in ("logger", "log"):
                return True
            if head == "System" and (len(prefix_parts) >= 2 and prefix_parts[1] in ("out", "err")):
                return True
            return False

        def add_chain(parts, *, allow_prefix: bool = False, force_full_chain: bool = False):
            """
            添加调用链关键词：
            - 总是添加方法名（最后一段）
            - allow_prefix=True：添加前缀（前两段）与完整链
            - force_full_chain=True：即使不允许前缀，也添加完整链（少量场景：method_reference）
            """
            if not parts:
                return
            # 方法名
            add(parts[-1])

            if len(parts) == 1:
                return

            prefix = parts[:-1]
            prefix_str = ".".join(prefix[:2]) if len(prefix) >= 2 else prefix[0]
            chain_str = ".".join(parts)

            if allow_prefix:
                add(prefix_str)
                add(chain_str)
            elif force_full_chain:
                add(chain_str)
            # else: 不添加链，以免变量名前缀噪音

        def handle_method_invocation(n):
            # name 可为 identifier 或 scoped_identifier（如 Collections.sort）
            name_node = n.child_by_field_name("name")
            obj_node = n.child_by_field_name("object")

            # scoped_identifier 作为 name（如 Arrays.asList）直接作为链
            if name_node and name_node.type in ("scoped_identifier", "scoped_type_identifier"):
                chain = flatten_qualifier(name_node)
                add_chain(split_chain(chain), allow_prefix=True)
                return

            callee = text(name_node) if name_node else ""
            prefix = flatten_qualifier(obj_node) if obj_node else ""
            parts = split_chain(prefix) + ([callee] if callee else [])
            if not parts:
                return
            allow_prefix = should_keep_prefix(parts[:-1])
            # 若方法是短方法白名单，保留完整链（例如 info/printf 等出现在日志或输出）
            force_full_chain = parts[-1] in self.short_method_whitelist
            add_chain(parts, allow_prefix=allow_prefix, force_full_chain=force_full_chain)

        def handle_field_access(n):
            # 保留前两段：如 System.out / LoggerFactory.getLogger
            chain = flatten_qualifier(n)
            parts = split_chain(chain)
            if not parts:
                return
            if should_keep_prefix(parts):
                if len(parts) >= 2:
                    add(".".join(parts[:2]))
                else:
                    add(parts[0])

        def handle_object_creation(n):
            # new BufferedReader(...)
            type_node = n.child_by_field_name("type")
            if not type_node:
                return
            type_chain = flatten_qualifier(type_node)
            if not type_chain:
                return
            add("new")
            add(type_chain)
            last = type_chain.split(".")[-1]
            if last != type_chain:
                add(last)

        def handle_catch_clause(n):
            # catch (IOException | FileNotFoundException e)
            param = n.child_by_field_name("parameter")
            if not param:
                add("catch")
                return
            types = []
            stack = [param]
            while stack:
                cur = stack.pop()
                if cur.type in ("type_identifier", "scoped_type_identifier", "scoped_identifier"):
                    types.append(flatten_qualifier(cur))
                else:
                    stack.extend(cur.children)
            for ty in types:
                add(ty)
                last = ty.split(".")[-1]
                if last != ty:
                    add(last)
            add("catch")

        def handle_throw_statement(n):
            # throw new IOException(...)
            stack = [n]
            while stack:
                cur = stack.pop()
                if cur.type == "object_creation_expression":
                    handle_object_creation(cur)
                else:
                    stack.extend(cur.children)

        def handle_method_reference(n):
            # System.out::println / String::valueOf
            scope = n.child_by_field_name("scope")
            name = n.child_by_field_name("name")
            scope_chain = flatten_qualifier(scope) if scope else ""
            callee = text(name) if name else ""
            parts = split_chain(scope_chain) + ([callee] if callee else [])
            if not parts:
                return
            allow_prefix = should_keep_prefix(parts[:-1])
            # method_reference 一般希望保留完整链
            add_chain(parts, allow_prefix=allow_prefix, force_full_chain=True)

        # DFS
        stack = [node]
        while stack:
            cur = stack.pop()
            t = cur.type
            if t == "method_invocation":
                handle_method_invocation(cur)
            elif t == "field_access":
                handle_field_access(cur)
            elif t == "object_creation_expression":
                handle_object_creation(cur)
            elif t == "catch_clause":
                handle_catch_clause(cur)
            elif t == "throw_statement":
                handle_throw_statement(cur)
            elif t == "method_reference":
                handle_method_reference(cur)
            else:
                # 叶子：语言级保留字
                if len(cur.children) == 0:
                    tok = text(cur)
                    if tok in self.kw_lang:
                        add(tok)

            stack.extend(cur.children)

        return found

    def _calculate_complexity(self, ast_types, lines):
        cc = 1
        for t in ast_types:
            if t in COMPLEXITY_NODES:
                cc += 1
        norm_score = min(1.0, (cc * 0.5 + lines * 0.1) / 10.0)
        return round(norm_score, 2)

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
