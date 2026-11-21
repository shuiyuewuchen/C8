# 赵心皓_C8_proposal.md

# C8 项目申请书：微信群 → 班级管理 Agent 子系统

> 挑战：C8 Real-World Project Execution（真实项目落地）
> 申请方向：**Project B（企业本体 Agent 系统）技术路线下的真实子项目**
> 具体项目：WeChat Group as Class Management Agent Skill（《C8 WeChat Class Management Challenge》）
> 申请人：赵心皓
> 版本：v1.0 ｜ 提交日期：2026-05-16

---

## 1. 项目选择（Project Selection）

- **我选择的项目**：**B** 方向下的真实任务——`微信群 → 班级管理 Agent 子系统`。
  材料包中的《C8 WeChat Class Management Challenge》是导师给定的真实需求，其技术内核与
  Project B 同源：领域本体/Property Graph、KSTAR 认知循环、NL→Graph 查询、Agent Skill 封装。
  我把它作为 B 方向在**班级管理场景**的落地实例，而不是另起炉灶做一个新题目。

- **为什么适合我**：

  **我的相关经验**
  - 长期在 Elite20 群内承担信息整理：把散落在群文件里的提交物、通知、问答整理成可检索的清单。
    这正是本项目要自动化的原始痛点，我不是从零想象需求，而是从亲历的重复劳动出发。
  - 具备 Python + SQLite + CLI 工具链能力；能独立搭建零依赖系统，不依赖额外运维资源。
  - 在 C5 中已建立 GitHub 仓库与 README/复用声明的工作习惯；在 C6 中已完成 Web 交付。

  **我在 C1–C7 中展示的相关能力（用具体产出证明，而非"我很感兴趣"）**

  | 挑战 | 我的具体能力证据 | 在本项目中的直接用途 |
  |---|---|---|
  | C1 翻译 | 把非结构化外语材料转成结构化中文术语表 | 把微信原始消息 normalize 成统一 Message schema |
  | C2 论文 | 用学术规范组织 proposal/AAR，区分预期 R̂ 与实际 R | Proposal、周报、AAR 的写作骨架 |
  | C3 群内参与 | 群内提问—回答—追问的完整互动记录 | 作为 QA Extractor 的真实数据来源与标注直觉 |
  | C4 技能分享 | 输出过带触发词、IO 说明的可复用 skill | 6 个 `SKILL.md`，遵循 agentskills.io 规范 |
  | C5 GitHub | 仓库结构、README、复用声明 | Skill 目录结构与可独立运行的入口脚本 |
  | C6 Web App | 端到端部署与访问验证 | 本地 Dashboard（至少 5 个数据维度） |
  | C7 内容传播 | 把结构化材料改写成可发布内容 | 周报自动转公众号素材 |

  **我对这个领域的理解**
  - 微信群不是需要被替换的"落后系统"，而是事实标准；正确做法是**在其上加一层智能层**。
  - 真正的难点不是爬取消息，而是三件事：**统一 schema、意图判定、可验收闭环**。
  - 老师要的不是更多图表，而是自然语言提问后能立刻得到可行动的答案
    （"C4 还有谁没交？"比一个提交率数字有价值得多）。

---

## 2. 拿来主义分析（Reference + Adaptation）

> 这是最重要的评分项。以下 7 个来源均已实际检索、阅读并对链接做了可达性核对。

### 参考来源

| # | 来源 | 链接 | 核心思想 |
|---|---|---|---|
| 1 | freestylefly/wechat-cli | https://github.com/freestylefly/wechat-cli | 本地 SQLCipher 解密，只读 CLI，默认 JSON 输出，专为 Agent 工具调用设计 |
| 2 | sjzar/chatlog | https://github.com/sjzar/chatlog | HTTP API + MCP SSE 暴露聊天数据；TUI 降低使用门槛 |
| 3 | Agent Skills 开放规范 | https://agentskills.io/specification | 一个 skill = 目录 + SKILL.md（YAML frontmatter + 指令），渐进式披露 |
| 4 | Neo4j Property Graph 模型 | https://neo4j.com/docs/ | 节点/边/属性构成领域图，关系本身携带语义 |
| 5 | SQLite FTS5 | https://www.sqlite.org/fts5.html | 在嵌入式数据库内做全文索引，无需外部搜索服务 |
| 6 | KSTAR 认知循环（课程材料） | 课程《真实项目执行方案0511.pdf》/《C8.pdf》 | K→S→T→Â→R̂，用 R̂ 与 R 的差值作为学习信号 |
| 7 | Wechaty（写回通道） | https://wechaty.js.org/ | 通过协议层实现群消息写入与自动回复 |

### 逐来源的 adopted / removed / improved

| 来源 | 直接复用（adopted） | 去掉（removed） | 重构/新增（improved） |
|---|---|---|---|
| 1 wechat-cli | JSON-first 输出、只读原则、`history/group/members` 命令语义 | 不在核心代码里硬编码依赖；不复制其解密实现 | 新增 `wcm/bridge.py` 适配层：把 `time/text/id` 等异构字段归一到统一 schema，使 L2–L4 完全不感知数据来源 |
| 2 chatlog | HTTP/MCP 分层思想——数据访问与业务分析解耦 | 去掉 TUI 与常驻 HTTP 服务（引入运维成本） | 把 HTTP API 作为 `cli` 适配器的备选实现写入 SETUP.md，形成可替换的 transport 接口 |
| 3 Agent Skills 规范 | `name`/`description` frontmatter、目录即 skill、渐进披露 | 去掉通用示例中的营销性描述 | 为每个 skill 增加**输入/输出契约**与**边界条件**章节；补充可直接执行的 `*.py` 入口 |
| 4 Neo4j 图模型 | Student/Challenge/Submission/Message/QAPair 节点与 SENT/SUBMITTED/ASKED/ANSWERED/MENTORED 边 | 去掉 Neo4j 服务与 Cypher 依赖 | 用 SQLite 实现同构 `PropertyGraph`（节点表+边表+CRUD+邻域查询），保留更换后端的接口 |
| 5 SQLite FTS5 | "检索能力内建在存储层"的思路 | v1 暂不引入 FTS5 虚拟表（避免复杂度前置于验证） | 先用 `challenge_linker` 的关键词/扩展名匹配跑通闭环；FTS5 列为 W5 候选，需 A/B 对比后再决定 |
| 6 KSTAR | K/S/T/A/R 五段结构与 R̂ 可验证原则 | 去掉"只写收获不写差距"的汇报式 AAR | 引入 **ΔR = R̂ − R** 作为显式字段，并要求写"不是根本原因但看起来像的"，防止假复盘 |
| 7 Wechaty | 双向通道的设计位置（Nudge Skill） | **整个写回能力在 v1 去掉** | 原因：自动发消息涉及账号风险与误伤真实同学，只读闭环已能交付 80% 价值；写回仅保留接口设计，不实现 |

### 对比与创造性组合

三个来源之间存在明确张力，我没有简单拼接，而是做了取舍组合：

- **wechat-cli vs chatlog**：前者零服务、CLI-first、AI 友好；后者有 HTTP/MCP 但需要常驻进程。
  我采用 **wechat-cli 作为默认 transport + chatlog 作为备选 transport**，把差异收敛到 `bridge.py` 一个文件。
- **Neo4j vs SQLite**：图语义 vs 可携带性。我选择 **图模型 + SQLite 实现**——
  保留前者的领域抽象，换取"单文件可直接打开验证"的验收优势。
- **规则引擎 vs LLM 分类**：LLM 灵活但成本/延迟不可控且不可复现。我采用
  **规则先行 + 可插拔 LLM 接口**，并把"规则与标注同源导致准确率上界偏高"写进局限，而不是隐瞒。

**组合后的新东西**：一个不依赖任何服务、可离线复现、可被 6 种 Agent 调用、
并且自带验收脚本的"班组智能层"——这是任何单一来源都不具备的。

---

## 3. 执行方案（KSTAR）

### K（Knowledge）：我已有的知识和资源

- **相关技能**：Python 标准库（json/sqlite3/re/http.server/unittest）、CLI 工具链、
  Agent Skill 规范、KSTAR 复盘方法。
- **可用工具**：本地文件系统、Python 3.11、SQLite、`wechat-cli`（现场可选）、
  AI 助手（用于方案推敲、代码生成、测试设计与文档迭代，全过程留痕）。
- **团队/协作资源**：Elite20 项目协同群（需求来源与验证对象）、
  课程材料包《真实项目执行方案0511.pdf》《C8 WeChat Class Management Challenge》、
  C1–C7 已有产出作为能力证据。

### S（Situation）：当前问题是什么

- **现状**：提交靠老师翻群文件；活跃度凭感觉；好问题淹没在聊天流；通知发出后不知道谁看了。
- **痛点**：
  1. 群消息是**只增不改的消息流**，没有任何结构化视图；
  2. 提交命名不统一，缺 AI 日志也照样被当作"已交"；
  3. 老师的问题（"C4 还有谁没交"）需要人工翻十分钟。
- **约束条件**：
  - 不得替换微信、不得写回群消息（只读优先）；
  - 构建机器上**没有真实微信群数据库**，必须设计可复现的脱敏样本并如实声明范围；
  - 零第三方依赖、无服务、可离线运行；
  - 8 周内交付，每周必须有可验证产出与 AAR。

### T（Task）：我要解决什么

- **核心目标**：构建端到端的"消息流 → 结构化 → 可查询 → 主动预警"闭环系统，
  并让其可被任意兼容 Agent Skill 规范的 Agent 调用。

- **子任务分解**：
  1. **W1–W2**：数据桥接与意图理解（统一 schema、双适配器、分类器、挑战关联、提交检测、QA 提取）
  2. **W3–W4**：领域图与 Skill 封装（Property Graph、学生画像、6 个 SKILL.md、自然语言查询）
  3. **W5–W6**：闭环与验收（Watcher 增量、4 类预警、周报、Dashboard、自动验收脚本）
  4. **W7–W8**：真实使用与迭代（现场接入真实群、人工标注留出集复核、复盘与作品集归档）

### Â（Action Plan）：怎么做

| 周 | 执行步骤 | AI/Agent 用法 | 输入 → 输出 |
|---|---|---|---|
| W1 | 定义领域模型与 schema；写 bridge 双适配器；生成 100+ 条脱敏样本 | 让 AI 提 3 套 schema 方案并逐条比较，我选嵌套 sender 版本 | 原始消息 → `messages.jsonl` |
| W2 | 两遍分类（先定 reply 意图再定最终意图）；挑战关联；提交质检；QA 配对 | 用 AI 生成规则词表初稿 → 人工剔除歧义词 → 回归测试 | 消息流 → 提交矩阵 + QA 对 |
| W3 | SQLite 节点/边表 + CRUD + 邻域查询；画像聚合；6 个 Skill 文档 | AI 生成 SKILL.md 骨架，我补 IO 契约与边界条件 | 结构化数据 → 可查询图 + Skill 包 |
| W4 | 自然语言路由；6 类查询示例；独立运行入口 | AI 写首版路由，我发现"助教被算成学生"的归类错误并修正 | 图 → 自然语言答案 |
| W5 | Watcher checkpoint；4 类预警规则；周报生成器 | AI 生成规则模板，我用真实输出反推阈值 | 增量消息 → alerts + 周报 |
| W6 | 18 项自动验收；Dashboard；README/SETUP/架构文档 | AI 起草验收项，我逐项加"实测值"字段防止空泛通过 | 全链路 → 验收报告 APPROVE |
| W7 | 现场接入 `wechat-cli --adapter cli`；人工标注 50 条留出集 | AI 辅助设计标注表，人工独立标注 | 真实群 → 外部效度评估 |
| W8 | 汇总 AAR、ΔR 收敛分析、作品集归档 | AI 辅助结构化，我负责判断与取舍 | 全过程 → 能力档案 |

### R̂（Expected Result）：预计产出什么

| 周 | 可交付物 | 具体成功标准（可验证） | 验证方法 |
|---|---|---|---|
| W1 | bridge、schema、脱敏样本、SETUP | ≥120 条消息、≥5 种消息类型、CLI 重复运行结果一致 | 运行 bridge + 检查 `messages.jsonl` |
| W2 | classifier / linker / detector / qa-extractor | 准确率 >70%、≥5 个提交事件、≥10 个 Q&A | `classification_eval.json` + 输出计数 |
| W3 | Property Graph、画像、6 个 Skill | ≥20 学生 × 8 挑战、6 个 SKILL.md、≥5 类自然语言查询 | `graph_stats.json` + 目录检查 |
| W4 | 预警、周报、Dashboard、验收脚本 | ≥17 项验收通过、≥3 类预警、≥5 个仪表盘维度、12 个测试 | `verify.py` + unittest |
| W5 | 真实数据接入记录、留出集标注 | 真实群 ≥100 条、人工标注 50 条、外部准确率 >65% | 现场复现 + 标注表 |
| W6 | 增益对比报告 | 至少 1 项可量化改进（如检索耗时下降） | A/B 记录 |
| W7–W8 | 完整 AAR 序列与作品集 | ΔR 相对误差从 >35% 收敛到 <10% | AAR 汇总表 |

**总验收标准**：`python3 verify.py` 输出 `APPROVE`，且 12 个测试全部通过。

---

## 4. 我的角色（Your Role）

- **主角色：Builder（构建者）**
  动手实现桥接、分类、图存储、验收脚本与文档，产出可运行、可独立使用的系统。

- **兼任角色**：Architect（定义领域模型与分层边界）、Researcher（技术选型与来源对比）。
  不做 Operator：我不拥有真实微信群的生产访问权限，也不做写回操作。

- **我负责的具体模块**
  - Layer 1 适配层与统一 schema
  - Layer 2 分类/提交/QA 信号提取
  - Layer 3 Property Graph 与 Skill 契约
  - Layer 4 预警、周报、验收脚本
  - AAR 与 AI 日志的真实性维护

- **我的边界（我不负责什么）**
  - 不负责微信客户端本身的解密工具开发（采用开源 wechat-cli）；
  - 不负责真实生产环境的部署运维与账号权限申请；
  - 不实现自动写回群消息（风险高，v1 明确不做）；
  - 不代替老师做教学决策，系统只提供可行动信息。

- **我需要的支持**
  1. 现场提供一台已登录微信、具备密钥初始化条件的机器，用于 W5 真实数据复验；
  2. 一位老师用 30 分钟做真实需求确认与验收签字；
  3. 若进入真实数据阶段，需要脱敏与合规确认。

---

## 5. 早期验证（Proof of Capability）

> 评分公式：Proposal 文字质量 × 30% + 早期验证物质量 × 70%。
> 因此我没有只交文档，而是已经把系统做出来并跑通。

**已提交的早期验证物**（详见 `赵心皓_C8_demo.md` 与 `03_系统实现_wechat-class-manager/`）：

1. **可运行代码仓库**：8 阶段 pipeline + 7 个核心模块 + 6 个标准 Skill；
2. **可验证数据产物**：`outputs/` 下 15 个文件，含提交矩阵、QA 对、图数据库、周报、验收报告；
3. **自动验收记录**：`verification_report.md`，18/18 通过，结论 **APPROVE**；
4. **测试结果**：12 个单元/集成测试全部通过；
5. **早期实测数字**：168 条消息、24 学生 × 8 挑战、40 次提交、18 个 Q&A、
   分类准确率 96.4%、244 节点 / 401 边、16 条预警、6 类自然语言查询。

这不是 demo，而是一个已经能在脱敏数据上端到端跑通、并自带验收证据的系统。
与真实项目的唯一差距是**数据源尚未切换到生产微信群**——这一差距被如实写入 W1/W2 AAR，
并列入 W5 计划，而不是被包装成"已完成"。

---

## 附：Proposal 自检清单

- [x] 选择具体项目并说明原因（B 方向 + 指定真实任务）
- [x] 拿来主义分析列了 7 个来源（≥3）
- [x] 每个来源有 adopted / removed / improved
- [x] 含来源间对比与创造性组合
- [x] 执行方案用 KSTAR（K→S→T→Â→R̂）
- [x] R̂ 具体到数字，可在 AAR 中对比
- [x] 定义明确主角色与边界
- [x] 至少 1 个早期验证物（实际提供 5 类）
- [x] 有 AI 日志与拿来说明
