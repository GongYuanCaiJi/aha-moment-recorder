# Obsidian 反代接入驗證

## 結論

已在隔離測試 Vault 完成 Obsidian 的真實接入驗證：Obsidian Copilot 3.3.3 能透過與 ChatGPT/Codex 相同的本機反代與憑證來源，呼叫 `gpt-5.6-luna`，並在 Obsidian 介面收到預期回覆。後續分類測試使用 Luna、`reasoning_effort=medium`。

這次沒有修改 ChatGPT/Codex 的任何設定，也沒有重啟 ChatGPT。測試只使用副螢幕上的隔離 Vault，不觸碰正式筆記。

## Execution Path

```text
Obsidian Copilot
  -> http://127.0.0.1:8317/v1
  -> cli-proxy-wrap (wrap.py)
  -> http://127.0.0.1:8316
  -> cli-proxy-api / gpt-5.6-luna
```

ChatGPT/Codex 的現行程序環境同時可見：

- `OPENAI_BASE_URL=http://127.0.0.1:8788/v1`
- `OPENAI_TARGET_API_URL=http://127.0.0.1:8317/v1`

本次沒有改動這些環境變數。即時檢查顯示 `8317` 的 `wrap.py` 正在監聽；`8788` 當下沒有 listener，因此 Obsidian 使用 ChatGPT/Codex 實際可達的 target path `8317`，而不是碰 ChatGPT 的設定。

`wrap.py` 會從本機私有 provider 設定的第一個 `api-keys` 項目取得上游 API key；驗證輸出只記錄 key 存在與長度，不保存或展示內容。設定檔位置不提交到 repository。

## Obsidian 測試設定

測試 Vault：隔離的 temporary test Vault（位置不提交到 repository）

設定檔：`<vault>/.obsidian/plugins/copilot/data.json`

- 外掛：Copilot `3.3.3`
- model：`gpt-5.6-luna`
- reasoning：`medium`
- base URL：`http://127.0.0.1:8317/v1`
- API key：本機私有 provider 設定的第一個 key（只在本機設定，不寫入本 repo）
- `stream=false`、`enableCors=true`
- `indexVaultToVectorStore=NEVER`、`enableSemanticSearchV3=false`；測試不會把 Vault 建索引或上傳

Copilot 官方支援自訂 OpenAI-compatible model、API key 與 base URL；參見 [官方 README](https://github.com/logancyang/obsidian-copilot) 與 [官方發佈紀錄](https://github.com/logancyang/obsidian-copilot/blob/master/RELEASES.md)。

### 為什麼使用 `openrouterai` provider 標籤

Copilot 會對名稱以 `gpt-5` 開頭、且 provider 是 `openai` 或 `3rd party (openai-format)` 的 model 強制使用 `/v1/responses`。目前這條本機反代的 `/v1/responses` 會回 `502 no response from upstream`，而 `/v1/chat/completions` 正常。

因此測試設定把 provider 標籤改成 `openrouterai`，但仍明確指定本機 `baseUrl=127.0.0.1:8317/v1` 與同一把 key。這不是連到 OpenRouter；它只是讓 Copilot 走可用的 Chat Completions 路徑。

## Observed Evidence

| 時間（Asia/Taipei） | 證據 | 結果 |
|---|---|---|
| 00:52 左右 | Obsidian 以原始 `3rd party (openai-format)` 設定請求 `/v1/responses` | 反代回 `502 Bad Gateway`，`no response from upstream` |
| 00:56:54–00:56:57 | 隔離 Vault 的 Copilot UI 送出 `Reply with exactly OBSIDIAN_CHAT_COMPLETIONS_OK` | UI 收到完全相同的 `OBSIDIAN_CHAT_COMPLETIONS_OK` |
| 同一輪 | 本機 proxy log | `POST /v1/chat/completions` `200 OK` |
| 00:58:09 | 同一 endpoint、同一 key 的獨立 non-stream probe | HTTP `200`、model `gpt-5.6-sol`、回覆 `DIRECT_PROXY_OK` |
| 全程 | Obsidian 測試視窗 bounds `x=3328,y=256,size=1024x800`；主螢幕為 `2560x1440` | 測試視窗位於副螢幕；未操作主螢幕 |
| 2026-08-02 03:55–04:00 | 背景 `record_bridge.py` 將合成音訊、原始文字、逐字稿寫入同一筆 Vault record，經 `127.0.0.1:8317/v1` 呼叫 `gpt-5.6-luna` | `record.md` 保留三種原始來源，並產生分類、主題、結構化輸出、摘要；Git branch `record-bridge/live` 產生新 commit |

## Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| ChatGPT/Codex 怎麼接入？ | 目前程序以 `OPENAI_TARGET_API_URL=127.0.0.1:8317/v1` 指向 `wrap.py`，key 由本機私有 provider config 提供 | live process env、LaunchAgent、`wrap.py`、socket probe | `8788` 當下未監聽 | Obsidian 使用 live target `8317`；不修改 ChatGPT |
| Obsidian 能否使用同一反代？ | Copilot 支援自訂 OpenAI-compatible base URL、model 與 key；Luna/medium 已由隔離 UI 測試與背景 bridge 請求確認 | Copilot 官方 README/RELEASES、fresh bridge log | 正式既有 Vault 尚未指定 | 使用專用隔離 Vault，不碰既有正式 Vault |
| 真實 client 是否成功？ | Obsidian UI 收到 marker，proxy log 同輪回 `200` | Computer Use AX state + wrap log | 目前只用合成測試文字 | 不把測試資料當正式內容；正式資料需另訂測試範圍 |
| 為何不走 Responses API？ | 目前 upstream 對 `/v1/responses` 回 502；Chat Completions 可用 | fresh proxy log + plugin behavior | upstream 是否未來支援 Responses 尚未確認 | 以 custom provider label 固定走 Chat Completions；日後可再研究原生 Responses |

## 背景橋接器（2026-08-02）

`prototype/record-bridge/record_bridge.py` 已接上兩個本機來源：Voice Memos 的 iCloud 同步 `Recordings` 目錄，以及 iPhone Files／Shortcuts 可寫入的 `AhaMomentInbox`。它把每筆來源、音訊附件和逐字稿寫入同一個 `records/<record-id>/record.md`；同名 `.transcript.txt` 出現後會在下一輪掃描補進原記錄。每筆 frontmatter 的 `processing_mode` 可以個別切換 `capture-only`／`collect-and-organize`。`com.aha-moment-recorder.bridge.plist` 以 user LaunchAgent 在背景每 15 秒掃描，不開啟或移動任何視窗。

已直接驗證：背景程序常駐、真實反代請求成功、原始音訊／文字／逐字稿保持不變、AI 四欄只出現一次、逐字稿更新會在同一個 Git record 產生下一個 commit，工作樹保持乾淨。

## 邊界與下一步

- 本次只改了隔離測試 Vault 的 Copilot 設定；沒有改動使用者既有的 proxy wrapper、provider service、ChatGPT/Codex 或正式 Vault。
- 專用隔離 Vault 已建立並接上背景 bridge；既有正式 Vault 沒有被修改。Voice Memos 的 `.m4a` 可自動同步，但 Apple 沒有把 transcript 當成穩定 sidecar 暴露；沒有逐字稿時系統會先保留音訊並標記待補，不會偽造逐字稿。
