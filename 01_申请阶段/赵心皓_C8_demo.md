# 赵心皓_C8_demo.md

# 早期验证物：wechat-class-manager 可运行系统

> 对应 Proposal Part 5。评分公式为「Proposal 文字质量 × 30% + 早期验证物质量 × 70%」，
> 因此本文件不是截图或设想，而是**已经跑通并带验收记录**的系统说明。
> 完整代码位于 `../03_系统实现_wechat-class-manager/`。

---

## 1. 一句话证明

```bash
cd "03_系统实现_wechat-class-manager"
python3 run_pipeline.py && python3 verify.py
# 实测输出：Verification: 18/18 passed -> APPROVE
```

一个陌生人在干净环境里只需两条命令，就能复现全部产物与验收结论——这就是"已经开始做了"的证据。

---

## 2. 实跑结果（真实输出，非预期值）

| 指标 | 实测值 | 来源文件 |
|---|---:|---|
| 处理群消息 | 168 条 | `outputs/pipeline_summary.json` |
| 消息类型 | 5 种（text/file/link/image/voice） | `outputs/messages.jsonl` |
| 意图分类准确率 | 96.4%（162/168） | `outputs/classification_eval.json` |
| 识别提交事件 | 40 次（其中 2 次标记 `needs_revision`：缺 AI 日志） | `outputs/submissions.json` |
| 抽取 Q&A 对 | 18 对 | `outputs/qa_pairs.json` |
| Property Graph | 244 节点 / 401 边；24 学生 × 8 挑战 | `outputs/graph_stats.json` |
| 自动预警 | 16 条，4 类 | `outputs/alerts.json` |
| 自然语言查询 | 6 类，全部返回实质答案 | `outputs/nl_query_demo.json` |
| 单元测试 | 12/12 通过 | `python3 -m unittest discover -s tests` |
| 自动验收 | 18/18 通过 → **APPROVE** | `outputs/verification_report.md` |

数据窗口：2026-05-11 09:00 ~ 2026-06-09 06:18（脱敏样本）。

---

## 3. 系统架构速览

```
[微信只读适配]  wechat-cli / fixture
        │ normalize → 统一 Message schema
        ▼
[L2 理解]  7 类意图 + C1–C8 关联 + 提交质检 + QA 配对
        ▼
[L3 记忆]  SQLite Property Graph（节点/边/CRUD/邻域） + 学生画像
        ▼
[L4 行动]  Watcher 增量 → 4 类预警 → 周报 → 仪表盘 / NL 查询
```

六个标准 Skill（`skills/*/SKILL.md`）：
`wechat-bridge`、`msg-classifier`、`submission-tracker`、`qa-sink`、`student-profile`、`class-report`。
每个都有明确的输入/输出契约与独立可执行入口，可被 Claude Code / OpenClaw 等 Agent 直接识别。

---

## 4. 三个可演示场景（真实输出摘录）

### 场景 A：老师问"C4 还有谁没交？"

```
问：C4 还有谁没交？
答：C4 未提交（21 人）：何五, 冯四, 刘二, 唐一, 孙七, 宋十, 张三, …
```

链路：`NL router → submissions.json → student_profiles → 格式化回答`。

### 场景 B：提交完整性质检

```
张三 C1 proposal → accepted
王五 C1 proposal → needs_revision（missing: AI日志）
```

系统不是简单统计"有没有文件"，而是落实课程规则：**没有 AI 日志的提交不算完成提交**。

### 场景 C：自动周报与预警

`outputs/weekly_report.md` 由代码生成，含 5 个章节；
`outputs/alerts.json` 触发 4 类预警：截止风险 1、沉默学生 6、低提交率 8、活跃度下滑 1。

---

## 5. 早期验证物的边界（诚实声明）

1. **数据源是脱敏样本，不是生产微信群。** 构建机器没有已登录的微信数据库；
   `cli` 适配器代码与安装文档已完成，但需要在现场机器上复验。这不是"已接入真实数据"。
2. **分类器 96.4% 是内部上界。** 规则词表和标注集由同一设计者产出，
   外部效度需要用独立人工标注的留出集重新测。
3. **只读。** 没有实现把消息写回群的能力，这是有意为之的风险控制。

以上三条均写入 AAR，而不是在 proposal 中隐去。

---

## 6. 文件清单

```
03_系统实现_wechat-class-manager/
├── README.md  SETUP.md  requirements.txt
├── run_pipeline.py  verify.py
├── wcm/                # 7 个核心模块
├── skills/             # 6 个 Skill（SKILL.md + 可执行脚本）
├── config/             # 挑战定义 + 群配置（24 人）
├── data/               # 脱敏样本 + 可复现生成器 + 独立标注
├── tests/test_all.py   # 12 个测试
├── docs/architecture.md
└── outputs/            # 15 个运行产物（含 APPROVE 验收报告）
```
