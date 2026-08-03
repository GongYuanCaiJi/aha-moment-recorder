# Record bridge

這個目錄保留舊 prototype 的相容入口。真正的記錄管線現在位於
`aha_moment_recorder`，只使用 Python standard library；舊指令仍可直接執行，
但會轉交給同一套公開 adapters 與 `RecordPipeline`。

## 手動跑一次

推薦使用 package CLI：

```sh
python3 -m aha_moment_recorder run \
  --vault "$HOME/Documents/Aha Moment Vault" \
  --source "$HOME/Library/Mobile Documents/com~apple~CloudDocs/AhaMomentInbox"
```

遷移期間原本的 invocation 仍然有效：

```sh
python3 prototype/record-bridge/record_bridge.py \
  --vault "$HOME/Documents/Aha Moment Vault"
```

預設模式是 `collect-and-organize`。只想保留來源時：

```sh
python3 -m aha_moment_recorder run \
  --vault "$HOME/Documents/Aha Moment Vault" \
  --mode capture-only
```

## 收進來的來源

- 音訊：`.m4a`、`.mp3`、`.wav`、`.caf`、`.aif`、`.aiff`、`.flac`
- 文字：`.txt`、`.md`、`.markdown`
- 附件：常見圖片、PDF、Office、影片、CSV/JSON/XML 與 ZIP 檔

同名的 `.transcript.txt`、`.transcript.md` 或
`.transcript.markdown` 會被視為逐字稿 sidecar；即使沒有音訊，逐字稿也會
保留在同一筆記錄中。原始文字、原始音訊、逐字稿與附件會放在同一個
`records/<record-id>/` 目錄，AI 只更新 `record.md` 的 `## AI 整理` 區塊。

## 設定

設定來源的優先順序是 TOML → environment → CLI。可用 `--config` 指定 TOML：

```toml
[record_bridge]
vault = "/path/to/vault"
sources = ["/path/to/inbox"]
state = "/path/to/vault/.bridge/state.json"
endpoint = "https://provider.example/v1"
model = "compatible-model"
mode = "collect-and-organize"
```

常用 environment names 是 `AHA_VAULT`、`AHA_SOURCES`、`AHA_ENDPOINT`、
`AHA_MODEL`、`AHA_MODE`、`AHA_API_KEY` 與 `AHA_API_KEY_FILE`。API key 不放在
TOML 或 CLI value 中；HTTP adapter 呼叫標準 OpenAI-compatible
`/chat/completions` endpoint。

輸出位置：

```text
<vault>/records/<record-id>/record.md
<vault>/records/<record-id>/attachments/
<vault>/.bridge/state.json
```

若 Vault 本身就是 Git worktree，Git adapter 只會針對該筆記錄目錄與 state
建立 path-scoped commit；commit 失敗會保留可重試狀態。
