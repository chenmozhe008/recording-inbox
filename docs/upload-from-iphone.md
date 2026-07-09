# iPhone 端：把录音送进飞书云盘 inbox

Mac 端只认一个入口：飞书云盘里你指定的 inbox 文件夹。录音怎么进去都行，下面三种方式按门槛从低到高。

## 方式一：手动分享（零配置，先跑通全链路用这个）

1. 用 iPhone 自带「语音备忘录」录音；
2. 录完点分享 → 选「飞书」；
3. 在飞书里选「保存到云文档」→ 选你的 inbox 文件夹。

下一分钟 Mac 就会拉走处理。先用这个方式验证链路通，再考虑自动化。

## 方式二：快捷指令自动上传（推荐日常用）

做一个快捷指令，录音文件分享给它就自动传到 inbox，全程不用打开飞书。

前置：你已经按 `docs/setup-feishu-app.md` 建好了飞书自建应用，手里有 `app_id`、`app_secret` 和 inbox 文件夹的 `folder_token`。

在 iPhone「快捷指令」App 里新建，依次加这几个动作：

1. **「接收分享的输入」**：类型勾选「文件」（这样能从语音备忘录的分享菜单调起）；
2. **「获取 URL 内容」**（第一次调用，拿访问凭证）：
   - URL：`https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
   - 方法：POST，请求体 JSON：`app_id` = 你的 app_id，`app_secret` = 你的 app_secret
3. **「获取词典值」**：从上一步结果里取 `tenant_access_token`；
4. **「获取文件详细信息」**：对快捷指令输入取「大小（字节）」和「名称」；
5. **「获取 URL 内容」**（第二次调用，上传文件）：
   - URL：`https://open.feishu.cn/open-apis/drive/v1/files/upload_all`
   - 方法：POST
   - 头部：`Authorization` = `Bearer 上一步的token`
   - 请求体选「表单」，加字段：
     - `file_name`（文本）= 文件名称
     - `parent_type`（文本）= `explorer`
     - `parent_node`（文本）= 你的 inbox folder_token
     - `size`（文本）= 文件大小（字节数）
     - `file`（文件）= 快捷指令输入
6. （可选）**「显示通知」**：提示上传成功。

用法：语音备忘录录完 → 分享 → 选这个快捷指令。

> 注意：`app_secret` 写在你自己手机的快捷指令里，只在你的设备上，风险可控；但**不要把配好的快捷指令直接分享给别人**，里面带着你的密钥。

## 方式三：配套 iOS App（进阶，需要自己编译）

仓库作者日常用的是一个专门的录音 App（灵动岛计时、分段保存、录音标记、直传飞书），源码在主项目里。因为苹果的限制，个人开发者签名的 App 只有 7 天有效期，**没法直接分发安装包**——你需要 Mac + Xcode 自己签名装到手机上，7 天后重装一次续期。

对大多数人，方式二已经够顺手；方式三适合愿意折腾 Xcode 的玩家。
