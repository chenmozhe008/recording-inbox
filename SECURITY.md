# Security Policy

## 敏感信息

请勿在 Issue、PR、日志或截图中提交：

- API Key；
- 飞书文件夹 token、open_id、chat_id；
- Webhook 地址；
- `config.json`、`.env`；
- 真实录音、逐字稿和内部纪要。

仓库 CI 会扫描常见密钥格式和作者本机绝对路径，但自动扫描不能替代人工检查。

## 报告安全问题

不要用公开 Issue 报告可利用的密钥泄露或权限漏洞。请通过 GitHub 仓库所有者公开资料中的私密联系方式报告，并说明影响范围和复现条件。
