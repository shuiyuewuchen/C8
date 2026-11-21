# 赵心皓_C8_W1_AI日志.md

## 目标
建立统一消息 schema 与双适配器桥接层。

## 第 1 轮
**Prompt**：`帮我设计一个微信群消息的 JSON schema，要能表达文本、文件、图片和回复关系。`

**AI 输出**：给出一个包含 15 个字段的大 schema，含 `emoji_count`、`is_at_all` 等当时用不到的字段。

**我的判断**：过度设计。课程验收只要求 msg_id / timestamp / sender / type / content / media_ref / reply_to。

## 第 2 轮（收窄）
**Prompt**：`只保留 7 个必需字段：msg_id, timestamp, sender{wechat_id,nickname}, type, content, media_ref, reply_to。sender 必须是嵌套对象。写一个 Python dataclass，并提供 to_dict/from_dict 兼容异构输入。`

**AI 输出**：符合要求的 dataclass，但 `to_dict()` 输出了扁平的 `sender_wechat_id` / `sender_nickname`。

**我当时没发现**，直到 W4 验收 L1-2 报 FAIL 才修正为嵌套结构。这是一个真实教训：
AI 生成的代码"看起来对"不等于符合契约，必须有自动验收兜底。

## 第 3 轮（适配器）
**Prompt**：`写两个适配器：fixture 读取本地 JSONL，cli 调用 wechat-cli history --format json。把字段归一化逻辑放在一个 normalize() 里，两个适配器共用。要求只读，不写回微信。`

**AI 输出**：基本可用，但 `read_cli` 里直接用了 `--days` 参数——而实际 wechat-cli 的 history 命令用 `--start-time/--end-time`。

**我的修改**：改为 over-fetch 后在本地按时间戳过滤，避免依赖特定 CLI 版本参数。

## 第 4 轮（样本生成器）
**Prompt**：`生成一个可复现的脱敏微信群消息样本，包含 24 名学生、8 个挑战、至少 150 条消息，涵盖通知/提交/提问/回答/讨论/资源/闲聊，并把 ground truth 标签单独存到另一个文件。`

**AI 输出**：生成了 164 条，但 ground truth 和消息写在同一个文件里。

**我的修改**：拆成 `sample_messages.jsonl` 与 `fixtures/labels.json`；
增加 image/voice 类型；修正学生数硬编码 12 → `len(STUDENTS)`；最终 168 条。

## 反思
这一轮 AI 帮我快速搭出骨架，但**三次错误都由我或验收脚本发现**：
schema 扁平化、CLI 参数假设、标签与数据同文件。
结论：AI 适合生成候选实现，不适合做最终判定；契约检查必须写成可执行代码。
