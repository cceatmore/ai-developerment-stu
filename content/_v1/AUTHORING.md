# 课程内容编写规范

本目录是「AI 应用开发工程师 50 天训练系统」的全部学习内容。系统运行时**不调用任何 AI 接口**，所有讲解、题目、参考答案、评分要点都来自这里的 YAML 文件，所以内容质量就是产品质量。

## 1. 学员画像（决定讲法）

- 软件工程专业，有前端/全栈工作经验，做过需求沟通、接口集成、部署和现场调试。
- 熟悉 Cursor 等 AI 编程工具，目前主要靠 AI 写代码，自己写 Prompt、拆需求、验收；**几乎不读代码**，对内部实现、异常处理、底层逻辑掌握不足。
- Python 基础较弱，其他语言有一定经验（可以用 JavaScript/TypeScript 做类比）。
- 目标岗位：AI 应用开发 / AI Agent 开发 / 大模型应用开发 / Python AI 后端 / 企业 AI 解决方案。
- 每天 60 分钟：讲解 20 分钟、互动提问 10 分钟、代码理解 10 分钟、面试训练 15 分钟、总结 5 分钟。
- 有阅读障碍倾向：**段落短、重点加粗、多用列表和图**，但不能为了短而省略原理。

讲法要求：
- 不从计算机基础重新讲起，不教怎么手写简单代码。
- 先讲概念（用人话），再讲原理（为什么这样设计、内部怎么运转），最后讲工程应用。
- 每个知识点都要回答「不这样做会怎样」。
- 不要只教框架用法，要讲清框架背后的机制。
- 不要把大模型训练、复杂数学推导、微调算法作为重点（Transformer/Attention 讲到「能在面试中讲清楚直觉和计算流程」即可）。

## 2. 技术准确性（最重要）

- **不能编造技术事实**。API 名称、参数、版本号、默认值必须来自官方文档或可靠资料；拿不准的写明「不确定 / 以官方文档为准」。
- 变化快的主题（LLM API 结构化输出、Function Calling 格式、OpenAI Responses API、LangChain / LangGraph 版本与 API、MCP 规范版本与传输方式、pgvector 索引类型、Python 3.13+ free-threading、FastAPI/Pydantic v2 写法等）**必须先用 WebSearch / WebFetch 检索最新官方资料**，然后：
  - 在知识点的 `freshness` 字段写明：核对日期（2026-11）、对应版本、旧写法 vs 新写法。
  - 在 `sources` 里列出官方文档链接（只放你实际打开或检索到的链接）。
- 不要把过时写法当最佳实践（例如：LangChain 旧的 `LLMChain`/`initialize_agent`、Pydantic v1 的 `class Config`/`.dict()`、FastAPI 的 `@app.on_event`、OpenAI SDK 0.x 的 `openai.ChatCompletion.create`）。如需提及，明确标注「旧写法」。
- 代码示例尽量可运行：写全 import，使用当前主流版本 API；依赖外部服务的地方（API Key、数据库）用环境变量并说明。

## 3. 文件结构

每天一个文件：`content/days/dayNN.yaml`（NN 两位数）。顶层字段：

| 字段 | 说明 |
|---|---|
| `day` / `phase` | 天数；阶段 = (day-1)//10+1 |
| `title` | 当天主题 |
| `goals` | 学习目标，2~4 条，可检验（「能解释…」「能分析…」） |
| `knowledge_points` | 3~5 个知识点，至少 1 个 P0 |
| `quiz` | 互动提问 5~8 题：≥2 道客观题（single/multi/judge），≥3 道主观题，其中 ≥1 道 scenario 或 design；每个 P0 知识点至少被 1 道题覆盖 |
| `code_reading` | 1 段代码阅读材料 + 2~3 道代码理解题 |
| `interview` | 4~5 道面试题，difficulty 非递减（1 基础 → 4 工程/架构深挖） |
| `sources` | 当天的参考资料（可选） |

### 3.1 知识点字段（对应讲解的 9 个部分）

| 字段 | 讲解部分 | 最低长度 |
|---|---|---|
| `name` | 1. 知识点名称 | — |
| `level` | P0 必须掌握 / P1 理解原理和场景 / P2 了解即可 | — |
| `summary` | 简短易记的一句话总结 | 8~120 字 |
| `why` | 2. 为什么需要学习它 | 50 字 |
| `problem` | 3. 它解决什么问题 | 50 字 |
| `principle` | 4. 核心原理（Markdown，可含 mermaid 图） | P0 400 / P1 250 / P2 120 字 |
| `scenarios` | 5. 实际工作中的应用场景 | 60 字 |
| `code` | 6. 代码示例（适用时，Markdown 代码块） | 可选 |
| `pitfalls` | 7. 常见错误和容易混淆的地方 | 80 字 |
| `interview_asks` | 8. 面试官可能怎么提问（≥2 条） | — |
| `project_example` | 9. 一个实际项目中的例子 | 80 字 |
| `freshness` | 时效说明（变化快的主题必填） | 可选 |
| `sources` | `[{title, url}]` | 可选 |

P0 知识点的 `principle` 实际上应该写到 800~1500 字，最低长度只是校验底线。

### 3.2 题目字段

所有题目共用结构：

```yaml
- id: d21-q1          # 互动提问 dNN-qN；面试 dNN-iN；代码题 dNN-cN-qN
  kp: d21-k1          # 关联知识点（必填，用于复习调度和掌握度计算）
  type: single        # single | multi | judge | short | scenario | code | design | oral
  question: 题干（Markdown）
  options: [A 文本, B 文本, C 文本, D 文本]   # 仅 single/multi，不要写 "A." 前缀
  answer: [1]         # single/multi 填选项下标（从 0 开始）；judge 填 true/false
  explain: 解析       # 客观题必填 ≥40 字：为什么对、其他选项错在哪
  key_points:         # 主观题必填 ≥3 条（面试题 ≥4 条）
    - {text: 评分要点, dim: concept}     # dim: concept 概念 | principle 原理 | project 结合项目 | engineering 工程思维
  reference: 参考答案  # 主观题必填 ≥120 字（面试题 ≥200 字）
  followup:            # 可选但推荐：答得不完整时的追问
    question: 追问
    key_points: [要点1, 要点2]
    reference: 追问参考答案
  difficulty: 2        # 仅面试题：1~4
  oral: 口头表达版      # 仅面试题必填 ≥120 字：适合面试时说出口的 1~2 分钟版本，第一人称，有结构（先结论再展开），尽量带一个项目例子
  category: rag        # 可选：python_backend | llm | rag | agent | mcp | engineering | architecture（默认按天数推断）
```

评分要点写法：
- 每条要点是**可判断对错的具体陈述**，而不是「理解了 RAG」这种空话。好的例子：「指出向量相似度只衡量语义接近，不保证片段包含答案」。
- 要点覆盖四个维度，面试题至少包含 1 条 `project` 或 `engineering`。
- 学员会先写答案，再对照要点逐条自评，所以要点要能让人对照判断「我说到了没有」。

客观题要求：干扰项必须是**真实常见的误解**，不能一眼看出错误。多选题至少 2 个正确答案。

### 3.3 代码阅读

```yaml
code_reading:
  id: d21-c1
  kp: [d21-k1, d21-k2]
  title: 最小 RAG 问答管道
  scenario: 场景描述（谁调用、在什么业务里）
  language: python
  code: |
    （15~60 行，真实工程风格：类型注解、异常处理、日志；与当天主题强相关）
  walkthrough:
    function: 这段代码实现什么功能
    key_functions: 每个关键函数负责什么
    params: 参数如何传递
    data_flow: 数据如何流动（可用 mermaid）
    failure_points: 哪些地方可能出错（超时、空结果、类型错误、外部服务失败…）
    debugging: 如何调试（看哪些日志、打什么断点、怎么复现）
    change_request: 如果需求改成 XXX，应该改哪里
  questions:          # 2~3 道，type 用 code，要求解释执行过程，不能是选择题
    - id: d21-c1-q1
      kp: d21-k1
      type: code
      question: 按执行顺序说明…
      key_points: [...]
      reference: ...
```

代码复杂度随天数递增：第 1 阶段是 Python/FastAPI/SQL 片段；第 2 阶段加入 LLM 调用、重试、结构化输出；第 3 阶段是 RAG 组件；第 4 阶段是 LangGraph/MCP/Agent 循环；第 5 阶段是带 Redis、队列、鉴权、监控的生产级片段。代码里要**故意保留 1~2 个值得审查的问题**（例如缺少超时、异常被吞掉、权限没校验），并在 failure_points 和题目里引导学员找出来。

## 4. Markdown 与图

- 字段内容是 Markdown：可以用 **加粗**、列表、表格、代码块。
- 复杂流程、架构、数据流**必须配图**，使用 mermaid 代码块。只允许 `flowchart`、`sequenceDiagram`、`stateDiagram-v2`、`classDiagram`、`erDiagram`。
- mermaid 节点文字一律用双引号包住：`A["用户问题"] --> B["向量检索 Top-K"]`；节点文字里不要出现双引号、尖括号和分号；sequenceDiagram 的参与者用 `participant U as 用户`。
- 每天至少 2 张图（principle 或 walkthrough.data_flow 中）。

## 5. YAML 注意事项

- 长文本一律用 `|` 块，缩进用空格，不用 Tab。
- 单行字符串里含有 `: `、`#`、`[`、`{`、引号开头等字符时，用双引号包住，或改用 `|` 块。
- `options` 中每个选项如有冒号也要加引号。
- 写完立刻校验（在 `backend` 目录）：`uv run python -m app.validate 21`，必须输出 `OK` 才算完成。

## 6. 示例（节选，展示格式；实际内容要满足长度要求）

```yaml
day: 21
phase: 3
title: RAG 原理
goals:
  - 能用自己的话讲清 RAG 的完整流程（离线入库 + 在线问答）
  - 能解释为什么不能把所有文档直接塞进 Prompt
knowledge_points:
  - id: d21-k1
    name: 为什么需要 RAG
    level: P0
    summary: 上下文窗口装得下不等于模型用得好；RAG 只把相关证据交给模型
    why: |
      企业问答、客服、内部助手……
    problem: |
      ……
    principle: |
      **一、模型知识的两个天然缺陷**……

      ```mermaid
      flowchart LR
        A["文档"] --> B["解析与切片"] --> C["Embedding"] --> D[("向量库")]
        Q["用户问题"] --> E["问题向量化"] --> F["Top-K 检索"]
        D --> F --> G["拼接 Prompt"] --> H["LLM 生成带引用的回答"]
      ```
    scenarios: |
      ……
    pitfalls: |
      - **误区：相似度高 = 答案正确。**……
    interview_asks:
      - 你们为什么用 RAG 而不是微调？
      - 上下文窗口已经 100 万 Token 了，还需要 RAG 吗？
    project_example: |
      ……
    freshness: 核对于 2026-11：……
    sources:
      - {title: "OpenAI Docs - Retrieval", url: "https://platform.openai.com/docs/..."}
quiz:
  - id: d21-q1
    kp: d21-k1
    type: judge
    question: 只要模型的上下文窗口足够大，就可以不用 RAG，把全部文档放进 Prompt 效果一定更好。
    answer: false
    explain: ……
  - id: d21-q2
    kp: d21-k1
    type: scenario
    question: 用户问「2024 年差旅报销标准」，系统却引用了 2021 年的旧制度。可能是哪些环节的问题？如何修复？
    key_points:
      - {text: "指出两份制度语义相近，向量相似度无法区分年份", dim: principle}
      - {text: "提出入库时记录年份/版本等 metadata 并在检索时过滤", dim: engineering}
      - {text: "提出旧版本文档下线或标记失效的数据更新机制", dim: engineering}
    reference: |
      ……
    followup:
      question: 如果只能改一处，你会改入库阶段还是检索阶段？为什么？
      key_points: [入库阶段补 metadata 是根因修复]
      reference: ……
interview:
  - id: d21-i1
    kp: d21-k1
    type: oral
    difficulty: 1
    question: 什么是 RAG？它解决了什么问题？
    key_points: [...]
    reference: |
      ……
    oral: |
      ……
```

## 7. 50 天课程总表（避免重复、保证衔接）

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 01 | Python 基础与运行机制 | Python 特点、解释执行、变量、数据类型 |
| 02 | Python 数据结构 | list、tuple、dict、set、可变与不可变 |
| 03 | 函数与面向对象 | 函数、参数、返回值、类、继承、封装 |
| 04 | Python 工程基础 | 模块、包、异常处理、虚拟环境、依赖管理 |
| 05 | Python 进阶 | 装饰器、生成器、迭代器、上下文管理器 |
| 06 | Python 并发 | 同步与异步、async/await、asyncio |
| 07 | Python 运行机制 | GIL、线程、进程、协程、适用场景 |
| 08 | HTTP 与 API | HTTP 方法、状态码、请求响应、JSON、RESTful |
| 09 | FastAPI | 路由、依赖注入、Pydantic、请求校验 |
| 10 | 数据库 | SQL、PostgreSQL、索引、事务、ORM |
| 11 | 大语言模型基础 | LLM、预训练、推理、模型能力边界 |
| 12 | Transformer | Transformer 架构、Attention、自注意力机制 |
| 13 | Token 与上下文 | Token、上下文窗口、Token 计算、上下文限制 |
| 14 | Embedding | 向量表示、语义空间、相似度 |
| 15 | Prompt Engineering | System Prompt、User Prompt、上下文设计 |
| 16 | 模型参数 | Temperature、Top-P、模型参数与输出差异 |
| 17 | LLM API | API 调用、流式响应、SSE、错误处理 |
| 18 | Function Calling | 工具调用原理、工具定义、参数 Schema |
| 19 | Structured Output | JSON Schema、结构化输出、Pydantic 校验 |
| 20 | LLM 工程实践 | 超时、重试、限流、Token 成本、模型选择 |
| 21 | RAG 原理 | RAG 的定义、解决的问题、完整流程 |
| 22 | 文档处理 | PDF、Word、TXT、文档解析 |
| 23 | 文本切片 | Chunk、Chunk Size、Overlap、切片策略 |
| 24 | Embedding 实践 | 文本向量化、向量维度、相似度计算 |
| 25 | 向量数据库 | pgvector、向量存储、索引 |
| 26 | 检索机制 | Top-K、相似度检索、混合检索 |
| 27 | RAG 优化 | Rerank、Query Rewrite、Metadata Filter |
| 28 | RAG 生成 | Prompt 组装、上下文注入、引用来源 |
| 29 | RAG 评估 | Recall、Precision、Faithfulness、检索评估 |
| 30 | RAG 综合架构 | 企业知识库完整架构、性能与安全、权限隔离、数据更新 |
| 31 | Agent 基础 | Agent 定义、与普通 LLM 应用的区别 |
| 32 | Agent 核心机制 | ReAct、思考、行动、观察 |
| 33 | Tool Calling | 工具注册、工具执行、结果反馈 |
| 34 | LangChain | 核心组件、Runnable、链式调用 |
| 35 | LangGraph | State、Node、Edge、Graph |
| 36 | LangGraph 进阶 | Checkpoint、持久化、断点恢复 |
| 37 | Agent 控制机制 | 循环、终止条件、超时、重试 |
| 38 | MCP | MCP 架构、Host、Client、Server、Tools、Resources |
| 39 | 多 Agent | 多 Agent 协作、任务分配、通信与协调 |
| 40 | Agent 安全 | 权限控制、Prompt Injection、人工确认 |
| 41 | Redis | 缓存、会话、过期机制、常见应用 |
| 42 | 异步任务 | 任务队列、后台任务、消息队列 |
| 43 | 实时通信 | SSE、WebSocket、流式输出 |
| 44 | Docker | 镜像、容器、Docker Compose、部署 |
| 45 | 后端安全 | JWT、鉴权、RBAC、接口权限 |
| 46 | 系统性能 | 并发、限流、缓存、数据库优化 |
| 47 | AI 应用安全 | 数据泄露、Prompt Injection、工具权限、敏感信息 |
| 48 | AI 应用评估 | 自动化测试、评估集、回归测试、日志与监控 |
| 49 | 系统架构设计 | RAG + Agent + 数据库 + Redis 综合架构 |
| 50 | 综合模拟面试 | 全面考核、薄弱项分析、求职能力评估 |

衔接原则：后面的天数可以引用前面学过的概念（一句话带过并说明「见 Day NN」），不要重复展开；Day 10/20/30/40/50 的面试题要有阶段综合性质。
