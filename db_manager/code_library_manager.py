# code_library_manager.py
import json

def insert_baseline_code_data(conn):
    """
    向数据库中插入预置的代码文件和代码片段数据。
    """
    with conn.cursor() as c:
        # 1. 插入代码文件元数据
        c.execute("INSERT IGNORE INTO code_files (id, filename, content) VALUES (%s, %s, %s)",
                  (1, 'Demo.java', 'Wrapper Content'))

        # 2. 插入基线代码片段
        snippets = [
            (1, """public void readFile() {
        try {
            File f = new File("test.txt");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }""", 0.2, json.dumps(["method_declaration", "try_statement", "catch_clause"]),
             json.dumps(["public", "void", "try", "catch", "new"])),

            (1, """public int add(int a, int b) {
        return a + b;
    }""", 0.1, json.dumps(["method_declaration", "return_statement"]),
             json.dumps(["public", "int", "return"]))
        ]

        sql = "INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)"
        c.executemany(sql, snippets)

    print("[Code Library Manager] 预置代码数据已插入。")


def save_analyzed_results(conn, filename, file_content, snippets):
    """
    将一个文件的分析结果（文件本身和提取的代码片段）保存到数据库。
    这是一个事务性操作。
    :param conn: 数据库连接对象
    :param filename: 原始文件名
    :param file_content: 原始文件内容
    :param snippets: CodeAnalyzer返回的代码片段列表
    """
    with conn.cursor() as c:
        # 1. 插入 code_files 表，获取新生成的文件ID
        c.execute("INSERT INTO code_files (filename, content) VALUES (%s, %s)",
                  (filename, file_content))
        file_id = conn.insert_id()  # 获取刚刚插入行的自增 ID
        if not snippets:
            print(f"[Code Library Manager] 文件 '{filename}' 中未检测到可保存的片段。")
            return
        # 2. 准备并批量插入 code_snippets 表
        snippets_to_insert = []
        for s in snippets:
            snippets_to_insert.append((
                file_id,
                s['start_line'],
                s['end_line'],
                s['content'],
                s['difficulty'],
                json.dumps(s['ast_features']),
                json.dumps(s['keywords'])
            ))

        sql = """
              INSERT INTO code_snippets
              (file_id, start_line, end_line, content, complexity_score, ast_features, keywords)
              VALUES (%s, %s, %s, %s, %s, %s, %s) \
              """
        c.executemany(sql, snippets_to_insert)

    print(f"[Code Library Manager] 已成功保存 '{filename}' (ID: {file_id}) 及其 {len(snippets)} 个代码片段。")