# src/matching/utils.py
import json
import re


def safe_read_json(raw, default=None):
    """
    安全读取 JSON 字符串/字节，解析失败时返回 default。

    参数:
        raw: str / bytes / bytearray / None
        default: 解析失败时返回的默认值（默认 {}）
    """
    if default is None:
        default = {}
    if raw is None:
        return default
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="ignore")
        return json.loads(raw)
    except Exception:
        return default


def tokenize_to_set(tokens):
    """
    将输入转换为小写的去重 token 集合。

    支持:
        - None -> 空集合
        - 字节串 -> 按 UTF-8 解码后作为一个 token
        - 字符串 -> 视为一个整体 token（不会按字符拆分）
        - 其他可迭代对象 -> 逐个元素转为字符串并归一化

    任何 token 会先 strip，再转换为小写；空字符串会被忽略。
    """
    out = set()
    if tokens is None:
        return out

    # bytes / bytearray 先整体解码
    if isinstance(tokens, (bytes, bytearray)):
        try:
            tokens = tokens.decode("utf-8", errors="ignore")
        except Exception:
            tokens = str(tokens)

    # 单个字符串视为一个 token
    if isinstance(tokens, str):
        tokens = [tokens]

    for t in tokens:
        if isinstance(t, (bytes, bytearray)):
            try:
                t = t.decode("utf-8", errors="ignore")
            except Exception:
                t = str(t)
        if not isinstance(t, str):
            t = str(t)
        s = t.strip().lower()
        if s:
            out.add(s)
    return out


# 低价值/符号类 AST token（在 AST 匹配中剔除）
_PUNCTUATION_TOKENS = {
    "{", "}", "(", ")", ";", ".", ",", ":", "\"", "'", "\\", "[", "]"
}
_OPERATOR_TOKENS = {
    "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=",
    "+", "-", "*", "/", "%", "&&", "||", "!", "==", "!=", ">", "<", ">=", "<=", "="
}
_LOW_VALUE_AST_TOKENS = {
    "string_literal", "string_fragment", "decimal_integer_literal", "hex_integer_literal",
    "octal_integer_literal", "binary_integer_literal", "floating_point_literal",
    "null_literal", "comment"
}


def sanitize_ast_nodes(nodes):
    """
    过滤掉低价值/符号类 AST token，保留语义节点与类型/构造相关标识。

    返回：清洗后的去重小写集合
    """
    raw = tokenize_to_set(nodes)
    cleaned = set()
    for tok in raw:
        # 数字或空白
        if not tok or re.fullmatch(r"\d+", tok):
            continue
        # 单字符或双字符的纯标点/操作符（简单防御）
        if tok in _PUNCTUATION_TOKENS or tok in _OPERATOR_TOKENS:
            continue
        if tok in _LOW_VALUE_AST_TOKENS:
            continue
        cleaned.add(tok)
    return cleaned