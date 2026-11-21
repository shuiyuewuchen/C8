---
name: wechat-bridge
description: Extract a WeChat group's message stream and normalise it to the canonical Message JSONL schema. Use when an agent needs to read class-group messages, archive submissions, or feed downstream class-management skills. Output is de-identified and stays local.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# WeChat Bridge (Layer 1)

Turns a WeChat channel into a structured message stream.

## Inputs
- `adapter`: `fixture` (offline, reproducible) or `cli` (live `wechat-cli`)
- `group`: group name for the CLI adapter
- `days`: look-back window

## Outputs
- `outputs/messages.jsonl` — one canonical Message per line

## Canonical schema
`msg_id`, `timestamp`, `sender{wechat_id,nickname}`, `type`, `content`, `media_ref`, `reply_to`

## Steps
1. Call `bridge.bridge(adapter, group, days)`.
2. Verify count and message-type diversity before passing downstream.
3. On `cli` adapter, never write back to WeChat; the bridge is read-only.

## Edge cases
- Missing `msg_id` → record is rejected (fail loud, do not silently drop).
- Unknown message types are coerced to `text` and counted in the run log.

## Run
`python3 skills/wechat-bridge/bridge.py --adapter fixture`
