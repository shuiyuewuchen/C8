# wechat-class-manager

> 把一个微信群变成一个 Agent 可调用的班级管理系统——不是替换微信，而是在消息流之上加一层智能层，让消息变得**可查询、可追踪、可行动**。

这是 C8「真实项目落地」交付的可运行系统，对应《C8 WeChat Class Management Challenge》的 L1–L4 四级要求。**零第三方依赖，Python 3.9+ 即可运行。**

## 快速开始

```bash
cd 03_系统实现_wechat-class-manager
python3 run_pipeline.py           # 用内置脱敏样本跑通全流程（约 1 秒）
python3 verify.py                 # 自动验收，输出 outputs/verification_report.md
python3 -m unittest discover -s tests -v   # 12 个测试
python3 run_pipeline.py --serve   # 启动本地仪表盘 http://127.0.0.1:8765
```

接入真实微信群（需本机已登录微信并完成密钥初始化）：

```bash
python3 run_pipeline.py --adapter cli --group "Elite20-项目协同群" --days 7
```

## 目录结构

```
├── run_pipeline.py          # 8 阶段端到端流水线
├── verify.py                # L1–L4 自动验收（18 项）
├── wcm/
│   ├── core.py              # 领域模型 + 配置 + 工具
│   ├── bridge.py            # L1 数据桥接（fixture / cli 双适配器）
│   ├── analyze.py           # L2 分类、挑战关联、提交检测、QA 提取
│   ├── graph.py             # L3 Property Graph(SQLite) + 学生画像
│   ├── engines.py           # L4 预警、周报、自然语言查询
│   ├── watcher.py           # L4 增量 Watcher（checkpoint 去重）
│   └── dashboard.py         # L4 零依赖本地仪表盘
├── skills/                  # 6 个可被 Agent 调用的 Skill（agentskills.io 规范）
│   ├── wechat-bridge/  msg-classifier/  submission-tracker/
│   └── qa-sink/  student-profile/  class-report/
├── config/                  # 挑战定义、群配置（JSON：零 YAML 依赖）
├── data/                    # 脱敏样本 + 可复现生成器 + 独立标注
├── tests/                   # 12 个单元/集成测试
├── docs/                    # 架构设计
└── outputs/                 # 运行产物（含验收报告）
```

## 三层蛋糕架构

| 层 | 内容 | 实现 |
|---|---|---|
| Layer 3 班级管理 Skills | 考勤/提交/QA/画像/通知/报告 | `skills/` 六个标准 SKILL.md |
| Layer 2 Agent Runtime | 分类→路由→动作→记忆 | `wcm/analyze.py` + `wcm/engines.py` |
| Layer 1 微信通道适配 | DB 解密/消息解析/文件映射 | `wcm/bridge.py`（read-only） |

## 四个认知层级（KSTAR 对应）

| Level | 能力 | 对应 KSTAR | 本文实现 |
|---|---|---|---|
| Bronze | 看到消息流 | K→S 感知 | 164 条消息，7 种类型 |
| Silver | 理解意图 | S→T 理解 | 7 类意图，准确率 97% |
| Gold | 生成行动 | T→A 应用 | 6 个 Skill + Property Graph |
| Platinum | 闭环学习 | A→R→K 创造 | Watcher + 4 类预警 + 周报 + 仪表盘 |

## 交付物索引（outputs/）

- `verification_report.md` — 18 项验收记录，结论 APPROVE
- `pipeline_summary.json` — 全链路关键指标
- `messages.jsonl` / `enriched_messages.jsonl` — 原始与增强消息流
- `submissions.json` — 学生×挑战提交矩阵 + 缺失项
- `qa_pairs.json` — 抽取的问答对与质量分
- `class_graph.sqlite` — Property Graph（可用 sqlite3 直接查询）
- `student_profiles.json` — 24 名学生画像
- `alerts.json` / `weekly_report.md` / `dashboard_data.json` / `dashboard.html`
- `nl_query_demo.json` — 6 类自然语言查询示例
- `classification_eval.json` — 分类评估（分意图 precision/recall）

## 隐私与边界

只读桥接，不写回微信；样本数据为脱敏构造；画像只存聚合量不复制消息正文。详见 `docs/architecture.md` 与验收报告的「范围声明」。
