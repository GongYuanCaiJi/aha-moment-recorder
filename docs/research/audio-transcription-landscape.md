# 錄音轉錄與 Obsidian 整理：現成做法研究

> 研究日期：2026-08-03。這份文件研究別人已經怎麼做；它不是新的產品規格，也不直接決定本 repo 要採用哪一個 provider。

## 先講結論

外面已經有成熟的共通做法，而且它們沒有把問題做成一個全新的「錄音產品」：

1. **先保存原始音訊，再做逐字稿，再選擇是否交給 LLM 整理。** 這三步通常是可重試的獨立階段。
2. **同一筆記錄通常由一個 Markdown note 加上原始音訊檔組成。** 成功的 Obsidian 流程會在 note 裡嵌入音訊、保留逐字稿，再把整理結果放在額外區段。
3. **手機端多半只負責收錄或把檔案放進同步資料夾；Mac 端負責背景處理。** 這比要求 iPhone 長時間在背景跑整套 AI 流程更常見。
4. **轉錄與整理使用不同的模型／服務。** Whisper、faster-whisper 或 whisper.cpp 負責語音轉文字；LLM 只處理已經存在的文字。現在的 `gpt-5.6-luna` 對話路由不能因為能整理文字，就推定它能轉錄音訊。
5. **最接近本案、又不必先自創產品的方向**是：保留現有 Apple Notes／Voice Memos 收錄方式，讓 Mac 的 worker 讀取同步後的原始音訊，接一個可替換的本機 STT adapter，然後沿用目前的四欄位整理流程。先比較候選，再決定是否實作；不要先把 provider 寫死。

這個結論不是說「現在已經自動完成 iPhone → Obsidian」。現成專案的 README 多半是作者自述，且 Apple 來源、同步、權限與檔案關聯仍必須在本機 fixture 實測。

## 研究問題與範圍

要回答的是：**別人如何把手機或 Mac 的錄音保存、轉錄、可選地整理，再放進 Obsidian；哪些做法能保留原始內容，哪些做法不符合本案？**

本次只採用官方文件、官方產品文件和 GitHub 原始專案頁面。專案 README 的能力標示為「專案自述」，不是本 repo 的 runtime 驗證。

## 別人實際採用的五種模式

### 1. Obsidian 外掛內完成：Whisper plugin

[Whisper — Speech-to-text for Obsidian](https://github.com/nikdanilov/whisper-obsidian-plugin) 已經把「錄音／上傳 → Whisper 轉錄 → 可選 LLM 後處理」放在 Obsidian 裡，支援 desktop 和 mobile，也能由 iOS Shortcuts 以 `obsidian://whisper` URL 觸發。它的 note template 同時提供 `{{audioFile}}` 和 `{{transcription}}`，範例用 `![[audio]]` 把原音訊嵌入同一篇 note。

這驗證了兩件事：

- **原始音訊與逐字稿放在同一篇 note 是現成、合理的做法。**
- **LLM 後處理應是選項，而不是轉錄的必要條件。**

限制也很清楚：需要 community plugin、API key 或 Whisper-compatible endpoint；README 沒有替我們保證原始檔案的長期版本、去重、失敗重試或 Apple Notes／Voice Memos 的來源關聯。因此它適合作為低成本 POC 參考，不應直接被當成本 repo 的完整資料契約。

### 2. 手機丟檔，Mac watcher 背景處理：local-whisper-obsidian

[local-whisper-obsidian](https://github.com/serg-markovich/local-whisper-obsidian) 的流程是「手機錄 voice memo → Syncthing 或 iCloud 同步 → Mac／Linux watcher 監看路徑 → faster-whisper 本機轉錄 → 直接建立帶 YAML frontmatter 的 Obsidian Markdown」。作者明確標示 no cloud、no API keys、no subscriptions，並把 AI enrichment（標題、tags、摘要）拆成後續階段。

這是和本案最接近的**背景處理模式**：手機不需要執行長時間的 AI；Mac 只要等檔案同步完成，就能轉錄、重試和寫回。它同時提醒我們要處理模型下載、CPU 速度、watcher 的穩定檔案判定，以及 macOS 支援程度（作者自己也標註 macOS 維護但未積極測試）。

### 3. Mac menubar + 本機模型 + Markdown：stt-md

[stt-md](https://github.com/dreamxist/stt-md) 是小型 macOS menubar app：用 whisper.cpp 做本機轉錄、用 Ollama 產生結構化 JSON，再把 Markdown 寫入 Obsidian。它刻意使用 flat files、沒有自建資料庫；在 Obsidian mode 會掃描既有 tags／wikilinks，過濾 LLM 產生但 Vault 不存在的連結，並可把連結追加到 Daily Note。

它的設計價值是「**Vault 是真相，LLM 是不可信輸入**」：模型可以產生候選分類，但寫入前要受既有詞彙限制。這和本案的分類／主題需求相容；不過它的輸出 schema、語言和 Daily Note 結構是作者自己的產品選擇，不能直接搬進本 repo。

### 4. 一體化本機應用，再匯出 Obsidian：VoiceVault

[VoiceVault](https://github.com/PJH720/VoiceVault) 將 on-device Whisper、local LLM、分類、摘要、RAG 搜尋與 Obsidian Markdown export 放在一個桌面應用；README 說明原始錄音保留在本機，並可選擇雲端 LLM。架構上以 `whisper-cli` 子程序轉錄，再把分類／摘要結果輸出成含 YAML frontmatter 的 Markdown。

這證明「原音 → 逐字稿 → 結構化輸出」可以完全在本機跑通；但它把 capture、搜尋和 export 綁成一個產品。對本案而言，應只借用階段化與本機模型的做法，不要因此再造一個取代 Apple Notes／Voice Memos 的新 App。

### 5. 已包成可被其他程式呼叫的 Mac 服務：TypeWhisper、MacWhisper

[TypeWhisper](https://github.com/TypeWhisper/typewhisper-mac) 是 macOS 本機語音工具，提供只綁 `127.0.0.1` 的 HTTP API、CLI、檔案轉錄、多個本機／雲端引擎與可插拔 provider。它的 API 以 `POST /v1/transcribe` 接收檔案並回傳文字、語言、時長與處理時間；錄音工作也有 `recording → finalizing → completed／failed` 狀態。

[MacWhisper 的 watch folder 與整合文件](https://docs.macwhisper.com/article/35-automatically-transcribing-files-in-watch-folders) 和 [整合文件](https://docs.macwhisper.com/article/53-integrating-macwhisper-with-other-services) 則展示另一個常見模式：監看資料夾，完成轉錄後以 webhook 或 Obsidian Local REST API 建立／更新 Markdown。這個整合需要 MacWhisper Pro，因此可作為「商用最少 glue」參考，不是本 repo 的開源核心。

## 轉錄引擎的現成選擇

| 候選 | 別人怎麼用 | 優點 | 需要注意的缺口 |
|---|---|---|---|
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | C/C++、Apple Silicon 優化、CPU/GPU、可離線；提供 CLI 和本機 HTTP server | macOS／Apple Silicon 友善，不需要 Python 服務，音訊不必離開電腦 | CLI 主要要求 16-bit WAV；需管理模型、ffmpeg／輸入格式與 server lifecycle |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Python library；CTranslate2 實作，支援 VAD、CPU/GPU、量化 | 速度／記憶體效率好，容易被 watcher 或 Python worker 呼叫 | 本身是 library，不是我們現在可直接 POST 的服務；要自行包 adapter 或採用下列 server |
| [speaches](https://github.com/speaches-ai/speaches) | 以 faster-whisper 為後端的 OpenAI API-compatible server，支援 streaming、動態載入、CPU/GPU、Docker | 可沿用 OpenAI client 形狀，最適合接入「可替換 provider」邊界 | 需要 Python／Docker、模型下載與本機服務生命週期；仍要測繁體中文品質與資源用量 |
| [TypeWhisper local API](https://github.com/TypeWhisper/typewhisper-mac) | Mac app 內封裝多個本機引擎，透過 localhost API／CLI 呼叫 | 自帶模型與狀態管理，外部程式只需呼叫 HTTP／CLI | 依賴另一個桌面 App；它是外部產品，不是 repo 內可控的最小依賴 |
| 雲端專用 transcription endpoint | OpenAI 官方將 `gpt-4o-transcribe`／`gpt-4o-mini-transcribe` 定義成 speech-to-text model，使用 `/v1/audio/transcriptions` | 免本地模型管理，可能有較快或較高品質的繁中結果 | 私人音訊需上傳；目前本 repo 使用的反代對 `/v1/audio/transcriptions` 實測回 404，不能假定 `gpt-5.6-luna` 對話路由可直接代替 |

`whisper.cpp` 的官方 README 也明確展示 Apple Silicon、macOS／iOS、offline on-device 與本機 server；`faster-whisper` README 把 `speaches` 列為 OpenAI-compatible server。這讓「本機 STT、既有 LLM 整理」成為已有先例，而不是我們自行發明的架構。

OpenAI 的官方模型頁面把 GPT-4o Transcribe 與 GPT-4o mini Transcribe 標為 speech-to-text，並列出 `/v1/audio/transcriptions`；這和目前文字整理模型的 chat endpoint 是不同能力。參考：[GPT-4o Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)、[GPT-4o mini Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)。

## 和本案需求的對照

| 本案要求 | 現成做法給出的答案 | 本 repo 仍必須守住的界線 |
|---|---|---|
| 原始音訊一定保留 | Whisper plugin、VoiceVault、local-whisper-obsidian 都以原始音檔或 Vault attachment 為起點；部分產品只在處理完成後保留 Markdown，不能一概視為符合 | 永不因轉錄／整理成功而刪除或覆寫原音訊；失敗也要留下來源和待處理狀態 |
| 音訊、逐字稿、整理稿是同一個東西 | Obsidian plugin 的 template 直接在一篇 note 嵌入 audio + transcript；watcher 類方案則用同一個 record id／Markdown 產物串起來 | 不要把原文、逐字稿、AI 結果變成互相獨立、無法關聯的長期真相 |
| AI 可選，預設可整理，個別可只收錄 | Whisper plugin 有可選 post-processing；Scribe／VoiceVault 也把轉錄與整理分階段 | `processing_mode` 只控制是否跑整理；四個結果仍固定為分類、主題、結構化輸出、摘要，不另加待辦欄位 |
| 手機快速收錄、Mac 自動處理 | local-whisper-obsidian 的同步資料夾 + watcher、MacWhisper watch folder、TypeWhisper local API 都採這種分工 | Apple Notes／Voice Memos 到同步路徑的具體來源仍要由本機測試確認；不要把 README 當成 iPhone 實際行為證據 |
| 本地優先、雲端 AI 可選 | whisper.cpp／faster-whisper／VoiceVault／stt-md 都有本機路徑；Whisper plugin、TypeWhisper 也支援相容雲端 provider | 轉錄 provider 必須可替換；把「是否上傳原音」當成明確的設定與紀錄，不要隱式上傳 |
| 失敗可重試，且不影響其他記錄 | Scribe README 提到逐步保存；TypeWhisper 暴露 completed／failed 狀態；watcher 方案以檔案完成後觸發 | 需要由本 repo 的 pipeline 定義 idempotency、重試與錯誤可見性；這不是任何外掛自動保證的能力 |

## 目前本 repo 的實際缺口

本 repo 先前已用 synthetic audio fixture 實測現有反代：`POST /v1/audio/transcriptions` 回 HTTP 404；文字整理的 chat endpoint 可以工作。這表示：

- 不是「分類／摘要的 LLM 不存在」；
- 是「現有反代沒有提供可直接使用的 transcription 路由」；
- 因此 83 筆只有 `.m4a` 的 Voice Memos 目前只能保存原音並標成待處理，不能假裝已完成逐字稿與四欄位整理。

這個缺口正是 GitHub Issue [#29](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/29) 的範圍；provider、私人音訊是否上傳與繁體中文品質則留在 [#13](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/13) 決定。這一輪研究不替你把兩張 ticket 的決策偷做掉。

## 建議的下一步（仍然是 research/POC，不是直接選定產品）

把候選縮成同一個測試問題，而不是先寫新產品：

1. 準備同一段短的繁體中文 fixture，包含口語、專有名詞、停頓與一個可核對的數字。
2. 用相同輸入分別測 `whisper.cpp`／TypeWhisper local API 與 `speaches`（faster-whisper）。若要比較雲端，只把它列為明確 opt-in 的第三組。
3. 每個候選都檢查：逐字稿內容、繁中錯字、處理時間、CPU／記憶體、音訊是否留在本機、服務失敗後能否重試。
4. 只有一個候選通過後，才在 Issue #29 實作一個 `Transcriber` adapter；adapter 的輸出寫回同一筆記錄，再交給現有的四欄位 organizer。
5. 對 `只收錄` 的記錄，轉錄可以依來源／設定需要，但不得自動產生 AI 整理；改成 `收錄並整理` 後才重跑整理階段。

這個順序借用的是現成專案的共同做法：**先保留檔案、階段化處理、provider 可換、結果寫回 Markdown／同一筆記錄**。它不要求我們再創一個 iPhone App，也不把 Obsidian 變成第二個平行資料庫。

## Research ledger：question → claim → source → gap → action

| question | claim | source | gap | action |
|---|---|---|---|---|
| 別人是否把原音、逐字稿、整理放在同一筆？ | Whisper Obsidian plugin 的 template 同時嵌入 audio file 和 transcription；VoiceVault／local-whisper-obsidian 也以音檔到 Markdown 為主流程。 | [Whisper plugin](https://github.com/nikdanilov/whisper-obsidian-plugin)、[VoiceVault](https://github.com/PJH720/VoiceVault)、[local-whisper-obsidian](https://github.com/serg-markovich/local-whisper-obsidian) | README 不等於本機完整 restore／provenance 驗證。 | fixture 必須逐項檢查原音、逐字稿與整理區段仍屬同一筆。 |
| 背景處理通常放哪裡？ | 手機同步檔案，Mac watcher／桌面服務轉錄，是現成常見模式。 | [local-whisper-obsidian](https://github.com/serg-markovich/local-whisper-obsidian)、[MacWhisper watch folders](https://docs.macwhisper.com/article/35-automatically-transcribing-files-in-watch-folders)、[TypeWhisper](https://github.com/TypeWhisper/typewhisper-mac) | Apple Notes／Voice Memos 的來源檔案何時算完成仍要測。 | 用同步後的穩定檔案觸發，先做 bounded POC。 |
| 本地 STT 是否已有可重用 building block？ | whisper.cpp、faster-whisper、speaches 都已提供本機推論；speaches 另提供 OpenAI-compatible API。 | [whisper.cpp](https://github.com/ggml-org/whisper.cpp)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[speaches](https://github.com/speaches-ai/speaches) | 繁體中文品質與本機資源未在本案測量。 | 用同一繁中 fixture 做品質／延遲／資源比較。 |
| 雲端 STT 是否等於目前的文字 LLM？ | 官方將 Transcribe 模型與 `/v1/audio/transcriptions` 定義為專用語音轉文字能力；不能由 chat 整理能力推論具備 STT。 | [GPT-4o Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)、[GPT-4o mini Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe) | 本反代是否日後增加該路由未知；現在實測為 404。 | 在 #13 決定是否允許雲端與 provider；不要把 404 workaround 寫成假定。 |
| 是否有「整理可選」的先例？ | Whisper plugin 有 optional post-processing；其他方案也把 transcription 與 enrichment 分階段。 | [Whisper plugin](https://github.com/nikdanilov/whisper-obsidian-plugin)、[Scribe](https://github.com/Mikodin/obsidian-scribe)、[local-whisper-obsidian](https://github.com/serg-markovich/local-whisper-obsidian) | 每個專案的 mode／失敗語意不同。 | 沿用本 repo 的 `只收錄`／`收錄並整理`，只在 adapter 完成後接 organizer。 |
| 商用整合是否值得直接依賴？ | MacWhisper 提供 watch folder、webhook、Obsidian Local REST API，但整合是 Pro 功能。 | [MacWhisper integrations](https://docs.macwhisper.com/article/53-integrating-macwhisper-with-other-services) | 不是開源核心，且檔案／API 權限與版本依賴外部產品。 | 可作手動基準，不作本 repo 必要依賴。 |

## 來源索引

- [Whisper — Speech-to-text for Obsidian](https://github.com/nikdanilov/whisper-obsidian-plugin)
- [local-whisper-obsidian](https://github.com/serg-markovich/local-whisper-obsidian)
- [stt-md](https://github.com/dreamxist/stt-md)
- [VoiceVault](https://github.com/PJH720/VoiceVault)
- [TypeWhisper for Mac](https://github.com/TypeWhisper/typewhisper-mac)
- [MacWhisper watch folders](https://docs.macwhisper.com/article/35-automatically-transcribing-files-in-watch-folders)
- [MacWhisper integrations](https://docs.macwhisper.com/article/53-integrating-macwhisper-with-other-services)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [speaches](https://github.com/speaches-ai/speaches)
- [GPT-4o Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)
- [GPT-4o mini Transcribe](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)
