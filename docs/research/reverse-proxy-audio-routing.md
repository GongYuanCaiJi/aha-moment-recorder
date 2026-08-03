# 文字反代不能處理音訊時，別人怎麼接

> 研究日期：2026-08-04。這份文件只回答「反代只能處理文字、不能處理音訊時的接法」，不選定本 repo 最終 provider，也不修改現有 ChatGPT 反代設定。

## 先講結論

**別人通常不會要求原本的文字反代直接學會聽音訊。** 常見做法是把「語音轉文字」當成另一個 API 能力，然後採取下面其中一條路：

1. **旁邊加一個 STT service**：本機 `whisper.cpp`、`faster-whisper`、`speaches`、WhisperServer 或 MLX ASR 提供 `/v1/audio/transcriptions`；原本反代繼續只負責文字整理。
2. **換成／加一層真正支援 audio 的 gateway**：LiteLLM、OpenRouter、DeltaLLM 等 gateway 對外提供音訊 endpoint，再把請求翻譯給實際 STT provider。
3. **在本 repo 自己分兩個 base URL**：`STT_BASE_URL` 指向本機或專用雲端轉錄服務，`LLM_BASE_URL` 維持目前反代與 `gpt-5.6-luna`。這是最少影響現有 ChatGPT 反代的做法。
4. **如果一定要對外只有一個 URL**，再放一個很薄的路由層：文字路徑轉發到目前反代，音訊路徑轉發到本機 STT。這不是讓 Luna 直接聽音訊，而是把兩種能力放在同一個入口後面。

因此，這個問題的答案不是「找一個神奇的文字模型」。真正的答案是：**反代的 API capability 不完整，就在反代旁邊補一個 STT capability，或使用能做 capability translation 的 gateway。**

## 先釐清目前卡點

本 repo 已有的實際證據是：

- 文字整理的 chat request 可以經由目前反代送到 `gpt-5.6-luna`。
- `POST /v1/audio/transcriptions` 對 synthetic audio fixture 回 HTTP 404。

HTTP 404 表示目前這條 gateway／upstream 路徑沒有提供這個音訊能力；它不是「Luna 分類品質不好」。即使日後反代新增 `/v1/audio/transcriptions`，也仍要指定一個真正的 transcription model 或 provider。文字 chat model 與 STT endpoint 是兩個不同的契約。

## 現成方案如何解決

### 做法 A：旁路本機 STT，保留原本的文字反代

這是最常見、也最符合本案「不要動 ChatGPT 反代」的方式：

```text
原始 .m4a
   │
   ├─ POST /v1/audio/transcriptions → 本機 STT service
   │                                  └─ transcript
   │
   └─ POST /v1/chat/completions     → 現有反代 → gpt-5.6-luna
                                      └─ 分類／主題／結構化輸出／摘要
```

別人已經把這種本機 STT 做成可重用的 OpenAI-compatible server：

- [speaches](https://github.com/speaches-ai/speaches) 用 `faster-whisper`，提供 OpenAI-compatible API、streaming transcription、動態模型載入，以及 CPU／GPU／Docker 支援。
- [WhisperServer](https://github.com/pfrankov/whisper-server) 是 macOS menu bar app，在本機暴露 `/v1/audio/transcriptions`，接受 m4a、wav、mp3，並可自動下載模型。
- [mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr) 在 Apple Silicon 上提供本機 HTTP server；同時有非同步 job API 和 OpenAI-compatible transcription endpoint。
- [openedai-whisper](https://github.com/matatonic/openedai-whisper) 直接實作 `/v1/audio/transcriptions`，但作者已標註 mostly obsolete，README 自己推薦改用 speaches 或其他替代品，因此不應作新部署的首選。

這些服務的共同點是：**不需要把音訊送進現有文字反代，也不需要更改目前 Luna 的設定。** 我們的程式只需對兩個 endpoint 使用不同 client/base URL。

### 做法 B：使用能翻譯音訊 endpoint 的 AI gateway

另一類做法是讓 gateway 本身理解音訊 API，再把不同 provider 的格式統一成 OpenAI 形狀。

- [LiteLLM](https://github.com/BerriAI/litellm) 的 provider 能力表包含 `/audio/transcriptions`；官方文件說它把 OpenAI input/output format 翻譯成不同 provider endpoint，並提供 retry／fallback。能力不是所有 provider 都有，必須按 provider matrix 選擇支援 transcription 的後端。
- [DeltaLLM 的 proxy 文件](https://deltallm.readthedocs.io/en/latest/api/proxy/) 展示了更直接的 adapter：對外提供 `POST /v1/audio/transcriptions`，收到 multipart audio 後，轉成 ElevenLabs 原生的 `POST /v1/speech-to-text`，再把回應改回 OpenAI-compatible 格式。
- [OpenRouter transcription API](https://openrouter.ai/docs/api/api-reference/transcriptions/create-audio-transcriptions) 直接提供 `/api/v1/audio/transcriptions`，以 base64 audio、STT model、language 統一請求；它也支援用 `/chat/completions` 的 `input_audio` 把音訊送給支援 audio input 的模型。[OpenRouter audio guide](https://openrouter.ai/docs/guides/overview/multimodal/audio)

這種做法的重點不是 gateway 自己訓練模型，而是**把「公開 API 形狀」和「上游 provider 的原生 API」分開**。這正是目前 404 所缺的那一層。

### 做法 C：直接改用一個 audio-capable cloud endpoint

如果不要求音訊留在本機，另一個現成做法是直接讓 STT client 指向專用雲端 transcription provider；文字整理仍然走目前反代。

OpenAI 官方 SDK 對 transcription 使用 `client.audio.transcriptions.create(...)`，與 `client.chat.completions.create(...)` 是不同 API。OpenAI 的官方 Python client 也列出支援的音訊格式、STT model、language、response format 與 streaming 參數。[官方 transcription client](https://github.com/openai/openai-python/blob/main/src/openai/resources/audio/transcriptions.py)

這條路的缺點不是技術上做不到，而是私人錄音的上傳、費用、保留政策與反代是否允許該路由。它必須明確 opt-in，不能因為文字整理已能上雲，就默默把原始音訊也上傳。

## 「同一個反代 URL」到底怎麼做

如果使用者端或 repo 不想管理兩個 URL，有兩種成熟做法：

### 方案 1：讓 gateway 自己有兩個 upstream

```text
app → LiteLLM／自建 router :4000
       ├─ /v1/chat/completions     → 現有文字反代 :8317
       └─ /v1/audio/transcriptions → speaches／WhisperServer :8765
```

對 app 而言仍然只有一個 `base_url`；對內部而言是兩個能力各自走對的 upstream。這是「統一入口」，不是「同一個模型處理所有媒介」。

### 方案 2：repo 自己維持兩個 client

```text
LLM_BASE_URL=http://127.0.0.1:8317/v1
STT_BASE_URL=http://127.0.0.1:8765/v1
```

這更簡單，也更容易測試和回滾。現有 ChatGPT 反代完全不動；日後如果真的把 transcription route 加進反代，只需改設定，不需改 record pipeline。

## 哪些「看似繞法」不是好解法

| 想法 | 為什麼不行／不適合 |
|---|---|
| 把 `.m4a` base64 塞進目前純文字 chat request | 只有明確支援 `input_audio` 的 multimodal endpoint 才有意義；一般文字 chat route 不會因此獲得 STT 能力。 |
| 把 `gpt-5.6-luna` 的 model name 換成另一個名字 | model name 不會自動新增 `/v1/audio/transcriptions` route；必須確認 gateway 和 upstream 都支援 audio。 |
| 讓反代把音訊先轉成文字再交給 Luna，但不留下中間檔 | 會失去原始音訊保存、重試和 provenance，不符合本案「原始資訊一定保留」。 |
| 將整個 ChatGPT 反代改成新的 gateway | 會擴大影響範圍，也違反目前「不要動 ChatGPT 設定」的邊界；應先做 repo-local sidecar 或獨立 STT base URL。 |
| 直接採用已停止維護的 OpenAI-compatible Whisper server | 可以作為概念證明，但不適合新部署；應優先比較 speaches、WhisperServer 或 MLX ASR。 |

## 對本 repo 的直接結論

這不是「我們還沒找到正確的 Luna model」；是目前架構只接了文字能力。

最少改動的實際路徑應該是：

1. **維持現有 `LLM_BASE_URL` 和 `gpt-5.6-luna` 不動。** 它繼續負責四欄位 AI 整理。
2. **新增一個獨立 `Transcriber` 入口。** 它的 base URL 先指向本機 OpenAI-compatible STT service，而不是目前 ChatGPT 反代。
3. **先比較一個 Mac-native 候選和一個通用 server 候選。** 例如 WhisperServer／MLX ASR 對 speaches；用同一段繁體中文 fixture 測品質、速度、記憶體和 m4a 支援。
4. **逐字稿完成後，才把文字交給目前的 Luna organizer。** 對 `只收錄` 記錄不呼叫 organizer；切換成 `收錄並整理` 才重跑。
5. **只有在真的需要單一 URL 時，才加 route layer。** 這一層只做 `/chat` 與 `/audio/transcriptions` 的路由，不接管資料模型，也不改原始記錄保存規則。

這條路徑等於把「音訊能力」補在反代旁邊，而不是把現有文字反代硬改成音訊模型。它也保留日後改用 OpenRouter、LiteLLM 或雲端 Transcribe provider 的可能性。

## Research ledger：question → claim → source → gap → action

| question | claim | source | gap | action |
|---|---|---|---|---|
| 文字反代不能聽音訊時，大家是否會硬改文字模型？ | 常見做法是分開 STT 與 LLM endpoint，或用 gateway 做 capability translation；不是換一個文字 model name。 | [LiteLLM](https://docs.litellm.ai/)、[DeltaLLM proxy](https://deltallm.readthedocs.io/en/latest/api/proxy/)、[OpenRouter transcription](https://openrouter.ai/docs/api/api-reference/transcriptions/create-audio-transcriptions) | 本 repo 的反代實作細節與是否可加 route 尚未公開確認。 | 先保留目前反代，測獨立 STT sidecar。 |
| 是否已有可直接補上的 OpenAI-compatible STT？ | speaches、WhisperServer、MLX Qwen3 ASR 都提供 `/v1/audio/transcriptions` 或等價 OpenAI client 呼叫。 | [speaches](https://github.com/speaches-ai/speaches)、[WhisperServer](https://github.com/pfrankov/whisper-server)、[mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr) | 繁體中文品質、m4a 讀取與 Mac 資源尚未在本機比較。 | 用同一 fixture 做 bounded benchmark。 |
| 是否能維持一個公開 URL？ | LiteLLM／自建 router 可將 chat 與 transcription 分別轉發到不同 upstream；公開端仍是一個 API。 | [LiteLLM provider matrix](https://github.com/BerriAI/litellm/)、[DeltaLLM proxy](https://deltallm.readthedocs.io/en/latest/api/proxy/) | route policy、auth、錯誤與重試尚未定義。 | 只有兩個 base URL 穩定後，才評估 route layer。 |
| 是否能用同一個雲端 router？ | OpenRouter 提供專用 transcription endpoint，也支援部分模型的 `input_audio` chat input。 | [OpenRouter audio](https://openrouter.ai/docs/guides/overview/multimodal/audio)、[OpenRouter transcription](https://openrouter.ai/docs/api/api-reference/transcriptions/create-audio-transcriptions) | 隱私、價格、繁體中文品質和能否沿用目前 Luna 不明。 | 把它列為獨立 opt-in provider，不改現有反代。 |
| 音訊是否應該直接交給 Luna？ | 目前沒有證據顯示 Luna 對話路由支援音訊；現有 transcription route 實測 404。 | 本 repo live probe；[OpenAI transcription client](https://github.com/openai/openai-python/blob/main/src/openai/resources/audio/transcriptions.py) | 反代上游是否未來增加 audio model 未知。 | 不把 Luna 當成 STT；先接專用 Transcriber。 |

## 來源索引

- [LiteLLM 官方文件](https://docs.litellm.ai/)
- [LiteLLM provider matrix](https://github.com/BerriAI/litellm/)
- [DeltaLLM proxy endpoints](https://deltallm.readthedocs.io/en/latest/api/proxy/)
- [OpenRouter audio guide](https://openrouter.ai/docs/guides/overview/multimodal/audio)
- [OpenRouter transcription API](https://openrouter.ai/docs/api/api-reference/transcriptions/create-audio-transcriptions)
- [speaches](https://github.com/speaches-ai/speaches)
- [WhisperServer for macOS](https://github.com/pfrankov/whisper-server)
- [mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr/)
- [openedai-whisper](https://github.com/matatonic/openedai-whisper)
- [OpenAI audio transcription client](https://github.com/openai/openai-python/blob/main/src/openai/resources/audio/transcriptions.py)
