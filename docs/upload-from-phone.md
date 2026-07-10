# 手机端：把录音送进 inbox

电脑端只认一个入口：飞书云盘里的 inbox 文件夹。录音从 iPhone、Android、微信、网盘或电脑拖进去都可以。

> ⚠️ 先说一个坑：手机上用系统「分享 → 飞书」**进不了** inbox 文件夹。
> iPhone 语音备忘录分享给飞书只有「音视频转妙记」，安卓只有「发送给自己/群、音视频转文字」——
> 这些要么进 IM、要么走飞书妙记（**消耗妙记额度**），都不会落进云盘 inbox。
> 所以手机端要么在**飞书 App 里主动上传**，要么用 **iPhone 快捷指令**，别走系统分享。

## 最简单路径：飞书 App 里手动上传

### iPhone

语音备忘录里的录音，飞书上传时选不到，得先导出到「文件」再传：

1. 语音备忘录里录完 → 点分享 → 选「保存到"文件"」，存到 iPhone 本地或 iCloud。
2. 打开飞书 App → 云空间 → 进 `recording-inbox` 文件夹。
3. 点右下角 `+` → 上传 → 从「文件」里选刚存的那段录音。

每天都录的话，别每次这么点——直接用下面的「快捷指令自动上传」，分享一下就进 inbox。

### Android

安卓要注意：很多手机（比如小米）用系统录音机「分享到飞书」，弹出来只有
「发送给自己 / 发送给同事或群 / 音视频转文字」三个入口 —— 这几个都**进不了**
云盘的 inbox 文件夹（其中「音视频转文字」还会走飞书妙记、消耗妙记额度）。

所以安卓**别用系统分享**，直接在飞书 App 里上传最稳：

1. 打开飞书 App。
2. 进「云空间」。
3. 打开你的 `recording-inbox` 文件夹。
4. 点右下角 `+` → 上传 → 从手机里选刚录的音频文件。

这样录音一定落进 inbox 文件夹，电脑端下一轮就能接手。

> 如果你从**文件管理器**（而不是录音 App）里分享音频到飞书，部分机型/版本会
> 多出「保存到云盘」选项，也可以用；但飞书内主动上传是所有安卓机都通用的稳妥做法。

## 电脑拖进去也可以

别人微信、企业微信、网盘发给你的音频，不用传手机：

1. 下载到电脑。
2. 打开飞书云盘的 `recording-inbox` 文件夹。
3. 直接拖进去。

后台下一轮会自动处理。

## iPhone 快捷指令自动上传（进阶）

适合每天录很多音的人。做好后：语音备忘录分享给快捷指令，自动上传到 inbox，不用手动打开飞书。

需要一个飞书自建应用的 `App ID` / `App Secret`，步骤见 [setup-feishu-app.md](setup-feishu-app.md)。

快捷指令动作：

1. 接收分享输入，类型选「文件」。
2. 获取 URL 内容：`https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
   - 方法：POST
   - 请求体选「JSON」，加两个字段（值换成你自己应用的）：

     ```json
     {
       "app_id": "cli_xxxxxxxx",
       "app_secret": "你的 App Secret"
     }
     ```

3. 获取词典值：`tenant_access_token`（从上一步的结果里取）。
4. 获取文件详细信息：名称、大小。
5. 获取 URL 内容：`https://open.feishu.cn/open-apis/drive/v1/files/upload_all`
   - 方法：POST
   - Header：`Authorization` = `Bearer ` + 第 3 步取到的 tenant_access_token
   - 请求体选「表单」，字段：
     - `file_name`：文件名（第 4 步的「名称」）
     - `parent_type`：`explorer`
     - `parent_node`：inbox 文件夹链接里 `/folder/` 后面那串字符（形如 `FldbxxxxxxxxN`）
     - `size`：文件大小（第 4 步的「大小」）
     - `file`：分享输入的文件
6. 显示通知：上传完成。

不要把带 `app_secret` 的快捷指令发给别人。

配置过程卡住了不用硬磕——退回上面「飞书 App 里手动上传」那条路一样能用，
或者把本页丢给 AI 助手让它一步步带你配。

## 日常怎么判断成功

- 手机端只负责上传，不负责转写。
- 电脑端开机并运行后台任务后，1 分钟内会接手。
- 结果在飞书输出文件夹和 `output/minutes/` 里。
- 想不用主动去翻结果？配一个飞书群机器人 webhook（见 [setup-feishu-app.md](setup-feishu-app.md)），
  转写完成会直接推一张卡片到群里，点开就是纪要；失败也会推告警。

如果半天没结果，先看电脑：

```bash
python scripts/setup_check.py
python scripts/run.py
```
