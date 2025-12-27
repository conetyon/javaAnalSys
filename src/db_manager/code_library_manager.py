# db_manager/code_library_manager.py
import json
from .base import BaseManager


class CodeLibraryManager(BaseManager):
    """
    负责代码文件(code_files)和代码片段(code_snippets)的数据库操作。
    """

    def insert_baseline_code_data(self):
        """
        插入预置的基线代码数据。
        使用 INSERT IGNORE 处理 ID 冲突，但建议在开发初期使用 TRUNCATE 清理表。
        """
        statements = [
            # 使用 INSERT IGNORE 避免主键冲突
            ("INSERT IGNORE INTO code_files (id, filename, content) VALUES (%s, %s, %s)",
             (1, 'Demo.java', 'Wrapper Content')),

            # 这里的 snippets 硬编码了 file_id=1
            ("INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
             (1, 'public void readFile() {...}', 0.2, json.dumps(["method_declaration"]),
              json.dumps(["try", "catch"]))),

            ("INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
             (1, 'public int add(int a, int b) { return a + b; }', 0.1, json.dumps(["return_statement"]),
              json.dumps(["return"]))),

            ("INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
             (1, 'set', 0.1, json.dumps(["set"]),
              json.dumps(["set"]))),

            ("INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
             (1, 'set int', 0.8, json.dumps(["set"]),
              json.dumps(["set"])))
        ]

        client = self._get_client()
        client.execute_transaction(statements)
        print("[Code Library Manager] 预置代码数据已插入。")

    def save_analyzed_results(self, filename: str, file_content: str, snippets: list):
        """
        幂等地保存文件分析结果：
        1. 检查文件是否存在。
        2. 【新增优化】如果文件存在且内容未变，直接跳过（防止ID跳变）。
        3. 如果内容变了或文件不存在，执行更新/插入逻辑。
        """
        if not snippets:
            print(f"[Code Library Manager] 文件 '{filename}' 中未检测到可保存的片段，跳过保存。")
            return
        with self._get_client(autocommit=False) as tx:
            cursor = tx._conn.cursor()
            try:
                # 1. 检查文件是否已存在，同时查出旧的内容
                cursor.execute(
                    "SELECT id, content FROM code_files WHERE filename = %s FOR UPDATE",
                    (filename,)
                )
                row = cursor.fetchone()
                file_id = None

                if row:
                    # --- 分支 A: 文件已存在 ---
                    db_id, db_content = row

                    # 【核心修复】比对内容
                    # 如果数据库里的内容 和 当前读取的文件内容 完全一致
                    if db_content == file_content:
                        # 认为无需更新，直接结束，不产生 ID 跳变
                        # print(f"[Code Library Manager] 文件 '{filename}' 内容未变更，跳过数据库写入。")
                        return
                        # 如果内容不一致，说明文件被修改了，需要执行更新逻辑
                    file_id = db_id
                    print(f"[Code Library Manager] 检测到 '{filename}' 内容变更，正在更新数据库...")
                    # 更新文件内容
                    cursor.execute(
                        "UPDATE code_files SET content = %s WHERE id = %s",
                        (file_content, file_id)
                    )
                    # 删除该文件关联的旧片段（因为行号可能都变了，必须删了重存）
                    cursor.execute("DELETE FROM code_snippets WHERE file_id = %s", (file_id,))

                else:
                    # --- 分支 B: 文件不存在，执行插入逻辑 ---
                    cursor.execute(
                        "INSERT INTO code_files (filename, content) VALUES (%s, %s)",
                        (filename, file_content)
                    )
                    file_id = cursor.lastrowid
                    if not file_id:
                        raise ValueError(f"无法获取插入的文件 ID: {filename}")
                # 2. 准备批量片段数据
                snippets_to_insert = [
                    (
                        file_id, s['start_line'], s['end_line'], s['content'], s['difficulty'],
                        json.dumps(s['ast_features']), json.dumps(s['keywords'])
                    )
                    for s in snippets
                ]
                # 3. 批量插入新片段
                # 只有在内容变更 或 新文件 时才会执行到这里，ID 会增加是正常的
                sql = """
                      INSERT INTO code_snippets
                      (file_id, start_line, end_line, content, complexity_score, ast_features, keywords)
                      VALUES (%s, %s, %s, %s, %s, %s, %s) \
                      """
                cursor.executemany(sql, snippets_to_insert)
                print(f"[Code Library Manager] 已保存 '{filename}' (ID: {file_id})，更新 {len(snippets)} 个片段。")
            except Exception as e:
                print(f"[Error] 保存分析结果失败: {e}")
                tx._conn.rollback()
                raise
            finally:
                cursor.close()

    def get_all_snippets(self):
        """
        获取数据库中所有的代码片段
        供 Matcher 使用
        """
        sql = "SELECT * FROM code_snippets"
        client = self._get_client()
        return client.fetch_all(sql)
