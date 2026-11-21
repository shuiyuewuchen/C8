# 架构设计：微信群 → 班级管理 Agent 子系统

## 1. 设计目标

微信群是中国大学课程管理的事实标准，但它只是消息流。本系统不替换微信，而是在其上加一层 Agent 智能层，把消息流变成可查询、可追踪、可行动的结构化数据。

三条硬约束：

1. **不拆楼**：微信侧只读，不写回、不自动化操作。
2. **可迁移**：换一个群/换一个数据提取工具，上层模块不改。
3. **可验收**：每个 Level 都有可自动执行的验收项，不靠主观描述。

## 2. 分层

```
Layer 3  Skills        attend  submit  qa-sink  profile  nudge  report
                       (skills/*/SKILL.md，agentskills.io 标准)
─────────────────────────────────────────────────────────────────────
Layer 2  Runtime        on_message → classify → route to skill
                        on_schedule → watcher → alerts → report
                        on_query    → NL router → graph → answer
─────────────────────────────────────────────────────────────────────
Layer 1  Adapter       wechat-cli (SQLCipher 解密, JSON)  |  fixture
                        → normalize → MessageStream (JSONL)
```

## 3. 领域模型（Property Graph）

节点：`Student`、`Challenge`、`Submission`、`Message`、`QAPair`
边：`SENT`、`TAGGED_WITH`、`SUBMITTED`、`FOR_CHALLENGE`、`ASKED`、`ANSWERED`、`MENTORED`、`PROGRESSED_TO`

存储选择：**SQLite**（`outputs/class_graph.sqlite`）而非 Neo4j。理由：
- 单文件可携带，评审者用 `sqlite3` 直接打开验证；
- 不需要额外服务，符合"可独立使用"；
- 24 学生 × 8 挑战的规模远未到需要原生图数据库的程度。
升级路径：保持 `PropertyGraph` 接口不变，替换后端为 Neo4j/Memgraph 即可。

## 4. KSTAR 记忆编码

每条有意义的群交互编码为一个 Episode：

- **K**：课程上下文 + 已知画像 + 挑战定义
- **S**：`{who, what, where, when, context}`
- **T**：`classify_and_route | extract_submission | build_qa | update_profile`
- **A**：实际操作（分类、存储、回复、标记）
- **R**：结果 + 更新后状态（写入图数据库）

闭环学习信号：`activity_delta` 预警比较最近时段与之前时段的消息速率（ΔE），
对应 KSTAR 的 A→R→K 环节。

## 5. 关键决策与取舍

| 决策 | 选择 | 被拒方案 | 理由 |
|---|---|---|---|
| 配置格式 | JSON | YAML | 零第三方依赖，避免 pip 步骤 |
| 分类方法 | 规则优先 + 可插拔 LLM | 纯 LLM | 成本/延迟可控，规则可解释、可测试 |
| 图存储 | SQLite | Neo4j | 便携、免运维 |
| 仪表盘 | stdlib http.server | Flask/Streamlit | 零依赖 |
| 提交完整性质检 | 文件名契约 | 自由文本匹配 | 误报低，且能暴露"缺 AI 日志"这一真实痛点 |
| 双向通道 | 暂不实现 | Wechaty 写回 | 风险高，先做只读闭环 |

## 6. 数据流

```
wechat-cli / fixture
      │ normalize
      ▼
messages.jsonl ──► enrich (intent + challenge_ref)
                      │
        ┌─────────────┼──────────────┬─────────────────┐
        ▼             ▼              ▼                 ▼
  submissions.json  qa_pairs.json  student_profiles  class_graph.sqlite
        └─────────────┼──────────────┴─────────────────┘
                      ▼
        watcher → alerts → weekly_report → dashboard / NL query
```

所有步骤由 `run_pipeline.py` 编排，可重复执行；`verify.py` 独立读取产物进行验收。

## 7. 局限

1. 规则与标注同源，分类准确率是内部上界。
2. 单条消息只解析第一个文件名。
3. 未在真实微信数据库上执行（构建环境限制），`cli` 适配器已完成但需要现场复验。
4. 写回群消息的双向通道未实现。
