import pymysql
import json
import yaml  # 新增
import os

DB_NAME = "javalearningsys"  # 保持变量名兼容


# --- 1. 加载配置的函数 ---
def load_db_config():
    # 确保配置文件存在
    if not os.path.exists("config/config.yaml"):
        raise FileNotFoundError("配置文件 config/config.yaml 未找到！")

    with open("config/config.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config['database']


# --- 2. 构建 PyMySQL 需要的参数字典 ---
# 加载 YAML 配置
yaml_conf = load_db_config()
# 转换为 pymysql.connect 需要的参数格式
DB_CONFIG = {
    "host": yaml_conf['host'],
    "port": yaml_conf.get('port', 3306),
    "user": yaml_conf['user'],
    "password": str(yaml_conf['password']),  # 确保密码是字符串
    "database": yaml_conf['db_name'],
    "charset": "utf8mb4",
    "autocommit": True
}

def get_connection():
    # 确保连接时指定数据库，如果数据库不存在，需要先创建数据库（此处假设库已存在）
    return pymysql.connect(**DB_CONFIG)


def init_db():
    # 初始连接不指定数据库，先尝试创建数据库（防止报错）
    try:
        temp_config = DB_CONFIG.copy()
        db_name = temp_config.pop('database')
        conn = pymysql.connect(**temp_config)
        c = conn.cursor()
        c.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.close()
    except Exception as e:
        print(f"Warning checking database: {e}")

    # 正式连接
    conn = get_connection()
    c = conn.cursor()

    # 1. 知识点表 (支持树形结构)
    # MySQL需要显式指定 AUTO_INCREMENT
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_points
                 (
                     id
                     INT
                     PRIMARY
                     KEY
                     AUTO_INCREMENT,
                     name
                     TEXT
                     NOT
                     NULL,
                     parent_id
                     INTEGER,
                     level
                     INTEGER, -- 0:领域, 1:模块, 2:知识点
                     ast_template
                     TEXT,    -- JSON
                     keywords
                     TEXT,    -- JSON
                     semantic_vec
                     BLOB     -- 预留
                 )''')

    # 2. 代码文件表 (元数据)
    c.execute('''CREATE TABLE IF NOT EXISTS code_files
                 (
                     id
                     INT
                     PRIMARY
                     KEY
                     AUTO_INCREMENT,
                     filename
                     TEXT,
                     filepath
                     TEXT,
                     content
                     LONGTEXT
                 )''')

    # 3. 代码片段表 (实际匹配单元)
    c.execute('''CREATE TABLE IF NOT EXISTS code_snippets
    (
        id
        INT
        PRIMARY
        KEY
        AUTO_INCREMENT,
        file_id
        INTEGER,
        start_line
        INTEGER,
        end_line
        INTEGER,
        content
        LONGTEXT,
        complexity_score
        REAL,
        ast_features
        TEXT, -- JSON
        keywords
        TEXT, -- JSON
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


# 预置基线数据 (DML)
def insert_baseline_data(conn):
    c = conn.cursor()

    # --- 1. 插入知识点 ---
    ast_tpl = json.dumps({
        "required_nodes": ["try_statement", "catch_clause"],
        "structure": "nested"
    })
    keywords = json.dumps(["try", "catch", "Exception", "throw"])

    # MySQL语法: 使用 %s 并在 INSERT IGNORE 中指定主键插入
    c.execute(
        "INSERT IGNORE INTO knowledge_points (id, name, parent_id, level, ast_template, keywords) VALUES (%s, %s, %s, %s, %s, %s)",
        (101, "Exception Handling", 10, 2, ast_tpl, keywords))

    # --- 2. 插入代码文件 ---
    c.execute("INSERT IGNORE INTO code_files (id, filename, content) VALUES (%s, %s, %s)",
              (1, 'Demo.java', 'Wrapper Content'))

    # --- 3. 插入基线代码片段 ---
    code_a = """public void readFile() {
        try {
            File f = new File("test.txt");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }"""

    c.execute(
        "INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
        (1, code_a, 0.2, json.dumps(["method_declaration", "try_statement", "catch_clause"]),
         json.dumps(["public", "void", "try", "catch", "new"])))

    code_b = """public int add(int a, int b) {
        return a + b;
    }"""
    c.execute(
        "INSERT IGNORE INTO code_snippets (file_id, content, complexity_score, ast_features, keywords) VALUES (%s, %s, %s, %s, %s)",
        (1, code_b, 0.1, json.dumps(["method_declaration", "return_statement"]),
         json.dumps(["public", "int", "return"])))

    conn.commit()
    print("[DB] Database initialized and baseline data inserted.")


if __name__ == "__main__":
    conn = init_db()
    insert_baseline_data(conn)
    conn.close()
