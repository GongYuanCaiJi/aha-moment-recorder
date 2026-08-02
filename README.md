# Aha Moment Recorder

這是一套 macOS-first、local-first 的個人記錄 CLI：把文字、錄音、逐字稿與附件收錄到同一個 Vault 記錄，再選擇只收錄或交給你指定的 OpenAI-compatible endpoint 做通用整理。來源內容不會被 AI 結果覆寫。

這個 repo 提供可攜的記錄管線；macOS LaunchAgent 只是可選的背景執行 adapter。

目前是 private pre-release repository。核心 CLI、測試、CI、安裝與安全邊界已整理成可公開的狀態；已知未包含的功能與正式公開前檢查見 [開源準備狀態](docs/open-source-readiness.md)。

## 需要什麼

- macOS（`install-agent` / `uninstall-agent` 需要 macOS；核心 package 本身可在其他平台測試）
- Python 3.11 或更新版本
- 一個來源收件匣、一個可寫入的 Vault
- 若使用「收錄並整理」，一個可接受 `/chat/completions` 的 OpenAI-compatible endpoint 與認證

## 安裝

從 checkout 安裝；核心不需要第三方 runtime dependency。若要匯入既有 Apple Notes，請安裝 macOS extra：

```sh
git clone https://github.com/GongYuanCaiJi/aha-moment-recorder.git
cd aha-moment-recorder
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[macos]'
aha-moment-recorder --help
```

也可以在未安裝前使用 `python3 -m aha_moment_recorder ...`。

## 初始化設定

`init` 會建立 Vault 的 `records/`、state 檔與來源收件匣；指定 `--config` 時也會寫一份不含秘密的 TOML：

```sh
aha-moment-recorder init \
  --config "$HOME/.config/aha-moment-recorder/settings.toml" \
  --vault "$HOME/Documents/Aha Moment Vault" \
  --source "$HOME/Aha Moment Inbox" \
  --endpoint "http://127.0.0.1:8317/v1" \
  --model "gpt-5.6-luna"
```

已存在的設定檔預設不覆寫；確認要用目前 CLI flags 重建時才加 `--force`。

設定合併順序是 TOML < environment < CLI。相對於 TOML 的路徑以設定檔所在目錄解析；environment 或 CLI 的相對路徑以執行目錄解析。常用欄位如下：

```toml
[aha_moment_recorder]
vault = "/Users/you/Documents/Aha Moment Vault"
sources = ["/Users/you/Aha Moment Inbox"]
state = "/Users/you/Documents/Aha Moment Vault/.bridge/state.json"
endpoint = "http://127.0.0.1:8317/v1"
model = "gpt-5.6-luna"
mode = "collect-and-organize" # or capture-only
reasoning_effort = "medium"
timeout = 120
auto_commit = true
retry_ai = false
dry_run = false
api_key_file = "/Users/you/.config/aha-moment-recorder/api-key"
apple_notes_database = "/Users/you/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
include_deleted_notes = false
```

設定 `apple_notes_database` 後，`run`／`watch` 會把既有 Apple Notes（預設不含「Recently Deleted」）讀進同一套記錄管線；備忘錄文字、可讀出的音訊與附件會放在同一筆 `record.md`，暫時讀不到的附件會留下名稱與待重試標記。匯入用的暫存來源位於 Vault 的 `.bridge/apple-notes-sources/`，不會放進 GitHub repo。

Apple Notes 的資料庫受 macOS 隱私權保護。若終端機可以讀取、但 LaunchAgent 的 `doctor` 顯示匯入延後，請在「系統設定 → 隱私權與安全性 → 完整磁碟取用」允許執行該 virtualenv 的 Python；這是 macOS 的一次性權限，不是程式繞過權限。沒有這項權限時，Voice Memos 與其他來源仍會繼續處理，Apple Notes 會在下一輪重試。

不要把 `api_key` 寫入 TOML。可用環境變數：

```sh
export AHA_API_KEY='在目前 shell 內設定，不要提交或貼到 log'
```

對背景 LaunchAgent 請使用只允許本人讀取的 key file。LaunchAgent 不會可靠地繼承你目前 shell 的 `AHA_API_KEY`，而 plist 也不會嵌入秘密：

```sh
mkdir -p "$HOME/.config/aha-moment-recorder"
umask 077
printf '%s\n' '你的 API key' > "$HOME/.config/aha-moment-recorder/api-key"
chmod 600 "$HOME/.config/aha-moment-recorder/api-key"
```

## 先檢查，再執行

```sh
aha-moment-recorder doctor --config "$HOME/.config/aha-moment-recorder/settings.toml"
aha-moment-recorder run --config "$HOME/.config/aha-moment-recorder/settings.toml"
```

`doctor` 輸出 JSON，檢查 Vault、來源目錄、state parent、endpoint、認證是否已設定；不會輸出認證值。成功回傳 0，環境缺失回傳 1，設定檔或設定值無法解析回傳 2。

`run` 只掃描一次並輸出每筆結果。`watch` 持續掃描：

```sh
aha-moment-recorder watch --config "$HOME/.config/aha-moment-recorder/settings.toml"
```

`--mode capture-only` 只保存來源，不呼叫 AI；`collect-and-organize` 會保留來源並追加通用整理。`--no-git-commit` 可停用 Vault 為 Git worktree 時的自動 commit。

## macOS LaunchAgent

安裝會先以 `plutil -lint` 驗證產生的 plist；若同 label 已 loaded，會先 `launchctl bootout`，再 `launchctl bootstrap`，最後 `launchctl kickstart -k`。這些命令只針對目前使用者的 `gui/<uid>` domain。預設 plist 是：

```text
~/Library/LaunchAgents/com.aha-moment-recorder.plist
```

stdout/stderr 預設固定在 Vault：

```text
<vault>/.bridge/launchagent.stdout.log
<vault>/.bridge/launchagent.stderr.log
```

操作與檢查：

```sh
aha-moment-recorder install-agent \
  --config "$HOME/.config/aha-moment-recorder/settings.toml"

launchctl print "gui/$(id -u)/com.aha-moment-recorder"
aha-moment-recorder doctor \
  --config "$HOME/.config/aha-moment-recorder/settings.toml"
tail -f "$HOME/Documents/Aha Moment Vault/.bridge/launchagent.stderr.log"

aha-moment-recorder uninstall-agent
```

`install-agent` 的 JSON 會回報 plist、stdout/stderr、`loaded`、`running`、`last_exit` 與 `last_exit_success`。`doctor` 發現 plist 時也會檢查同一組狀態與 log path；`loaded` 不代表最近一次執行成功，請一併看 `last_exit` 和 stderr。

`install-agent` 會用目前執行的 Python interpreter 產生 `ProgramArguments`，並以設定檔或明確 flags 啟動 `watch`。若需要不使用預設位置，可傳 `--agent-path`、`--stdout-path` 與 `--stderr-path`。搬移 Python virtualenv 或 checkout 後，先 `uninstall-agent` 再用新環境重新 `install-agent`，避免 plist 留著舊的 interpreter path。

## Vault 形狀與隱私

每筆記錄位於：

```text
<vault>/records/<record-id>/
├── record.md
└── attachments/
```

Vault 內的 `.bridge/state.json` 保存可重試的處理狀態。原始文字、音訊、逐字稿與附件留在同一筆記錄；AI 整理只更新明確的 AI section。只收錄模式不會送出 AI request。

目前不會自行替純音訊檔產生逐字稿：只有音訊、尚未有逐字稿的記錄會保留原始音訊並標成 `transcript pending`，等逐字稿來源出現後再自動整理。這個 repo 不會在沒有明確設定下把私人音訊送到另一個轉錄服務。

請把 Vault、錄音、逐字稿、key file 與 LaunchAgent log 視為私人資料，不要放進 GitHub checkout。repo 的 `.gitignore` 會忽略常見 `records/`、`.bridge/`、log、local config 與 credential pattern，但提交前仍應檢查 staged diff。

## 常見失敗

- `config file does not exist`：先用上面的 `init --config ...`，或確認 `--config` 指到絕對路徑。
- `doctor` 回傳 1：逐一查看 JSON 中 `vault`、`sources` 與 `state_parent`；程式不會替你猜測私人目錄。
- `401` 或 endpoint 連線失敗：確認 endpoint 是 provider 的 base URL（通常含 `/v1`）、key file 可讀，並重新執行 `doctor`。不要把 key 放進 CLI argument。
- `install-agent requires macOS`：LaunchAgent 是 macOS optional adapter；核心的 `init`、`doctor`、`run` 仍可在測試環境使用。
- `loaded` 但沒有成功結果：用 `launchctl print` 看 `running` 與 `last exit`，再檢查回報的 stdout/stderr。最常見原因是 interpreter、WorkingDirectory、config path 或 key file 權限已變更。
- SSH 或沒有 GUI session 時無法使用 `gui/<uid>`：回到該使用者的登入 macOS session 執行 install/status；不要改用 system LaunchAgent 來繞過這個限制。

## 移除

```sh
aha-moment-recorder uninstall-agent \
  --agent-path "$HOME/Library/LaunchAgents/com.aha-moment-recorder.plist"
python3 -m pip uninstall aha-moment-recorder
```

這不會刪除 Vault、records、state、config 或 key file；若要清理，請先備份並由使用者手動決定。`uninstall-agent` 只 bootout 並移除這個 package 的 plist。

## 開發與授權

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile aha_moment_recorder/*.py build_backend.py
git diff --check
```

貢獻方式見 [CONTRIBUTING.md](CONTRIBUTING.md)，安全問題見 [SECURITY.md](SECURITY.md)。本專案採 [MIT License](LICENSE)。行為準則見 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)，變更紀錄見 [CHANGELOG.md](CHANGELOG.md)。
