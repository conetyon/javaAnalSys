import os
import yaml
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, jsonify, request
from flask_cors import CORS # 导入CORS

# --- 1. 配置加载与数据库连接 ---

def load_db_config():
    """从 config.yaml 加载数据库配置"""
    config_path = "../config/config.yaml"
    if not os.path.exists(config_path):
        # 在Flask应用上下文中，使用app.logger来记录错误会更好
        # 但在启动阶段，直接抛出异常是合适的
        raise FileNotFoundError(f"配置文件 {config_path} 未找到！")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config['database']

def get_connection():
    """获取一个数据库连接"""
    try:
        yaml_conf = load_db_config()
        db_config = {
            "host": yaml_conf['host'],
            "port": yaml_conf.get('port', 3306),
            "user": yaml_conf['user'],
            "password": str(yaml_conf['password']),
            "database": yaml_conf['db_name'],
            "charset": "utf8mb4",
        }
        return pymysql.connect(**db_config)
    except Exception as e:
        # 在应用启动或连接获取阶段打印错误
        print(f"数据库连接失败: {e}")
        raise

# --- 2. Flask 应用和 API ---

app = Flask(__name__)
# 关键：为整个应用启用CORS，允许来自任何源的请求。
# 在生产环境中，你应该更精确地指定来源，例如: CORS(app, origins="http://localhost:3000")
CORS(app)


def list_to_tree(data):
    """将扁平的、包含 parent_id 的列表转换为嵌套的树状结构"""
    if not data:
        return []

    node_map = {item['id']: item for item in data}

    for node in node_map.values():
        node['children'] = []
        # 为前端组件适配字段
        node['title'] = node['name']
        node['key'] = node['id']

    tree = []
    for node in node_map.values():
        if node['parent_id'] is not None and node['parent_id'] in node_map:
            parent_node = node_map[node['parent_id']]
            parent_node['children'].append(node)
        else:
            # 根节点
            tree.append(node)

    return tree


@app.route('/api/knowledge-tree', methods=['GET'])
def get_knowledge_tree():
    """API接口：获取完整的知识点树状结构"""
    conn = None
    try:
        conn = get_connection()
        # 使用字典光标，这样 fetchall() 返回的是字典列表
        with conn.cursor(DictCursor) as c:
            recursive_query = """
            WITH RECURSIVE KnowledgeHierarchy AS (
                -- 初始部分: 找到所有根节点
                SELECT id, name, parent_id, level, CAST(id AS CHAR(1000)) AS sort_path
                FROM knowledge_points
                WHERE parent_id IS NULL

                UNION ALL

                -- 递归部分: 查找子节点
                SELECT kp.id, kp.name, kp.parent_id, kp.level, CONCAT(kh.sort_path, '/', kp.id)
                FROM knowledge_points AS kp
                JOIN KnowledgeHierarchy AS kh ON kp.parent_id = kh.id
            )
            -- 最终查询: 从递归结果中选出所有数据并排序
            SELECT id, name, parent_id, level
            FROM KnowledgeHierarchy
            ORDER BY sort_path;
            """
            c.execute(recursive_query)
            flat_list = c.fetchall()

        # 将扁平列表转换为嵌套树状JSON
        tree_data = list_to_tree(flat_list)

        return jsonify(tree_data)

    except Exception as e:
        app.logger.error(f"获取知识树时发生错误: {e}")
        return jsonify({"error": "服务器内部错误"}), 500
    finally:
        if conn:
            conn.close()


# --- 3. 启动应用 ---
if __name__ == "__main__":
    # 直接运行此脚本即可启动服务
    # host='0.0.0.0' 允许从局域网内的其他机器访问
    # debug=True 会在代码更改后自动重启服务，并提供详细的错误页面
    app.run(host='0.0.0.0', port=5000, debug=True)
