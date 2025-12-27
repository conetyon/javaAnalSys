# config.py
import os
import yaml

# 定位 yaml 文件路径
# 1. 获取当前文件(config.py)所在的目录
# 结果应该是: D:\bupt-codes\graduation-design\java-ana-mvp
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. 拼接相对路径
# os.path.join 会自动根据操作系统处理斜杠
YAML_PATH = os.path.join(BASE_DIR, 'config', 'db.yaml')


def load_db_name():
    """从 yaml 文件中解析数据库名称"""
    default_name = "javalearningsys"  # 兜底值

    if not os.path.exists(YAML_PATH):
        print(f"[Config] Warning: {YAML_PATH} not found. Using default.")
        return default_name

    try:
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 根据你的 yaml 结构：
        # db:
        #   javalearningsys:  <-- 我们要提取这个键名
        #     host: ...

        db_config = data.get('db', {})
        if db_config:
            # 获取字典的第一个键名
            first_db_key = list(db_config.keys())[0]
            return first_db_key

    except Exception as e:
        print(f"[Config] Error loading yaml: {e}")

    return default_name


# 这里是“单一事实来源”
# 当其他文件 import config 时，代码会自动执行 load_db_name() 并赋值
DB_NAME = load_db_name()
