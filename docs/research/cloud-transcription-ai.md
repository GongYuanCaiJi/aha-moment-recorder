# 雲端語音轉寫與 AI 整理方案

研究日期：2026-07-27

## 結論

不要把語音轉寫和 AI 整理綁成同一個模型，也不要現在就鎖定 GPT-5.6。建議將兩個步驟做成可分別替換的供應商介面：錄音先交給專用語音轉寫服務產生逐字稿；只有處理模式為「收錄並整理」的記錄，才把逐字稿或原始文字交給生成式 AI。來源內容、逐字稿與 AI 整理結果仍屬於同一筆記錄，雲端只負責運算，本地才是唯一紀錄簿。

第一輪 POC 建議同時驗證下列候選，而不是直接選定單一供應商：

- 語音轉寫：以 OpenAI `gpt-4o-transcribe` 作為簡單、低留存基準；以 Google Cloud Speech-to-Text V2 `chirp_3`、`cmn-Hant-TW` 作為台灣繁體中文基準。
- AI 整理：以 OpenAI `gpt-5.6-luna`、Google `gemini-3.5-flash-lite` 付費 API、Anthropic `claude-haiku-4-5` 作為成本組；若整理忠實度不足，再比較 `gpt-5.6-terra` 或 `claude-sonnet-5`。GPT-5.6 Sol 不應預設使用，除非測試證明較高成本能帶來必要的品質改善。
- Apple `SpeechAnalyzer` 與 Foundation Models 是值得保留的本機隱私路線，但此次找到的官方介面是 Apple 平台框架，不是可由背景電腦工作程序呼叫的通用雲端 API，因此不列入本輪雲端供應商決選。

在完成繁體中文實測前，以上都只是候選。官方聲稱支援中文或多語言，不等於已證明能準確處理台灣口語、英中夾雜、專有名詞及長時間隨性口述。

## 不可妥協的資料邊界

1. 雲端服務不得成為記錄的保存位置；請求成功或失敗後，來源內容仍以本地版本為準。
2. 原始錄音與來源文字不被 AI 內容覆寫；逐字稿和 AI 整理結果是同一筆記錄內的衍生版本。
3. 「只收錄」不得呼叫生成式 AI；使用者之後改成「收錄並整理」時才送出。
4. 預設不加入任何供應商的訓練或資料分享計畫，也不使用免費 Gemini tier 處理私人記錄。
5. 預設使用一般同步 API，由本地佇列負責背景重試；不要用會額外保存資料的供應商 Files、Batch、conversation/thread 或 background state。
6. 每次結果都記錄供應商、模型或固定版本、prompt 版本、schema 版本、時間與失敗原因，才能重跑、比較及日後更換供應商。

## 語音轉寫比較

| 候選 | 繁體中文 | 長錄音 | 資料保存與刪除 | 延遲與成本 | 判斷 |
| --- | --- | --- | --- | --- | --- |
| OpenAI `gpt-4o-transcribe` | 官方支援 Chinese；官方也明確提醒簡繁體輸出不一定符合預期，可用繁體中文 prompt 改善。尚無台灣中文品質保證。 | 單次檔案上限 25 MB，超過必須切段，且應避免切在句中。 | `/v1/audio/transcriptions` 的官方表格列為不用於訓練、無 abuse-monitoring retention、無 application-state retention，且可用 ZDR。 | 依音訊 token 計價：每百萬輸入音訊 token US$2.50、輸出 US$10；官方沒有給這個使用情境的端到端延遲承諾。 | 操作與隱私基準。缺點是長錄音切段，以及繁體字形需 prompt 與實測確認。 |
| Google Cloud STT V2 `chirp_3` | 有明確的 `cmn-Hant-TW` locale，但目前官方標為 Preview；該 locale 不在官方列出的 Chirp 3 diarization 語言內。 | `BatchRecognize` 一般支援 1 分鐘至 1 小時；啟用 word-level timestamp 時上限降為 20 分鐘。超過 60 秒或 10 MB 的官方流程要求先放進 Cloud Storage。 | Cloud STT 預設不記錄音訊或逐字稿；sync/stream 在記憶體處理，async 結果約保存 5 天。Cloud Storage 物件須由我們設定刪除；預設 soft delete 仍保留 7 天。不得開啟 data logging，否則資料可被用來改善模型且既有資料不會因關閉設定自動刪除。 | V2 Standard 每分鐘 US$0.016；dynamic batch 每分鐘 US$0.003、24 小時內完成，另計 Cloud Storage。 | 最值得驗證的台灣繁中基準。缺點是 locale 尚為 Preview，且長錄音引入 GCS 保存與刪除生命週期。 |
| Apple `SpeechAnalyzer` / `SpeechTranscriber` | 可指定 locale；支援情況需在目標裝置與 OS 實際查詢。 | 官方示範可轉寫錄音檔，也支援 live transcription。 | Apple 提供裝置端 speech recognition 能力檢查；舊 `SFSpeechRecognizer` 也明確區分可否在裝置端辨識。 | 不按雲端 API token 或分鐘計費，但受 Apple 裝置、OS、語言模型可用性限制。 | 適合未來原生 iPhone／Mac 本機路線，不是目前背景電腦可直接採用的通用雲端 API。 |

OpenAI 依據：[Speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)、[`gpt-4o-transcribe` model](https://developers.openai.com/api/docs/models/gpt-4o-transcribe)、[API data controls](https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint)。

Google 依據：[Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)、[Cloud STT setup](https://docs.cloud.google.com/speech-to-text/docs/setup)、[data usage FAQ](https://docs.cloud.google.com/speech-to-text/docs/v1/data-usage-faq)、[data logging](https://docs.cloud.google.com/speech-to-text/docs/v1/data-logging)、[pricing](https://cloud.google.com/speech-to-text/pricing)、[Cloud Storage lifecycle](https://docs.cloud.google.com/storage/docs/lifecycle)。

Apple 依據：[SpeechAnalyzer](https://developer.apple.com/documentation/speech/speechanalyzer)、[WWDC25 SpeechAnalyzer session](https://developer.apple.com/videos/play/wwdc2025/277/)、[`supportsOnDeviceRecognition`](https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition)。

## AI 整理比較

這一步只接收文字，不接收原始錄音。三家都有正式 API 與 JSON Schema 類型的結構化輸出，但「符合 schema」只保證形狀，不保證摘要忠於來源；仍須做內容驗證並保留逐字稿供追溯。

| 候選 | API 與結構化輸出 | 資料保存、訓練與刪除 | 每百萬文字 token 定價（輸入／輸出） | 判斷 |
| --- | --- | --- | --- | --- |
| OpenAI GPT-5.6 Luna / Terra / Sol | Responses API；支援 Structured Outputs。三者都不接受 audio，所以只能用於逐字稿後處理。 | API 資料預設不訓練。Responses 預設會保存 application state 至少 30 天，且一般 abuse monitoring 最多 30 天；應明確設 `store:false`，不使用 background mode、Files 或 Batch。若要排除 abuse log 內容，仍需申請 ZDR/MAM。 | Luna US$1／US$6；Terra US$2.50／US$15；Sol US$5／US$30。 | 供應商整合最少，但不能因此跳過跨供應商品質測試。先測 Luna，失敗再升級 Terra；Sol 只作高品質上限。 |
| Google Gemini 3.5 Flash-Lite（付費） | Gemini API 支援 JSON Schema structured output；3.5 Flash-Lite 是低成本、高吞吐候選。 | Gemini 免費 tier 會用資料改善產品，付費 tier 不會，因此私人記錄只能用付費 tier。若採 Vertex AI，Google 未經允許不會用客戶資料訓練；要達 ZDR 仍須處理 abuse logging 例外，並停用會保存資料的 grounding 或 session-resumption 功能。 | US$0.30／US$2.50。 | 成本最低的主力候選；需測繁體中文忠實度與 thinking token 對實際帳單的影響。 |
| Anthropic Claude Haiku 4.5 / Sonnet 5 | Messages API；兩者支援 Structured Outputs。Messages 接受文字與圖片，不是語音轉寫 API。 | 商用 API 預設不訓練，輸入輸出於 30 天內刪除；ZDR 須經企業申請。Structured Outputs 在 ZDR 下僅暫存 schema 最多 24 小時；Files 會保留至刪除，Batch 可保存 29 天，因此都不應用於此流程。 | Haiku 4.5 US$1／US$5；Sonnet 5 標準 US$3／US$15。 | Haiku 是成本比較組，Sonnet 是較高品質比較組；官方沒有台灣繁中專用基準，必須實測。 |
| Apple Foundation Models | 裝置端文字模型可摘要、抽取與產生標籤，`@Generable` 可產生型別化結構。 | 核心為 on-device，模型能否使用取決於裝置是否支援並開啟 Apple Intelligence。 | 無雲端 token 費，但受裝置資格、模型版本與 context 限制。 | 可作未來「完全不送雲端」選項；不可當作所有電腦與手機都能使用的雲端 fallback。 |

OpenAI 依據：[GPT-5.6 models](https://developers.openai.com/api/docs/models)、[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[API data controls](https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint)。

Google 依據：[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)、[Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)、[Vertex AI zero data retention](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention)。

Anthropic 依據：[models overview](https://platform.claude.com/docs/en/about-claude/models/overview)、[Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)、[API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention)、[commercial retention](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data)、[commercial training policy](https://privacy.anthropic.com/en/articles/7996868-is-my-data-used-for-model-training)。

Apple 依據：[Foundation Models tasks](https://developer.apple.com/documentation/foundationmodels/generating-content-and-performing-tasks-with-foundation-models)、[`Generable`](https://developer.apple.com/documentation/foundationmodels/generable)、[`SystemLanguageModel`](https://developer.apple.com/documentation/foundationmodels/systemlanguagemodel)。

## 成本示例

以下只用來比較量級，不是月費報價；實際費用會受音訊編碼、模型 tokenization、推理 token、重試與價格更新影響。

- 600 分鐘錄音／月：Google STT Standard 約 US$9.60；dynamic batch 約 US$1.80，但可能等到 24 小時且另計 Cloud Storage，所以不適合預設的快速背景處理。
- OpenAI 轉寫目前按 audio token 計價，官方沒有提供足以把任意錄音分鐘數精確換算成 token 的固定比率；應在 POC 直接記錄實際 usage，不用非官方每分鐘估值混比。
- 假設每月 AI 整理合計 100,000 input tokens 與 20,000 output tokens：Gemini 3.5 Flash-Lite 約 US$0.08、Claude Haiku 4.5 約 US$0.20、GPT-5.6 Luna 約 US$0.22、GPT-5.6 Terra 約 US$0.55、Claude Sonnet 5 約 US$0.60、GPT-5.6 Sol 約 US$1.10。這個例子顯示個人規模下，語音轉寫與資料生命週期通常比文字整理 token 費更值得優先最佳化。

## 選型驗證門檻

正式選型前，應使用同一組由使用者授權的測試樣本做盲測。樣本至少要涵蓋安靜與吵雜環境、短筆記與長口述、台灣口語、英中夾雜、專有名詞、停頓與自我修正。

語音轉寫要量測：

- 中文字錯誤率（CER）、漏句與憑空補字。
- 繁體字形比例、專有名詞與英中切換準確率。
- 切段後的跨段銜接、時間戳與失敗重試結果。
- 完成時間 p50／p95、實際 usage 與單筆成本。

AI 整理要量測：

- schema 驗證成功率，以及每個欄位是否能回溯到來源內容。
- 是否擅自增加事實、改變語氣或把不確定內容寫成確定結論。
- 使用者可直接接受、需小修、需重做的比例。
- 完成時間 p50／p95、輸入輸出 token 與單筆成本。

任何候選若需要開啟訓練分享、無法關閉不必要的持久保存，或無法說明刪除生命週期，就算文字品質較高也不得成為預設。若兩個候選品質接近，優先選擇資料暴露較少、正式版 API、操作較簡單且成本較低者。

## Research ledger

| Question | Claim | Source | Gap | Action |
| --- | --- | --- | --- | --- |
| 哪個 STT 最適合台灣繁中？ | Google 有明確 `cmn-Hant-TW`，OpenAI 支援 Chinese 並可用 prompt 引導繁體；兩者都沒有可直接代表本使用情境的官方品質數字。 | [Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)、[OpenAI speech-to-text](https://developers.openai.com/api/docs/guides/speech-to-text) | 台灣口語、英中夾雜與專有名詞的相對品質未知；Google locale 仍為 Preview。 | 用相同授權樣本比較 CER、繁體字形、漏句與專名，結果決定預設；供應商保持可替換。 |
| 長錄音怎麼處理？ | OpenAI 要切成不超過 25 MB；Chirp 3 Batch 一般支援至 1 小時，但需 GCS，word timestamp 會把上限降到 20 分鐘。 | [OpenAI speech-to-text](https://developers.openai.com/api/docs/guides/speech-to-text)、[Google Chirp 3](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3)、[Google setup](https://docs.cloud.google.com/speech-to-text/docs/setup) | 實際錄音格式、平均大小與常見時長尚未量測。 | POC 記錄檔案大小與時長；測試語意邊界切段及 GCS 暫存刪除流程。 |
| 哪個模型適合整理？ | OpenAI、Gemini、Claude 都能產生符合 JSON Schema 的輸出；GPT-5.6 本身不支援音訊，必須在 STT 後使用。 | [OpenAI GPT-5.6](https://developers.openai.com/api/docs/models)、[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)、[Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | schema 正確不代表內容忠實，且沒有本產品繁中整理基準。 | 先測低成本模型；以來源可追溯、不得新增事實和人工接受率決定是否升級模型。 |
| 私人筆記會不會被訓練或長期保存？ | 三家商用／付費 API 都提供不將資料用於一般模型訓練的路線，但標準保存、abuse log、檔案與批次功能各不相同；真正 ZDR 通常需要額外設定或申請。 | [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint)、[Google Vertex AI ZDR](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention)、[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)、[Anthropic retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) | 尚未知道個人帳戶能否取得各家的 ZDR／MAM 或 abuse-logging 例外。 | 第一版假設沒有企業 ZDR：只送明確選取內容、使用 stateless API、停用資料分享、避免 Files／Batch／provider background，並在設定頁清楚揭露。 |
| 刪除能做到什麼程度？ | OpenAI transcription endpoint 本身不保留 application state；Google async transcript 約 5 天，GCS 物件由我們刪除且預設 soft delete 7 天；Anthropic Files 保留至刪除、Batch 29 天。 | [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data#default-usage-policies-by-endpoint)、[Google data FAQ](https://docs.cloud.google.com/speech-to-text/docs/v1/data-usage-faq)、[GCS lifecycle](https://docs.cloud.google.com/storage/docs/lifecycle)、[Anthropic API retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) | 供應商安全／法規保留例外不能由應用程式刪除。 | UI 不承諾「立即從所有供應商永久刪除」；記錄實際供應商政策，GCS 用獨立暫存 bucket 與最短生命週期。 |
| 延遲是否足以背景自動整理？ | Google dynamic batch 明定 24 小時內完成；其餘一般 API 沒有足以代表台灣網路與長錄音的官方端到端保證。 | [Google RPC processing strategy](https://cloud.google.com/speech-to-text/v2/docs/reference/rpc/google.cloud.speech.v2)、各家 API 文件 | 真實 p50／p95 未知。 | 預設用一般同步 API加本地佇列，不用 24 小時 batch；POC 實測後再定義產品等待狀態與逾時。 |
| Apple 能否取代雲端？ | Apple 提供 SpeechAnalyzer 與裝置端 Foundation Models，也能產生型別化結果。 | [SpeechAnalyzer](https://developer.apple.com/documentation/speech/speechanalyzer)、[Foundation Models](https://developer.apple.com/documentation/foundationmodels/generating-content-and-performing-tasks-with-foundation-models)、[`Generable`](https://developer.apple.com/documentation/foundationmodels/generable) | 裝置、OS、locale、模型可用性不同；此次未找到等價的通用 Apple 雲端開發者 API。 | 列為後續 iOS／macOS 原生隱私路線，先做裝置能力偵測與 fallback 研究，不阻塞雲端 POC。 |
