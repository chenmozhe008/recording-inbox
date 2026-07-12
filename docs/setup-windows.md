# Windows 10/11 安装指南

推荐 Windows 10/11 64 位、Python 3.11 或 3.12、Node.js 18+。Python 3.13 可以尝试，但部分语音依赖在不同机器上可能缺少预编译包；普通用户优先使用 3.11/3.12。

## 1. 克隆项目

在 PowerShell 或 Windows Terminal 中运行：

```powershell
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox
```

## 2. 安装 lark-cli

```powershell
npm install -g @larksuite/cli
lark-cli auth login --domain drive,docs --scope "im:message.send_as_user im:message"
lark-cli auth status --json
```

授权时用飞书确认。项目使用当前账号读取录音、创建纪要并给自己发送结果消息，不需要额外配置群机器人 Webhook。

如果系统找不到命令：

```powershell
where.exe lark-cli.cmd
```

把找到的完整路径填进 `config.json` 的 `executables.lark_cli`。

## 3. 安装本地转写环境

```powershell
python -m venv asr-venv
asr-venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
asr-venv\Scripts\pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple funasr modelscope torch torchaudio soundfile scikit-learn zhconv truststore imageio-ffmpeg
```

`imageio-ffmpeg` 自带 ffmpeg，通常无需单独下载。

如果 `editdistance` 或其他包编译失败，不要手工往 `site-packages` 伪造包。先删除 `asr-venv`，换 Python 3.11/3.12 重新创建环境；仍失败再提交 Issue，并附完整错误和 Python 版本。

## 4. 运行配置向导

```powershell
python scripts\setup.py
```

提前在飞书云盘建立：

- inbox：手机或电脑上传录音；
- output：接收智能纪要，可留空。

向导中直接粘贴完整文件夹链接，不需要自己截取 token。

## 5. 自检和首次试跑

```powershell
python scripts\setup_check.py
python scripts\setup_check.py --test-notification
python scripts\run.py
```

`--test-notification` 会发送一条真实飞书测试消息，不想发送时跳过。

首次试跑前，上传一条 30 秒以上、能听清人声的录音。成功标志：

- `output\minutes\` 出现 Markdown；
- 飞书 output 文件夹出现文档；
- 当前飞书账号收到完成消息；
- `data\tasks\<录音>\status.json` 为 `published`。

## 6. 开启后台自动处理

双击：

```text
windows\setup_scheduled_task.bat
```

任务计划每分钟静默运行一次。查看：

```powershell
schtasks /query /tn "recording-inbox"
type logs\run.out.log
type logs\run.err.log
```

电脑关机时录音留在飞书，重新开机登录后自动继续。

## 卸载后台任务

双击：

```text
windows\remove_scheduled_task.bat
```

不会删除录音、纪要或任务数据。

## 常见问题

| 问题 | 处理 |
|---|---|
| pip 下载慢 | 使用上面的清华镜像；失败时切回官方 PyPI 再试 |
| ffmpeg 找不到 | 确认 `imageio-ffmpeg` 安装在 `asr-venv` |
| 定时任务弹黑框 | 重新运行官方 `setup_scheduled_task.bat` |
| 后台找不到 lark-cli | 用 `where.exe lark-cli.cmd` 找完整路径 |
| 文档生成但没通知 | 检查 IM 权限并运行通知测试 |
| 重启后不继续 | 更新到最新版并查看 `logs\run.err.log` |

更多见 [故障恢复指南](troubleshooting.md)。
