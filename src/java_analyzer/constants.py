# analyzers/constants.py
# 目标：
# 1) 精简语言级关键词，强调结构与异常控制流，减少噪声
# 2) 明确保留的调用前缀白名单，降低变量前缀带来的噪音
# 3) 短方法白名单，确保高教学价值的短词不过滤
# 4) 别名归一化（canonical aliases），提升 KP 与抽取词的一致性
# 5) 可选关键词权重表（暂未在搜索侧使用，预留）

# 仅保留结构性/控制流/异常相关关键字；不含 public/static/final 等修饰符
JAVA_KEYWORDS = {
    # 控制流
    "if", "else", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "return",
    # 异常与资源
    "try", "catch", "finally", "throw", "throws",
    # 其它结构
    "new", "synchronized", "instanceof", "this", "super",
}

# 复杂度相关的节点类型（tree-sitter-java）
COMPLEXITY_NODES = {
    "if_statement", "for_statement", "enhanced_for_statement",
    "while_statement", "do_statement",
    "switch_statement",  # 注意：部分语法版本也有 switch_expression
    "catch_clause", "try_statement", "throw_statement",
    "conditional_expression", "binary_expression",
    "lambda_expression", "method_reference",
    "synchronized_statement", "assert_statement",
}

# 允许保留的调用/类型前缀（减少变量名前缀噪音）
# 判定规则见 analyzer：首段大写（类名）或命中该白名单即保留前缀
ALLOWED_PREFIX_PREFIXES = {
    # 标准库/常见工具
    "System", "Math", "Objects", "Optional",
    "Arrays", "Collections", "Collectors",
    "Files", "Paths", "Pattern", "Matcher",
    "Stream", "IntStream", "LongStream",
    # 日志
    "Logger", "LoggerFactory", "Log", "LOG", "LOGGER", "Slf4j",
}

# 短方法白名单：短词但高价值，确保不过滤
SHORT_METHOD_WHITELIST = {
    "println", "printf", "print",
    "sort", "asList",
    "of", "ofNullable",
    "max", "min",
    "readLine", "close", "flush",
}

# 别名归一化：统一到小写规范形式，减少 KP 与抽取词形差异
# 使用方式：在 analyzer.add(token) 或搜索前，将 token.lower() 过此映射
CANONICAL_ALIASES = {
    # 输出与日志
    "system.out.println": "println",
    "system.err.println": "println",
    "printstacktrace": "printstacktrace",  # 保持原样小写规范
    "logger.info": "log.info",
    "logger.error": "log.error",
    "logger.debug": "log.debug",
    # 集合/数组
    "arrays.aslist": "aslist",
    "collections.sort": "sort",
    # IO/文件
    "files.readalllines": "readalllines",
    "files.lines": "lines",
    # 类型名：统一小写规范形式（匹配时不区分大小写）
    # 这些会在 analyzer 中以原样与小写并存，一般不必特别映射
}

# 停用/低价值标识符：变量名等，遇到时可过滤（长度+白名单组合判定）
STOP_IDENTIFIERS = {
    "i", "j", "k", "t", "tmp", "temp", "tmp1", "tmp2",
    "s", "str", "string", "ch", "c",
    "n", "num", "val", "value",
    "obj", "item", "it", "res", "ret", "flag",
    "args", "arg",
}

# （可选）关键词权重表：用于未来的加权召回/排序
# 注意：当前搜索侧可能未使用该表，建议后续在 SearchService 中启用
KEYWORD_WEIGHTS = {
    "println": 3.0,
    "printstacktrace": 2.5,
    "ioexception": 2.0,
    "bufferedreader": 1.5,
    "filereader": 1.2,
    "try": 1.0, "catch": 1.0, "new": 0.8,
    "readline": 1.2, "aslist": 1.2, "sort": 1.2,
}
