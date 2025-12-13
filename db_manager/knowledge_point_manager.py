# knowledge_point_manager.py
import json


def insert_knowledge_points(conn):
    """
    向数据库中插入预置的知识点数据。
    使用 INSERT IGNORE 来避免重复插入导致的错误。
    """
    with conn.cursor() as c:
        points = [
            (1, "Java", None, 0, '{}', '["java", "programming language"]'),
            (10, "Java 基础", 1, 1, '{}', '["core java", "basics"]'),
            (20, "集合框架", 1, 1, '{}', '["jcf", "java collection framework", "data structures"]'),
            (101, "数据类型", 10, 2, '{"template": "PrimitiveType", "details": ["int", "double", "boolean"]}',
             '["primitive types", "variables", "int", "char"]'),
            (102, "流程控制", 10, 2, '{}', '["control flow", "if", "else", "switch"]'),
            (1021, "条件语句", 102, 3, '{"template": "IfStatement"}', '["if-else", "conditional"]'),
            (1022, "循环语句", 102, 3, '{"template": "ForStatement"}', '["for", "while", "loop", "iteration"]'),
            (201, "List", 20, 2, '{"template": "Declare<List>"}', '["list", "arraylist", "linkedlist", "ordered"]'),
            (202, "Set", 20, 2, '{"template": "Declare<Set>"}', '["set", "hashset", "treeset", "unique"]')
        ]

        sql = "INSERT IGNORE INTO knowledge_points (id, name, parent_id, level, ast_template, keywords) VALUES (%s, %s, %s, %s, %s, %s)"
        c.executemany(sql, points)

    print("[Knowledge Manager] 预置知识点数据已插入。")


def display_knowledge_point_tree(conn):
    """
    使用 WITH RECURSIVE 查询所有知识点，并以树状结构在控制台打印。
    """
    with conn.cursor() as c:
        recursive_query = """
                          WITH RECURSIVE KnowledgeHierarchy AS (SELECT id, \
                                                                       name, \
                                                                       parent_id, \
                                                                       level, \
                                                                       0                      AS depth, \
                                                                       CAST(id AS CHAR(1000)) AS sort_path \
                                                                FROM knowledge_points \
                                                                WHERE parent_id IS NULL \
                                                                UNION ALL \
                                                                SELECT kp.id, \
                                                                       kp.name, \
                                                                       kp.parent_id, \
                                                                       kp.level, \
                                                                       kh.depth + 1, \
                                                                       CONCAT(kh.sort_path, '/', kp.id) \
                                                                FROM knowledge_points AS kp \
                                                                         JOIN KnowledgeHierarchy AS kh ON kp.parent_id = kh.id)
                          SELECT id, name, parent_id, level, depth \
                          FROM KnowledgeHierarchy \
                          ORDER BY sort_path; \
                          """
        c.execute(recursive_query)
        all_nodes = c.fetchall()

        if not all_nodes:
            print("数据库中没有知识点数据。")
            return

        print("\n--- 知识点层级结构 ---")
        for node in all_nodes:
            node_id, name, _, level, depth = node
            indent = "    " * depth
            print(f"{indent}- {name} (ID: {node_id}, Level: {level})")
