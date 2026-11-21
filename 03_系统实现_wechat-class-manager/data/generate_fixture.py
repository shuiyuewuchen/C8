"""Deterministically build a de-identified, reproducible WeChat message fixture.

Usage: python3 data/generate_fixture.py
Output: data/sample_messages.jsonl  +  data/fixtures/labels.json

Ground-truth labels are deliberately kept in a SEPARATE file so that the bridge
output mirrors what a real wechat-cli would return (no intent column).
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
random.seed(20260511)

STAFF = [
    {"nickname": "助教-王老师", "wechat_id": "staff_teacher_01"},
    {"nickname": "助教-李老师", "wechat_id": "staff_ta_01"},
]
STUDENTS = [
    "张三", "李四", "王五", "赵六", "孙七", "周八",
    "吴九", "郑十", "陈一", "刘二", "杨三", "黄四",
    "何五", "高六", "林七", "罗八", "谢九", "宋十",
    "唐一", "许二", "韩三", "冯四", "邓五", "曹六",
]
START = datetime(2026, 5, 11, 9, 0)
END = datetime(2026, 6, 10, 21, 0)
SPAN_MIN = int((END - START).total_seconds() / 60)

records: list[dict] = []
labels: dict[str, str] = {}


def add(offset_min: int, sender: dict, typ: str, content: str, label: str,
        media: str = "", reply_to: str = "") -> str:
    mid = f"m{len(records)+1:04d}"
    ts = START + timedelta(minutes=min(offset_min, SPAN_MIN))
    rec = {
        "msg_id": mid,
        "timestamp": ts.isoformat(timespec="seconds") + "+08:00",
        "sender": {"wechat_id": sender["wechat_id"],
                   "nickname": sender["nickname"] if "nickname" in sender else sender},
        "type": typ,
        "content": content,
        "media_ref": media,
        "reply_to": reply_to,
    }
    records.append(rec)
    labels[mid] = label
    return mid


def stu(name: str) -> dict:
    return {"nickname": name, "wechat_id": "wxid_" + str(STUDENTS.index(name) + 1).zfill(2)}


# ---- announcements (teacher, with deadline signals) ------------------------
announce_texts = [
    "【通知】5月16日前提交 G1 提案，请各位务必确认命名规范。",
    "@全体 本周三 19:00 周会，议题是项目池确认，务必参加。",
    "通知：C2 论文提交截止 5月27日，AI日志必须一并提交。",
    "@全体 换组窗口 5月14日全天开放，注意时间。",
    "请各位注意：G2 提交需要六件套 + 验证视频，截止 6月10日。",
    "通知：C5 GitHub 仓库链接请统一填到腾讯文档，截止 6月7日。",
    "【deadline】C6 Web App 部署上线 6月10日截止，逾期需说明。",
    "@全体 6月17日班级成果展，3分钟演示 + 2分钟问答。",
]
for i, txt in enumerate(announce_texts):
    add(int(SPAN_MIN * i / 9), STAFF[0], "text", txt, "announcement")

# ---- submissions, with and without AI log ---------------------------------
sub_plan = [
    ("张三", "C1", True, True), ("李四", "C1", True, True),
    ("王五", "C1", False, False), ("张三", "C2", True, True),
    ("赵六", "C2", True, False), ("孙七", "C2", True, True),
    ("周八", "C4", True, True), ("吴九", "C4", True, True),
    ("郑十", "C4", False, False), ("陈一", "C5", True, True),
    ("刘二", "C5", True, True), ("杨三", "C6", True, True),
    ("黄四", "C6", True, True), ("王五", "C8", True, True),
    ("李四", "C8", True, True),
]
for i, (name, cid, with_log, with_demo) in enumerate(sub_plan):
    off = int(SPAN_MIN * (0.08 + 0.72 * i / len(sub_plan)))
    base = f"{name}_{cid}_proposal.md"
    add(off, stu(name), "file", f"提交 {cid} proposal，请查收。", "submission", media=base)
    if with_log:
        add(off + 3, stu(name), "file", f"{cid} AI日志补充", "submission",
            media=f"{name}_{cid}_AI日志.md")
    if with_demo:
        add(off + 6, stu(name), "file", f"{cid} 早期验证物", "submission",
            media=f"{name}_{cid}_demo.pdf")

# ---- questions + answers (reply chain) ------------------------------------
qa_topics = [
    ("C5 GitHub 仓库要公开吗？", "建议先建私有仓库，验收前改成 public，注意不要泄露密钥。"),
    ("请问 C8 proposal 的 R̂ 要写多具体？", "要具体到可验证的数字，例如'完成 3 个模块 + 测试通过率 100%'。"),
    ("G1 提案的竞品分析至少几个？", "至少 2 个，最好一个同类产品一个可迁移方案。"),
    ("怎么用 wechat-cli 提取群消息？", "先 sudo wechat-cli init，再 history '群名' --limit 100 --format json。"),
    ("为什么我的验证报告是 REJECT？", "先检查六件套是否齐全，尤其是 AI日志和 README。"),
    ("C4 skill 的 description 怎么写？", "要同时说明做什么、什么时候用，并包含可检索关键词。"),
    ("请问 deadline 能不能延期？", "需要提前说明原因并拿到老师书面确认，否则按逾期记录。"),
    ("AAR 里的 ΔR 怎么算？", "ΔR = R̂ − R，即预期产出减去实际产出，差距要诚实暴露。"),
    ("腾讯文档意向表填错了怎么办？", "在截止前直接改，逾期需要找协同组备案。"),
    ("如何判断 L2 和 L3 的区别？", "L2 是单点改进，L3 要形成可复用结构并能被他人调用。"),
    ("请问周报要手动写吗？", "可以用 class-report 自动生成，再人工补充洞察。"),
    ("Property Graph 用 Neo4j 还是 SQLite？", "原型阶段 SQLite 足够，需要原生图查询时再换 Neo4j。"),
    ("提交文件名可以用英文吗？", "可以，但要保持 姓名_C编号_描述.扩展名 的结构。"),
    ("C6 部署用什么平台？", "静态站可以用边缘托管，需要后端就用云服务，注意保留部署链接。"),
    ("群里问题太多了怎么沉淀？", "用 qa-sink 自动抽取问答对，按 challenge_ref 打标签。"),
    ("asked 一个问题没人回怎么办？", "可以在周会上提出，或 @ 对应模块的负责人。"),
    ("怎么证明 AI 日志是真实协作？", "保留多轮 prompt 迭代记录，体现优化过程而不是一句话指令。"),
    ("C7 推文可以直接用周报吗？", "可以，周报本身就是结构化素材，改写成故事即可。"),
]
for i, (q, a) in enumerate(qa_topics):
    off = int(SPAN_MIN * (0.12 + 0.75 * i / len(qa_topics)))
    asker = STUDENTS[i % len(STUDENTS)]
    answerer = STAFF[1]["nickname"] if i % 3 == 0 else STUDENTS[(i + 3) % len(STUDENTS)]
    qid = add(off, stu(asker), "text", q, "question")
    add(off + 4 + (i % 7), {"nickname": answerer,
                            "wechat_id": "staff_ta_01" if answerer.startswith("助教") else stu(answerer)["wechat_id"]},
        "text", a, "answer", reply_to=qid)

# ---- resources -------------------------------------------------------------
resources = [
    "分享一个 Agent Skills 规范：https://agentskills.io/specification",
    "推荐 wechat-cli 仓库：https://github.com/freestylefly/wechat-cli",
    "chatlog 支持 HTTP API：https://github.com/sjzar/chatlog",
    "SQLite FTS5 文档：https://www.sqlite.org/fts5.html",
    "这份 KSTAR 资料很有用，参考链接 https://example.edu/kstar",
    "分享模板：项目进度看板（腾讯文档）https://docs.qq.com/",
    "推荐阅读《Knowledge Graphs》相关章节，链接 https://example.edu/kg",
    "本周案例库更新，地址 https://example.edu/cases",
    "Neo4j property graph 文档：https://neo4j.com/docs/",
    "GitHub Actions 入门：https://docs.github.com/actions",
]
for i, txt in enumerate(resources):
    add(int(SPAN_MIN * (0.05 + 0.85 * i / len(resources))), stu(STUDENTS[(i+2) % len(STUDENTS)]),
        "link", txt, "resource")

# ---- discussions -----------------------------------------------------------
discussion_texts = [
    "我觉得 C8 最难的 not 是技术，而是把需求定义清楚，建议先做需求对齐。",
    "我认为可以把提取和分类拆成两个 skill，这样别的课程也能复用。",
    "同意楼上，我建议先定 schema，再写解析代码，避免返工。",
    "其实规则引擎已经能覆盖大部分场景，但是遇到反问句会误判。",
    "原因是群里消息太杂，我觉得应该先按消息类型做硬过滤。",
    "我不同意全部用 LLM，成本和延迟都受不了，建议混合方案。",
    "建议把预警阈值做成配置项，不同班级可以不同。",
    "讨论一下：Q&A 提取是靠回复链还是时间窗口？我觉得两者结合更稳。",
    "我认为 AAR 的价值在于暴露预测偏差，不是写漂亮话。",
    "其实上周的 demo 已经验证了架构，这周应该补测试。",
    "我的方案是先做 SQLite 版本，跑通后再考虑 Neo4j。",
    "我觉得仪表盘至少要展示 5 个维度，不然老师用不起来。",
    "建议每周固定时间跑一次报告，形成节奏。",
    "原因是提交命名不统一，导致检测器漏报，建议写进群公告。",
    "我认为拿来主义不是抄，而是理解后做取舍。",
    "同意，我建议把删除项也写清楚，这样评审能看到判断过程。",
    "其实可以用 FTS5 做全文检索，避免自己写模糊匹配。",
    "我觉得先把 fixture 数据做扎实，再谈真实数据接入。",
    "讨论：如果微信版本升级导致解析失败怎么办？我建议 adapter 隔离。",
    "我认为这个系统的真正用户是老师，所以查询接口要比图表重要。",
    "建议把 AI 日志模板内置到 skill 里，降低记录成本。",
    "我不同意现在就做写回群功能，风险太高，先做只读。",
    "我觉得周报可以直接作为公众号素材，这样 C7 也串起来了。",
    "原因是缺少验收记录，我觉得应该先出一个 verify 脚本。",
    "我认为预测能力校准比多做几个功能更重要，ΔR 要收敛。",
]
for i, txt in enumerate(discussion_texts):
    add(int(SPAN_MIN * (0.02 + 0.9 * i / len(discussion_texts))), stu(STUDENTS[i % len(STUDENTS)]),
        "text", txt, "discussion")

# ---- social chatter --------------------------------------------------------
social_texts = ["收到", "谢谢", "早上好", "哈哈", "辛苦了", "好的", "加油", "👍", "晚上好", "明白了"]
for i in range(42):
    add(int(SPAN_MIN * (0.01 + 0.96 * i / 42)), stu(STUDENTS[i % len(STUDENTS)]),
        "text", social_texts[i % len(social_texts)], "social")

# ---- non-submission files (negative controls) -----------------------------
for i, f in enumerate(["会议纪要.pdf", "班级合照.jpg", "签到表.xlsx"]):
    add(int(SPAN_MIN * (0.3 + 0.2 * i)), stu(STUDENTS[i]), "file",
        "群里文件备份", "social", media=f)

# ---- other media types (prove the bridge distinguishes text/file/image/voice)
for i, (typ, txt) in enumerate([
    ("image", "[图片] 项目进度看板截图"),
    ("voice", "[语音] 45秒 关于评审安排的说明"),
    ("image", "[图片] 白板讨论照片"),
    ("voice", "[语音] 30秒 关于部署失败的复盘"),
]):
    add(int(SPAN_MIN * (0.2 + 0.15 * i)), stu(STUDENTS[(i + 5) % len(STUDENTS)]),
        typ, txt, "social", media=f"media/{typ}_{i+1}.dat")

records.sort(key=lambda r: (r["timestamp"], r["msg_id"]))
# re-key labels by final msg_id (stable) - ids unchanged by sort
out = HERE / "sample_messages.jsonl"
out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
labels_path = HERE / "fixtures" / "labels.json"
labels_path.parent.mkdir(parents=True, exist_ok=True)
labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"generated {len(records)} messages, {len(labels)} labels -> {out.name}")
