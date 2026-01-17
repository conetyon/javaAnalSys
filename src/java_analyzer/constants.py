# src/java_analyzer/constants.py
# 核心常量定义：关键字、复杂度节点、前缀白名单、别名归一化

# ============ 语言级关键字（仅保留结构性/控制流关键字） ============
JAVA_KEYWORDS = {
    # 控制流
    "if", "else", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "return",
    # 异常与资源
    "try", "catch", "finally", "throw", "throws",
    # 其它结构
    "new", "synchronized", "instanceof", "this", "super",
}

# ============ 复杂度相关的 AST 节点类型 ============
COMPLEXITY_NODES = {
    "if_statement", "for_statement", "enhanced_for_statement",
    "while_statement", "do_statement", "switch_statement",
    "catch_clause", "try_statement", "throw_statement",
    "conditional_expression", "binary_expression",
    "lambda_expression", "method_reference",
    "synchronized_statement", "assert_statement",
}

# ============ 允许保留的调用前缀（避免变量名噪音） ============
ALLOWED_PREFIX_PREFIXES = {
    # 标准库/常见工具（首字母大写，明显是类名）
    "System", "Math", "Objects", "Optional",
    "Arrays", "Collections", "Collectors",
    "Files", "Paths", "Pattern", "Matcher",
    "Stream", "IntStream", "LongStream",
    # 日志（常见变量名也允许）
    "Logger", "LoggerFactory", "Log", "LOG", "LOGGER", "Slf4j",
}

# ============ 短方法白名单（高价值短词，确保不被过滤） ============
SHORT_METHOD_WHITELIST = {
    "println", "printf", "print",  # 输出
    "sort", "asList",              # 集合工具
    "of", "ofNullable",            # Optional/Stream工厂
    "max", "min",                  # 数学/Stream
    "readLine", "close", "flush",  # IO
    "info", "warn", "error", "debug",  # 日志
}

# ============ 别名归一化（统一到小写规范形式） ============
CANONICAL_ALIASES = {
    # 输出与日志
    "system.out.println": "println",
    "system.err.println": "println",
    "printstacktrace": "printstacktrace",
    "logger.info": "log.info",
    "logger.error": "log.error",
    "logger.debug": "log.debug",
    "logger.warn": "log.warn",
    # 集合/数组工具
    "arrays.aslist": "aslist",
    "collections.sort": "sort",
    # IO/文件
    "files.readalllines": "readalllines",
    "files.lines": "lines",
}
