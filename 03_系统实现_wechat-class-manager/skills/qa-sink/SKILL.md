---
name: qa-sink
description: Extract question-answer pairs from a WeChat class group using reply chains and a time window, tag them by challenge, and score answer quality. Use when building a course FAQ, mining recurring questions, or preparing material for a weekly report.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# Q&A Sink (Layer 3)

## Inputs
- `messages`: MessageStream with intent labels
- `window_minutes`: max gap for non-reply matching (default 45)

## Outputs
- `outputs/qa_pairs.json` — question, answer, asker, answerer, topic_tags, quality_score

## Matching policy
1. Explicit reply chain (`reply_to` points at a question) — highest confidence.
2. Same topic within the time window, answered by a different person.
3. Quality score from length, solution markers and reply-chain presence.

## Edge cases
- Self-answers are ignored.
- Answers shorter than 8 characters are ignored.
- One answer is consumed by at most one question (avoids double counting).

## Run
`python3 skills/qa-sink/sink.py`
