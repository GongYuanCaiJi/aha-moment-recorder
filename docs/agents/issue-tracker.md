# Issue tracker：GitHub

此 repo 的 issues 與 PRDs 都放在 GitHub Issues。所有操作皆使用 `gh` CLI。

## 操作慣例

- **建立 issue**：`gh issue create --title "..." --body "..."`。多行內容使用 heredoc。
- **讀取 issue**：`gh issue view <number> --comments`，以 `jq` 篩選 comments，並一併取得 labels。
- **列出 issues**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，並依需要加上 `--label` 與 `--state` 篩選條件。
- **回覆 issue**：`gh issue comment <number> --body "..."`
- **套用／移除 labels**：`gh issue edit <number> --add-label "..."`／`--remove-label "..."`
- **關閉 issue**：`gh issue close <number> --comment "..."`

從 `git remote -v` 判斷 repo；在 clone 內執行時，`gh` 會自動完成這件事。

## 將 pull requests 納入 triage

**PRs as a request surface: no.** _（若此 repo 將外部 PRs 視為 feature requests，可改成 `yes`；`/triage` 會讀取此設定。）_

設為 `yes` 時，PRs 會使用與 issues 相同的 labels 與 states，並改用對應的 `gh pr` 指令：

- **讀取 PR**：`gh pr view <number> --comments`；用 `gh pr diff <number>` 讀取 diff。
- **列出等待 triage 的外部 PRs**：執行 `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`，僅保留 `authorAssociation` 為 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR` 或 `NONE` 的項目；排除 `OWNER`、`MEMBER` 與 `COLLABORATOR`。
- **回覆／加 label／關閉**：使用 `gh pr comment`、`gh pr edit --add-label`／`--remove-label`、`gh pr close`。

GitHub 的 issues 與 PRs 共用同一組編號，因此單獨的 `#42` 可能指任一類型；先執行 `gh pr view 42`，失敗時再改用 `gh issue view 42`。

## 當 skill 要求「publish to the issue tracker」

建立一個 GitHub issue。

## 當 skill 要求「fetch the relevant ticket」

執行 `gh issue view <number> --comments`。

## Wayfinding 操作

供 `/wayfinder` 使用。**map** 是單一 issue，**child** issues 則作為 tickets。

- **Map**：一個標有 `wayfinder:map` 的 issue，其內容保存 Notes、Decisions-so-far 與 Fog。使用 `gh issue create --label wayfinder:map` 建立。
- **Child ticket**：透過 GitHub sub-issues endpoint（使用 `gh api`）連結至 map 的 issue。若 sub-issues 未啟用，則把 child 加入 map 內容中的 task list，並在 child 內容頂端加入 `Part of #<map>`。Labels 使用 `wayfinder:<type>`，其中 type 為 `research`、`prototype`、`grilling` 或 `task`。ticket 被 claim 後，指派給負責推進的開發者。
- **Blocking**：使用 GitHub 原生的 **issue dependencies**，作為 canonical 且可在 UI 查看的一致表示。以 `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>` 新增相依關係；`<blocker-db-id>` 是 blocker 的數字型 **database id**，可透過 `gh api repos/<owner>/<repo>/issues/<n> --jq .id` 取得，不能使用 `#number` 或 `node_id`。GitHub 以 `issue_dependencies_summary.blocked_by` 回報仍開啟的 blockers，這是即時 gate。若 dependencies 無法使用，則在 child 內容頂端加入 `Blocked by: #<n>, #<n>`。所有 blockers 關閉後，ticket 才算解除阻擋。
- **Frontier query**：列出 map 仍開啟的 children（使用 `gh issue list --state open`，並限定於 map 的 sub-issues 或 task list），排除仍有開啟 blocker（`issue_dependencies_summary.blocked_by > 0`，或 `Blocked by` 列出的 issue 仍開啟）或已有 assignee 的項目；依 map 中的順序取第一個。
- **Claim**：`gh issue edit <n> --add-assignee @me`；這是 session 的第一次寫入操作。
- **Resolve**：先執行 `gh issue comment <n> --body "<answer>"`，再執行 `gh issue close <n>`，最後將 context pointer（gist 與 link）附加至 map 的 Decisions-so-far。
