def find_nodes_by_type(node, type_name):
    """递归查找特定类型的节点"""
    found = []
    if node.type == type_name:
        found.append(node)
    for child in node.children:
        found.extend(find_nodes_by_type(child, type_name))
    return found

def extract_ast_types(node):
    """递归提取所有子节点的 AST 类型"""
    types = [node.type]
    for child in node.children:
        types.extend(extract_ast_types(child))
    return types
