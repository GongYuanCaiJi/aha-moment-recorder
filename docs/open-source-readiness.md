# 開源發布狀態

查核日期：2026-08-04

repository 已設為 **public**。核心程式已能由陌生使用者從 GitHub checkout 安裝、測試與執行；GitHub 的安全與維護設定也已完成 live verification。

## 已驗證

- Default branch 是 `agent/wayfinder-bootstrap`，目前 head 為 `cd5d0e6`。
- 以乾淨 clone 執行 package install、CLI `--help`、`init`、`doctor`、capture-only `run`：全部成功。
- 乾淨 clone 的 Python unittest 共 45 tests，全部通過；`py_compile`、wheel build 與 `git diff --check` 也通過。
- GitHub Actions 的 Python 3.11、3.12、3.13 checks 全部通過。
- Root MIT `LICENSE`、`README.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`CHANGELOG.md`、`.env.example` 與第三方授權清單均存在。
- Default branch 已啟用 required CI checks，禁止 force-push 與 branch deletion。
- GitHub vulnerability alerts、automated security fixes、secret scanning、push protection 與 private vulnerability reporting 均已啟用；secret-scanning alerts 目前為 0。
- 對目前公開 refs 的人工 pattern scan 沒有找到明顯 token、private key 或本機秘密檔；`.env`、Python cache 與 runtime records 沒有被 tracked。

## 公開後仍需維護

### 作者 metadata

目前公開歷史中有 35 個 commit 使用 `daniel890913@gmail.com` 作為 author／committer。這是公開 repository 的既有 commit metadata；若日後要移除，必須由 owner 另行決定 history rewrite，且會改變 SHA、分支與 PR 歷史。

### 公開 refs 與研究內容

公開 repository 會暴露可達 branches、tags、PR 與 commit metadata。目前仍有 research PR 與遠端 branches；它們已可被公眾看見，後續可依維護需要逐一合併、關閉或刪除。研究文件若有本機環境細節，也應在日後維護時持續脫敏。

### 第一個 release

目前仍未建立第一個 Git tag 或 GitHub Release。若要發布正式版本，請建立 `0.1.0` tag、更新 `CHANGELOG.md`，並附上同一套 clean-clone evidence；在正式 release 前可維持 public pre-release 狀態。

## 已知產品邊界（不是開源 blocker）

- 不提供行動端 App 或特定外部資料庫的原生匯入 adapter；來源檔案需要先進入設定的 source inbox。
- 不在本 repo 內提供雲端語音服務；預設音訊轉錄使用使用者本機安裝的 `whisper-cli`。
- 不提供自有雲端同步、備份服務或第二裝置的實機驗收。
- 不承諾特定 AI provider 的模型品質，只驗證 OpenAI-compatible transport 與四欄位結果契約。
- 搜尋、回顧、向量索引、多人協作與其他產品級功能屬後續範圍。

## 維護檢查

- [x] Public visibility、MIT license、README、貢獻與安全入口。
- [x] Clean-clone install、`doctor`、capture-only E2E、45 tests、compile、wheel 與 diff check。
- [x] Required CI checks、Dependabot、secret scanning、push protection 與 private vulnerability reporting。
- [ ] 建立第一個 `0.1.0` tag 與 GitHub Release。
- [ ] 若 owner 不希望公開個人 author／committer email，另行決定是否重寫歷史。
