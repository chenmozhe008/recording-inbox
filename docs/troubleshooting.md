# 故障恢复指南

先运行：

```bash
python scripts/setup_check.py
python scripts/run.py
```

## 从哪里看问题？

```text
logs/run.out.log                     正常运行记录
logs/run.err.log                     后台错误
data/tasks/<录音>/status.json        当前状态和错误原因
data/tasks/<录音>/transcript.txt     文字记录
data/tasks/<录音>/minutes.md          智能纪要
```

## 状态说明

```text
pending
  → transcribing
  → transcript_ready
  → summarizing
  → minutes_ready
  → published
```

失败状态：

- `transcription_failed`：本地转写失败；
- `minutes_failed`：模型 API 或纪要生成失败；
- `publish_failed`：飞书文档导入失败。

可恢复失败会在下一轮继续。音频缺失、过短等确定性问题会标记为不可自动重试。

## 电脑关机后会怎样？

- 还没下载的录音留在飞书 inbox；
- 已下载的任务状态保存在磁盘；
- 重新开机后，后台任务从当前阶段继续；
- 断电遗留的死锁会立即清理；
- 电脑关机期间无法发送离线通知，这是本地处理方案的物理限制。

## 常见问题

| 现象 | 优先检查 |
|---|---|
| inbox 有录音但没处理 | 电脑是否开机、后台任务是否安装、lark-cli 是否登录 |
| 一直显示上一轮运行中 | 更新到最新版；新版会识别死进程并清锁 |
| 转写失败 | FunASR 环境、ffmpeg、音频是否有有效人声 |
| 纪要只有文字记录 | `.env` 是否有 Key、`summary_enabled` 是否开启 |
| API 401/403 | Key 无效或权限问题 |
| API 402 | 余额不足 |
| 飞书文档没生成 | output 文件夹链接和账号权限 |
| 文档有但没收到消息 | IM 权限；运行 `setup_check.py --test-notification` |
| Windows 后台没反应 | `logs/run.err.log`、任务计划、`lark-cli.cmd` 路径 |

## 如何安全重试？

多数失败直接运行：

```bash
python scripts/run.py
```

不要删除整个 `data/`。如果需要让某个飞书文件重新拉取，只处理对应任务和台账记录，并先备份；不确定时提交 Issue。
