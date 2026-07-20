# macOS 安装指南

推荐 macOS 13+、Python 3.11 或 3.12、Apple Silicon。Intel Mac 也能使用，但本地转写会更慢。

## 1. 克隆项目

```bash
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox
```

## 2. 安装基础依赖

```bash
brew install python@3.12 ffmpeg node
npm install -g @larksuite/cli
```

没有 Homebrew 时，先按 [brew.sh](https://brew.sh/) 的官方说明安装。

## 3. 安装本地转写环境

```bash
python3.12 -m venv asr-venv
./asr-venv/bin/python -m pip install --upgrade pip setuptools wheel
./asr-venv/bin/pip install -r requirements/asr-macos.txt
```

依赖文件固定了仓库真实验证过的 FunASR/ModelScope 核心版本；PyTorch 仍由 pip 按当前 Mac 芯片和 Python 选择兼容 wheel。

首次转写会下载 SenseVoice、VAD、标点和说话人模型，耗时和磁盘占用明显高于后续运行。下载完成后模型会留在 ModelScope 本机缓存，后续任务直接复用；首次运行时请保持网络稳定，不要中途清理缓存目录。

## 4. 授权飞书

```bash
lark-cli auth login --domain drive,docs --scope "im:message.send_as_user im:message"
lark-cli auth status --json
```

命令会给出浏览器链接或二维码，需要你在飞书中确认。项目使用当前账号读取录音、创建纪要并给自己发送结果消息，不需要额外配置 Webhook。

## 5. 运行配置向导

```bash
python3 scripts/setup.py
```

准备两个飞书文件夹：

- 录音收件箱：上传新录音；
- 录音结果：接收智能纪要和文字稿。

向导中直接粘贴浏览器地址栏的完整文件夹链接。

## 6. 自检和首次试跑

```bash
python3 scripts/setup_check.py
python3 scripts/setup_check.py --test-notification
python3 scripts/run.py
```

`--test-notification` 会发送一条真实飞书测试消息，不想发送时跳过这一条。

首次试跑前，往“录音收件箱”上传一条 30 秒以上、能听清人声的录音。成功标志：

- `output/minutes/` 出现 Markdown；
- “录音结果”文件夹出现两篇飞书文档；
- 当前飞书账号收到完成消息；
- `data/tasks/<录音>/status.json` 为 `published`。

## 7. 开启后台自动处理

```bash
mkdir -p logs
sed "s|/path/to/recording-inbox|$(pwd)|g" \
  launchd/com.example.recording-inbox.plist \
  > ~/Library/LaunchAgents/com.example.recording-inbox.plist
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

模板使用项目里的 `asr-venv/bin/python`，不会依赖后台环境中不稳定的系统 Python 路径。

如果提示服务已存在：

```bash
launchctl bootout gui/$(id -u)/com.example.recording-inbox
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

之后每 3 分钟自动检查一次。电脑关机时录音留在飞书，重新开机登录后自动继续。

## 卸载后台任务

```bash
launchctl bootout gui/$(id -u)/com.example.recording-inbox
rm ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

不会删除录音、纪要或任务数据。
