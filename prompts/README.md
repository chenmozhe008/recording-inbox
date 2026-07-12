# 纪要模板

默认使用 `meeting`，它就是仓库里经过真实使用调整的通用智能纪要。普通用户不需要选择；只有固定场景才切换其他模板。

- `meeting`：默认智能纪要（推荐）
- `customer`：客户沟通
- `interview`：访谈整理
- `podcast`：自媒体 / 播客
- `course`：课程笔记
- `training`：培训 / 分享
- `project`：项目沟通
- `research`：调研 / 座谈
- `review`：工作复盘
- `dictation`：灵感口述

想完全自定义时，新建一个 Markdown 文件，把路径填进 `summary_prompt_file`。
程序会保留标题、智能纪要、主题大纲、待办、章节、决策和金句这些基础结构，
再叠加你写的行业要求。
