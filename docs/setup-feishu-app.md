# 飞书侧配置

分两部分：电脑端（人人都要做，5 分钟）和自建应用（只有用快捷指令自动上传才需要）。

## 一、电脑端：lark-cli 安装与授权（必做）

lark-cli 是飞书官方命令行工具，本项目所有飞书操作（下载录音、导入文档）都靠它。
它用「设备授权」模式登录你自己的飞书账号，**不需要你创建任何应用**。

```bash
# 1. 安装（需要 Node.js，没有就先 brew install node）
npm install -g @larksuite/cli

# 2. 授权登录（会给一个链接/二维码，用飞书 App 扫码确认）
lark-cli auth login --domain drive,docs

# 3. 确认授权成功
lark-cli auth status
```

## 二、建 inbox 文件夹，拿 folder_token（必做）

1. 打开飞书网页版 → 云文档 → 云盘，新建一个文件夹，比如叫 `录音inbox`；
2. 打开这个文件夹，看浏览器地址栏：
   `https://xxx.feishu.cn/drive/folder/FldbxxxxxxxxxxxxxxxxxxxN`
   最后那串就是 `folder_token`；
3. 填进 `config.json` 的 `feishu_inbox_folder_token`。

想让纪要也发成飞书在线文档的话，再建一个输出文件夹（比如 `会议纪要`），同样方式拿 token 填进 `feishu_output_folder_token`。留空则只出本地 Markdown。

## 三、自建应用（只有快捷指令自动上传才需要）

iPhone 快捷指令直接调飞书开放平台 API 上传文件，需要一个「自建应用」的凭证：

1. 打开 [飞书开放平台](https://open.feishu.cn) → 开发者后台 → 创建企业自建应用（个人版飞书也可以建）；
2. 名字随意（比如「录音上传」），创建后进「凭证与基础信息」，记下 `App ID` 和 `App Secret`；
3. 进「权限管理」，搜索并开通：`drive:drive`（查看、评论、编辑和管理云空间中所有文件）——快捷指令上传文件要用；
4. 进「版本管理与发布」，创建版本并发布（个人版通常秒过审）；
5. **关键一步**：把 inbox 文件夹共享给这个应用——回到云盘 inbox 文件夹 → 分享 → 添加协作者 → 搜你的应用名字 → 给「可编辑」权限。不做这步，快捷指令上传会报无权限。

拿到 `App ID` / `App Secret` 后，回到 `docs/upload-from-phone.md` 继续配快捷指令。

## 常见问题

- **`lark-cli auth login` 打不开链接**：手机飞书 App 扫二维码也行（`lark-cli auth qrcode`）。
- **下载报权限错误**：确认授权时带了 `--domain drive,docs`；重新 `lark-cli auth login` 补授权即可。
- **快捷指令上传 403**：九成是第三步第 5 条没做（文件夹没共享给应用）。
