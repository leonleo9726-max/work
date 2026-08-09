# Issue tracker：GitHub

本仓库的 issue、spec 和实现 ticket 均存放在 GitHub Issues。请从仓库根目录使用 `gh` CLI，以便自动识别 `origin`。

## 核心操作

- 创建：`gh issue create --title "..." --body "..."`
- 读取并包含评论：`gh issue view <number> --comments`
- 列出：`gh issue list --state open --json number,title,body,labels,comments`
- 评论：`gh issue comment <number> --body "..."`
- 添加或移除标签：`gh issue edit <number> --add-label "..."` 或 `--remove-label "..."`
- 关闭：`gh issue close <number> --comment "..."`

多行内容使用临时正文文件或其他安全引用方式。任何对外可见的写操作执行前，都要先检查拟发布内容。

## 将 Pull Request 纳入 triage

**PRs as a request surface: no.** 除非以后明确修改此标记，否则外部 Pull Request 不进入 triage 队列。

## Skill 术语

- “Publish to the issue tracker”表示创建一个 GitHub issue。
- “Fetch the relevant ticket”表示读取指定 GitHub issue 及其评论。
- Skill 提到 triage role 时，使用 `docs/agents/triage-labels.md` 中的标签映射。

## Wayfinder 操作

`wayfinder` map 使用一个 GitHub issue，子 issue 表示决策 ticket。

- Map 使用 `wayfinder:map` 标签；子 ticket 使用 `wayfinder:<type>`，其中 type 为 `research`、`prototype`、`grilling` 或 `task`。
- 优先使用 GitHub sub-issues 和原生 issue dependencies。不可用时，通过 task list 关联子项，并在子 issue 中记录 `Blocked by: #<number>`。
- 所有 blocker 已关闭且没有 assignee 时，ticket 才可领取。
- 只有实现已获授权时，才使用 `gh issue edit <number> --add-assignee @me` 领取任务。
- 解决 ticket 时，记录决策、关闭 issue，并从 map issue 链接结果。
