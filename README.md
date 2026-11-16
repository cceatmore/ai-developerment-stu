# 50 天 AI 应用与 Agent 开发训练

本机运行的学习网站。课程共 50 个学习日，讲解、题目和答案都预先写在仓库里，学习时不调用任何 AI。

学习记录只存在本机的 `data/` 文件夹。

---

## 1. 启动

### 推荐：Docker（每天打开网页就能学）

装好 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 后，在项目目录执行**一次**：

```powershell
docker compose up -d --build
```

之后每天打开 <http://127.0.0.1:8765> 即可。容器会随 Docker Desktop 自动启动。

| 操作 | 命令 |
|---|---|
| 停止 | `docker compose stop` |
| 改了 `content/` 里的课程内容后 | 网页「数据与设置」→ 重新加载内容（不用重启） |
| 改了代码后 | `docker compose up -d --build` |

学习记录在项目的 `data/` 文件夹（挂载进容器），删除容器不会丢。

### 不用 Docker

装 [uv](https://docs.astral.sh/uv/) 和 Node.js 20+，双击 **`start.bat`**。关掉黑色窗口＝停止服务。

---

## 2. 每天怎么学

打开首页 → 点 **开始今天的学习**，按顺序做：

| 步骤 | 做什么 | 时间 |
|---|---|---|
| **1. 复习** | 每天第一次打开先做一组选择题。**基础 8 题，距离上次学习每多 1 天加 4 题**（最多 20） | 5–12 分钟 |
| **2. 讲解** | 3–4 个知识点：一句话记住 → 类比 → 原理 → 场景 → 易错点。配套视频/文章可选 | 25–35 分钟 |
| **3. 当天测试** | 12 道选择/判断题（含读代码题）。**≥70 分解锁下一天**；没过就重测，每次换题，并多出错得多的知识点 | 10 分钟 |
| **4. 面试 3 题** | 3 道题，以**场景题**为主。**不影响解锁**，可以稍后做 | — |
| **5. 总结** | 测试通过后自动生成：得分、薄弱点、接下来重点复习什么 | — |

### 阶段卷（满分 100）

每 10 天一张：**单选 20×2 + 多选 10×3 + 判断 10×1 + 案例 4×5 = 100 分**。题目覆盖这 10 天的每一天。
**≥70 分才解锁下一阶段**，没过可以换一套重考。

### 复习从哪里出题

按优先级：**错题** → **到期复习**（学完后第 1、2、4、7、16 天）→ **掌握不扎实的** → **超过 7 天没碰过的旧知识**（防遗忘抽查）。

---

## 3. 课程安排

| 阶段 | 天数 | 内容 |
|---|---|---|
| 1 | Day 01–10 | Python 与后端速通（对照 JS/TS 学）：语法、异步、FastAPI、数据库、Redis、流式与部署 |
| 2 | Day 11–20 | 大模型应用基础：LLM 原理、Token、API、Prompt、结构化输出、Function Calling、Embedding、上下文工程 |
| 3 | Day 21–30 | RAG：文档解析、切片、向量库、混合检索、重排、引用、Agentic RAG、评测、企业知识库架构 |
| 4 | Day 31–40 | Agent：手写循环、工具设计、规划反思、记忆、LangGraph、MCP、多 Agent、Harness 与 Coding Agent |
| 5 | Day 41–50 | 评测、可观测、AI 安全、鉴权多租户、性能成本、系统设计、项目包装、综合模拟面试 |

**学习方法**参考了 Hello-Agents（Datawhale）、李宏毅生成式 AI 课程、吴恩达 Agentic AI、Hugging Face Agents Course、LangChain Academy、Anthropic 工程博客：
**先直觉后原理 → 先手写最小版再学框架 → 用熟悉的概念做类比 → 一个项目贯穿 → 用测试驱动记忆**。

---

## 4. 三个实践项目

跟着课程进度**逐个模块解锁**。每个模块要**勾完验收清单 + 复述原理 ≥60 分**才算完成。

| 项目 | 开始 |
|---|---|
| **企业知识库 RAG** | Day 07 |
| **智慧园区运营 Agent** | Day 32 |
| **前端 Coding Agent** | Day 40 |

每个项目有：市场与 JD 分析、架构、简历写法、面试讲解稿，以及「模拟面试」里的**项目深挖面试**。

---

## 5. 分数和掌握程度

- **选择题**：系统判分；多选少选得一半分，错选 0 分。
- **面试题**：先写回答，再对照评分要点逐条自评（说到了 / 部分 / 没说到）。想要更严格的评价，点 **「复制给 AI 评审」**，粘贴到 Cursor 等工具。
- **掌握程度**只看作答，不会因为「读完了」就算掌握：

| 程度 | 条件 |
|---|---|
| 初步理解 | 做过题 |
| **基本掌握** | 在 ≥2 个不同日子作答，最近平均 ≥70 |
| **熟练掌握** | 在 ≥3 个不同日子作答，最近平均 ≥85（有面试题时自评也要 ≥75） |

---

## 6. 数据

| 内容 | 位置 |
|---|---|
| 学习记录 | `data/study.db` |
| 自动备份 | `data/backups/`，每次启动备份一次，保留最近 14 份 |
| 日志 | `data/logs/app.log` |
| 课程内容 | `content/days/day01~50.yaml`、`content/projects/p1~p3.yaml` |

- 换电脑：拷走 `data/` 文件夹；或在「数据与设置」**导出 JSON** 再导入。
- 旧版（v1）的学习记录在第一次启动新版时会自动移到 `data/backups/study-v1-*.db`，不会删除。
- 服务只监听本机 `127.0.0.1`，不对外开放。

---

## 7. 修改课程内容

1. 编辑 `content/days/dayNN.yaml`（字段说明见 `content/AUTHORING.md`）。
2. 校验：`cd backend` → `uv run python -m app.validate 12`（第 12 天）或 `uv run python -m app.validate p1`（项目 1）。
3. 网页「数据与设置」→ **重新加载内容**。

学习时发现内容过时或有误，在知识点底部点「标记内容过时/有误」，「数据与设置」里会集中列出。
变化快的知识点（LLM、Agent 框架、MCP 等）带有写作时的版本说明和官方链接，**以官方文档为准**。

---

## 8. 开发与测试

```powershell
cd backend
uv run pytest -q                    # 后端测试
uv run python -m app.validate       # 全量内容校验

# 浏览器测试（使用本机 Edge；先用独立数据目录启动一个服务）
$env:STUPY_DATA_DIR="..\data-smoke"; $env:STUPY_PORT="8770"; uv run python -m app.main
uv run --with playwright python tests/e2e_smoke.py
$env:SMOKE_BASE="http://127.0.0.1:8770"; uv run --with playwright python tests/check_mermaid.py

# 前端开发（热更新，接口代理到 8765）
cd frontend; npm install; npm run dev
```

---

## 9. 常见问题

**打不开 127.0.0.1:8765**：Docker Desktop 是否在运行？`docker compose ps` 看状态，`docker compose logs` 看报错。

**首页提示「有课程内容校验未通过」**：「数据与设置」里会列出是哪个文件，运行 `uv run python -m app.validate N` 看具体错误。

**图表显示「图表渲染失败」**：图下方会显示源码，不影响学习。

**想重新开始**：先导出备份，再停止服务、删除 `data/study.db`，重新启动。
