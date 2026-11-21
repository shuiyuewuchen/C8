"""Layer 4 - zero-dependency local dashboard (stdlib http.server)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .core import OUT_DIR, write_json, write_text


def build_dashboard_data(enriched: Any, submissions: Any, qa_pairs: Any,
                         profiles: Any, alerts: Any, challenges: Any) -> Dict[str, Any]:
    by_challenge = []
    n_students = len(profiles)
    for c in challenges:
        done = len({s.student for s in submissions if s.challenge == c["id"]})
        by_challenge.append({"id": c["id"], "name": c["name_cn"], "done": done,
                             "rate": round(100.0 * done / n_students, 1) if n_students else 0})
    intents: Dict[str, int] = {}
    for e in enriched:
        intents[e.intent] = intents.get(e.intent, 0) + 1
    payload = {
        "summary": {
            "messages": len(enriched), "submissions": len(submissions),
            "qa_pairs": len(qa_pairs), "students": n_students, "alerts": len(alerts),
        },
        "by_challenge": by_challenge,
        "intent_distribution": intents,
        "top_students": sorted(profiles, key=lambda p: -p["messages"])[:8],
        "alerts": [a.to_dict() for a in alerts],
    }
    write_json(OUT_DIR / "dashboard_data.json", payload)
    return payload


HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Elite20 班级状态仪表盘</title>
<style>
:root{--bg:#f7f8fa;--card:#fff;--ink:#1f2329;--muted:#646a73;--line:#e5e6eb;--accent:#3370ff;--warn:#d93026}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
header{padding:28px 40px 12px}header h1{margin:0;font-size:24px}header p{margin:6px 0 0;color:var(--muted)}
main{padding:12px 40px 48px;max-width:1180px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px}
.kpi .num{font-size:30px;font-weight:700;color:var(--accent)}.kpi .lab{color:var(--muted);font-size:13px}
h2{font-size:17px;margin:28px 0 12px}.bar{height:9px;background:#eef0f3;border-radius:6px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--accent)}table{width:100%;border-collapse:collapse;background:var(--card)}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}
.tag{display:inline-block;background:#eef3ff;color:var(--accent);border-radius:4px;padding:1px 7px;margin-right:4px;font-size:12px}
.alert{border-left:3px solid var(--warn);padding:8px 12px;background:#fff;border-bottom:1px solid var(--line)}
footer{padding:20px 40px;color:var(--muted);font-size:12px}
</style></head><body>
<header><h1>Elite20 班级状态仪表盘</h1><p>微信群 → 结构化数据 → 可查询、可追踪、可行动 ｜ 由 wechat-class-manager 自动生成</p></header>
<main>
<div class="grid" id="kpis"></div>
<h2>各挑战完成率</h2><div id="challenges" class="card"></div>
<h2>发言 Top 8</h2><table id="students"></table>
<h2>实时预警</h2><div class="card" id="alerts" style="padding:0"></div>
</main><footer>数据源：脱敏样本消息流 ｜ 本地运行，数据不出机器 ｜ 对应 C6A 仪表盘升级版</footer>
<script>
fetch('/api/data').then(r=>r.json()).then(d=>{
const kpis=[['消息总数',d.summary.messages],['识别提交',d.summary.submissions],['Q&A 对',d.summary.qa_pairs],['学生数',d.summary.students],['预警数',d.summary.alerts]];
document.getElementById('kpis').innerHTML=kpis.map(k=>`<div class="card kpi"><div class="num">${k[1]}</div><div class="lab">${k[0]}</div></div>`).join('');
document.getElementById('challenges').innerHTML=d.by_challenge.map(c=>`<div style="margin:10px 0"><div style="display:flex;justify-content:space-between"><span>${c.id} ${c.name}</span><span>${c.done} 人 · ${c.rate}%</span></div><div class="bar"><i style="width:${c.rate}%"></i></div></div>`).join('');
document.getElementById('students').innerHTML='<tr><th>学生</th><th>消息</th><th>答疑</th><th>提交</th><th>标签</th></tr>'+d.top_students.map(s=>`<tr><td>${s.name}</td><td>${s.messages}</td><td>${s.answers}</td><td>${s.submissions}</td><td>${s.skill_tags.map(t=>`<span class="tag">${t}</span>`).join('')}</td></tr>`).join('');
document.getElementById('alerts').innerHTML=d.alerts.length?d.alerts.map(a=>`<div class="alert"><b>[${a.severity}] ${a.kind}</b> · ${a.subject}：${a.detail}</div>`).join(''):'<div class="alert" style="border-color:var(--accent)">本周期无预警</div>';
});
</script></body></html>
"""


def write_dashboard_html(path: Path | None = None) -> Path:
    path = path or (OUT_DIR / "dashboard.html")
    write_text(path, HTML)
    return path


def serve(data_path: Path | None = None, port: int = 8765) -> None:
    data_path = data_path or (OUT_DIR / "dashboard_data.json")
    html_path = write_dashboard_html()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/data"):
                body = data_path.read_bytes()
                ctype = "application/json; charset=utf-8"
            else:
                body = html_path.read_bytes()
                ctype = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    addr = ("127.0.0.1", port)
    print(f"Dashboard: http://{addr[0]}:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(addr, Handler).serve_forever()
