import sqlite3
import json

DB_NAME = "javalearningsys.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. 知识点表 (支持树形结构)
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_points
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY,
                     name
                     TEXT
                     NOT
                     NULL,
                     parent_id
                     INTEGER,
                     level
                     INTEGER, -- 0:领域, 1:模块, 2:知识点
                     ast_template
                     TEXT,    -- JSON: 定义该知识点的AST模式
                     keywords
                     TEXT,    -- JSON: 关联关键字列表
                     semantic_vec
                     BLOB     -- 预留: 语义向量
                 )''')

    # 2. 代码文件表 (元数据)
    c.execute('''CREATE TABLE IF NOT EXISTS code_files
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY,
                     filename
                     TEXT,
                     filepath
                     TEXT,
                     content
                     TEXT
                 )''')

    # 3. 代码片段表 (实际匹配单元)
    c.execute('''CREATE TABLE IF NOT EXISTS code_snippets
    (
        id
        INTEGER
        PRIMARY
        KEY,
        file_id
        INTEGER,
        start_line
        INTEGER,
        end_line
        INTEGER,
        content
        TEXT,
        complexity_score
        REAL, -- 难度：圈复杂度/行数综合计算
        ast_features
        TEXT, -- JSON: 提取到的AST节点类型列表
        keywords
        TEXT, -- JSON: 提取到的关键字
        semantic_vec
        BLOB, -- 预留
        FOREIGN
        KEY
                 (
        file_id
                 ) REFERENCES code_files
                 (
                     id
                 )
        )''')

    conn.commit()
    return conn


# 预置基线数据 (DML) - 模拟 "DML形式给一份"
def insert_baseline_data(conn):
    c = conn.cursor()

    # --- 1. 插入知识点: "异常处理 (Try-Catch)" ---
    # 定义AST模板: 只有当AST中包含 try_statement 和 catch_clause 时才匹配
    ast_tpl = json.dumps({
        "required_nodes": ["try_statement", "catch_clause"],
        "structure": "nested"
    })
    keywords = json.dumps(["try", "catch", "Exception", "throw"])

    c.execute(
        "INSERT OR IGNORE INTO knowledge_points (id, name, parent_id, level, ast_template, keywords) VALUES (?, ?, ?, ?, ?, ?)",
        (101, "Exception Handling", 10, 2, ast_tpl, keywords))

    # --- 2. 插入代码文件 (假设已存在) ---
    c.execute("INSERT OR IGNORE INTO code_files (id, filename, content) VALUES (1, 'Demo.java', 'Wrapper Content')")

    # --- 3. 插入基线代码片段 (用于测试算法无需解析) ---
    # 片段A: 一个完美的 Try-Catch 示例
    code_a = """public void readFile() {
        try {
            File f = new File("test.txt");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }"""
    # 这是一个 Try-Catch 结构
    c.execute(
        "INSERT OR IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (?, ?, ?, ?, ?)",
        (1, code_a, 0.2, json.dumps(["method_declaration", "try_statement", "catch_clause"]),
         json.dumps(["public", "void", "try", "catch", "new"])))

    # 片段B: 一个普通的计算方法 (干扰项)
    code_b = """public int add(int a, int b) {
        return a + b;
    }"""
    c.execute(
        "INSERT OR IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (?, ?, ?, ?, ?)",
        (1, code_b, 0.1, json.dumps(["method_declaration", "return_statement"]),
         json.dumps(["public", "int", "return"])))

    conn.commit()
    print("[DB] Database initialized and baseline data inserted.")


if __name__ == "__main__":
    conn = init_db()
    insert_baseline_data(conn)
    conn.close()
