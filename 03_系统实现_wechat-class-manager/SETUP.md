# 安装与运行指南

## 1. 环境要求

- Python 3.9+（仅标准库，`requirements.txt` 为空依赖声明）
- 可选：`wechat-cli`（接入真实群消息时才需要）
- 可选：现代浏览器（查看本地仪表盘）

## 2. 离线演示（不需要微信）

```bash
cd "03_系统实现_wechat-class-manager"
python3 run_pipeline.py
python3 verify.py
```

预期输出：`Verification: 18/18 passed -> APPROVE`。

如需重新生成样本数据：

```bash
python3 data/generate_fixture.py
python3 run_pipeline.py
```

## 3. 接入真实微信群

### 3.1 安装 wechat-cli（官方仓库）

```bash
# 方式 A：npm（macOS arm64 有预编译二进制）
npm install -g @canghe_ai/wechat-cli

# 方式 B：pip
pip install wechat-cli

# 方式 C：源码
git clone https://github.com/freestylefly/wechat-cli.git
cd wechat-cli && pip install -e .
```

官方仓库：<https://github.com/freestylefly/wechat-cli>

### 3.2 初始化（ macOS 需要完全磁盘访问权限）

1. 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 加入你的终端。
2. 保持微信运行，执行 `sudo wechat-cli init`。
3. 若出现 `task_for_pid failed`，按工具提示重新签名微信后重试。
4. 验证：`wechat-cli sessions --limit 5`、`wechat-cli history "群名" --limit 20 --format json`。

### 3.3 运行桥接

```bash
python3 run_pipeline.py --adapter cli --group "Elite20-项目协同群" --days 7
```

桥接器通过 `subprocess` 调用 `wechat-cli history ... --format json`，把不同版本的字段
（`time`/`timestamp`、`text`/`content` 等）归一到统一 schema。**全程只读，不向微信写任何内容。**

备选适配器：`sjzar/chatlog`（HTTP API + MCP，<https://github.com/sjzar/chatlog>），
可在 `wcm/bridge.py::read_cli` 中替换实现，上层模块无需改动。

## 4. 单独运行某个 Skill

每个 skill 都是独立可执行的：

```bash
python3 skills/wechat-bridge/bridge.py --adapter fixture
python3 skills/msg-classifier/classifier.py
python3 skills/submission-tracker/tracker.py
python3 skills/qa-sink/sink.py
python3 skills/student-profile/profiler.py
python3 skills/class-report/reporter.py
```

在 Claude Code / OpenClaw 中，把 `skills/` 复制到对应的 skills 目录
（Claude Code：`.claude/skills/`；通用：`.agents/skills/`），Agent 会按 description 自动选择。

## 5. 仪表盘

```bash
python3 run_pipeline.py --serve          # 或 python3 -m wcm.dashboard
# 浏览器打开 http://127.0.0.1:8765
```

只监听 `127.0.0.1`，不对外暴露。

## 6. 常见问题

| 问题 | 处理 |
|---|---|
| `wechat-cli not found` | 确认 PATH；或改用 `--adapter fixture` |
| `init` 失败 | 检查完全磁盘访问权限；确认微信在运行 |
| 分类准确率异常低 | 真实群数据与标注集分布不同，先人工标注 50 条再调关键词 |
| 提交漏检 | 检查文件名是否符合 `姓名_C编号_描述.ext`；批量上传目前只解析第一个文件 |
| 图表空白 | 先运行 `run_pipeline.py` 生成 `outputs/dashboard_data.json` |
