# 纪要模板

`config.json` 的 `summary_template` 可选：

- `meeting`：会议纪要
- `interview`：访谈整理
- `course`：课程笔记
- `project`：项目沟通

想完全自定义时，新建一个 Markdown 文件，把路径填进 `summary_prompt_file`。
程序会保留标题、智能纪要、主题大纲、待办、章节、决策、金句和文字记录这些基础结构，
再叠加你写的行业要求。
