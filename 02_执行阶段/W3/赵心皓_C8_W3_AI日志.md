# 赵心皓_C8_W3_AI日志.md

## 目标
实现 Property Graph、学生画像、6 个标准 Skill 与自然语言查询。

## 第 1 轮（图存储）
**Prompt**：`用 SQLite 实现一个 property graph，有 nodes 表和 edges 表，支持 upsert 节点/边、查邻居、统计数量。不要第三方依赖。`

**AI 输出**：完整的 `PropertyGraph` 类，包含 WAL 模式与索引，质量不错。

**我做的验证**：写了一个临时测试插入 2 节点 1 边，检查 `neighbours()` 返回正确标签。
这一步救了我：初版 `upsert_edge` 没有 `INSERT OR REPLACE`，重复 run_pipeline 会抛主键冲突。
**我的修改**：改为 `INSERT OR REPLACE`。

## 第 2 轮（画像 bug）
**Prompt**：`从消息、提交、QA 对学生聚合画像：消息数、提问数、答疑数、提交数、挑战列表、最近活跃、技能标签。staff 不算学生。`

**AI 输出**：主循环正确过滤 staff，但 QA 累加循环没有过滤。

**我如何发现**：打印画像名单看到"助教-李老师"。
这是本周最重要的真实 bug，已写入 AAR W3 失败分析。
**我的修改**：QA 循环中加 `startswith("助教")` / `startswith("老师")` 过滤。

## 第 3 轮（SKILL.md 规范）
**Prompt**：`按 agentskills.io 规范写 6 个 SKILL.md：wechat-bridge, msg-classifier, submission-tracker, qa-sink, student-profile, class-report。name 必须与目录同名，description 要写做什么和何时用。每个还要有 Inputs/Outputs/Edge cases/Run，并配一个可独立运行的 .py 入口。`

**AI 输出**：第一轮把 description 写得很短（"用于分类消息"），不符合规范建议。

**我的追问**：`description 要包含具体关键词和可检索场景，例如 submission、missing AI log、nudge。`
→ 修正后 6 个描述都包含触发词，Agent 能据此自动选择。

## 第 4 轮（自然语言查询）
**Prompt**：`写一个自然语言查询路由，支持：某人提交了哪些挑战、某挑战还有谁没交、谁最活跃、某话题常见问题、班级状态。要能处理中文口语化问法。`

**AI 输出**：正则路由可用，但"李四答疑几次"不在 5 类里，会返回兜底。

**我的修改**：补第 6 类查询模式，并在 `DEMO_QUERIES` 中加入该问题，
这样验收能覆盖 6 类。实测新增加query返回"李四 共回答 0 个问题"——
答案正确（李四确实未答疑），但暴露了画像与 QA 之间的统计口径一致性的问题，已记录。

## 反思
AI 生成聚合代码时最容易漏的是**多写入路径的一致性**。
单个循环它写得很对，两个循环共享同一个过滤条件时就会漏一个。
应对策略不是"再问一次 AI"，而是**用真实输出做交叉校验**（成员数 vs 配置数）。
