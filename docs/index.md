---
layout: default
title: recording-inbox - 开源 AI 录音工作流
description: 把 iPhone、Android 或电脑录音上传到飞书，Windows/macOS 自动本地转写并生成带摘要、待办、章节和文字记录的智能会议纪要。
permalink: /
---

# 录完上传，自动得到飞书智能纪要

`recording-inbox` 是一套开源、可自部署的 AI 录音工作流：手机或电脑录音进入飞书云盘后，Mac 或 Windows 自动完成本地语音转文字、AI 会议纪要、飞书文档归档和结果通知。

[查看 GitHub 仓库](https://github.com/chenmozhe008/recording-inbox) · [macOS 安装](https://github.com/chenmozhe008/recording-inbox/blob/master/docs/setup-macos.md) · [Windows 10/11 安装](https://github.com/chenmozhe008/recording-inbox/blob/master/docs/setup-windows.md) · [常见问题](https://chenmozhe008.github.io/recording-inbox/faq/)

## 它解决什么问题？

录音很容易，录完后的下载、转写、纠错、总结、提取待办、命名和归档才真正耗时。这个项目把它们连成一条可以自动恢复的流水线：

```text
iPhone / Android / 电脑录音
→ 飞书云盘 inbox
→ Windows / macOS 本地 FunASR 转写
→ AI 生成摘要、主题、待办、章节和文字记录
→ 飞书文档归档
→ 飞书消息通知
```

## 为什么选择它？

- **本地转写不消耗妙记分钟数**：适合大量、长期和长录音；
- **不是只输出逐字稿**：直接得到可浏览和继续协作的结构化纪要；
- **设备入口统一**：iPhone、Android、聊天软件音频和电脑文件进入同一个 inbox；
- **模板可以自己改**：支持会议、访谈、课程、项目沟通和自定义提示词；
- **中断后可以继续**：电脑关机、进程中断或通知失败后按已有阶段恢复；
- **隐私和费用更可控**：音频在本地转写，只有启用 AI 纪要时才发送文字到所选模型 API；
- **普通用户可借助 AI Agent 安装**：Codex、Claude Code 或 Cursor 可以按仓库部署手册完成安装和自检。

本地转写不按分钟收费，但电脑运行和可选的 AI 纪要 API 仍可能产生少量成本。

## 结果长什么样？

![脱敏智能纪要示例](./assets/sample-minutes-preview.jpg)

[查看完整脱敏纪要](https://github.com/chenmozhe008/recording-inbox/blob/master/examples/sample-minutes.md)

## 适合谁？

- 每天有大量会议，希望自动形成结构化纪要；
- 采访、调研和客户沟通时间长，人工整理成本高；
- 课程、培训、直播或播客录音需要持续沉淀为文字资料；
- 已经使用飞书，希望上传、通知、文档和协作都留在飞书；
- 对行业术语、纪要结构和待办提取有自己的要求。

偶尔只转一两条录音，飞书妙记通常更省事；完全不使用飞书时，其他工具更合适。

## 已验证到什么程度？

- Windows、macOS、Ubuntu Python 3.11 跨平台 CI 已通过；
- macOS 本机测试和无隐私合成中文录音本地转写已通过；
- 断电遗留锁、幂等去重、通知重试、模板和单人标签清理有自动测试；
- iPhone、Android 真机界面和第一次接触项目的用户安装仍是人工验收项。

[查看完整验证矩阵](https://github.com/chenmozhe008/recording-inbox/blob/master/docs/validation.md)

## 开始使用

把下面这段发给 Codex、Claude Code 或 Cursor：

```text
帮我部署 https://github.com/chenmozhe008/recording-inbox
先读 AGENTS.md，根据我的系统选择 macOS 或 Windows 路径。
需要扫码、粘贴飞书文件夹链接或填写 API Key 时再让我操作，
最后必须跑环境自检和模拟测试。
```

[查看 v0.1.0 Release](https://github.com/chenmozhe008/recording-inbox/releases/tag/v0.1.0) · [提交 Issue](https://github.com/chenmozhe008/recording-inbox/issues) · [给项目一个 Star](https://github.com/chenmozhe008/recording-inbox)
