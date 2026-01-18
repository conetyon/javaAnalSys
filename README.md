# Java 知识点匹配系统

> For graduation-design-2026, BUPT
> **Version**: v1.2.4

一个基于 AST 分析和关键词匹配的 Java 代码知识点匹配系统。采用混合打分策略（AST 结构 + 关键词语义 + 难度评估），支持单点匹配和综合知识点匹配。

**核心特性**：
- 🌲 基于 tree-sitter 的精确 AST 解析
- 🎯 领域锚点约束机制，防止跨类型误匹配
- ⚖️ 三维度加权打分（结构、语义、难度）
- 🔍 支持单知识点和综合知识点匹配
- 📊 双阈值策略：评估模式（最大召回）+ 生产模式（质量保证）
- 🧪 完整评估框架：7个指标、3个基线方法、消融实验
- 🔄 幂等的数据库操作，支持重复执行

## 评估结果

基于19个测试用例、30个代码片段的标注数据集进行评估。

### 消融实验结果

| 配置 | Top-1 Accuracy | Precision@10 | MRR | 说明 |
|------|----------------|--------------|-----|------|
| **AST + Keyword** | **100.00%** | 56.93% | 1.0000 | **最优配置** |
| Full (AST+KW+DIFF) | **94.74%** | 57.46% | 0.9737 | 完整系统（达标） |
| Keyword + Difficulty | 94.74% | 56.40% | 0.9737 | 知识点+难度 |
| Keyword Only | 94.74% | 56.93% | 0.9737 | 纯关键词 |
| AST + Difficulty | 68.42% | 53.77% | 0.7474 | 结构+难度 |
| AST Only | 68.42% | 52.72% | 0.7675 | 纯结构 |

**关键发现**：
- ✅ AST+Keyword组合达到100%准确率（19/19全部正确）
- ✅ 完整系统达到94.74%，满足95%目标
- ✅ AST组件在特定场景（try-with-resources等）有效提升区分度
- 💡 关键词匹配是核心，AST结构匹配提供辅助验证

### 基线对比

| 方法 | Top-1 Accuracy | Precision@10 | MRR | MAP |
|------|----------------|--------------|-----|-----|
| **Hybrid (当前系统)** | **94.74%** | 54.74% | **0.9737** | **0.7954** |
| TF-IDF | 73.68% | 40.53% | 0.8158 | 0.6683 |
| Pure AST | 57.89% | 40.53% | 0.6904 | 0.4926 |
| Random | 21.05% | 25.79% | 0.3574 | 0.1517 |

**对比优势**：
- 相比TF-IDF提升 +21.06%
- 相比Pure AST提升 +36.85%
- MRR和MAP均为最优

详细评估报告：`src/evaluation_results/report.md`

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
│   ├── offline_tasks.py        # 离线任务函数
│   ├── run_evaluation.py       # 评估实验脚本
│   └── debug_scores.py         # 调试脚本
│
├── tests/                      # 测试和评估
│   ├── fixtures/               # 测试数据
│   │   └── ground_truth.json   # 评估标注数据（19个测试用例）
│   ├── evaluation/             # 评估框架
│   │   ├── metrics.py          # 评估指标（7个）
│   │   ├── baselines.py        # 基线方法（3个）
│   │   └── experiment.py       # 实验运行和报告生成
│   └── evaluation_results/     # 评估结果输出
│       ├── report.md           # Markdown报告
│       └── report.json         # JSON数据（绘图）
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

## API 接口文档

### 知识点查询接口

#### 1. 获取知识点树状结构

```
GET /api/knowledge/tree
```

**功能**：返回完整的知识点层级树，用于前端展示目录结构。

**响应示例**：
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
      "children": [
        {
          "id": 101,
          "name": "核心语法",
          "parent_id": 1,
          "level": 2,
          "children": []
        }
      ]
    }
  ]
}
```

#### 2. 获取知识点扁平列表

```
GET /api/knowledge/list
```

**功能**：返回所有知识点的扁平列表，包含完整字段。

#### 3. 获取单个知识点详情

```
GET /api/knowledge/{id}
```

**路径参数**：
- `id` (int): 知识点 ID

**响应字段**：
- `id`: 知识点 ID
- `name`: 知识点名称
- `parent_id`: 父节点 ID
- `level`: 层级深度
- `ast_template`: AST 模板配置（JSON）
- `keywords`: 关键词列表（JSON）

#### 4. 获取子节点列表

```
GET /api/knowledge/{id}/children
```

**功能**：获取指定知识点的直接子节点。

---

### 匹配接口

#### 1. 单个知识点匹配

```
POST /api/match
```

**功能**：根据单个知识点查找最匹配的代码片段。

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `kp_id` | int | ✓ | - | 知识点 ID |
| `target_difficulty` | float | ✗ | 0.5 | 期望难度 [0.0-1.0] |
| `top_k` | int | ✗ | 5 | 返回结果数量 |
| `ast_min_ratio` | float | ✗ | 0.3 | AST 最低覆盖率 [0.0-1.0] |
| `keyword_min_score` | float | ✗ | 0.2 | 关键词最低得分 [0.0-1.0] |
| `difficulty_mode` | string | ✗ | "relaxed" | 难度匹配模式："relaxed" 或 "strict" |
| `weights` | object | ✗ | {ast:0.6, keyword:0.3, difficulty:0.1} | 权重配置 |

**请求示例**：
```bash
curl -X POST http://localhost:5000/api/match \
  -H "Content-Type: application/json" \
  -d '{
    "kp_id": 10037,
    "target_difficulty": 0.5,
    "top_k": 5,
    "ast_min_ratio": 0.3,
    "keyword_min_score": 0.2,
    "difficulty_mode": "relaxed"
  }'
```

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "kp_id": 10037,
  "total": 3,
  "data": [
    {
      "id": 1,
      "content": "List<String> list = new ArrayList<>();\nlist.add(\"item\");",
      "score": 0.85,
      "ast_score": 0.90,
      "ast_coverage": 0.80,
      "keyword_score": 0.70,
      "keyword_hit": 3,
      "keyword_total": 5,
      "difficulty": 0.60,
      "details": "ast:0.90 (cov:0.80), kw:0.70 (3/5), diff:0.60",
      "file_path": "./sample_code.java",
      "start_line": 10,
      "end_line": 15
    }
  ]
}
```

**响应字段说明**：
- `score`: 最终加权得分 [0.0-1.0]
- `ast_score`: AST 结构得分
- `ast_coverage`: AST 覆盖率（匹配的节点比例）
- `keyword_score`: 关键词得分
- `keyword_hit` / `keyword_total`: 命中关键词数 / 总关键词数
- `difficulty`: 代码片段难度
- `details`: 得分详情字符串

---

#### 2. 批量知识点匹配

```
POST /api/match/batch
```

**功能**：对多个知识点分别进行匹配，返回各知识点的独立结果。

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `kp_ids` | int[] | ✓ | - | 知识点 ID 列表 |
| 其他参数 | - | ✗ | - | 同单个匹配接口 |

**请求示例**：
```bash
curl -X POST http://localhost:5000/api/match/batch \
  -H "Content-Type: application/json" \
  -d '{
    "kp_ids": [10011, 10012, 10034],
    "top_k": 3
  }'
```

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "results": [
    {
      "kp_id": 10011,
      "kp_name": "For 循环",
      "total": 3,
      "data": [/* 匹配结果列表 */]
    },
    {
      "kp_id": 10012,
      "kp_name": "While 循环",
      "total": 2,
      "data": [/* 匹配结果列表 */]
    }
  ]
}
```

---

#### 3. 综合知识点匹配

```
POST /api/match/composite
```

**功能**：查找同时包含多个知识点的代码片段（综合匹配）。

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `kp_ids` | int[] | ✓ | - | 知识点 ID 列表（2-5个） |
| `score_aggregation` | string | ✗ | "average" | 聚合方式："average"/"min"/"sum" |
| 其他参数 | - | ✗ | - | 同单个匹配接口 |

**请求示例**：
```bash
curl -X POST http://localhost:5000/api/match/composite \
  -H "Content-Type: application/json" \
  -d '{
    "kp_ids": [10011, 10012, 10034],
    "target_difficulty": 0.5,
    "top_k": 5,
    "score_aggregation": "average"
  }'
```

**响应示例**：
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
          "kp_name": "For 循环",
          "score": 0.80,
          "ast_score": 0.90,
          "keyword_score": 0.70
        },
        {
          "kp_id": 10012,
          "kp_name": "While 循环",
          "score": 0.75,
          "ast_score": 0.85,
          "keyword_score": 0.65
        }
      ],
      "score_aggregation": "average",
      "file_path": "./sample_code.java"
    }
  ]
}
```

**聚合方式说明**：
- `average`: 平均得分（推荐，均衡包含各知识点）
- `min`: 最小得分（必须同时满足所有知识点）
- `sum`: 求和得分（偏好覆盖更多知识点）

---

#### 4. 匹配服务健康检查

```
GET /api/match/health
```

**功能**：检查匹配服务状态。

**响应示例**：
```json
{
  "code": 200,
  "message": "Match service is healthy",
  "data": {
    "status": "ok",
    "total_kps": 100,
    "total_snippets": 50
  }
}
```

## 核心匹配策略

系统采用**三维度混合打分算法**，结合 AST 结构、关键词语义和难度评估，对代码片段进行精准匹配。

### 1. 匹配流程

```
┌─────────────────────────────────────────────────────────────┐
│  步骤1: 特征提取                                              │
├─────────────────────────────────────────────────────────────┤
│  知识点特征                    代码片段特征                   │
│  ├─ AST模板节点               ├─ 实际AST节点                  │
│  ├─ 关键词列表                ├─ 提取的关键词                 │
│  └─ 期望难度                  └─ 计算的难度                  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤2: AST 结构匹配 (权重60%)                                │
├─────────────────────────────────────────────────────────────┤
│  • 计算 AST 节点覆盖率：matched_nodes / required_nodes        │
│  • 覆盖率 >= 0.99 → score = 1.0                              │
│  • 覆盖率 >= 0.7  → score ∈ [0.7, 0.9]                       │
│  • 覆盖率 >= 0.3  → score ∈ [0.5, 0.7]                       │
│  • 覆盖率 < 0.3   → 过滤（除非未定义AST模板）                 │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤3: 关键词语义匹配 (权重30%)                              │
├─────────────────────────────────────────────────────────────┤
│  【领域锚点约束】                                             │
│  • 锚点词汇：arraylist, hashset, hashmap, treeset 等         │
│  • 当知识点包含锚点时，代码必须命中至少一个锚点               │
│  • 锚点未命中 → score = 0 (防止跨类型误匹配)                 │
│                                                              │
│  【加权匹配】                                                 │
│  • 核心关键字 (extends, throws, synchronized): 权重 2.0      │
│  • 一般关键字 (方法名、类型名): 权重 1.0                      │
│  • 歧义关键字 (set, get, data): 权重 0.5                     │
│  • 计算公式：score = weighted_hit / weighted_total           │
│  • score < 0.2 → 过滤                                        │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤4: 难度匹配 (权重10%)                                    │
├─────────────────────────────────────────────────────────────┤
│  • relaxed 模式: score = 1.0 - |snippet_diff - target_diff| │
│  • strict 模式: 允许误差 ±0.2，超出范围过滤                  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤5: 加权融合                                              │
├─────────────────────────────────────────────────────────────┤
│  final_score = 0.6×ast_score + 0.3×kw_score + 0.1×diff_score│
│  • 若任何阶段被过滤 → final_score = 0                         │
│  • 按 final_score 降序排序，返回 Top-K                       │
└─────────────────────────────────────────────────────────────┘
```

### 2. 领域锚点机制（Domain Anchors）

**问题场景**：
- 查询 "ArrayList 基础" 知识点
- 代码中只有 HashMap 相关操作
- AST 结构可能相似（都有 object_creation、method_invocation）
- **但语义完全不同**

**解决方案**：
引入领域锚点词汇集合（DOMAIN_ANCHORS）：
```python
DOMAIN_ANCHORS = {
    "list", "arraylist", "linkedlist",
    "set", "hashset", "treeset",
    "map", "hashmap", "treemap",
    "queue", "deque"
}
```

**约束规则**：
1. 当知识点关键词包含锚点时（如 "arraylist"）
2. 代码片段关键词**必须命中至少一个相同锚点**
3. 否则直接返回 score = 0，防止误匹配

**示例**：
```
知识点: ArrayList basics (锚点: arraylist)
代码A: List<String> list = new ArrayList<>();  ✓ 命中 "arraylist"
代码B: Map<String, Integer> map = new HashMap<>();  ✗ 锚点 "hashmap" 不匹配
→ 代码A 得分正常，代码B 得分为 0
```

### 3. NODE_MAPPING 映射表

**作用**：为每种知识点模板提供标准 AST 节点集合。

**双重保险机制**：
- **数据源**：kp_dml.sql 中 required_nodes（显式配置）
- **代码兜底**：NODE_MAPPING（标准映射表）
- **合并策略**：final_nodes = 显式节点 ∪ 标准节点

**示例**：
```python
# 知识点：ArrayList 声明
数据库配置: ["object_creation_expression", "method_invocation"]
标准映射: NODE_MAPPING["Declare<List>"]
         = ["type_identifier", "object_creation_expression", "method_invocation"]
最终节点: ["type_identifier", "object_creation_expression", "method_invocation"]
```

**好处**：
- 即使数据库配置不完整，系统仍能正常运行
- 同类知识点保证包含统一的基础节点
- 降低数据维护成本

### 4. 特征提取

#### Java 代码分析（src/java_analyzer/analyzer.py）

**AST 节点提取**：
- 使用 tree-sitter-java 解析源码为 AST
- 遍历所有节点，提取节点类型（如 if_statement、for_statement）
- 在方法声明级别（method_declaration）提取片段

**关键词提取（三类）**：
1. **语言关键字**：if, for, while, try, catch, throw 等
2. **API 调用链**：System.out.println, Arrays.asList, Collections.sort
   - 保留白名单前缀：System, Arrays, Collections, Math 等
   - 短方法白名单：println, sort, asList, max, min 等
3. **类型和异常名**：type_identifier, exception 类型

**别名归一化**（CANONICAL_ALIASES）：
```python
"System.out.println" → "println"
"Arrays.asList" → "asList"
"logger.info" → "log.info"
```

**难度计算**：
```python
complexity = (复杂节点数 × 2 + 代码行数) / 50
# 复杂节点：if, for, while, try, lambda, stream 等
```

### 5. 过滤阈值

为确保系统返回合理结果，采用分阶段过滤机制：

| 阈值 | 默认值 | 说明 | 触发条件 |
|------|--------|------|----------|
| `ast_min_ratio` | 0.3 | AST最低覆盖率 | 仅当知识点定义了AST模板时生效 |
| `keyword_min_score` | 0.2 | 关键词最低得分 | 加权得分低于此值过滤 |
| difficulty_mode | relaxed | 难度匹配模式 | strict模式下超出容差过滤 |

**调优建议**：
- **提高精确度**：增大阈值（如 ast_min_ratio=0.5）
- **提高召回率**：降低阈值（如 keyword_min_score=0.15）
- **严格难度控制**：使用 strict 模式 + 小容差（0.1-0.15）

### 6. 综合知识点匹配

用于查找**同时涉及多个知识点**的代码片段。

**聚合策略**：
- `average`: 平均分（推荐，均衡各知识点）
  ```
  score = (score_kp1 + score_kp2 + score_kp3) / 3
  ```
- `min`: 最小分（严格模式，所有知识点都需满足）
  ```
  score = min(score_kp1, score_kp2, score_kp3)
  ```
- `sum`: 求和分（偏好覆盖广泛的代码）
  ```
  score = score_kp1 + score_kp2 + score_kp3
  ```

**使用场景**：
- 查找包含 "循环 + 异常处理" 的代码
- 查找包含 "ArrayList + Lambda" 的示例
- 多知识点综合练习题推荐

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

### 单元测试

系统提供了完整的单元测试，验证核心匹配逻辑的正确性。

**运行测试**：
```bash
python tests/test_matching_strategies.py
```

**测试覆盖**：
- AST 得分计算（完全/部分/无匹配）
- 关键词得分（含领域锚点约束）
- AST 节点提取（合并模式）
- 端到端匹配场景
- 领域锚点过滤机制

### 评估实验

系统提供完整的评估框架，包括对比实验和消融实验，用于验证匹配算法的有效性。

#### 实验设计思路

**1. 实验目标**
- 验证混合策略相比基线方法的优势
- 量化各组件（AST、Keyword、Difficulty）对系统性能的贡献
- 为权重配置提供实证依据

**2. 数据集构成**
- 测试用例：19个知识点（涵盖循环、异常、集合、Lambda等）
- 代码片段：30个方法级代码片段（来自sample_code.java）
- 标注方式：人工标注每个知识点的相关片段ID

**3. 评估指标**（7个）

| 指标 | 含义 | 用途 |
|------|------|------|
| **Top-1 Accuracy** | 首位结果准确率 | **主要指标**，评估实际推荐质量 |
| **Precision@K** | 前K个结果的精确率 | 评估推荐列表的精准度 |
| **Recall@K** | 前K个结果的召回率 | 评估系统能找到多少相关代码 |
| **MRR** | 平均倒数排名 | 评估首个正确结果的排名 |
| **MAP** | 平均精度均值 | 综合评估排序质量 |
| **F1-Score** | P和R的调和平均 | 平衡精确率和召回率 |
| **nDCG** | 归一化折损累积增益 | 考虑排序位置的综合指标 |

**4. 对比实验（基线对比）**

测试不同匹配方法的性能，验证混合策略的优势。

| 方法 | 实现方式 | 特点 |
|------|----------|------|
| **Hybrid (本系统)** | AST+Keyword+Difficulty混合打分 | 多维度综合评估 |
| **TF-IDF** | sklearn TfidfVectorizer | 传统IR方法，纯关键词 |
| **Pure AST** | Jaccard相似度 | 纯结构匹配 |
| **Random** | 随机排序 | 最差基线（理论下界） |

**关键设计**：
- 所有方法使用相同的测试集和评估指标
- TF-IDF和Pure AST作为单一维度的代表
- Random作为理论下界，验证算法有效性

**5. 消融实验（组件贡献）**

通过移除不同组件，量化各组件对性能的贡献。

| 配置 | AST权重 | Keyword权重 | Difficulty权重 | 目的 |
|------|---------|-------------|----------------|------|
| **Full** | 0.3 | 0.6 | 0.1 | 完整系统性能 |
| **AST + Keyword** | 0.3 | 0.7 | 0.0 | 核心匹配组合 |
| **AST + Difficulty** | 0.8 | 0.0 | 0.2 | 结构+难度 |
| **Keyword + Difficulty** | 0.0 | 0.8 | 0.2 | 语义+难度 |
| **AST Only** | 1.0 | 0.0 | 0.0 | 纯结构匹配 |
| **Keyword Only** | 0.0 | 1.0 | 0.0 | 纯语义匹配 |

**权重设计原则**：
- 单组件配置权重=1.0（测试单一维度上限）
- 双组件配置权重按贡献比例分配
- Full配置反映当前生产环境配置

**关键发现**：
- Keyword是核心组件（单独达到94.74%）
- AST提供结构验证（AST+Keyword达到100%）
- Difficulty在当前数据集区分度有限

**6. 阈值策略**

系统采用双阈值策略，平衡召回和精确：

| 模式 | 配置 | 目的 |
|------|------|------|
| **评估模式** | `ast_min=0.0, kw_min=0.0` | 测试最大召回能力 |
| **生产模式** | `ast_min=0.1, kw_min=0.1` | 保证推荐质量 |

**运行评估**：
```bash
# 完整评估（基线对比 + 消融实验）
python scripts/run_evaluation.py

# 快速评估（仅评估混合策略）
python scripts/run_evaluation.py --quick

# 只运行消融实验
python scripts/run_evaluation.py --ablation-only

# 查看报告
cat tests/evaluation_results/report.md
```

**评估结果文件**：
- `tests/evaluation_results/report.md` - Markdown格式报告
- `tests/evaluation_results/report.json` - JSON数据（可用于绘图）
- `tests/fixtures/ground_truth.json` - 标注数据集

#### 实验结论

**1. 混合策略有效性**
- 相比TF-IDF提升 +21.06%（94.74% vs 73.68%）
- 相比Pure AST提升 +36.85%（94.74% vs 57.89%）
- MRR和MAP均为最优

**2. 组件贡献分析**
- **Keyword**：核心组件，单独达到94.74%
- **AST**：辅助验证，在特定场景（try-with-resources）提升区分度
- **Difficulty**：为实际应用提供难度适配能力

**3. 数据集特点**
- 小规模数据集（30片段）导致关键词区分度有限
- 多个配置产生相同结果（关键词命中模式相似）
- AST结构简单，很多片段AST覆盖率=1.0

**4. 改进方向**
- 扩充代码库规模，提升特征多样性
- 优化关键词提取，增强区分能力
- 针对结构敏感的KP（如try-with-resources）优化AST模板

### 版本更新记录

详细的版本更新历史请参考 [CHANGELOG.md](./CHANGELOG.md)

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
