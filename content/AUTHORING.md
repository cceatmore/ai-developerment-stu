# 课程内容编写规范（v2）

本目录是「AI 应用 + AI Agent 开发工程师 50 天训练系统」的全部学习内容。系统运行时**不调用任何 AI 接口**，所有讲解、题目、答案都来自这里的 YAML，**内容质量就是产品质量**。

旧版内容在 `content/_v1/`（只作素材参考，不会被加载）。主题重合时可以复用其中准确的讲解，但要按本规范重写题目。

## 1. 学员画像（决定讲法）

- 5 年以上前端经验，做过前端技术负责人：**Vue2/Vue3 + TypeScript、uniapp 小程序、ECharts 大屏、地图 SDK、视频流播放、权限指令、axios 封装与无感刷新令牌、Node 中间层、nginx 部署、Vite 构建优化**。行业：智慧园区 / 智慧体育 SaaS、CRM 报价系统。
- 熟悉 AI 编程工具，主要靠 AI 写代码，**很少读代码**；Python 基础弱；了解 Java 基础和 Linux 常用命令。
- 求职方向：**AI 应用开发工程师 和 AI Agent 开发工程师 两类都要面**。
- 时间不固定：每天至少 1 小时碎片时间，有时 3 小时；只在工作日学，周一或休息后回来会先做较多复习。
- 有阅读障碍倾向：**段落短、重点加粗、多用列表、表格和图**；但不能为了短而省略原理。

## 2. 学习方法（参考的主流课程，讲法必须遵守）

调研了 Datawhale《Hello-Agents》、李宏毅《生成式 AI 导论》、吴恩达 DeepLearning.AI《Agentic AI》、Hugging Face Agents Course、LangChain Academy《Introduction to LangGraph》、Anthropic《Building effective agents》等，共同的有效做法：

1. **先直觉，后原理**：先用一个生活或前端例子讲清「它是什么、为什么要有它」，再讲内部怎么运转。
2. **先手写最小版本，再学框架**：Agent 循环、RAG、工具调用都先讲「不用框架时代码长什么样」，再讲 LangChain/LangGraph 帮你做了什么。
3. **前端类比**（`analogy` 字段）：能类比就类比。例：async/await ↔ Promise；Pydantic ↔ zod；FastAPI 依赖注入 ↔ Vue provide/inject 或 axios 拦截器；SSE ↔ EventSource；LangGraph State ↔ Pinia store + 状态机；工具 Schema ↔ TS 接口；RBAC ↔ 前端权限指令。类比之后必须说明**不一样的地方**。
4. **一个项目贯穿**：讲解里的 `project_example` 尽量落到三个实践项目（见第 8 节）。
5. **测验驱动**：每天的知识点都要能被选择题检验；面试题以场景题为主。

## 3. 技术准确性（最重要）

- **不能编造技术事实**。API 名称、参数、版本号、默认值必须来自官方文档或可靠资料；拿不准的写明「以官方文档为准」。
- 变化快的主题（OpenAI Responses/Chat Completions、结构化输出、Function Calling、DeepSeek/通义的 OpenAI 兼容接口、LangChain v1 / LangGraph 1.x API、MCP 规范版本与 Streamable HTTP 传输、A2A、Agent Skills、Langfuse/LangSmith、RAGAS、pgvector 索引、FastAPI/Pydantic v2 写法、Python 3.13+）**必须先用 WebSearch / WebFetch 检索最新官方资料**，然后在 `freshness` 写明核对日期（2026-11）、版本、旧写法 vs 新写法，在 `sources` 列出实际打开过的链接。
- 不要把过时写法当最佳实践（LangChain 的 `LLMChain` / `initialize_agent`、Pydantic v1 的 `class Config` / `.dict()`、FastAPI `@app.on_event`、OpenAI SDK 0.x 的 `openai.ChatCompletion.create`、MCP 旧的 HTTP+SSE 传输）。需要提及时标注「旧写法」。
- 代码示例写全 import，用当前主流 API；API Key 等用环境变量。

## 4. 配套资源 `resources`（1~4 条）

- 只放**真实存在、你用 WebSearch/WebFetch 核实过**的链接；优先中文、免费、口碑好的：Hello-Agents（GitHub / datawhale.cn）、李宏毅课程（官网或 B 站官方/授权搬运）、吴恩达课程（deeplearning.ai）、HF Agents Course、LangChain Academy、官方文档（FastAPI、Pydantic、OpenAI、Anthropic、MCP、LangGraph、pgvector、Langfuse）。
- `note` 写清楚**看哪一章/哪一段、看完能解决今天哪个疑问**。`minutes` 写建议观看/阅读时长。
- 资源是**选看**的，讲解本身必须自洽，不看资源也能学会。

```yaml
resources:
  - title: "Hello-Agents 第四章 智能体经典范式构建"
    url: "https://github.com/datawhalechina/hello-agents"
    kind: repo        # video | article | doc | course | repo
    lang: zh          # zh | en
    minutes: 30
    note: "只看 4.2 ReAct 小节，对照今天的手写 Agent 循环"
```

## 5. 每天的文件 `content/days/dayNN.yaml`

| 字段 | 要求 |
|---|---|
| `day` / `phase` | 天数；阶段 = (day-1)//10+1 |
| `title` | 当天主题 |
| `goals` | 2~4 条可检验的目标（「能解释…」「能判断…」） |
| `minutes` | 预计总时长（核心流程，通常 60） |
| `resources` | 见第 4 节 |
| `knowledge_points` | **3~4 个**，至少 1 个 P0；每个知识点读 5~7 分钟 |
| `test` | 当天测试题池 **16~22 道，全部客观题**：≥7 单选、≥3 多选、≥3 判断；**每个知识点 ≥3 题**；≥1 道读代码题（`code` 字段）。系统每次抽 12 道，≥70 分解锁下一天，没过就换题重测 |
| `exam` | 阶段卷题池 **恰好 9 道**：4 单选 + 2 多选 + 2 判断 + 1 案例（`case`）。**不要和 test 重复或只改几个字**，难度略高于 test，偏综合 |
| `interview` | **恰好 3 道**面试官题，难度非递减，**至少 2 道 `scenario` 或 `design`**（面试官爱出场景题） |

### 5.1 知识点（对应讲解的 9 个部分）

| 字段 | 讲解部分 | 最低长度 |
|---|---|---|
| `name` | 1. 名称 | — |
| `level` | P0 必须掌握 / P1 理解原理和场景 / P2 了解 | — |
| `summary` | 一句话记住它 | 8~120 字 |
| `analogy` | 前端类比 + 不一样的地方（可选，能类比就写） | — |
| `why` | 2. 为什么要学 | 50 字 |
| `problem` | 3. 解决什么问题 | 50 字 |
| `principle` | 4. 核心原理（Markdown + mermaid） | P0 400 / P1 250 / P2 120 字；P0 实际写 800~1500 字 |
| `scenarios` | 5. 工作中的应用场景 | 60 字 |
| `code` | 6. 代码示例（Markdown 代码块，可选） | — |
| `pitfalls` | 7. 常见错误与易混淆点 | 80 字 |
| `interview_asks` | 8. 面试官可能怎么问（≥2 条），每条带能说出口的短答案 | question + answer |
| `project_example` | 9. 在实践项目里怎么用 | 80 字 |
| `freshness` / `sources` | 时效说明 / 官方链接 | 变化快的主题必填 |

### 5.2 题目

```yaml
- id: d21-t1            # test: dNN-tN；exam: dNN-eN；interview: dNN-iN
  kp: d21-k1            # 必填
  type: single          # single | multi | judge | case（以上为客观题）| scenario | design | short | oral
  question: 题干（Markdown）
  code: |               # 可选：读代码题的代码（≥4 行），题干问「输出什么 / 哪里有问题 / 改哪里」
    ...
  lang: python
  options: [选项, 选项, 选项, 选项]   # single/multi/case；不要写 "A." 前缀；含冒号时加引号
  answer: [1]           # 选项下标（从 0 开始）；judge 填 true/false
  explain: 解析          # 客观题必填 ≥40 字：为什么对 + 其他选项错在哪
```

客观题要求：
- 考**理解和判断**，不考死记（不要问「某参数默认值是多少」这种）。
- 干扰项必须是**真实常见的误解**，不能一眼看出错。选项长度相近，不要让正确答案总是最长的那个。
- 正确答案位置要分散（不要总是 B）。多选题 2~4 个正确项。
- `case`：≥80 字的真实业务场景 + 「最合理的做法/根因是」，单选，5 分值。

面试题（interview）额外字段：
```yaml
  difficulty: 2         # 1~4
  key_points:           # ≥4 条，可对照判断「我说到没有」的具体陈述
    - {text: "指出向量相似度不保证包含答案", dim: principle}   # dim: concept | principle | project | engineering
  reference: |          # ≥200 字参考答案
  oral: |               # ≥120 字：面试时说出口的 1~2 分钟版本，第一人称，先结论再展开，带项目例子
```
场景题示例：「线上用户反馈 Agent 偶尔会重复下单，你怎么排查和修复？」「老板要你一周内上线一个内部知识库问答，你怎么选型、怎么证明效果？」至少 1 条要点是 `project` 或 `engineering`。

## 6. Markdown 与图

- 字段内容是 Markdown：**加粗**、列表、表格、代码块。
- 复杂流程、架构、数据流**必须配图**，用 mermaid，只允许 `flowchart`、`sequenceDiagram`、`stateDiagram-v2`、`classDiagram`、`erDiagram`。
- 节点文字一律双引号：`A["用户问题"] --> B["向量检索 Top-K"]`；节点文字里不要出现双引号、尖括号、分号；sequenceDiagram 参与者用 `participant U as 用户`。
- 每天至少 2 张图。

## 7. YAML 与校验

- 长文本用 `|` 块，空格缩进，不用 Tab。
- 单行字符串含 `: `、`#`、`[`、`{`、引号开头等字符时加双引号或改用 `|`。**行内代码里出现 `: ` 的句子（如 `class State(TypedDict): x`）必须加引号或用 `|` 块。**
- 写完在 `backend` 目录校验：`uv run python -m app.validate 21`，输出 `OK` 才算完成；项目文件：`uv run python -m app.validate p1`。

## 8. 50 天大纲（按学习日计，不按日历）

衔接原则：后面的天数引用前面的概念时一句话带过并注明「见 Day NN」，不重复展开。Day 10/20/30/40 面试题偏阶段综合；Day 50 全面综合。

### 第 1 阶段 · Python 与后端速通（对照 JS/TS 学）

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 01 | 从 JS 到 Python | 解释执行与运行方式、变量即名字绑定、动态类型与真值、uv 与虚拟环境（对照 Node/npm） |
| 02 | 数据结构 | list/tuple/dict/set、可变与不可变、切片与推导式、浅拷贝深拷贝（对照 Array/Object/Map） |
| 03 | 函数、类与类型注解 | 参数形式（*args/**kwargs/关键字）、闭包与作用域、类与 dataclass、typing 类型注解（对照 TS） |
| 04 | 工程基础 | 模块与包、异常处理与异常链、logging、配置与环境变量（.env / pydantic-settings） |
| 05 | Python 进阶语法 | 装饰器、迭代器与生成器（yield 是流式输出的基础）、上下文管理器 |
| 06 | 异步与并发 | asyncio 事件循环、async/await、gather 与超时、GIL/线程/进程怎么选 |
| 07 | HTTP 与 FastAPI | HTTP 语义与状态码、FastAPI 路由与 Pydantic v2 校验、依赖注入、统一错误处理 |
| 08 | 数据库 | SQL 与 PostgreSQL、索引与事务、SQLAlchemy 2 ORM（async）、迁移（Alembic） |
| 09 | Redis 与后台任务 | 缓存与过期、会话与限流、任务队列与幂等、消息队列基础 |
| 10 | 流式与部署（阶段综合） | SSE vs WebSocket（对照 EventSource）、StreamingResponse、Docker 镜像与 Compose |

### 第 2 阶段 · 大模型应用基础

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 11 | 大模型是怎么工作的 | 文字接龙（next token）、预训练与后训练（SFT/RLHF）、推理模型、能力边界与幻觉 |
| 12 | Transformer 直觉 | Attention 直觉与计算流程、推理过程（prefill/decode）、KV Cache 与长上下文代价 |
| 13 | Token 与上下文窗口 | 分词与计费、上下文窗口与截断、长上下文退化（lost in the middle / context rot） |
| 14 | 调用 LLM API | 消息角色、Chat Completions 与 Responses API、OpenAI 兼容接口（DeepSeek/通义）、流式与错误码 |
| 15 | Prompt 工程 | System Prompt 设计、few-shot、思维链与推理模型的提示差异、提示模板与版本管理 |
| 16 | 结构化输出 | JSON Schema 约束输出、Pydantic 校验与修复重试、结构化输出 vs JSON mode |
| 17 | Function Calling | 工具定义与参数 Schema、调用流程（模型提议→代码执行→结果回传）、并行工具调用 |
| 18 | Embedding 与相似度 | 向量表示、余弦相似度、Embedding 模型选择（多语言/维度/成本）、相似≠正确 |
| 19 | LLM 工程化 | 超时/重试/退避/熔断、限流与配额、缓存（含 prompt caching）、成本与延迟、模型路由选型 |
| 20 | 上下文工程入门（阶段综合） | 上下文由什么组成、动态组装与裁剪、评测意识第一课（小型 golden set） |

### 第 3 阶段 · RAG 与知识系统（AI 应用主线）

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 21 | RAG 全流程 | 为什么需要 RAG、离线入库与在线问答、RAG vs 长上下文 vs 微调 |
| 22 | 文档解析 | PDF/Word/表格/扫描件解析、清洗、元数据设计 |
| 23 | 切片策略 | chunk size 与 overlap、按结构切片、父子块、上下文增强切片（contextual retrieval） |
| 24 | 向量数据库 | pgvector/Milvus/Qdrant 选型、HNSW/IVF 索引、元数据过滤 |
| 25 | 混合检索 | BM25 关键词检索、向量检索、RRF 融合、Top-K 怎么定 |
| 26 | 重排与查询改写 | Cross-encoder 重排、Query Rewrite、多轮指代消解、HyDE |
| 27 | 生成与引用 | Prompt 组装与上下文注入、引用来源、拒答与防幻觉 |
| 28 | Agentic RAG | 检索决策、多跳检索、Corrective RAG、GraphRAG 了解 |
| 29 | RAG 评测 | Recall@K / MRR、Faithfulness、答案正确率、RAGAS、评测集构建 |
| 30 | 企业知识库架构（阶段综合） | 权限隔离（ACL 在检索阶段过滤）、数据更新与版本、性能与成本 |

### 第 4 阶段 · Agent 核心（Agent 主线）

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 31 | Agent 是什么 | Agent vs Workflow、常见 workflow 模式（链式/路由/并行/编排-执行/评估-优化）、什么时候不该用 Agent |
| 32 | 手写 Agent 循环 | ReAct（思考-行动-观察）、模型与代码的分工、终止条件与最大步数 |
| 33 | 工具设计与失败处理 | 工具粒度与描述、参数校验、错误回传给模型、超时/重试/幂等 |
| 34 | 规划与反思 | Plan-and-Execute、Reflection 自我纠错、任务分解 |
| 35 | 记忆与上下文管理 | 短期/长期记忆、摘要压缩与上下文卸载、记忆检索 |
| 36 | LangGraph 基础 | State/Node/Edge/Reducer、条件边、与手写循环对比（对照 Pinia + 状态机） |
| 37 | LangGraph 进阶 | Checkpoint 持久化与断点恢复、Human-in-the-loop 中断与审批、流式输出 |
| 38 | MCP | Host/Client/Server 架构、Tools/Resources/Prompts、传输（stdio / Streamable HTTP）、写一个 MCP Server |
| 39 | 多 Agent 与协议 | Supervisor / Orchestrator-Worker、子 Agent 与上下文隔离、A2A、Agent Skills |
| 40 | Agent 运行时与 Coding Agent（阶段综合） | Harness 概念（循环/工具注册/上下文组装/断点/沙箱/权限）、Coding Agent 工作原理 |

### 第 5 阶段 · 评测、生产化与求职

| 天 | 主题 | 核心知识点 |
|---|---|---|
| 41 | 评测基础 | 为什么要评测、评测集构建、指标设计、错误分析 |
| 42 | LLM-as-Judge 与轨迹评测 | rubric 设计、与人工一致性、pass@k、工具调用正确率与轨迹评分 |
| 43 | 可观测性 | Trace/Span、Langfuse/LangSmith、OpenTelemetry、日志与指标 |
| 44 | 回归与发布 | CI 评测门禁、Prompt/模型版本管理、A/B 与灰度、线上数据飞轮 |
| 45 | AI 安全 | Prompt Injection（直接/间接）、工具权限最小化、数据泄露与脱敏、Guardrails |
| 46 | 鉴权与多租户 | JWT 与刷新令牌、RBAC 与资源级授权、租户隔离、审计日志 |
| 47 | 性能与成本 | 延迟分解与首字时间、并发与限流、缓存、模型路由与 Token 预算 |
| 48 | 系统设计 | RAG + Agent + DB + Redis + 队列综合架构、面试系统设计题答题框架 |
| 49 | 项目包装与简历 | 项目叙事（背景-难点-方案-指标）、前端转 AI 的故事线、项目深挖应对 |
| 50 | 综合模拟面试 | 两类岗位高频题全覆盖、薄弱项自查清单 |

## 9. 三个实践项目 `content/projects/p1.yaml` ~ `p3.yaml`

每个模块是一个 30~90 分钟、可以让 AI 写大部分代码的步骤。模块字段：`id`（p1-m1…）、`name`、`unlock_day`、`minutes`、`features`、`goal`、`design`（≥200 字）、`data_flow`（≥80 字）、`key_code`（≥200 字，必须读懂的关键代码）、`ai_prompt`（≥120 字，直接粘给 AI 的需求说明，含约束和验收标准）、`tests`（functional/api/exception/review 四类检查项）、`retell`（主观题：用自己的话复述原理）。

项目顶层：`id`、`title`、`role`、`intro`、`market`（为什么市场需要、命中哪些 JD 关键词）、`tech_stack`、`architecture`（含 mermaid）、`resume`（简历写法模板，指标位置写「用你的评测结果填写」，**不编造数字**）、`modules`、`deep_dive`（≥8 道面试官深挖题，id 如 p1-d1，主观题，带 difficulty/key_points/reference/oral）、`materials`（architecture_doc / deployment / interview_pitch）。

| 项目 | 对应岗位 | 模块解锁日 |
|---|---|---|
| **p1 企业知识库问答（RAG）**：文档上传解析、切片入库、混合检索 + 重排、带引用回答与拒答、评测集证明效果、ACL 权限、Vue3 流式聊天界面 | AI 应用开发 | 07 骨架 / 08 数据模型 / 10 Compose+SSE / 14 LLM 客户端 / 16 意图识别结构化输出 / 22 文档解析 / 23 切片入库 / 25 混合检索 / 26 重排+改写 / 27 引用与拒答+前端 / 29 评测 / 30 权限+部署 |
| **p2 智慧园区运营 Agent**：衔接学员的智慧园区 SaaS 背景。查询设备/告警/客流、只读 Text2SQL 数据分析、创建和派发工单（需人工审批）、MCP 封装业务系统、评测与 Trace、Vue3 运营工作台 | AI Agent 开发 | 32 手写循环 / 33 工具加固 / 35 记忆 / 36 LangGraph / 37 断点+审批 / 38 MCP Server / 39 Text2SQL 子 Agent+Supervisor / 42 任务评测 / 43 Trace / 45 安全 / 46 工作台 |
| **p3 前端 Coding Agent**：读 Vue/TS 仓库、检索上下文、生成或修改组件、在 Docker 沙箱里跑 vitest/eslint 并自我修复、审查 PR diff；体现 Harness 能力 | Agent 运行时 / Coding Agent | 40 最小循环 / 41 仓库上下文 / 44 沙箱与 CI / 47 生成-测试-修复循环 / 48 PR 审查 Agent+评测 / 49 交付与包装 |
