# 赵心皓_C8_W3_产出_图与Skill封装.md

# Week 3 可验证产出：Property Graph、学生画像与 Skill 封装

## 1. 交付文件

| 文件 | 说明 |
|---|---|
| `wcm/graph.py` | `PropertyGraph`（SQLite 节点/边表 + upsert + 邻域查询）+ `build_profiles` |
| `wcm/engines.py` | 自然语言查询路由（6 类问题） |
| `skills/*/SKILL.md`（6 个） | 遵循 agentskills.io 规范，含 IO 契约与边界条件 |
| `skills/*/*.py`（6 个） | 每个 Skill 的独立可执行入口 |
| `outputs/class_graph.sqlite` | 领域图数据库，可用 sqlite3 直接打开 |
| `outputs/graph_stats.json` | 节点/边统计 |
| `outputs/student_profiles.json` | 24 名学生画像 |
| `outputs/nl_query_demo.json` | 6 类查询的实测答案 |

## 2. Property Graph 结构

**节点**：Student(24)、Challenge(8)、Message(154)、Submission(40)、QAPair(18)
**边**：SENT(196)、TAGGED_WITH(63)、SUBMITTED(40)、FOR_CHALLENGE(40)、
ASKED(24)、ANSWERED(24)、MENTORED(14)
**合计**：244 节点 / 401 边

存储实现：

```sql
nodes(id TEXT PRIMARY KEY, label TEXT, props TEXT)
edges(src TEXT, dst TEXT, label TEXT, props TEXT, PRIMARY KEY(src,dst,label))
```

可直接验证：

```bash
sqlite3 outputs/class_graph.sqlite "SELECT label,COUNT(*) FROM nodes GROUP BY label;"
```

## 3. 学生画像样例

```json
{
  "name": "张三", "messages": 12, "questions": 1, "answers": 0,
  "submissions": 2, "challenges": ["C1","C2"],
  "skill_tags": ["稳定交付者", "主动提问者", "高活跃"]
}
```

标签规则：`稳定交付者`(≥2 提交) / `答疑贡献者`(≥2 回答) /
`主动提问者`(≥2 提问) / `高活跃`(≥10 消息) / `待激活`。
**只存聚合量，不复制消息正文**；staff 发送者被排除。

## 4. 六个标准 Skill

| Skill | 层 | 独立入口 |
|---|---|---|
| wechat-bridge | L1 | `bridge.py` |
| msg-classifier | L2 | `classifier.py` |
| submission-tracker | L3 | `tracker.py` |
| qa-sink | L3 | `sink.py` |
| student-profile | L3 | `profiler.py` |
| class-report | L4 | `reporter.py` |

每个 SKILL.md 均含 YAML frontmatter（name/description/license/metadata）与
Inputs / Outputs / Method / Edge cases / Run 五段，可被 Claude Code / OpenClaw 按描述自动选择。

## 5. 自然语言查询实测

| 问题 | 实测答案（摘录） |
|---|---|
| 张三提交了哪些挑战？ | 张三 已提交：C1, C2。 |
| C4 还有谁没交？ | C4 未提交（21 人）：何五, 冯四, 刘二… |
| 最近一周谁最活跃？ | Top5：张三(12)、李四(11)、周八(10)… |
| 关于 GitHub 的常见问题有哪些？ | 共 1 条 Q&A：C5 GitHub 仓库要公开吗？ |
| 这周班级状态如何？ | 24 名学生、168 条消息、40 次提交、18 条 Q&A，覆盖 6 个挑战 |
| 李四答疑几次？ | 李四 共回答 0 个问题。 |

六个查询全部返回实质答案，无兜底拒答。
