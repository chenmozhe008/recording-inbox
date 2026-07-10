# 贡献指南

感谢你帮助改进 recording-inbox。

## 先确认范围

这个仓库只维护轻量链路：飞书 inbox、电脑本地转写、智能纪要、飞书文档和通知。

多维表工作台、每日确认卡、任务分流、AI 自动执行和 iOS App 不在本仓库范围内。

## 提交 Bug

请提供：

- macOS / Windows 版本；
- Python 版本；
- 安装方式（手动或 AI Agent）；
- 可复现步骤；
- `status.json` 中的状态和错误；
- 已脱敏的日志片段。

不要上传 API Key、飞书 token、open_id、chat_id、Webhook 或个人录音。

## 提交代码

```bash
python -m py_compile scripts/*.py run_launcher.py
python -m unittest discover -s tests -v
```

PR 应保持改动集中、说明原因，并补相应测试。Windows 专属改动请说明是否在 Windows 10/11 真机验证。
