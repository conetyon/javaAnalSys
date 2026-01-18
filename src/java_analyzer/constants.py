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
# 目的：将 API 全限定调用（如 System.out.println）归一化为短名称（println）
# 支持静态导入后的匹配，提高关键词匹配准确性
CANONICAL_ALIASES = {
    # === 输出与日志 ===
    "system.out.println": "println",
    "system.err.println": "println",
    "system.out.print": "print",
    "system.out.printf": "printf",
    "printstacktrace": "printstacktrace",
    "logger.info": "log.info",
    "logger.error": "log.error",
    "logger.debug": "log.debug",
    "logger.warn": "log.warn",
    "log.info": "log.info",
    "log.error": "log.error",
    "log.debug": "log.debug",
    "log.warn": "log.warn",

    # === 包装类型解析 ===
    "integer.parseint": "parseint",
    "integer.valueof": "valueof",
    "integer.tostring": "tostring",
    "double.parsedouble": "parsedouble",
    "double.valueof": "valueof",
    "long.parselong": "parselong",
    "long.valueof": "valueof",
    "float.parsefloat": "parsefloat",
    "boolean.parseboolean": "parseboolean",

    # === 数学方法 ===
    "math.max": "max",
    "math.min": "min",
    "math.abs": "abs",
    "math.pow": "pow",
    "math.sqrt": "sqrt",
    "math.floor": "floor",
    "math.ceil": "ceil",
    "math.round": "round",
    "math.random": "random",

    # === StringBuilder/StringBuffer ===
    "stringbuilder.append": "append",
    "stringbuffer.append": "append",
    "stringbuilder.tostring": "tostring",
    "stringbuffer.tostring": "tostring",
    "stringbuilder.insert": "insert",
    "stringbuilder.delete": "delete",

    # === String 方法 ===
    "string.valueof": "valueof",
    "string.format": "format",
    "string.join": "join",

    # === Objects 工具 ===
    "objects.equals": "equals",
    "objects.requirenonnull": "requirenonnull",
    "objects.hash": "hash",
    "objects.isnull": "isnull",
    "objects.nonNull": "nonnull",
    "objects.tostring": "tostring",

    # === Optional 方法 ===
    "optional.of": "of",
    "optional.ofnullable": "ofnullable",
    "optional.empty": "empty",
    "optional.get": "get",
    "optional.orelse": "orelse",
    "optional.orelseget": "orelseget",

    # === 集合/数组工具 ===
    "arrays.aslist": "aslist",
    "arrays.sort": "sort",
    "arrays.copyof": "copyof",
    "arrays.fill": "fill",
    "arrays.equals": "equals",
    "arrays.tostring": "tostring",
    "collections.sort": "sort",
    "collections.reverse": "reverse",
    "collections.shuffle": "shuffle",
    "collections.unmodifiablelist": "unmodifiablelist",
    "collections.emptylist": "emptylist",
    "collections.singletonlist": "singletonlist",

    # === Stream 操作 ===
    "stream.of": "of",
    "stream.empty": "empty",
    "collectors.tolist": "tolist",
    "collectors.toset": "toset",
    "collectors.tomap": "tomap",
    "collectors.joining": "joining",
    "collectors.groupingby": "groupingby",

    # === IO/文件操作 ===
    "files.readalllines": "readalllines",
    "files.lines": "lines",
    "files.exists": "exists",
    "files.write": "write",
    "files.createfile": "createfile",
    "files.createdirectories": "createdirectories",
    "files.delete": "delete",
    "paths.get": "get",
    "path.tostring": "tostring",

    # === Pattern/Matcher (正则) ===
    "pattern.compile": "compile",
    "matcher.matches": "matches",
    "matcher.find": "find",
    "matcher.group": "group",

    # === 并发工具 ===
    "thread.sleep": "sleep",
    "thread.start": "start",
    "thread.join": "join",
    "executors.newfixedthreadpool": "newfixedthreadpool",
    "executors.newcachedthreadpool": "newcachedthreadpool",
    "future.get": "get",

    # === 时间日期 (Java 8+) ===
    "localdate.now": "now",
    "localdate.of": "of",
    "localdatetime.now": "now",
    "localdatetime.of": "of",
    "instant.now": "now",
    "datetimeformatter.ofpattern": "ofpattern",
}
