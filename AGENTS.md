# 给 AI Agent 的部署手册

用户希望部署 `recording-inbox`：飞书 inbox → 电脑本地转写 → AI 智能纪要 → 飞书文档和消息。

## 边界

- 不要把私有主系统的多维表、确认卡、任务分流或 iOS App 搬进来。
- 不要把 API Key、folder token、open_id、Webhook、个人路径或录音提交到 Git。
- 不要代替用户完成扫码、输入 Key、真实通知测试等需要本人确认的步骤。
- 先跑自检，再试录音，最后才安装后台任务。

## 先判断系统

- macOS：读 `docs/setup-macos.md`
- Windows 10/11：读 `docs/setup-windows.md`

不要默认用户使用 Mac。

## 需要用户本人完成

1. 飞书扫码授权；
2. 提供 inbox / output 文件夹完整链接；
3. 在本机安全输入 DeepSeek API Key；
4. 决定是否发送真实测试通知。

## macOS 最短路径

```bash
brew install python@3.12 ffmpeg node
npm install -g @larksuite/cli
python3.12 -m venv asr-venv
./asr-venv/bin/python -m pip install --upgrade pip setuptools wheel
./asr-venv/bin/pip install funasr modelscope torch torchaudio soundfile scikit-learn zhconv
lark-cli auth login --domain drive,docs --scope "im:message.send_as_user im:message"
python3 scripts/setup.py
python3 scripts/setup_check.py
```

## Windows 最短路径

```powershell
npm install -g @larksuite/cli
python -m venv asr-venv
asr-venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
asr-venv\Scripts\pip.exe install funasr modelscope torch torchaudio soundfile scikit-learn zhconv imageio-ffmpeg
lark-cli auth login --domain drive,docs --scope "im:message.send_as_user im:message"
python scripts\setup.py
python scripts\setup_check.py
```

普通用户优先 Python 3.11/3.12。Windows 编译依赖失败时，不要伪造 `site-packages`，换稳定 Python 建新虚拟环境。

## 验收

至少完成：

1. `setup_check.py` 核心项通过；
2. 用户上传一条 30 秒以上测试录音；
3. 手动运行 `scripts/run.py`；
4. `output/minutes/` 有 Markdown；
5. output 文件夹有飞书文档；
6. 经用户同意后，`--test-notification` 或真实完成通知成功；
7. `status.json` 为 `published`；
8. 才安装 launchd / Windows Task Scheduler。

## 排错顺序

1. `python scripts/setup_check.py`
2. `logs/run.err.log`
3. `data/tasks/<录音>/status.json`
4. `docs/troubleshooting.md`

修改代码后运行：

```bash
python -m py_compile scripts/*.py run_launcher.py
python -m unittest discover -s tests -v
```
