---
name: student-profile
description: Build per-student capability profiles from WeChat group interaction - message volume, questions asked, answers given, submissions, activity recency and inferred skill tags. Use when a teacher wants to understand student engagement or identify silent students.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# Student Profile (Layer 3)

## Inputs
- `messages`, `submissions`, `qa_pairs`

## Outputs
- `outputs/student_profiles.json`

## Tags
`稳定交付者` / `答疑贡献者` / `主动提问者` / `高活跃` / `待激活`

## Privacy rule
Only group-nickname-level aggregates are stored; no message content is copied
into the profile. Staff senders are excluded.

## Run
`python3 skills/student-profile/profiler.py`
