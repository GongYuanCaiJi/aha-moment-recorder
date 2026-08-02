# 開源準備狀態

目前 repository 維持 **private pre-release**。程式碼、文件與驗證流程已整理成可以公開的狀態，但在確認沒有私人資料後，才應將 GitHub visibility 改為 public。

## 已完成

- MIT license、README、貢獻指南、安全政策與行為準則。
- 可從 checkout 安裝的 Python package 與 CLI。
- 不依賴作者私有路徑或 repository 內秘密的設定與認證邊界。
- `capture-only` 與 `collect-and-organize` 的公開介面、來源保留規則與可重試 state。
- macOS LaunchAgent 的 install、running 狀態檢查、doctor 與 uninstall。
- 隔離 file-backed E2E、26 個 unittest、compile/diff 檢查，以及 Python 3.11、3.12、3.13 的 GitHub Actions。
- GitHub Issue/PR 模板與開源維護入口。

## 已知邊界（不是目前的回歸故障）

以下是刻意未包含在目前核心範圍內的工作：

- 不提供行動端 App 或特定外部筆記／錄音資料庫的原生匯入 adapter；來源檔案需要先進入設定的 source inbox。
- 不在本 repo 內實作語音轉寫 provider；逐字稿可由其他工具產生後作為 sidecar 收錄。
- 不提供自有雲端同步、備份服務或第二裝置的實機驗收。
- 不承諾特定 AI provider 的模型品質；只驗證 OpenAI-compatible transport 與四欄位結果契約。
- 搜尋、回顧、向量索引、多人協作與其他產品級功能仍是後續範圍。

這些未完成項不會阻止目前的核心 CLI 開源；它們應在新增功能前先建立獨立 issue 與驗收條件。

## 目前 GitHub 分支狀態

完整開源準備內容目前在 `agent/define-ai-output`，並由 [draft PR #14](https://github.com/GongYuanCaiJi/aha-moment-recorder/pull/14) 對應到現有 default branch。由於本機安全規則禁止未經人工 review 直接 push 到 `main`，default branch 尚未切換；在 PR 合併、default branch 整理與 fresh clone 再驗證前，不應把 repository visibility 改為 public。

## 公開前檢查

1. 確認 `git status`、staged diff 與 Git history 沒有 Vault、錄音、逐字稿、API key、local config 或 LaunchAgent log。
2. 確認 `README.md`、`SECURITY.md`、`CONTRIBUTING.md` 與 [CHANGELOG.md](../CHANGELOG.md) 的安裝、支援範圍與限制描述一致。
3. 確認 default branch 是包含最新驗證結果的 `main`，並將 CI required checks 與 branch protection 設好。
4. 在 GitHub 啟用 private vulnerability reporting（若帳號／repo 功能可用），確認 Security policy 可見。
5. 將 repository visibility 改為 public 前，再做一次 fresh clone、安裝、`doctor`、capture-only E2E 與 GitHub Actions 檢查。
6. 以 git tag 與 GitHub Release 發布第一個正式版本；`0.1.0` 目前只是 pre-release baseline。

## 目前的追蹤 issue

- [#1 v1 決策規格](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/1) 仍是產品層 map。
- [#8–#15](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/8) 是搜尋、同步、provider 與其他產品範圍的後續決策，不是核心管線的 release blocker。
- [#16 既有產品研究](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/16) 與 [#17 開源架構規格](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/17) 的成果已進入 repository；完成狀態會在 GitHub issue 上留下 evidence comment。
