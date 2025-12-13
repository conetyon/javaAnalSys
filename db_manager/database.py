# database.py
import pymysql
import yaml
import os

def load_db_config():
    """加载数据库配置"""
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 未找到！")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config['database']

# --- 构建 PyMySQL 需要的参数字典 ---
yaml_conf = load_db_config()
DB_CONFIG = {
    "host": yaml_conf['host'],
    "port": yaml_conf.get('port', 3306),
    "user": yaml_conf['user'],
    "password": str(yaml_conf['password']),
    "database": yaml_conf['db_name'],
    "charset": "utf8mb4",
    "autocommit": True  # 保持自动提交，简化操作
}

def get_connection():
    """获取一个数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def init_db():
    """
    初始化数据库：如果数据库不存在则创建，并创建所有表结构。
    返回一个可用的数据库连接。
    """
    try:
        # 1. 尝试连接时不指定数据库，以便创建数据库
        temp_config = DB_CONFIG.copy()
        db_name = temp_config.pop('database')
        conn = pymysql.connect(**temp_config)
        with conn.cursor() as c:
            c.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        print(f"[DB] 数据库 '{db_name}' 已确保存在。")
    except Exception as e:
        # 如果数据库已存在或因权限问题无法创建，这通常不是致命错误，继续尝试连接
        print(f"[DB-Warning] 检查/创建数据库时出现问题: {e}")

    # 2. 正式连接到指定数据库
    conn = get_connection()
    print("[DB] 数据库连接成功。")

    with conn.cursor() as c:
        # 创建知识点表
        c.execute('''CREATE TABLE IF NOT EXISTS knowledge_points
                     (id INT PRIMARY KEY AUTO_INCREMENT, name TEXT NOT NULL, parent_id INTEGER,
                      level INTEGER, ast_template TEXT, keywords TEXT, semantic_vec BLOB)''')

        # 创建代码文件表
        c.execute('''CREATE TABLE IF NOT EXISTS code_files
                     (id INT PRIMARY KEY AUTO_INCREMENT, filename TEXT, filepath TEXT, content LONGTEXT)''')

        # 创建代码片段表
        c.execute('''CREATE TABLE IF NOT EXISTS code_snippets
                    (id INT PRIMARY KEY AUTO_INCREMENT, file_id INTEGER, start_line INTEGER, end_line INTEGER,
                     content LONGTEXT, complexity_score REAL, ast_features TEXT, keywords TEXT,
                     semantic_vec BLOB, FOREIGN KEY(file_id) REFERENCES code_files(id))''')

    print("[DB] 所有数据表结构已初始化/验证。")
    return conn
