# 安全性

請不要在 GitHub issue、pull request、log 或測試 fixture 貼出 API key、token、私人 Vault、錄音或逐字稿。

這個 package 的安全邊界是：

- TOML 設定檔不能放 `api_key`、token 或 secret；認證只從 `AHA_API_KEY` 或 `api_key_file` 讀取。
- 個人資料只在本機 Vault 保存；只有啟用「收錄並整理」時，來源內容或逐字稿才會送到你設定的 OpenAI-compatible endpoint。
- LaunchAgent plist 只保存命令、路徑與固定 stdout/stderr 路徑，不保存認證值。
- `.gitignore` 會保護常見 local config、credential、runtime state、log 與 `records/`；提交前仍請檢查 `git diff --cached`。

若發現可能造成秘密外洩、任意檔案寫入或不安全 LaunchAgent 操作的問題，請使用 GitHub repository 的 private vulnerability reporting / Security Advisory。若該功能未啟用，請先透過 repository 維護者可接受的私下管道聯絡，並只提供最小重現資訊；不要先公開細節。
