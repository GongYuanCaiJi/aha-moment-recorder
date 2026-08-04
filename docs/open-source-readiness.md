# 開源發布準備狀態

查核日期：2026-08-04

目前 repository 仍維持 **private pre-release**。核心程式已能由陌生使用者從 GitHub checkout 安裝、測試與執行；但 visibility 改為 `public` 前，仍須完成下列發布 gate。

## 已驗證

- 根目錄有 MIT `LICENSE`、`README.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md` 與 `CHANGELOG.md`。
- Default branch 是 `agent/wayfinder-bootstrap`，目前 head 為 `7fdc39c`；GitHub 上的 default-branch CI run 已成功。
- 以乾淨 clone 執行 package install、CLI `--help`、`init`、`doctor`、capture-only `run`：全部成功。
- 乾淨 clone 的 Python unittest 共 45 tests，全部通過；`py_compile` 與 `git diff --check` 也通過。
- tracked tree 沒有 `.env`、Python cache、`*.DS_Store`、API key 或 private key；對目前可達 heads/remotes 的人工 pattern scan 沒有找到明顯 token 或秘密。
- `pyproject.toml` 沒有必要 runtime dependency；可選的 `apple-notes-parser` 0.2.x 使用 MIT License，且不會把第三方程式碼 vendored 進 repository。

## 公開前必須完成

### 1. 更新發布證據

本文件本身就是公開發布的 evidence。任何 branch、commit、測試數量或 GitHub PR 狀態變動，都必須同步更新這裡，不得保留舊的 SHA、測試數或已合併 PR 描述。

### 2. 決定 Git 歷史的作者識別

目前可達歷史中有 35 個 commit 使用 `daniel890913@gmail.com` 作為 author／committer。若這個信箱不應公開，必須在 visibility 變更前由 repository owner 決定是否重寫歷史；`.mailmap` 不能移除舊 commit metadata。

### 3. 建立可驗證的安全回報管道

`SECURITY.md` 指向 GitHub private vulnerability reporting，但目前 repository 仍是 private，GitHub API 尚未提供該功能的 endpoint。公開前必須在 visibility 變更後啟用並實際驗證該管道，或在 `SECURITY.md` 提供一個可履行的私下聯絡方式。

### 4. 完成公開 refs 審查

公開 repository 會暴露所有可達 branches、tags、PR 與 commit metadata。目前仍有 research PR 與遠端 branches 開啟；公開前逐一確認內容可公開，或合併／關閉／刪除不需要的 refs。研究文件中若有本機反代 port、process 名稱或作者環境細節，也要先移除或確認可公開。

### 5. 啟用最小 GitHub 保護

目前已啟用 default branch 的 required CI checks、Dependabot vulnerability alerts 與 automated security fixes；`dependabot.yml` 也已提交。Secret scanning／push protection 在 repository 保持 private 時不可用，必須在 visibility 變更後再啟用並 live-verify；這些設定不能只寫在文件裡。

## 已知產品邊界（不是發布 blocker）

- 不提供行動端 App 或特定外部資料庫的原生匯入 adapter；來源檔案需要先進入設定的 source inbox。
- 不在本 repo 內提供雲端語音服務；預設音訊轉錄使用使用者本機安裝的 `whisper-cli`。
- 不提供自有雲端同步、備份服務或第二裝置的實機驗收。
- 不承諾特定 AI provider 的模型品質，只驗證 OpenAI-compatible transport 與四欄位結果契約。
- 搜尋、回顧、向量索引、多人協作與其他產品級功能屬後續範圍。

## 公開前最終清單

- [ ] owner 確認是否公開歷史中的個人 author／committer email。
- [ ] 完成完整 history／refs secret scan，並處理所有 findings。
- [ ] 在 visibility 變更後 live-enable 並驗證安全回報與 secret scanning／push protection；目前 Dependabot alerts、automated security fixes 與 required CI checks 已啟用。
- [ ] 審查並整理所有公開 branches、tags、PR 與研究文件。
- [ ] 以新的乾淨 clone 重跑安裝、`doctor`、capture-only E2E、45 tests、compile 與 diff check。
- [ ] 建立第一個 `0.1.0` tag 與 GitHub Release；在此之前維持 `private pre-release`。
