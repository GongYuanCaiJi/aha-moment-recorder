# Obsidian 反代接入驗證

## 結論

已在隔離測試 Vault 完成 Obsidian 的真實接入驗證：Obsidian Copilot 3.3.3 能透過與 ChatGPT/Codex 相同的本機反代與憑證來源，呼叫 `gpt-5.6-sol`，並在 Obsidian 介面收到預期回覆。

這次沒有修改 ChatGPT/Codex 的任何設定，也沒有重啟 ChatGPT。測試只使用副螢幕上的隔離 Vault，不觸碰正式筆記。

## Execution Path

```text
Obsidian Copilot
  -> http://127.0.0.1:8317/v1
  -> cli-proxy-wrap (wrap.py)
  -> http://127.0.0.1:8316
  -> cli-proxy-api / gpt-5.6-sol
```

ChatGPT/Codex 的現行程序環境同時可見：

- `OPENAI_BASE_URL=http://127.0.0.1:8788/v1`
- `OPENAI_TARGET_API_URL=http://127.0.0.1:8317/v1`

本次沒有改動這些環境變數。即時檢查顯示 `8317` 的 `wrap.py` 正在監聽；`8788` 當下沒有 listener，因此 Obsidian 使用 ChatGPT/Codex 實際可達的 target path `8317`，而不是碰 ChatGPT 的設定。

`wrap.py` 會從 `/Users/shuaige/cli-proxy-api/config.yaml` 的第一個 `api-keys` 項目取得上游 API key；驗證輸出只記錄 key 存在與長度，不保存或展示內容。

## Obsidian 測試設定

測試 Vault：`/private/tmp/aha-moment-recorder-e2e-vault-20260801`

設定檔：`<vault>/.obsidian/plugins/copilot/data.json`

- 外掛：Copilot `3.3.3`
- model：`gpt-5.6-sol`
- base URL：`http://127.0.0.1:8317/v1`
- API key：同一份 `cli-proxy-api/config.yaml` 的第一個 key（只在本機設定，不寫入本 repo）
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
| 同一輪 | `/tmp/launchd-cli-proxy-wrap.log` | `POST /v1/chat/completions` `200 OK` |
| 00:58:09 | 同一 endpoint、同一 key 的獨立 non-stream probe | HTTP `200`、model `gpt-5.6-sol`、回覆 `DIRECT_PROXY_OK` |
| 全程 | Obsidian 測試視窗 bounds `x=3328,y=256,size=1024x800`；主螢幕為 `2560x1440` | 測試視窗位於副螢幕；未操作主螢幕 |

## Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| ChatGPT/Codex 怎麼接入？ | 目前程序以 `OPENAI_TARGET_API_URL=127.0.0.1:8317/v1` 指向 `wrap.py`，key 由 `cli-proxy-api/config.yaml` 提供 | live process env、LaunchAgent、`wrap.py`、socket probe | `8788` 當下未監聽 | Obsidian 使用 live target `8317`；不修改 ChatGPT |
| Obsidian 能否使用同一反代？ | Copilot 支援自訂 OpenAI-compatible base URL、model 與 key | Copilot 官方 README/RELEASES | 正式 Vault 尚未指定 | 先在隔離 Vault 完成 E2E，正式 Vault 另行指定後才套用 |
| 真實 client 是否成功？ | Obsidian UI 收到 marker，proxy log 同輪回 `200` | Computer Use AX state + wrap log | 目前只用合成測試文字 | 不把測試資料當正式內容；正式資料需另訂測試範圍 |
| 為何不走 Responses API？ | 目前 upstream 對 `/v1/responses` 回 502；Chat Completions 可用 | fresh proxy log + plugin behavior | upstream 是否未來支援 Responses 尚未確認 | 以 custom provider label 固定走 Chat Completions；日後可再研究原生 Responses |

## 邊界與下一步

- 本次只改了隔離測試 Vault 的 Copilot 設定；沒有改 `/Users/shuaige/cli-proxy-wrap`、`/Users/shuaige/cli-proxy-api`、Headroom、ChatGPT/Codex 或正式 Obsidian Vault。
- 若要套用到正式 Vault，還需要先指定要使用哪個 Vault；在此之前不會把 key 或外掛設定寫入正式筆記環境。
