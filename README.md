# Java 知识点匹配系统

> For graduation-design-2026, BUPT

一个基于 AST 分析和关键词匹配的 Java 代码知识点匹配系统。

## 项目结构

```
java-ana-mvp/
├── api/                        # API 层
│   ├── __init__.py             # Flask App 工厂
│   ├── routes/                 # 路由层
│   │   ├── __init__.py         # 路由注册
│   │   ├── knowledge.py        # 知识点相关接口
│   │   └── match.py            # 匹配相关接口
│   ├── schemas/                # 数据模型（Pydantic）
│   │   ├── __init__.py
│   │   ├── common.py           # 通用响应模型
│   │   ├── knowledge.py        # 知识点模型
│   │   └── match.py            # 匹配模型
│   ├── middleware/             # 中间件
│   │   ├── __init__.py
│   │   └── error_handler.py    # 统一异常处理
│   └── logs/                   # API 日志
│
├── src/                        # 业务逻辑层
│   ├── db_manager/             # 数据库管理
│   │   ├── __init__.py
│   │   ├── base.py             # 基类
│   │   ├── database.py         # 数据库初始化
│   │   ├── code_library_manager.py    # 代码库管理
│   │   └── knowledge_point_manager.py # 知识点管理
│   ├── java_analyzer/          # Java 代码分析器
│   │   ├── __init__.py
│   │   ├── analyzer.py         # AST 分析器
│   │   └── constants.py        # 常量定义
│   ├── matching/               # 匹配策略
│   │   ├── __init__.py
│   │   ├── strategies.py       # 匹配算法
│   │   └── utils.py            # 工具函数
│   ├── services/               # 服务层（API 和离线共用）
│   │   ├── __init__.py
│   │   ├── search_service.py   # 搜索匹配服务
│   │   └── knowledge_service.py # 知识点服务
│   └── logs/                   # 核心日志
│
├── scripts/                    # 离线脚本
│   ├── __init__.py
│   └── offline_tasks.py        # 离线任务函数
│
├── lib/                        # 基础设施
│   ├── __init__.py
│   ├── client/                 # 客户端封装
│   │   ├── __init__.py
│   │   └── db.py               # MySQL 连接池
│   ├── globals/                # 全局配置
│   │   └── __init__.py         # 日志句柄、配置对象
│   └── utils/                  # 工具类
│       ├── __init__.py
│       └── settings.py         # 配置加载
│
├── config/                     # 配置文件目录
│   └── db.yaml                 # 数据库配置
│
├── main.py                     # 离线任务入口
├── run_api.py                  # API 服务入口
├── config.py                   # 全局配置
├── requirements.txt            # 依赖列表
├── kp_dml.sql                  # 知识点预置数据
└── sample_code.java            # 示例代码
```

## 分层架构

### 1. API 层 (`api/`)

负责 HTTP 请求处理，包含：

| 模块 | 职责 |
|------|------|
| `routes/` | 路由定义，接收请求、参数校验、调用服务层 |
| `schemas/` | Pydantic 模型，定义请求/响应数据结构 |
| `middleware/` | 中间件，统一异常处理、日志记录 |

### 2. 服务层 (`src/services/`)

封装业务逻辑，**同时供 API 和离线任务调用**：

| 服务 | 职责 |
|------|------|
| `SearchService` | 知识点匹配搜索 |
| `KnowledgeService` | 知识点查询（树结构、详情等） |

### 3. 数据层 (`src/db_manager/`)

数据库操作封装：

| 模块 | 职责 |
|------|------|
| `DatabaseInitializer` | 数据库表结构初始化 |
| `KnowledgePointManager` | 知识点 CRUD |
| `CodeLibraryManager` | 代码片段 CRUD |

### 4. 基础设施 (`lib/`)

通用工具和配置：

| 模块 | 职责 |
|------|------|
| `client/db.py` | MySQL 连接池封装 |
| `globals/` | 全局日志句柄、配置对象 |
| `utils/` | 配置加载、工具函数 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

编辑 `config/db.yaml`：

```yaml
db:
  javalearningsys:
    host: localhost
    port: 3306
    user: root
    password: your_password
    db: javalearningsys
    charset: utf8mb4
    maxConn: 10
```

### 3. 初始化数据库

```bash
python main.py --init-db
```

### 4. 启动 API 服务

```bash
python run_api.py
```

服务默认运行在 `http://0.0.0.0:5000`

## 程序入口

### API 服务 (`run_api.py`)

```bash
# 启动服务（默认端口 5000）
python run_api.py

# 指定端口
python run_api.py --port 8080

# 开启调试模式
python run_api.py --debug

# 允许外部访问
python run_api.py --host 0.0.0.0
```

### 离线任务测试 (`main.py`)

**测试方式**：通过注释/取消注释选择测试场景（无需命令行参数）

```bash
# 直接运行（完整自动化流程）
python main.py
```

**自动化流程**（每次运行自动执行）：
1. **初始化数据库** - 创建表结构、插入预置知识点数据
2. **分析示例代码** - 提取 `sample_code.java` 的代码片段特征并存入数据库
3. **运行测试场景** - 执行选中的匹配测试

**使用步骤**：
1. 打开 `main.py` 文件
2. 在主入口 `if __name__ == "__main__":` 处找到步骤3的场景选择区域
3. 取消注释想要运行的场景（删除 `#` 号）
4. 修改场景函数内的 `kp_ids` 参数测试不同知识点
5. 运行 `python main.py`

**可用场景**：
- **场景 1**: `run_single_test()` - 单个知识点匹配
- **场景 2**: `run_multiple_test()` - 综合知识点匹配
- **工具函数**: `run_utility_functions()` - 查看知识点树、分析其他代码文件

**特点**：
- 所有步骤都是幂等操作，可重复执行
- 自动处理完整流程，无需手动初始化
- 数据库配置文件：`config/db.yaml`
- 示例代码文件：`./sample_code.java`（可替换）

**示例知识点 ID**：`10010, 10011, 10031, 10034, 10083`（print 相关）

## API 接口

### 知识点接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge/tree` | 获取知识点树状结构 |
| GET | `/api/knowledge/list` | 获取知识点扁平列表 |
| GET | `/api/knowledge/{id}` | 获取单个知识点详情 |
| GET | `/api/knowledge/{id}/children` | 获取子节点列表 |

### 匹配接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/match` | 单个知识点匹配 |
| POST | `/api/match/batch` | 批量知识点匹配（独立） |
| POST | `/api/match/composite` | 综合知识点匹配 |
| GET | `/api/match/health` | 匹配服务健康检查 |

### 请求示例

#### 单个知识点匹配

```bash
curl -X POST http://localhost:5000/api/match \
  -H "Content-Type: application/json" \
  -d '{
    "kp_id": 10011,
    "target_difficulty": 0.5,
    "top_k": 5,
    "ast_min_ratio": 0.4,
    "keyword_min_score": 0.4,
    "difficulty_mode": "relaxed"
  }'
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "kp_id": 10011,
  "total": 3,
  "data": [
    {
      "id": 1,
      "content": "for (int i = 0; i < 10; i++) { ... }",
      "score": 0.85,
      "ast_ratio": 0.9,
      "ast_coverage": 0.8,
      "keyword_score": 0.7,
      "keyword_hit": 3,
      "keyword_total": 5,
      "difficulty": 0.6,
      "details": "ast:0.90 (cov:0.80), kw:0.70 (3/5), diff:0.60",
      "file_path": "./sample_code.java"
    }
  ]
}
```

#### 综合知识点匹配

```bash
curl -X POST http://localhost:5000/api/match/composite \
  -H "Content-Type: application/json" \
  -d '{
    "kp_ids": [10011, 10012, 10034],
    "target_difficulty": 0.5,
    "top_k": 5,
    "ast_min_ratio": 0.3,
    "keyword_min_score": 0.3,
    "score_aggregation": "average"
  }'
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "kp_ids": [10011, 10012, 10034],
  "total": 3,
  "data": [
    {
      "id": 1,
      "content": "...",
      "composite_score": 0.75,
      "kp_count": 3,
      "kp_details": [
        {
          "kp_id": 10011,
          "kp_name": "循环语句",
          "score": 0.8,
          "ast_ratio": 0.9,
          "keyword_score": 0.7
        },
        {
          "kp_id": 10012,
          "kp_name": "条件语句",
          "score": 0.75,
          "ast_ratio": 0.85,
          "keyword_score": 0.65
        }
      ],
      "score_aggregation": "average",
      "file_path": "./sample_code.java"
    }
  ]
}
```

**score_aggregation 聚合方式**：
- `average`: 平均得分（推荐，均衡包含各知识点）
- `min`: 最小得分（必须同时满足所有知识点）
- `sum`: 求和得分（偏好覆盖更多知识点）

#### 获取知识点树

```bash
curl http://localhost:5000/api/knowledge/tree
```

响应：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "Java基础",
      "parent_id": null,
      "level": 1,
      "title": "Java基础",
      "key": 1,
      "children": [
        {
          "id": 2,
          "name": "变量与数据类型",
          "parent_id": 1,
          "level": 2,
          "children": []
        }
      ]
    }
  ]
}
```

## 调用关系

```
┌─────────────────────────────────────────────────────────────┐
│                        入口层                                │
├─────────────────────────────────────────────────────────────┤
│  run_api.py (API服务)          main.py (离线任务)            │
└──────────────┬─────────────────────────┬────────────────────┘
               │                         │
               ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│      API 层 (api/)       │  │   离线脚本 (scripts/)         │
│  routes/ → schemas/      │  │   offline_tasks.py           │
│  middleware/             │  │                              │
└──────────────┬───────────┘  └──────────────┬───────────────┘
               │                             │
               └──────────────┬──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   服务层 (src/services/)                     │
│  SearchService          KnowledgeService                    │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌───────────────────────────────┐
│  数据层 (src/db_manager/)│  │  分析层 (src/java_analyzer/)  │
│  KnowledgePointManager   │  │  JavaAnalyzer                 │
│  CodeLibraryManager      │  │                               │
└──────────────┬───────────┘  └───────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                 基础设施 (lib/)                              │
│  client/db.py (MySQL连接池)                                  │
│  globals/ (日志、配置)                                       │
└─────────────────────────────────────────────────────────────┘
```

## 开发指南

### 添加新接口

1. 在 `api/schemas/` 中定义请求/响应模型
2. 在 `api/routes/` 中添加路由函数
3. 在 `src/services/` 中实现业务逻辑（如需要）

### 添加离线任务

1. 在 `scripts/offline_tasks.py` 中添加任务函数
2. 在 `scripts/__init__.py` 中导出
3. 在 `main.py` 中添加命令行参数（如需要）

## 依赖说明

- **Flask** - Web 框架
- **flask-cors** - 跨域支持
- **Pydantic** - 数据校验
- **mysql-connector-python** - MySQL 驱动
- **tree-sitter** - AST 解析
- **tree-sitter-java** - Java 语法支持
- **PyYAML** - 配置文件解析

## License

MIT
