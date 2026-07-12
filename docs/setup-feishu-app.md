# 飞书配置

普通用户只需要：登录 lark-cli、建立两个文件夹。快捷指令自建应用和旧 Webhook 都是高级选项。

## 1. lark-cli 授权（必做）

```bash
npm install -g @larksuite/cli
lark-cli auth login --domain drive,docs --scope "im:message.send_as_user im:message"
lark-cli auth status --json
```

授权包含：

- 读取 inbox 音频；
- 创建和导入飞书文档；
- 用当前飞书账号给自己发送完成/失败消息。

它不需要你创建飞书自建应用。

## 2. 建立文件夹（必做）

在飞书云盘建立：

- `recording-inbox`：上传录音；
- `recording-minutes`：接收纪要，可选。

打开文件夹，复制浏览器地址栏完整链接，例如：

```text
https://your-team.feishu.cn/drive/folder/FOLDER_TOKEN
```

运行 `python scripts/setup.py`，把链接直接粘进去。程序自己提取 token。

## 3. 结果通知（默认）

新安装默认：

```json
{
  "feishu_notify_mode": "direct",
  "feishu_notify_user_id": "auto"
}
```

程序从 lark-cli 自动识别当前账号，完成后直接发飞书消息，不需要建群、加机器人或复制 Webhook。

验证：

```bash
python scripts/setup_check.py --test-notification
```

这条命令会发送真实测试消息。

## 4. 群机器人 Webhook（旧配置兼容）

已有用户可以继续使用：

```json
{
  "feishu_notify_mode": "webhook",
  "feishu_notify_webhook": "YOUR_WEBHOOK_URL"
}
```

新用户通常不需要这条路径。Webhook 只保留兼容和团队群通知场景。

## 5. iPhone 快捷指令自建应用（高级）

只有想让快捷指令直接调用飞书 API 上传时才需要 App ID / App Secret。日常手动上传、电脑拖拽、转写、纪要和结果通知都不依赖它。

配置步骤见 [手机上传教程](upload-from-phone.md#iphone-快捷指令高级)。App Secret 不要发给任何人、不要截图、不要提交 GitHub。

## 常见问题

- 登录链接打不开：运行 `lark-cli auth qrcode` 用飞书扫码。
- 下载无权限：重新授权 `drive,docs`，并确认账号能打开 inbox 文件夹。
- 消息无权限：重新申请 `im:message.send_as_user im:message` scope。
- output 没文档：检查 output 文件夹链接和编辑权限。
