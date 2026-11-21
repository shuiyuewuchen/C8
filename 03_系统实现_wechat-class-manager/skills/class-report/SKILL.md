---
name: class-report
description: Generate a weekly class-status report and trigger deadline, silence and submission-rate alerts from the accumulated class graph. Use at the end of each week, or when a teacher asks for class status, a printable report, or a pull-quote for a newsletter.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# Class Report (Layer 4)

## Inputs
- `messages`, `submissions`, `qa_pairs`, `student_profiles`, `challenges`

## Outputs
- `outputs/weekly_report.md` — 5 sections, Markdown
- `outputs/alerts.json` — alert objects
- `outputs/dashboard_data.json` — 5+ dashboard dimensions

## Alert rules
1. Deadline within 3 days and unsubmitted → high
2. Silent ≥ 7 days → medium
3. Challenge submission rate < 30% → high
4. Activity delta drop > 40% → medium (KSTAR learning signal)

## Natural-language queries
`张三提交了哪些挑战` / `C4 还有谁没交` / `最近一周谁最活跃` /
`关于 GitHub 的常见问题` / `这周班级状态如何`

## Run
`python3 skills/class-report/reporter.py`
