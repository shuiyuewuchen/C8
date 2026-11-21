---
name: msg-classifier
description: Classify WeChat class-group messages by intent and attach a challenge reference. Use when you need to know whether a message is a submission, question, answer, announcement, resource, discussion or social chatter, and which C1-C8 challenge it belongs to.
license: MIT
metadata:
  author: C8-operator
  version: "1.0"
---

# Message Classifier (Layer 2)

## Inputs
- `messages`: canonical MessageStream from `wechat-bridge`
- `challenges`: challenge config (keywords, deadlines)

## Outputs
- `outputs/enriched_messages.jsonl` — original message + `intent`, `challenge_ref`, `confidence`, `evidence`

## Intent taxonomy
`submission | question | answer | discussion | announcement | resource | social`

## Method
Two-pass hybrid: structural signals (message type, reply chain) + lexical signals
(keywords, lengths). A rule engine is used first; a LLM classifier can be
substituted for `classify_message()` without changing downstream contracts.

## Accuracy protocol
Evaluate against `data/fixtures/labels.json` with `evaluate_classifier()`.
Target > 70%. Note: rules and labels were co-designed, so this is an internal
upper bound; external validity requires a held-out human-labelled set.

## Run
`python3 skills/msg-classifier/classifier.py`
