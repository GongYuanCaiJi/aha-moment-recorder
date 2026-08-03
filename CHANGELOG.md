# 變更紀錄

本檔案記錄對使用者與貢獻者有影響的變更。尚未發布的內容放在 `Unreleased`；版本號遵循 Semantic Versioning。

## Unreleased

- 加入可插拔的本機 `WhisperCppTranscriber`：m4a 先在本機轉成逐字稿，再交給既有文字整理 endpoint。
- 自動把原始音訊、逐字稿與四欄位 AI 整理保留在同一筆記錄；轉錄失敗會保留原始音訊並可重試。
- CLI `doctor`、設定檔與 LaunchAgent 支援本機 STT command、model、language 與 timeout。

## 0.1.0（pre-release baseline，2026-08-02）

- 提供可攜的 Python 記錄管線與 `aha-moment-recorder` CLI。
- 將文字、音訊、逐字稿與附件保留在同一筆記錄中。
- 支援 `capture-only` 與 `collect-and-organize`，並以可驗證的四欄位 AI 整理契約保存分類、主題、結構化輸出與摘要。
- 支援可替換的 OpenAI-compatible endpoint、認證環境變數與 key file。
- 提供 macOS LaunchAgent 的安裝、健康檢查與移除流程。
- 加入隔離 E2E、公開介面 contract tests、Python 3.11–3.13 CI 與開源維護文件。
