# THROWAWAY PROTOTYPE — Mac capture capability probe

這個原型只回答一個問題：**在目前這台 Mac 上，作為 Obsidian 唯一長期 store 的核心能力，哪些可以自動確認？**

它不是產品實作，也不會讀寫現有 Obsidian Vault、建立 Shortcut、錄音、呼叫 LLM 或修改 Apple Notes／Voice Memos。預設模式會做唯讀的 App／CLI／URI 檢查，並跑兩個隔離驗證：記憶體中的來源不可覆寫契約，以及只存在暫存目錄的 file-backed record（真實 `.m4a`、附件與同一筆 Markdown 記錄）。

## 執行

```sh
python3 prototype/mac-capture-capability/probe.py
```

可選的互動模式：

```sh
python3 prototype/mac-capture-capability/probe.py --interactive
```

`--strict` 會把尚需帳號與第二台裝置的跨裝置同步視為未完成而回傳非零狀態：

```sh
python3 prototype/mac-capture-capability/probe.py --strict
```

正常執行的退出碼為 `0`，只要本機檢查、記錄契約與 scratch vault 都通過；`MANUAL` 只代表尚未由這個無副作用原型自動確認的外部條件。

## 目前已驗證的範圍

- `RECORD CONTRACT: PASS`：原始文字、原始音訊參照、逐字稿與附件在記憶體中保留；AI 結果以追加方式累積。
- `FILE-BACKED RECORD: PASS`：在暫存 scratch vault 產生真正的 AAC-in-MP4 `.m4a`、附件與同一筆 Markdown；第二次整理追加後，原始片段仍存在。測試結束會刪除 scratch vault。
- Mac Notes UI 另做過一次合成音檔 smoke check：貼入後 accessibility tree 看見 `音訊附件、1秒`；測試筆記已刪除。這是一次性 UI 證據，不冒充可由本腳本重跑的自動測試。

### 一次性真實 Mac E2E（2026-08-02）

另外以副螢幕上的 Apple Shortcuts 與 Obsidian 做過一次完整的隔離測試。使用的暫時捷徑是 `aha-moment-recorder Mac E2E`；測試 vault 位於 `/tmp/aha-moment-recorder-e2e-vault-20260801`，不會碰現有 vault。

- Shortcut 將原始文字寫入同一個本機 `records/mac-capture-e2e/record.md`。
- 同一個 Shortcut 追加 `分類`、`主題`、`結構化輸出`、`摘要` 四個 AI 結果區塊；這次使用固定合成整理文字，驗證的是寫回與保留契約，不是 LLM 品質測試。
- `record.md` 保留原始文字、音訊嵌入、逐字稿和附件連結；實際 `.m4a` 為 AAC-in-MP4、1 秒，Obsidian 畫面可見音訊播放器與附件連結。
- 第二次重跑後，每個原始 marker 與 AI 區塊仍各出現一次，證明覆寫原始收錄後再追加不會重複堆疊。
- Action Button、iPhone、跨裝置同步仍不在這個 Mac E2E 範圍內。

Action Button 只屬於 iPhone 的觸發方式，不列入這個 Mac 核心能力 probe。`obsidian-sync-account-and-cross-device` 仍是 `MANUAL`，因為它需要實際同步帳號與第二台裝置。

## 證據邊界

- `PASS`：本機可以用唯讀檢查直接確認。
- `MANUAL`：官方文件有能力描述，但需要使用者帳號、實際 UI 或第二台裝置；本原型不假裝通過。

官方背景：[Apple Notes on Mac](https://support.apple.com/en-mide/guide/notes/apdb5106e334/mac)、[Voice Memos transcription on Mac](https://support.apple.com/en-euro/guide/voice-memos/vm4a03609f0d/mac)、[Shortcuts from the command line](https://support.apple.com/en-ca/guide/shortcuts-mac/apd455c82f02/mac)、[Obsidian URI](https://obsidian.md/help/uri)。
