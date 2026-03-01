# Java 知识点匹配系统

> For graduation-design-2026, BUPT
> **Version**: v1.5.0

一个基于 AST 分析和关键词匹配的 Java 代码知识点匹配系统。采用混合打分策略（AST 结构 + 关键词语义 + 难度评估），支持单点匹配、综合知识点匹配和矩阵模式匹配。

**新增 v1.5.0**：完整前端界面（用户认证、历史记录、收藏功能、矩阵/组合匹配模式）。

## 📋 目录

- [核心特性](#核心特性)
- [系统运行流程](#系统运行流程)
- [快速开始](#快速开始)
- [前端使用](#前端使用)
- [实验评估](#实验评估)
  - [数据集说明](#数据集说明)
  - [实验设计](#实验设计)
  - [实验结果](#实验结果)
- [系统架构](#系统架构)
- [API 接口](#api-接口)
- [开发指南](#开发指南)

---

## 核心特性

- 🌲 **精确 AST 解析**：基于 tree-sitter-java 的方法级代码分析
- 🎯 **领域锚点约束**：防止集合类型等领域相关知识点的跨类型误匹配
- ⚖️ **三维度混合打分**：结构（AST）+ 语义（关键词）+ 难度
- 🔍 **灵活匹配模式**：支持单知识点、批量、综合匹配、矩阵匹配
- 🛡️ **智能兜底逻辑**：自动降低阈值重试，尽量不返回空结果
- 🔄 **幂等化设计**：数据库初始化和代码分析安全可重复执行

---

## 系统运行流程

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户代码项目                                  │
│                    (code_repos/*.java)                              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     1. 代码导入与分析                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │ 文件发现     │ → │ AST 解析     │ → │ 特征提取                 │ │
│  │ (.java)      │   │ (tree-sitter)│   │ (ast_features,keywords)  │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     2. 数据库存储                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ code_snippets 表                                              │  │
│  │ - id, content, content_hash                                   │  │
│  │ - ast_features (JSON): ['for_statement', 'method_invocation'] │  │
│  │ - keywords (JSON): ['arraylist', 'add', 'new', 'for']         │  │
│  │ - complexity_score: 0.45                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     3. 知识点匹配查询                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │ API 请求     │ → │ 混合打分     │ → │ 返回 Top-K 结果          │ │
│  │ (kp_id=10037)│   │ AST+KW+DIFF  │   │ (带分数、高亮)           │ │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 代码分析流程

当你运行 `--import-project` 或 `--import-all-projects` 时：

```
Java 源文件
    │
    ▼
┌───────────────────────────────────────┐
│ 1. 读取文件内容                        │
│    with open(file_path, 'r') as f:    │
│        code = f.read()                │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 2. tree-sitter AST 解析               │
│    parser.parse(code.encode('utf8'))  │
│                                       │
│    生成语法树:                         │
│    program                            │
│    └── class_declaration              │
│        └── method_declaration         │
│            ├── for_statement          │
│            └── method_invocation      │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 3. 方法级片段提取                      │
│    遍历所有 method_declaration 节点    │
│    每个方法 → 一个代码片段             │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 4. 特征提取 (每个片段)                 │
│                                       │
│ ast_features:                         │
│   - 遍历 AST 节点类型                  │
│   - ['for_statement', 'if_statement', │
│      'method_invocation', ...]        │
│                                       │
│ keywords:                             │
│   - 语言关键字: for, if, new, return  │
│   - API 调用: ArrayList, add, println │
│   - 类型名称: String, IOException     │
│   - 别名归一化: System.out.println→   │
│                 println               │
│                                       │
│ complexity_score:                     │
│   - 基于 AST 复杂度节点计算            │
│   - 范围: 0.0 ~ 1.0                   │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 5. 数据库存储                          │
│    REPLACE INTO code_snippets (       │
│        content, content_hash,         │
│        ast_features, keywords,        │
│        complexity_score               │
│    )                                  │
│                                       │
│    content_hash = SHA256(path+content)│
│    用于去重和幂等导入                  │
└───────────────────────────────────────┘
```

### 匹配查询流程

当用户调用 `POST /api/match` 时：

```
用户请求: { kp_id: 10037 }  (ArrayList 基本操作)
    │
    ▼
┌───────────────────────────────────────┐
│ 1. 获取知识点模板                      │
│    KP Template:                       │
│    - ast_template: {                  │
│        required_nodes: [              │
│          'object_creation_expression',│
│          'method_invocation'          │
│        ]                              │
│      }                                │
│    - keywords: ['arraylist', 'add',   │
│                 'new', 'list']        │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 2. 获取候选代码片段                    │
│    SELECT * FROM code_snippets        │
│    (20,022+ 个候选)                    │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 3. 混合打分 (每个候选)                 │
│                                       │
│ AST Score (权重 0.2):                 │
│   - 模板节点 vs 片段 AST 节点匹配度    │
│   - 领域锚点检查 (arraylist/list)     │
│                                       │
│ Keyword Score (权重 0.7):             │
│   - 加权关键词匹配（最重要特征）       │
│   - 核心词 2.0x, 普通词 1.0x          │
│   - 歧义词 0.5x (如 get, set)         │
│                                       │
│ Difficulty Score (权重 0.1):          │
│   - 与目标难度的接近程度              │
│                                       │
│ final = 0.2×AST + 0.7×KW + 0.1×DIFF  │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 4. 过滤与排序                          │
│    - AST 最低阈值: 0.4                │
│    - Keyword 最低阈值: 0.4            │
│    - 低于阈值 → score = 0             │
│    - 按 final_score 降序排序          │
└───────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────┐
│ 5. 返回 Top-K 结果                     │
│    {                                  │
│      "data": [                        │
│        {                              │
│          "id": 12345,                 │
│          "content": "...",            │
│          "score": 0.85,               │
│          "ast_score": 0.90,           │
│          "keyword_score": 0.80        │
│        },                             │
│        ...                            │
│      ]                                │
│    }                                  │
└───────────────────────────────────────┘
```

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd java-ana-mvp

# 安装依赖
pip install -r requirements.txt

# 配置数据库（编辑 config/db.yaml）
```

**数据库配置示例** (`config/db.yaml`):
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

### 2. 数据库初始化

系统提供统一的数据库设置入口：

```bash
# 完整初始化（推荐 - 首次使用）
python scripts/setup_database.py --all

# 执行内容：
#   - 创建数据库表结构
#   - 加载 100+ 知识点
#   - 导入 CodeSearchNet 数据集（20,022 个代码片段）
#   - 分析示例代码
```

**分步操作**（可选）：
```bash
python scripts/setup_database.py --init-schema      # 仅初始化表结构
python scripts/setup_database.py --load-kp          # 仅加载知识点
python scripts/setup_database.py --import-dataset   # 仅导入 CodeSearchNet 数据集
```

### 3. 导入用户项目

#### 导入单个项目（目录）
```bash
python scripts/setup_database.py --import-project /path/to/your/java/project
```

#### 导入单个文件
```bash
python scripts/setup_database.py --import-all-projects --repos-dir ./code_repos/MyClass.java
```

#### 批量导入多个项目
```bash
# 一键导入 code_repos/ 目录下所有项目
python scripts/setup_database.py --import-all-projects

# 指定其他目录
python scripts/setup_database.py --import-all-projects --repos-dir ./my_projects
```

**命令汇总**：

| 命令 | 说明 |
|------|------|
| `--all` | 完整初始化（表结构 + 知识点 + 数据集） |
| `--init-schema` | 仅初始化数据库表结构 |
| `--load-kp` | 仅加载知识点数据 |
| `--import-dataset` | 仅导入 CodeSearchNet 数据集 |
| `--import-project <path>` | 导入指定项目目录 |
| `--import-all-projects` | 批量导入 code_repos 下所有项目 |
| `--import-all-projects --repos-dir <path>` | 指定目录或单个文件导入 |

**导入特性**：

| 特性 | 说明 |
|------|------|
| 递归扫描 | 自动遍历所有子目录 |
| 智能过滤 | 只处理 `.java` 文件，跳过 `target/`, `build/`, `.git/`, `test/` 等 |
| 幂等导入 | 使用 `content_hash` 去重，重复运行安全 |
| 自动建表 | 表不存在时自动创建 |
| 错误容忍 | 单文件解析失败不影响其他文件 |

**导入流程**：
```
your-project/
├── src/
│   ├── Main.java          ← 提取方法级代码片段
│   └── utils/
│       └── Helper.java    ← 递归发现
├── lib/
│   └── Tool.java          ← 递归发现
├── target/                 ← 自动跳过
└── README.md               ← 自动跳过（非 .java）
```

**导入结果示例**：
```
[INFO] 扫描目录: code_repos
[INFO] 递归发现所有 .java 文件（自动跳过 target/build/.git 等目录）
[OK] 导入完成: 520 文件, 146 代码片段
```

> ⚠️ **注意**: 部分文件可能提取 0 个片段（如 Lombok 数据类只有字段声明，无显式方法）

### 4. 启动 API 服务

```bash
# 默认端口 5000
python run_api.py

# 自定义配置
python run_api.py --port 8080 --debug
```

### 5. 运行评估实验

```bash
# 完整评估（基线对比 + 消融实验）
python scripts/run_experiments.py

# 快速评估（仅混合策略）
python scripts/run_experiments.py --quick
```

---

## 前端使用

### 环境要求

- Node.js 18+
- npm 或 yarn

### 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置必要的变量
# JWT_SECRET=your-32-char-secret-here-change-me
# ADMIN_USERNAME=admin
# ADMIN_PASSWORD=your-secure-password
```

### 启动前端

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端默认运行在 `http://localhost:5173`，自动代理 `/api` 请求到后端 `http://localhost:5000`。

### 功能说明

#### 迭代 1：核心功能

| 功能 | 说明 |
|------|------|
| 知识点树 | 三级层级浏览（L1 分类 → L2 模块 → L3 知识点），支持中英双语 |
| 搜索过滤 | 支持中英文搜索知识点 |
| 代码匹配 | 点击叶子节点触发匹配，返回相关代码片段 |
| 参数配置 | 可调整返回数量和期望难度 |
| 代码高亮 | Java 语法高亮显示 |
| 复制代码 | 一键复制代码到剪贴板 |

#### 迭代 2：用户认证

| 功能 | 说明 |
|------|------|
| 用户注册 | 支持用户名、密码、邮箱（可选）注册 |
| 用户登录 | JWT Token 认证，access_token (15分钟) + refresh_token (7天) |
| 自动刷新 | Token 过期自动刷新，用户无感知 |
| 单设备登录 | 新设备登录自动踢出旧设备 |
| 路由守卫 | 受保护页面（历史、收藏）需登录访问 |

#### 迭代 3：高级功能

| 功能 | 说明 |
|------|------|
| 矩阵模式 | 按难度分级（easy/medium/hard）展示匹配结果 |
| 组合匹配 | 多选知识点（最多5个），查找同时涉及多个概念的代码 |
| 匹配历史 | 记录匹配操作，支持分页浏览和重新执行 |
| 代码收藏 | 收藏有价值的代码片段，支持管理和浏览 |
| 状态持久化 | 从历史/收藏页返回主页时恢复选中状态 |

### 技术栈

- **框架**: React 18 + TypeScript
- **UI**: Ant Design 5
- **构建**: Vite
- **HTTP**: Axios（带自动刷新拦截器）
- **代码高亮**: react-syntax-highlighter

### 目录结构

```
frontend/src/
├── api/              # API 封装层
│   ├── client.ts     # Axios 实例（Token 自动刷新）
│   ├── auth.ts       # 认证 API
│   ├── knowledge.ts  # 知识点 API
│   ├── match.ts      # 匹配 API
│   └── user.ts       # 用户 API（历史、收藏）
├── components/       # 通用组件
│   ├── KnowledgeTree.tsx   # 知识点树
│   ├── CodeBlock.tsx       # 代码高亮
│   ├── MatchResultCard.tsx # 结果卡片
│   ├── MatrixView.tsx      # 矩阵视图
│   ├── Header.tsx          # 顶部导航
│   └── PrivateRoute.tsx    # 路由守卫
├── contexts/         # React Context
│   └── AuthContext.tsx     # 认证状态管理
├── pages/            # 页面组件
│   ├── Dashboard.tsx       # 主面板
│   ├── LoginPage.tsx       # 登录页
│   ├── RegisterPage.tsx    # 注册页
│   ├── HistoryPage.tsx     # 历史记录
│   └── FavoritesPage.tsx   # 收藏列表
├── types/            # TypeScript 类型
│   ├── api.ts, auth.ts, knowledge.ts, match.ts, user.ts
│   └── index.ts
└── App.tsx           # 根组件（路由配置）
```

---

## 实验评估

### 数据集说明

#### 使用的数据集

本系统使用 **CodeSearchNet Java 子集**作为评估数据集：

- **来源**: [CodeSearchNet Corpus](https://github.com/github/CodeSearchNet)
- **规模**: 20,022 个 Java 代码片段
- **特点**: 来自真实开源项目的方法级代码片段
- **质量**: 经过基本清洗，保留可编译的完整方法

#### 为什么要把数据集写入数据库？

**原因 1：提供真实代码候选集**
- 系统需要从大规模代码库中检索匹配的代码片段
- 数据库作为候选池，存储 20,022 个真实代码片段
- 用户查询时从这些候选中返回最相关的结果

**原因 2：支持实验评估**
- Ground Truth 标注引用数据库中的片段 ID
- 评估时需要验证系统能否从 20,022 个候选中找到正确的片段
- 模拟真实应用场景（大规模代码库检索）

**原因 3：统一数据管理**
- 用户代码、示例代码、数据集代码统一存储
- 支持复杂查询（AST 特征、关键词、难度）
- 便于增量导入和版本管理

#### 数据集如何写入数据库？

**1. 数据处理流程**

```
CodeSearchNet JSONL
    ↓ (解析)
Java 代码文件
    ↓ (tree-sitter 分析)
AST 特征 + 关键词 + 难度
    ↓ (MySQL 导入)
数据库表 (code_files, code_snippets)
```

**2. 表结构设计**

```sql
-- 代码文件表
CREATE TABLE code_files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_path VARCHAR(512),
    source VARCHAR(64),           -- 'codesearchnet', 'user_project', etc.
    created_at TIMESTAMP
);

-- 代码片段表（方法级）
CREATE TABLE code_snippets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_id INT,
    content TEXT,
    content_hash VARCHAR(64) UNIQUE,  -- SHA-256，用于去重和实验稳定性
    ast_features JSON,                 -- ['class_declaration', 'for_statement', ...]
    keywords JSON,                     -- ['arraylist', 'add', 'new', ...]
    difficulty FLOAT,                  -- 0.0-1.0
    line_start INT,
    line_end INT,
    created_at TIMESTAMP
);
```

**3. 导入命令**

```bash
# 通过setup_database.py统一入口
python scripts/setup_database.py --import-dataset

# 内部调用: scripts/_internal/import_utils/import_codesearchnet_to_db.py
```

**4. 去重机制**

- 使用 `content_hash`（SHA-256）字段去重
- 避免重复导入相同代码
- 支持实验时的 ID 稳定性

#### 数据库中数据集的作用

**作用 1：代码检索候选池（核心作用）**
```python
# 用户查询 "ArrayList 基本操作"
# 系统从 20,022 个片段中检索 Top-10
results = search_service.search(kp_id=10037, top_k=10)
```

**作用 2：实验评估基准**
- **使用分级规则评估**: 自动评估搜索结果相关性
- Ground Truth 引用数据库中的片段（99 个测试用例，495 个标注片段）→ **已改为分级规则评估**
- 评估系统能否从 20k+ 候选中找到正确的代码
- **指标**: Binary Precision = 98.0%，Graded Precision = 58.4%，nDCG = 0.874

**作用 3：AST 特征和关键词索引**
```json
{
  "id": 12345,
  "ast_features": ["for_statement", "local_variable_declaration"],
  "keywords": ["arraylist", "add", "size", "get"],
  "difficulty": 0.45
}
```
- 预计算特征，查询时直接匹配
- 避免实时解析 AST（性能优化）

**作用 4：与用户代码混合检索**
- 用户导入的项目代码与数据集代码存储在同一表
- 统一的检索接口，无需区分数据源
- 扩展性：可持续增加更多数据集

---

### 实验设计

#### 设计思路

**目标**：验证混合策略（AST + Keyword + Difficulty）的有效性，并通过消融实验分析各组件的贡献。

**评估方法**：

采用 **分级规则评估体系**，替代传统的 Ground Truth 标注：

1. **分级判断规则**
   - Grade 2（高度相关）：目标特征是代码主要逻辑
   - Grade 1（部分相关）：包含目标特征但非主要
   - Grade 0（不相关）：不包含目标特征
   - 规则定义在 `experiments/evaluation/rules.py`（56 条规则）

2. **多维度信号**
   - 显式命名（方法名包含关键词）
   - 高密度（特征占比 ≥ 10%）
   - 多次出现（特征出现 ≥ 2 次）
   - 适中长度（5-30 行代码）

**评估指标**：

- **Binary Precision**: (G1+G2)/Total - 相关结果比例（主要指标）
- **Graded Precision**: (2×G2 + G1)/(2×Total) - 加权精确率
- **nDCG@10**: 排名质量（考虑分级的 DCG）

**消融实验配置**：

| 配置 | AST | Keyword | Difficulty | 说明 |
|------|-----|---------|------------|------|
| Full | 0.2 | 0.7 | 0.1 | 生产配置 |
| AST + Keyword | 0.3 | 0.7 | 0.0 | 无难度 |
| Keyword + Difficulty | 0.0 | 0.9 | 0.1 | 无 AST |
| AST + Difficulty | 0.9 | 0.0 | 0.1 | 无关键词 |
| AST Only | 1.0 | 0.0 | 0.0 | 纯结构 |
| Keyword Only | 0.0 | 1.0 | 0.0 | 纯语义 |

**实验环境**：

- **候选池**: 20,022 个代码片段（CodeSearchNet Java）
- **评估 KP**: 56 个知识点规则
- **截断位置**: Top-10

---

### 实验结果

#### 核心指标

基于 **56 个知识点、554 个评估片段** 的分级评估（2026-02-07）：

```
✓ Binary Precision: 98.0% (相关结果比例)
✓ Graded Precision: 58.4% (加权精确率)
✓ Average nDCG@10:  0.874 (排名质量)
✓ G0 (不相关):      2.0% (仅 11 个片段)
```

#### 分级分布

| Grade | 数量 | 比例 | 说明 |
|-------|------|------|------|
| G2 (高度相关) | 104 | 18.8% | 目标特征是主要逻辑 |
| G1 (部分相关) | 439 | 79.2% | 包含目标特征 |
| G0 (不相关) | 11 | 2.0% | 不包含目标特征 |

#### 消融实验结果

| 配置 | Binary P | Graded P | G2 | G1 | G0 |
|------|----------|----------|----|----|-----|
| **Full (AST+KW+DIFF)** | **98.0%** | **58.4%** | 104 | 439 | 11 |
| AST + Keyword | 98.0% | 58.5% | 105 | 438 | 11 |
| Keyword + Difficulty | 97.5% | 57.8% | 100 | 440 | 14 |
| Keyword Only | 97.7% | 59.2% | 115 | 426 | 13 |
| AST + Difficulty | 57.4% | 32.4% | 41 | 277 | 236 |
| AST Only | 55.8% | 32.3% | 49 | 260 | 245 |

**关键发现**：

1. ✅ **Keyword 是最重要特征**：Keyword Only 达到 97.7% Binary Precision
2. ✅ **AST 单独效果差**：AST Only 仅 55.8%，但可辅助排序
3. ✅ **Full 配置稳定**：98.0% Binary Precision，nDCG=0.874
4. ✅ **Difficulty 提升用户体验**：不主导排序但增强个性化

**权重优化历程**：

```
旧配置 (0.5/0.4/0.1): Binary P = 96.2%
新配置 (0.2/0.7/0.1): Binary P = 98.0% (+1.8%)
```

#### 完整评估报告

📊 详细报告: [`experiments/results/report.md`](experiments/results/report.md)

报告包含：
- 消融实验详细分析
- 各知识点 Per-KP 指标
- 分级分布统计

---

## 系统架构

### 项目结构

```
java-ana-mvp/
├── frontend/                     # 前端界面（React + TypeScript）
│   ├── src/
│   │   ├── api/                  # API 封装
│   │   │   ├── client.ts         # Axios 实例（Token 自动刷新）
│   │   │   ├── auth.ts           # 认证 API
│   │   │   ├── knowledge.ts      # 知识点 API
│   │   │   ├── match.ts          # 匹配 API
│   │   │   └── user.ts           # 用户 API（历史、收藏）
│   │   ├── components/           # 通用组件
│   │   │   ├── KnowledgeTree.tsx # 知识点树（中英双语、多选）
│   │   │   ├── CodeBlock.tsx     # 代码高亮
│   │   │   ├── MatchResultCard.tsx # 结果卡片（收藏按钮）
│   │   │   ├── MatrixView.tsx    # 矩阵视图（难度分级）
│   │   │   ├── Header.tsx        # 顶部导航（用户菜单）
│   │   │   └── PrivateRoute.tsx  # 路由守卫
│   │   ├── contexts/             # React Context
│   │   │   └── AuthContext.tsx   # 认证状态管理
│   │   ├── pages/                # 页面组件
│   │   │   ├── Dashboard.tsx     # 主面板
│   │   │   ├── LoginPage.tsx     # 登录页
│   │   │   ├── RegisterPage.tsx  # 注册页
│   │   │   ├── HistoryPage.tsx   # 历史记录
│   │   │   └── FavoritesPage.tsx # 收藏列表
│   │   └── types/                # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts            # Vite 配置（含 API 代理）
│
├── api/                          # Flask API 层
│   ├── __init__.py               # Flask 应用工厂
│   ├── routes/                   # 路由模块
│   │   ├── knowledge.py          # 知识点接口
│   │   ├── match.py              # 匹配接口
│   │   ├── auth.py               # 认证接口（登录/注册/刷新）
│   │   ├── user.py               # 用户接口（历史/收藏）
│   │   └── system.py             # 系统接口（健康检查、指标）
│   ├── schemas/                  # Pydantic 数据模型
│   │   ├── common.py             # 通用响应模型
│   │   ├── knowledge.py          # 知识点模型
│   │   ├── match.py              # 匹配请求/响应模型
│   │   ├── auth.py               # 认证模型
│   │   └── user.py               # 用户模型（历史/收藏）
│   └── middleware/               # 中间件
│       ├── error_handler.py      # 异常处理（含 UnauthorizedException）
│       ├── auth.py               # JWT 认证装饰器
│       ├── metrics.py            # 性能指标
│       └── request_logger.py     # 请求日志（带脱敏）
│
├── src/                          # 核心业务逻辑
│   ├── db_manager/               # 数据库管理
│   │   ├── base.py               # 管理器基类
│   │   ├── database.py           # 表结构初始化（含 users, match_history, favorites）
│   │   ├── knowledge_point_manager.py  # 知识点 CRUD
│   │   └── code_library_manager.py     # 代码片段 CRUD
│   ├── java_analyzer/            # AST 分析
│   │   ├── analyzer.py           # tree-sitter 解析
│   │   └── constants.py          # 关键词、别名定义
│   ├── matching/                 # 匹配策略
│   │   ├── strategies.py         # 混合打分算法
│   │   └── utils.py              # 匹配工具函数
│   └── services/                 # 服务层
│       ├── search_service.py     # 检索服务
│       ├── knowledge_service.py  # 知识点服务
│       ├── auth_service.py       # 认证服务（含单设备登录）
│       └── user_service.py       # 用户服务（历史/收藏）
│
├── experiments/                  # 评估实验
│   ├── datasets/                 # 数据集
│   │   ├── cache/                # 原始数据缓存
│   │   └── processed/            # 处理后数据
│   ├── evaluation/               # 评估框架
│   │   └── rules.py              # 分级规则定义（56 条 KP 规则）
│   └── results/                  # 评估结果
│       ├── report.md             # 可读报告
│       └── report.json           # 结构化数据
│
├── scripts/                      # 用户脚本（仅暴露 2 个入口）
│   ├── setup_database.py         # 数据库设置统一入口 ⭐
│   ├── run_experiments.py        # 实验评估统一入口 ⭐
│   └── _internal/                # 内部实现（用户不直接调用）
│       ├── run_evaluation.py     # 评估执行脚本
│       ├── init/                 # 初始化模块
│       │   ├── init_schema.py    # 数据库表结构
│       │   ├── load_knowledge_points.py  # 加载知识点
│       │   └── analyze_sample_code.py    # 分析示例代码
│       └── import_utils/         # 导入工具
│           ├── file_discovery.py # 文件发现
│           ├── hash_utils.py     # 哈希工具
│           ├── import_code_repos.py      # 项目导入
│           └── import_codesearchnet_to_db.py  # 数据集导入
│
├── lib/                          # 基础设施
│   ├── client/                   # 客户端
│   │   └── db.py                 # MySQL 连接池
│   ├── globals/                  # 全局配置和日志
│   │   └── __init__.py           # Cfg 单例、logger 实例
│   └── utils/                    # 工具模块
│       ├── settings.py           # YAML 配置解析
│       ├── sanitize.py           # 日志脱敏
│       └── matching_config.py    # 匹配参数配置
│
├── config/                       # 配置文件
│   ├── db.yaml                   # 数据库配置
│   ├── logger.yaml               # 日志配置
│   └── matching.yaml             # 匹配参数配置
│
├── openspec/                     # 项目提案和设计文档
│   ├── specs/                    # 系统规格说明
│   │   ├── frontend-ui/          # 前端 UI 规格
│   │   ├── user-auth/            # 用户认证规格
│   │   ├── api-service/          # API 服务规格
│   │   └── ...
│   └── changes/archive/          # 已归档的变更提案
│
├── run_api.py                    # API 服务入口 ⭐
├── .env.example                  # 环境变量模板
├── sample_code.java              # 示例代码
├── kp_dml.sql                    # 知识点预置数据
├── CLAUDE.md                     # 详细开发文档
└── CHANGELOG.md                  # 版本更新历史
```

### 核心数据流

**1. 代码导入流程**

```
Java 文件
    ↓ (tree-sitter 解析)
AST 树
    ↓ (特征提取)
{ast_features, keywords, difficulty}
    ↓ (数据库存储)
code_snippets 表
```

**2. 匹配查询流程**

```
用户查询 (kp_id)
    ↓ (获取 KP 模板)
{ast_template, keywords}
    ↓ (数据库查询候选)
候选代码片段 (20,022 个)
    ↓ (混合打分)
AST 得分 + Keyword 得分 + Difficulty 得分
    ↓ (过滤排序)
Top-K 结果
```

---

## API 接口

### 匹配接口

#### 单个知识点匹配

```bash
POST /api/match
Content-Type: application/json

{
  "kp_id": 10011,
  "target_difficulty": 0.5,
  "top_k": 5,
  "ast_min_ratio": 0.4,
  "keyword_min_score": 0.4,
  "w_ast": 0.2,
  "w_keyword": 0.7,
  "w_difficulty": 0.1
}
```

**响应示例**:
```json
{
  "code": 200,
  "kp_id": 10011,
  "total": 3,
  "data": [
    {
      "id": 1,
      "content": "for (int i = 0; i < 10; i++) { ... }",
      "score": 0.85,
      "ast_score": 0.90,
      "keyword_score": 0.75,
      "difficulty": 0.55
    }
  ]
}
```

#### 综合知识点匹配

```bash
POST /api/match/composite
Content-Type: application/json

{
  "kp_ids": [10011, 10012, 10034],
  "score_aggregation": "average"  # 或 "min", "sum"
}
```

#### 矩阵匹配（按难度分级）

按难度级别（easy/medium/hard）分组返回匹配结果，适合教育场景按学习者水平推荐代码示例。

```bash
# 单知识点矩阵匹配
POST /api/match/matrix
Content-Type: application/json

{
  "kp_id": 10011,
  "per_level": 5
}
```

**响应示例**:
```json
{
  "code": 200,
  "kp_id": 10011,
  "shape": [3, 5],
  "levels": ["easy", "medium", "hard"],
  "per_level": 5,
  "matrix": {
    "easy": [{"id": 1, "score": 0.92, "difficulty": 0.25, ...}],
    "medium": [{"id": 5, "score": 0.88, "difficulty": 0.45, ...}],
    "hard": [{"id": 12, "score": 0.85, "difficulty": 0.78, ...}]
  },
  "total": 12
}
```

```bash
# 综合知识点矩阵匹配
POST /api/match/composite/matrix
Content-Type: application/json

{
  "kp_ids": [10011, 10012],
  "per_level": 5,
  "score_aggregation": "average"
}
```

**矩阵模式特点**：
- 难度作为分类维度（行标签），不参与打分
- 打分公式：`score = 0.22×AST + 0.78×关键词`（归一化后移除难度权重）
- 每个难度级别内按语义相关性排序

#### 其他接口

- `GET /api/knowledge/tree` - 获取知识点树状结构
- `GET /api/knowledge/{id}` - 获取知识点详情
- `POST /api/match/batch` - 批量知识点匹配
- `GET /api/match/health` - 服务健康检查

#### 认证接口

```bash
# 用户注册
POST /api/auth/register
Content-Type: application/json

{
  "username": "user1",
  "password": "password123",
  "email": "user@example.com"  # 可选
}
```

```bash
# 用户登录
POST /api/auth/login
Content-Type: application/json

{
  "username": "user1",
  "password": "password123"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

```bash
# Token 刷新
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

#### 用户接口（需认证）

```bash
# 获取匹配历史
GET /api/user/history?page=1&page_size=20
Authorization: Bearer {access_token}
```

```bash
# 获取收藏列表
GET /api/user/favorites?page=1&page_size=20
Authorization: Bearer {access_token}
```

```bash
# 添加收藏
POST /api/user/favorites
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "snippet_id": 12345
}
```

```bash
# 取消收藏
DELETE /api/user/favorites/12345
Authorization: Bearer {access_token}
```

```bash
# 获取收藏 ID 列表（轻量接口）
GET /api/user/favorites/ids
Authorization: Bearer {access_token}
```

详细 API 文档见 [`CLAUDE.md`](CLAUDE.md#api-routes)

---

## 核心算法

### 三维度混合打分

```python
final_score = w_ast × ast_score + w_kw × keyword_score + w_diff × difficulty_score
```

**默认权重** (生产配置 v1.3.4):
- AST (结构): 20% - 辅助排序，避免噪声
- Keyword (语义): 70% - 最重要特征
- Difficulty (难度): 10% - 用户体验增强

### 关键技术

#### 1. 领域锚点 (Domain Anchors)

防止跨类型误匹配：

```python
DOMAIN_ANCHORS = {
    "list", "arraylist", "linkedlist",
    "set", "hashset", "treeset",
    "map", "hashmap", "treemap"
}

# 如果 KP 关键词包含锚点，代码必须命中至少一个
if has_domain_anchors and not any(anchor in snippet_kw for anchor in anchors):
    return 0.0  # 过滤掉
```

#### 2. 别名归一化 (Canonical Aliases)

```python
CANONICAL_ALIASES = {
    "System.out.println": "println",
    "Arrays.asList": "asList",
    "Collections.sort": "sort"
}

# 确保静态导入和全限定名的一致性
```

#### 3. 智能兜底机制

```python
# 首次查询返回 0 结果
if len(results) == 0 and thresholds_not_zero:
    # 自动降低阈值 50% 重试
    results = search(ast_min_ratio * 0.5, keyword_min_score * 0.5)
```

---

## 开发指南

### 添加新的匹配算法

1. 在 `src/matching/strategies.py` 中添加新函数
2. 更新 `calculate_match_score()` 调用新函数
3. 在 `api/schemas/match.py` 中添加新参数
4. 运行评估验证效果：`python scripts/run_experiments.py`

### 添加新知识点

1. 在 `kp_dml.sql` 中添加知识点数据
2. 定义 `ast_template.required_nodes` 和 `keywords`
3. 运行 `python scripts/setup_database.py --load-kp` 重新加载
4. 准备对应的代码样例并导入

### 导入新的代码数据集

```bash
# 方法1: 导入整个项目
python scripts/setup_database.py --import-project /path/to/project

# 方法2: 添加新数据集（需要修改 _internal/import_utils/）
# 1. 创建新的导入脚本 import_xxx.py
# 2. 在 setup_database.py 中添加新选项
# 3. 运行导入
```

---

## 常见问题

**Q: 数据库初始化失败？**
A: 检查 `config/db.yaml` 配置，确保 MySQL 服务启动，用户有创建数据库权限。

**Q: API 调用时如何禁用 Difficulty？**
A: 在请求中设置 `w_difficulty: 0.0` 或不传 `target_difficulty` 参数。

**Q: 如何提高匹配准确率？**
A: 当前默认配置（AST=0.2, KW=0.7, DIFF=0.1）已达到 98% Binary Precision。如需纯语义匹配，可设置 `{"w_ast": 0.0, "w_keyword": 1.0, "w_difficulty": 0.0}`。

**Q: 导入的用户代码会覆盖数据集吗？**
A: 不会。用户代码和数据集代码存储在同一表，通过 `source` 字段区分，统一检索。

---

## 依赖说明

### 后端依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Flask | 3.x | Web 框架 |
| flask-cors | - | 跨域支持 |
| Pydantic | 2.x | 数据校验 |
| mysql-connector-python | 8.x | MySQL 驱动 |
| tree-sitter | 0.20.x | AST 解析 |
| tree-sitter-java | - | Java 语法 |
| PyJWT | 2.x | JWT Token |
| bcrypt | 4.x | 密码哈希 |
| python-dotenv | 1.x | 环境变量 |
| PyYAML | 6.x | 配置解析 |
| scikit-learn | 1.x | 评估基线方法 |

### 前端依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| react | ^18.2.0 | UI 框架 |
| react-dom | ^18.2.0 | DOM 渲染 |
| react-router-dom | ^6.x | 路由管理 |
| antd | ^5.x | UI 组件库 |
| axios | ^1.x | HTTP 客户端 |
| react-syntax-highlighter | ^15.x | 代码高亮 |
| typescript | ^5.x | 类型检查 |
| vite | ^5.x | 构建工具 |

---

## 文档说明

- **README.md** (本文件) - 项目概览、快速开始、实验评估
- **CLAUDE.md** - 详细开发文档，架构设计、数据流、开发工作流
- **experiments/results/report.md** - 完整实验评估报告
- **CHANGELOG.md** - 版本更新历史
- **openspec/** - 项目提案和设计文档

---

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.5.0 | 2026-03-01 | 完整前端界面（用户认证、历史收藏、矩阵/组合匹配） |
| v1.4.0 | 2026-02-28 | 前端界面 MVP（知识点树、列表匹配、中英双语） |
| v1.3.5 | 2026-02-24 | 矩阵匹配模式（按难度分级返回），权重归一化 |
| v1.3.4 | 2026-02-07 | 分级评估重构，权重优化（AST=0.2, KW=0.7），Binary P 98.0% |
| v1.3.3 | 2026-02-07 | 非叶子节点校验、数据库备份、多知识点匹配修复 |
| v1.3.1 | 2026-01-31 | 移除异步导入 API（简化架构，CLI 脚本足够使用） |
| v1.3.0 | 2026-01-31 | 新增批量项目导入、修复代码分析 bug、完善文档 |
| v1.2.6 | 2026-01-25 | scripts 重构、目录整理、评估数据集更新 |
| v1.2.4 | 2026-01-18 | 兜底逻辑优化、权重 fix、评估报告完善 |

详细变更记录见 [CHANGELOG.md](CHANGELOG.md)

---

## 许可证

MIT License

---

**项目地址**: [GitHub Repository]
**文档**: [完整文档](CLAUDE.md) | [实验报告](experiments/results/report.md)
**作者**: BUPT Graduation Design 2026
