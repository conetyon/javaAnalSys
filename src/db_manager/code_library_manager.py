# src/db_manager/code_library_manager.py
import json
from .base import BaseManager
from lib.globals import core_logger as log


class CodeLibraryManager(BaseManager):
    """
    负责代码文件(code_files)和代码片段(code_snippets)的数据库操作。
    """

    def insert_baseline_code_data(self):
        """
        幂等插入预置的基线代码数据（Demo.java + 若干片段）。
        - 通过 filename 确保单个文件的稳定 file_id（存在则复用，不存在则插入）。
        - 通过 content 作为"片段唯一键"执行 UPDATE-or-INSERT，避免重复插入导致自增主键增长。
        - 不清表，不破坏现有 sample.java 等其他文件数据。
        """
        baseline_filename = "Demo.java"

        # 预置片段（可按需增删改）
        baseline_snippets = [
            # 片段 A：包含 try-catch-finally，能匹配 Try-Catch KP(10001)
            {
                "content": (
                    'public void processFile(String path) { '
                    'try { BufferedReader reader = new BufferedReader(new FileReader(path)); '
                    'String line = reader.readLine(); '
                    'while (line != null) { System.out.println(line); line = reader.readLine(); } '
                    '} catch (FileNotFoundException e) { System.err.println("File missing"); } '
                    'catch (IOException e) { e.printStackTrace(); } '
                    'finally { System.out.println("Done."); } '
                    '}'
                ),
                "complexity": 0.6,
                "ast": ["method_declaration", "try_statement", "catch_clause", "finally_block", "method_invocation"],
                "keywords": ["try", "catch", "finally", "IOException", "FileNotFoundException", "read"],
            },
            # 片段 B：简单 getter，不应匹配 Try-Catch
            {
                "content": 'public String getName() { return "Processor"; }',
                "complexity": 0.1,
                "ast": ["method_declaration", "return_statement", "string_literal"],
                "keywords": ["getter", "return"],
            },
            # 片段 C：for 循环求和，不含 Try-Catch（用于对比）
            {
                "content": (
                    "public int calculate(int n) { if (n < 0) return 0; int sum = 0; "
                    "for (int i=0; i<n; i++) { sum += i; } return sum; }"
                ),
                "complexity": 0.7,
                "ast": [
                    "method_declaration", "if_statement", "for_statement", "variable_declaration",
                    "assignment", "binary_expression", "return_statement", "primitive_type"
                ],
                "keywords": ["for", "sum", "int", "calculate"],
            },
            # 片段 D：占位
            {
                "content": "set int",
                "complexity": 0.2,
                "ast": ["set"],
                "keywords": ["set"],
            },
        ]

        with self._get_client(autocommit=False) as tx:
            cursor = tx._conn.cursor()
            try:
                # 1) 文件幂等：用 filename 锁定文件，存在则复用 ID，不存在则插入
                cursor.execute(
                    "SELECT id FROM code_files WHERE filename = %s ORDER BY id ASC LIMIT 1 FOR UPDATE",
                    (baseline_filename,)
                )
                row = cursor.fetchone()
                if row:
                    file_id = row[0]
                else:
                    cursor.execute(
                        "INSERT INTO code_files (filename) VALUES (%s)",
                        (baseline_filename,)
                    )
                    file_id = cursor.lastrowid
                    if not file_id:
                        raise ValueError("无法获取插入的文件 ID: Demo.java")

                # 2) 片段幂等：以 content 为唯一键，存在则 UPDATE，不存在则 INSERT
                cursor.execute(
                    "SELECT id, content FROM code_snippets WHERE file_id = %s",
                    (file_id,)
                )
                existing_rows = cursor.fetchall() or []
                # 可能存在同 content 的重复行，仅保留第一条用于 update，其余忽略
                existing_map = {}
                for r in existing_rows:
                    r_id, r_content = r
                    if r_content not in existing_map:
                        existing_map[r_content] = r_id

                # 执行 upsert
                for sn in baseline_snippets:
                    content = sn["content"]
                    complexity = sn["complexity"]
                    ast_json = json.dumps(sn.get("ast", []), ensure_ascii=False)
                    kw_json = json.dumps(sn.get("keywords", []), ensure_ascii=False)

                    if content in existing_map:
                        cursor.execute(
                            "UPDATE code_snippets "
                            "SET complexity_score = %s, ast_features = %s, keywords = %s "
                            "WHERE id = %s",
                            (complexity, ast_json, kw_json, existing_map[content])
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (file_id, content, complexity, ast_json, kw_json)
                        )

                tx._conn.commit()
                log.info("预置代码数据已幂等处理完成")

            except Exception as e:
                log.error(f"预置代码数据写入失败: {e}")
                tx._conn.rollback()
                raise
            finally:
                cursor.close()

    def save_analyzed_results(self, filename: str, snippets: list, filepath: str = None):
        """
        幂等地保存文件分析结果：
        1. 检查文件是否存在（通过 filename 或 filepath）。
        2. 若存在则更新片段，不存在则插入。

        Args:
            filename: 文件名
            snippets: 代码片段列表
            filepath: 可选，文件完整路径
        """
        if not snippets:
            log.debug(f"文件 '{filename}' 中未检测到可保存的片段，跳过保存")
            return

        with self._get_client(autocommit=False) as tx:
            cursor = tx._conn.cursor()
            try:
                # 1) 文件幂等：用 filename 查找
                cursor.execute(
                    "SELECT id FROM code_files WHERE filename = %s FOR UPDATE",
                    (filename,)
                )
                row = cursor.fetchone()

                if row:
                    file_id = row[0]
                    log.info(f"文件 '{filename}' 已存在 (ID: {file_id})，更新片段...")
                    cursor.execute("DELETE FROM code_snippets WHERE file_id = %s", (file_id,))
                else:
                    cursor.execute(
                        "INSERT INTO code_files (filename, filepath) VALUES (%s, %s)",
                        (filename, filepath or '')
                    )
                    file_id = cursor.lastrowid
                    if not file_id:
                        raise ValueError(f"无法获取插入的文件 ID: {filename}")

                # 2) 插入新片段
                snippets_to_insert = [
                    (
                        file_id, s.get('start_line'), s.get('end_line'), s.get('content'),
                        s.get('difficulty'), json.dumps(s.get('ast_features', []), ensure_ascii=False),
                        json.dumps(s.get('keywords', []), ensure_ascii=False)
                    )
                    for s in snippets
                ]
                sql = """
                      INSERT INTO code_snippets
                      (file_id, start_line, end_line, content, complexity_score, ast_features, keywords)
                      VALUES (%s, %s, %s, %s, %s, %s, %s)
                      """
                cursor.executemany(sql, snippets_to_insert)
                log.info(f"已保存 '{filename}' (ID: {file_id})，更新 {len(snippets)} 个片段")

                tx._conn.commit()
            except Exception as e:
                log.error(f"保存分析结果失败: {e}")
                tx._conn.rollback()
                raise
            finally:
                cursor.close()

    def get_all_snippets(self, limit: int = None):
        """
        获取数据库中所有的代码片段
        供 Matcher 使用

        Args:
            limit: 可选，限制返回的最大记录数（安全网，防止大表导致 OOM）
        """
        log.debug("[CodeLibraryManager.get_all_snippets] 开始获取所有代码片段")
        sql = "SELECT * FROM code_snippets"
        if limit and limit > 0:
            sql += f" LIMIT {limit}"
            log.warning("[CodeLibraryManager.get_all_snippets] 使用 LIMIT %d 限制结果集", limit)
        client = self._get_client()
        result = client.fetch_all(sql)
        log.info("[CodeLibraryManager.get_all_snippets] 获取到 %d 条代码片段", len(result) if result else 0)
        return result

    def find_snippet_candidates(self, keywords: list, ast_nodes: list, limit: int = 1000):
        """
        根据关键词和 AST 节点预筛选候选代码片段（性能优化）

        策略：
        1. 如果提供了关键词，在 keywords 字段中 LIKE 匹配（JSON 字符串模糊匹配）
        2. 如果提供了 AST 节点，在 ast_features 字段中 LIKE 匹配
        3. 使用 OR 连接，满足任一条件即可（高召回）
        4. LIMIT 限制结果集大小

        Args:
            keywords: 关键词列表（已规范化）
            ast_nodes: AST 节点类型列表
            limit: 最大返回记录数（默认 1000）

        Returns:
            List[Dict]: 匹配的代码片段列表
        """
        log.debug("[CodeLibraryManager.find_snippet_candidates] keywords=%s, ast_nodes=%s, limit=%d",
                  keywords[:3] if keywords else [], ast_nodes[:3] if ast_nodes else [], limit)

        where_conditions = []
        params = []

        # 关键词匹配：在 keywords JSON 字符串中模糊查找
        if keywords:
            # 对每个关键词生成 LIKE 条件（OR 连接）
            keyword_conditions = []
            for kw in keywords[:10]:  # 限制前10个关键词，避免 SQL 过长
                keyword_conditions.append("keywords LIKE %s")
                params.append(f'%"{kw}"%')  # JSON 中关键词以 "keyword" 形式存在

            if keyword_conditions:
                where_conditions.append("(" + " OR ".join(keyword_conditions) + ")")

        # AST 节点匹配：在 ast_features JSON 字符串中模糊查找
        if ast_nodes:
            ast_conditions = []
            for node in ast_nodes[:10]:  # 限制前10个节点
                ast_conditions.append("ast_features LIKE %s")
                params.append(f'%"{node}"%')

            if ast_conditions:
                where_conditions.append("(" + " OR ".join(ast_conditions) + ")")

        # 如果没有任何过滤条件，回退到 get_all_snippets
        if not where_conditions:
            log.warning("[CodeLibraryManager.find_snippet_candidates] 无过滤条件，回退到 get_all_snippets")
            return self.get_all_snippets(limit=limit)

        # 构建 SQL
        sql = "SELECT * FROM code_snippets WHERE " + " OR ".join(where_conditions)
        sql += f" LIMIT {limit}"

        client = self._get_client()
        result = client.fetch_all(sql, params)
        log.info("[CodeLibraryManager.find_snippet_candidates] 预筛选获取 %d 条候选", len(result) if result else 0)
        return result if result else []
