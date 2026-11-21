---
name: submission-tracker
description: Detect challenge submissions from WeChat file messages, build the student-by-challenge matrix, and flag missing required artefacts such as the AI usage log. Use when checking who submitted what, what is incomplete, or who needs a nudge before a deadline.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# Submission Tracker (Layer 3)

## Inputs
- `messages`: MessageStream (from wechat-bridge)
- `challenges`: ChallengeConfig (from config/challenges.json)

## Outputs
- `submissions: SubmissionMatrix` — student × challenge
- `missing: [MissingItem]` — e.g. `AI日志` absent
- `alerts: [Alert]` — items with `status=needs_revision`

## Detection rule
Filename pattern `姓名_C编号_描述.ext`, e.g. `张三_C4B_demo.pdf`.
A proposal without a companion AI log for the same challenge is marked
`needs_revision` — this encodes the course's "no AI log = no submission" rule.

## Edge cases
- Batch uploads in one message → only the first filename is parsed (documented limitation W2).
- Renamed files fall through to the challenge linker's keyword matcher.

## Run
`python3 skills/submission-tracker/tracker.py`
