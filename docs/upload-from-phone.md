# 手机端：把录音送进 inbox

电脑端只认一个入口：飞书云盘里的 inbox 文件夹。录音从 iPhone、Android、微信、网盘或电脑拖进去都可以。

## 最简单路径：手动上传

### iPhone

1. 用系统「语音备忘录」录音。
2. 录完点分享。
3. 选择飞书。
4. 选择「保存到云文档」。
5. 选你的 `recording-inbox` 文件夹。

### Android

不同手机录音 App 名字不一样，但路径类似：

1. 用系统录音机录音。
2. 在录音列表里点分享。
3. 选择飞书。
4. 保存到云文档。
5. 选你的 `recording-inbox` 文件夹。

如果分享菜单里没有飞书，就先在飞书 App 里打开 `recording-inbox` 文件夹，点上传文件，选择录音文件。

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
   - 请求体 JSON：`app_id`、`app_secret`
3. 获取词典值：`tenant_access_token`
4. 获取文件详细信息：名称、大小
5. 获取 URL 内容：`https://open.feishu.cn/open-apis/drive/v1/files/upload_all`
   - 方法：POST
   - Header：`Authorization: Bearer tenant_access_token`
   - 表单字段：
     - `file_name`：文件名
     - `parent_type`：`explorer`
     - `parent_node`：inbox folder token
     - `size`：文件大小
     - `file`：分享输入的文件
6. 显示通知：上传完成。

不要把带 `app_secret` 的快捷指令发给别人。

## 日常怎么判断成功

- 手机端只负责上传，不负责转写。
- 电脑端开机并运行后台任务后，1 分钟内会接手。
- 结果在飞书输出文件夹和 `output/minutes/` 里。

如果半天没结果，先看电脑：

```bash
python scripts/setup_check.py
python scripts/run.py
```
