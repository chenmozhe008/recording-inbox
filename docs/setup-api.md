# DeepSeek API 与 Key 安全说明

AI 智能纪要是可选功能。本地转写不需要 API Key；关闭 `summary_enabled` 后仍会生成文字记录。

## 申请步骤

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/)。
2. 注册并按平台要求完成必要的账号验证。
3. 在控制台创建 API Key。Key 通常只完整显示一次，立即保存到密码管理器。
4. 如账户没有可用余额，到平台充值页面按实际使用量充值。不要依赖教程里的固定最低金额。
5. 回到项目运行 `python scripts/setup.py`，在安全输入提示中粘贴 Key。

官方入口：

- [第一次 API 调用](https://api-docs.deepseek.com/)
- [模型与价格](https://api-docs.deepseek.com/quick_start/pricing)
- [错误码](https://api-docs.deepseek.com/quick_start/error_codes)

模型名称和价格会变化。仓库当前默认使用 `deepseek-v4-flash`，升级时先核对官方文档。

## Key 存在哪里？

向导把 Key 写进项目根目录 `.env`：

```text
DEEPSEEK_API_KEY=YOUR_API_KEY
```

`.env` 已被 `.gitignore` 排除。不要把真实 Key：

- 写进 `config.json`；
- 发给 AI Agent；
- 放进截图或录屏；
- 提交到 GitHub；
- 发到 Issue 或日志附件。

## 手工配置

不使用向导时，自己创建 `.env`，再在 `config.json` 填：

```json
{
  "summary_enabled": true,
  "summary_api_base": "https://api.deepseek.com",
  "summary_model": "deepseek-v4-flash",
  "summary_api_key_env": "DEEPSEEK_API_KEY"
}
```

其他 OpenAI 兼容接口也可以使用：修改 API 地址、模型名和 Key 环境变量名即可。

## 常见错误

| 错误 | 含义 | 处理 |
|---|---|---|
| 401 / 403 | Key 无效或没有权限 | 重新创建 Key，检查是否复制完整 |
| 402 | 余额不足 | 到开放平台检查余额 |
| 429 | 请求过快或受限 | 稍后重试，避免同时提交大量录音 |
| 500 / 503 | 服务端异常或过载 | 后台会重试，稍后再看 |
