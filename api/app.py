# api/app.py
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, jsonify
from flask_cors import CORS
import config

# --- 引入项目现有的工具类 ---
from lib.client.db import MySQLClient  # 数据库工具
from lib.globals import api_logger as log  # API 专用日志

app = Flask(__name__)
# 允许跨域
CORS(app)


def list_to_tree(data):
    """
    工具函数：将扁平列表转换为树状结构
    """
    if not data:
        return []

    # 建立 id -> node 的映射
    node_map = {item['id']: item for item in data}

    for node in node_map.values():
        node['children'] = []
        # 前端组件适配字段 (Ant Design / Element UI 等常用格式)
        node['title'] = node['name']
        node['key'] = node['id']

    tree = []
    for node in node_map.values():
        parent_id = node['parent_id']
        # 如果有父节点且父节点存在于结果集中，则加入父节点的 children
        if parent_id is not None and parent_id in node_map:
            parent_node = node_map[parent_id]
            parent_node['children'].append(node)
        else:
            # 否则视为根节点
            tree.append(node)

    return tree


@app.route('/api/knowledge-tree', methods=['GET'])
def get_knowledge_tree():
    """
    API接口：获取完整的知识点树状结构
    """
    log.info("[GET] /api/knowledge-tree - 开始获取知识点树结构")

    try:
        with MySQLClient(db=config.DB_NAME) as client:
            sql = """
                  WITH RECURSIVE KnowledgeHierarchy \
                                     AS (SELECT id, name, parent_id, level, CAST(id AS CHAR(1000)) AS sort_path \
                                         FROM knowledge_points \
                                         WHERE parent_id IS NULL \
                                         UNION ALL \
                                         SELECT kp.id, kp.name, kp.parent_id, kp.level, CONCAT(kh.sort_path, '/', kp.id) \
                                         FROM knowledge_points AS kp \
                                                  JOIN KnowledgeHierarchy AS kh ON kp.parent_id = kh.id)
                  SELECT id, name, parent_id, level
                  FROM KnowledgeHierarchy
                  ORDER BY sort_path; \
                  """

            # 使用默认 cursor 即可
            cursor = client._conn.cursor()
            cursor.execute(sql)

            # === 【修改重点开始】 ===
            # 1. 获取所有列名 (例如: ['id', 'name', 'parent_id', 'level'])
            columns = [col[0] for col in cursor.description]

            # 2. 获取原始数据
            raw_rows = cursor.fetchall()

            # 3. 将 (值1, 值2...) 强制转为 {'列1': 值1, '列2': 值2...}
            flat_list = []
            for row in raw_rows:
                # 兼容性处理：如果已经是字典(DictCursor生效)则直接用，如果是元组则转换
                if isinstance(row, dict):
                    flat_list.append(row)
                else:
                    flat_list.append(dict(zip(columns, row)))

            cursor.close()
            # === 【修改重点结束】 ===
        # 数据转换
        tree_data = list_to_tree(flat_list)

        count = len(flat_list)
        log.info(f"[GET] /api/knowledge-tree - 成功获取 {count} 个知识点节点")
        return jsonify({
            "code": 200,
            "message": "success",
            "data": tree_data
        })
    except Exception as e:
        log.error(f"[GET] /api/knowledge-tree - 异常: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "error": str(e)
        }), 500


# --- 启动入口 ---
if __name__ == "__main__":
    log.info("Starting Flask API Service on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
