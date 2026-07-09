# recording-inbox 项目规范

> 这是 feishu-minutes-automation（私有主系统）的**开源精简版**，教程配套项目。
> 定位：让读者一个周末跑通「iPhone 录音 → 飞书云盘 → Mac 本地转写 → 智能纪要 → Markdown/飞书文档」最小链路。

## 铁律

1. **这是精简版，不是主系统的镜像。** 主系统的功能（审过闭环、台账 Base、map-reduce、妙记兜底、月度归档、确认卡）**永远不进这个仓库**。有人提 issue 要这些功能，回答是「超出本项目范围」。
2. **面向读者写代码**：单文件职责单一、注释解释「为什么」、不用只有作者懂的缩写。读者是跟公众号教程来的非程序员/半程序员。
3. **脱敏红线**：任何 commit 前确认无 token/secret/open_id/chat_id/设备 ID/作者本机绝对路径。`config.json`、`.env` 永不入 git。
4. **依赖最少化**：能用标准库不引第三方；外部依赖只允许 lark-cli、FunASR/whisper.cpp、ffmpeg、DeepSeek API（可选）。
5. **从主系统同步改进时**，只搬"精简链路涉及的 bugfix"，不搬功能。

## 目录约定

```
scripts/     核心脚本（保持 ≤7 个文件）
docs/        教程（快捷指令配置 / 飞书自建应用配置）
launchd/     定时任务模板（占位路径，读者替换）
config.example.json   配置模板（读者拷成 config.json 填自己的）
```

## 验证

- 改脚本后：`python3 -m py_compile scripts/*.py`
- 发布前：跑 `scripts/setup_check.py` 确认依赖检查逻辑本身没坏
- 发布前：脱敏 grep（模式清单见主系统会话记录）

## 关联

私有上下文（主系统路径、文章草稿位置等）见 `CLAUDE.local.md`（gitignore，不随仓库发布）。
