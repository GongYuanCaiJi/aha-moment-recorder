# Record bridge

這是目前把 Apple capture 接到 Obsidian 的最小背景橋接器。它不建立另一個資料庫：每一筆來源都落在同一個資料夾中的 `record.md`，音訊附件也在同一筆記錄底下。

## 收進來的來源

- macOS Voice Memos 的 iCloud 同步目錄：
  `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings`
- iPhone Shortcuts／Files 可寫入的 iCloud Drive 收件匣：
  `~/Library/Mobile Documents/com~apple~CloudDocs/AhaMomentInbox`

同名的 `.transcript.txt`／`.transcript.md` 會被視為該音訊的逐字稿；同名一般 `.txt`／`.md` 會被視為原始文字。沒有逐字稿時，音訊仍會先收錄，之後只要把同名逐字稿放進收件匣，下一輪掃描就會更新同一筆記錄。

## 手動跑一次

```sh
python3 prototype/record-bridge/record_bridge.py \
  --vault "$HOME/Documents/Aha Moment Vault"
```

預設模式是 `collect-and-organize`。只想保留來源時：

```sh
python3 prototype/record-bridge/record_bridge.py \
  --vault "$HOME/Documents/Aha Moment Vault" \
  --mode capture-only
```

每筆 `record.md` 的 frontmatter 也有 `processing_mode`。把單筆改成
`capture-only` 會只收錄；之後改回 `collect-and-organize`，下一輪背景掃描會在
同一筆記錄補上 Luna 結果，不會建立第二份檔案。

## 輸出

```text
<vault>/records/<record-id>/record.md
<vault>/records/<record-id>/attachments/raw-audio.m4a
<vault>/.bridge/state.json
```

`record.md` 會保留原始文字、原始音訊、逐字稿，以及 Luna 產生的分類、主題、結構化輸出和摘要。AI 只追加到 `## AI 整理`，不會覆寫原始區塊。若 Vault 本身是 Git worktree，預設每次記錄變更會建立一個 commit；沒有 Git 時仍正常寫入。

## 背景監看

LaunchAgent 使用同一個指令加上 `--watch`，每 15 秒掃描一次。它只讀取 Voice Memos／iCloud 收件匣，寫入指定 Vault 與 `/tmp/aha-moment-recorder-bridge-*.log`；不會開啟或切換任何 App 視窗。

## 已知邊界

Voice Memos 的 `.m4a` 會隨 iCloud 出現在 Mac，但 Apple 沒有提供穩定的 transcript sidecar 檔案 API。橋接器因此把「音訊已保留、逐字稿待補」做成明確狀態，而不是假裝已經有逐字稿。逐字稿可以由 Apple Notes／Voice Memos 分享或 Shortcut 寫入同名 sidecar；收到後會自動補進同一筆記錄並啟動 Luna。
