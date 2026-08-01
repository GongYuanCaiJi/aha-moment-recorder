# Issue #16：既有產品能力與個人記錄工作流適配研究

研究日期：2026-08-01  
研究範圍：Apple Notes、Apple Voice Memos、Obsidian、Drafts、Bear、Typeless；以 iPhone-first、local-first 的個人記錄工作流為判準。  
Issue：[#16 重新研究既有產品能力與個人工作方式適配](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/16)

## 先講結論

沒有一個產品原生同時提供「原始文字、原始音訊、逐字稿、附件、AI 結果、可追溯版本」這個完整記錄單位。

- **Apple Notes** 最接近 iPhone-first 的低摩擦收錄：同一則 Note 可原生放文字、音訊、逐字稿與附件，並有 iCloud 同步、Recently Deleted、Apple Intelligence 摘要。可是摘要目前是錄音上的檢視／複製／分享結果，不是官方明確保證的持久 AI 欄位；完整匯出與持久版本歷史也不足。結論是「收錄原型的第一候選」，不是已完成的 local-first 記錄系統。
- **Obsidian** 最接近 local-first 與資料所有權：Vault 是本地 Markdown 與一般附件檔，官方有 Audio recorder、File recovery、Sync 版本歷史與 Plugin API。逐字稿、固定記錄結構、AI provenance 與跨裝置衝突處理仍要 glue 或自建。
- **Drafts** 是最強的文字快速收錄／自動化候選：原生版本歷史、iCloud sync、JSON backup、Trash、Shortcuts、JavaScript、URL scheme 與 LLM actions 都有官方文件；但官方文件沒有證明原始音訊會作為同一個 Draft 的持久組件保留。
- **Bear** 適合文字與附件，且有 TextBundle、完整 backup、Shortcuts、x-callback URL 與 macOS CLI/MCP；但沒有官方記錄原生錄音與逐字稿的證據，持久版本歷史也沒有明確文件。
- **Apple Voice Memos** 是最強的原始音訊／逐字稿來源，不是完整記錄容器。它有原生 iCloud 同步、匯出、刪除恢復與「另存新錄音」；文字、附件、AI 結果及非覆寫寫回要接 Notes 或另一個容器。
- **Typeless** 是輸入層，不是 durable record store。它把逐字結果插入目前聚焦的文字欄位；官方隱私文件說語音即時送雲端轉寫後不保留，History 是本機且受保留期限制；Ask anything 也可能直接替換選取文字。它不符合 offline-first 或完整記錄保存要求。

因此，Issue #16 的下一步邊界應是做一個**小型、可回復的 record fixture fit test**，而不是現在就定完整架構：至少用 Apple Notes、Obsidian、Drafts 各跑一次「文字 + 原始音訊 + 逐字稿 + 附件 + AI 結果 + 離線收錄 + 匯出／恢復 + 非覆寫寫回」；用實際操作結果決定下一張 decision ticket 要選哪個收錄基底。這份研究只提供產品能力證據，不替 repo 決定資料模型、LLM 供應商、保留政策或最終產品選型。

## 分類與證據規則

| 分類 | 意義 |
|---|---|
| **1. 現成／product-native** | 官方文件直接描述該能力，使用者不需另外建立記錄系統。 |
| **2. 少量 glue／integration** | 官方提供 Shortcuts、URL scheme、plugin、script 或檔案匯入／匯出，可把能力接起來；仍需設計少量欄位、命名或流程。 |
| **3. 必須自建／major gap** | 官方沒有證明該能力，或要有 durable component、版本、佇列、重試、恢復與 provenance 才能滿足需求；不能把「找不到文件」當成產品絕對不存在。 |

信心標記：

- **高**：官方文件明確描述，或有明確的官方 API／操作步驟。
- **中**：官方文件支持相鄰能力，但未明確保證完整工作流或版本／平台細節。
- **低**：只有官方未說明或行銷敘述，需現場驗證；本文件不把它當成已具備。

「同一個記錄」在本研究中指：使用者可以在不覆蓋來源的情況下，把來源文字或音訊、逐字稿、附件與 AI 結果互相追到一起。這不是說產品內部一定有同名的 record schema。

## 六產品比較

| 產品 | 文字／音訊收錄 | 原始來源、逐字稿、附件、版本 | 離線／同步／匯出／恢復／所有權 | Shortcuts／API／plugin／LLM | iPhone-first / local-first 判斷 |
|---|---|---|---|---|---|
| Apple Notes | 文字、附件、Note 內錄音與支援語言的轉寫原生。1／高 | 音訊與轉寫同屬錄音；可把逐字稿加入 Note。附件原生。AI 可摘要、複製、分享，但持久寫回需 glue。完整版本歷史未被官方文件證明。1 + 2 + 3／中高 | iCloud 同步、Recently Deleted；可 PDF/Markup 匯出，但不是完整 raw package backup。iCloud／裝置 backup 與 ADP 是恢復／隱私層，不等於本地權威。1 + 2 + 3／中 | Shortcuts 有 Find/Create/Append to Note；Use Model 可接 Apple Intelligence、Private Cloud Compute 或 ChatGPT。選定錄音的結果要非覆寫保存，可用 Append，但選取與 provenance 需測試。2／中 | iPhone-first 最佳；local-first 較弱，因權威資料與同步主要依 iCloud。 |
| Apple Voice Memos | 原始音訊、iPhone 12+ 轉寫、文字搜尋原生。1／高 | 可另存新錄音保留原件；沒有同一筆 Note 的文字／附件／AI 結果容器。轉寫和摘要不等於可攜式 durable record。1 + 2 + 3／中高 | 本機錄音不需雲端；iCloud 跨 iPhone/iPad/Mac；M4A／editable file 分享；Recently Deleted 可恢復。Apple backup 是額外保護，但沒有完整 record package。1 + 2／高 | iOS 26 Shortcuts 有 Find Voice Recording；可 Share to Notes／Files，之後以 Append 寫回。沒有官方文件證明能一步把原音訊、逐字稿、AI 結果綁成一個 Note。2 + 3／中 | iPhone 音訊收錄最佳；需要另一個容器才可能符合 local-first record。 |
| Obsidian | Markdown 文字原生；Core Audio recorder 把音檔存進 Vault 並嵌入 Note。1／高 | 附件是 Vault 中的一般檔案；逐字稿不是 Audio recorder 的原生輸出，需轉寫 glue／plugin。Sync/File recovery 有恢復與版本能力，但需看方案。1 + 2 + 3／高 | 本地 plain-text Vault 可離線使用；可用官方 Sync 或檔案同步；可 zip 全 Vault backup；E2EE 密碼遺失不可恢復。1／高 | 官方 Plugin API；可做轉寫、固定區塊、AI append 與 provenance。基本 append 是 2；完整 queue/retry/record schema 是 3。 | local-first 最強；iPhone-first 可行，但音訊轉寫與流程摩擦高於 Notes。 |
| Drafts | iPhone/iPad/Mac/Watch 快速文字收錄原生；可把外部音訊／影片轉成文字。1／高 | 自動 Draft version history 原生；官方沒有證明外部原始音訊會留在同一 Draft。附件／檔案 actions 存在，但不等於 durable audio component。1 + 2 + 3／中高 | iCloud sync；Trash；JSON .draftsExport backup/restore；內容可用 ADP 保護。1／高 | Shortcuts 有 Get/Append/Save Version；完整 JavaScript、URL scheme、AppleScript；AI actions 可選 LLM、建立新 Draft 或 append。2／高 | 文字-first 與自動化最佳；音訊記錄單位需要自建或改用外部來源。 |
| Bear | 文字 Note、照片／影片／PDF／一般檔案附件原生。1／高 | 沒有官方原生錄音／逐字稿流程；可用 x-callback add-file 附加外部音檔，再把外部逐字稿 append。沒有明確官方持久 revision history；backup 是快照。1 + 2 + 3／中 | Note 本機存在；Bear Pro 用 CloudKit sync；TextBundle／.bear2bk export/backup；restore 會替換目前 notes（含 trash），需先留副本。1／高 | Shortcuts、x-callback URL、macOS bearcli／MCP 可 search/read/create/append/attach；選定 Note 的 LLM 寫回可接，但雲端模型與非覆寫 provenance 仍是 glue。2／高 | iPhone-first 文字／附件合適；local-first 尚可；音訊與版本歷史是主要缺口。 |
| Typeless | 對聚焦文字欄位做語音輸入；文字結果由目的 App 保存。1／高 | 官方描述的本機 History 是逐字結果且受保留期限制；雲端不保留語音／transcript。沒有完整文字、原始音訊、附件、AI 結果、版本的 record。1（輸入層）+ 3（記錄層）／高 | 語音即時雲端處理；Ask anything 需要網路；未找到官方 export／backup／sync／recovery 或 public API/plugin 文件。3／中高 | 可在任意文字欄位插入；AI edit 會替換選取文字。要非覆寫寫回、保存來源與可恢復版本，需目的 App 或自建 glue。2（接收端）+ 3（Typeless 本身）／中 | iPhone-first 輸入方便；不符合 offline-first，也不能當 authoritative record store。 |

## 各產品按同一需求維度核對

### Apple Notes

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 原始文字、原始音訊、逐字稿、附件 | Note 原生承載文字、附件和錄音；官方說可對錄音轉寫、搜尋、Copy Transcript 或 Add Transcript to Note；刪除錄音也會刪除其 transcript。1／高 | 若要「來源音訊、逐字稿、附件、AI 結果」都成為明確可搬移的欄位，需確認 Add Transcript 後的資料形狀與匯出保真度。 |
| AI 結果且不覆寫來源 | Notes 可對錄音摘要，官方只明確描述 View、Copy、Share Summary；Shortcuts 有 Append to Note，Use Model 可把模型輸出交給後續 action。原生生成 + glue 非覆寫寫回。1 + 2／中高 | Apple 文件沒有明確說 Summary 會被持久寫成 Note 內容，也未描述 selected-record ID、模型輸出 provenance 或版本。需實測以固定標記 append 到同一 Note。 |
| 離線、同步、資料所有權 | 錄音與文字是在裝置上的 Notes 操作；iCloud Notes 在同一 Apple Account 裝置同步。同步、iCloud backup 與 ADP 有官方文件。1／中高 | 官方文件未把「完整離線工作流、排隊與衝突語意」當成保證；若 local-first 意思是本地資料權威，這不是原生模式。 |
| 匯出、backup、delete、recovery、version | Note 可 PDF/Markup export；刪除後 30 天內可從 Recently Deleted 恢復；Apple 建議裝置／iCloud backup。1／中高 | 沒找到官方完整 Notes package export 或個人 Note 的 durable revision history；PDF 不足以保證保留原始音訊、逐字稿和附件。要這兩項需自建／另存副本。3／中高 |
| Shortcuts/API/plugin/script | Shortcuts 有 Create、Find、Show、Append to Note；Mac automation 是否可用取決於 app dictionary，不能自行假設完整 Notes AppleScript API。2／高 | raw audio／transcript 是否能被 Shortcuts 直接選出並交給 LLM，官方頁面未完整定義；先做現場小測。 |
| iPhone-first/local-first | iPhone 收錄摩擦最低，Mac 可接續；local-first 不是它的主要資料模型。1／高 | 候選適合收錄原型；若選它，下一張 ticket 必須處理 export fidelity、版本、record identity 與本地 backup。 |

### Apple Voice Memos

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 原始音訊、逐字稿 | iPhone 12+ 可看／複製 transcript，且可搜尋；錄音是第一級資料。1／高 | 轉寫文字沒有同一 Note 的附件／AI 結構；若要保留原始文字輸入，需另一個文字容器。 |
| 不覆寫 | Trim／Replace 時可 Save Recording 覆寫或 Save as New Recording 留下原件。1／高 | 這是音訊編輯版本選項，不是完整 record version history；transcript 與外部 AI 結果的版本關聯要另做。 |
| 離線、同步、匯出、backup | 本機錄音是 native；Voice Memos in iCloud 會跨 Apple 裝置；可分享 rendered .m4a 或 editable file、存到 Files；Apple 說 iCloud／裝置 backup 是額外保護。1／高 | 官方沒有把完整「音訊 + transcript + AI result」打包匯出；iCloud backup 也不是可直接讀的資料所有權格式。 |
| delete、recovery、ownership | 刪除錄音預設留在 Recently Deleted 30 天，可調整，並可 Recover 或永久刪除。1／高 | 雲端／Apple Account 是同步層；若 local-first 要可獨立讀取的本地權威檔，需 Share／Files copy 或另一個容器。 |
| Shortcuts／LLM／寫回 | iOS 26 Shortcuts 有 Find Voice Recording；可 Share 到 Notes／Files，再用 Notes Append 或其他 action 寫 AI 結果。2／中 | 官方未證明可從單一選定錄音直接取得 raw audio + transcript，呼叫任意 cloud LLM，再以同一 ID 非覆寫回寫。這部分先視為 glue spike；完整可靠流程是 3。 |
| iPhone-first/local-first | 原始音訊收錄和恢復非常合適；作為完整個人記錄系統不合適。1／高 | 最合理角色是 source capture，不是唯一 store。 |

### Obsidian

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 原始文字、音訊、附件 | Markdown 直接在 Vault；Audio recorder 把音訊檔存到 Vault 並嵌入 Note；附件是 Vault 中的一般檔案。1／高 | 「同一記錄」靠 Note 內容與檔案路徑約定，不是官方 schema；需要穩定 ID／命名規則時是 2。 |
| 逐字稿 | 官方 Audio recorder 文件只描述錄音與檔案保存，沒有轉寫流程。3／高 | 需外部 transcription、plugin 或 Shortcuts／script；若 offline transcription 是硬需求，還要測模型與 iPhone 資源。 |
| AI 結果且不覆寫 | Markdown 可 append 新的 AI 整理區塊；官方 Plugin API 可讀寫 Vault。2／高 | 這只能保證文字落地，不自動保證輸入快照、模型、時間、錯誤、重試、重跑與版本 provenance；完整處理器是 3。 |
| 離線、同步、匯出、backup、recovery | 本地 plain-text Vault 可用檔案工具；官方 Sync 有版本歷史；File recovery 可恢復；官方建議 zip 全 Vault backup。1／高 | Sync 版本期限與附件歷史受方案／版本影響；E2EE 密碼遺失不可恢復。要用 iCloud/Dropbox/Git 等第三方 sync，責任與衝突風險要另評估。 |
| delete、ownership | 刪除的 notes／attachments 可由 Sync version history 或 File recovery 回復；資料本體是使用者可讀檔案，沒有專有封裝鎖定。1／高 | 需明訂誰是 authoritative copy，以及多裝置同時編輯時的衝突處理；產品本身不替個人 record contract 定義。 |
| plugin／script／LLM | 官方 Plugin API 與 sample plugin 足以做轉寫／AI append glue。2／高 | 若做成跨 iPhone/Mac、離線佇列、雲端 LLM、重試、恢復與不可變來源，已經不是小 glue。3／中高。 |
| iPhone-first/local-first | local-first 最強；iPhone capture 有本地檔案優勢，但設定與流程摩擦較高。1 + 2／中高 | 應先驗證手機錄音、同步延遲、附件路徑、匯出／恢復和外掛權限，不要只從 Vault 格式推導實際 UX。 |

### Drafts

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 原始文字 | Drafts 是開啟即輸入、auto-save 的文字收錄工具；iPhone/iPad/Mac/Watch 均有官方工作流。1／高 | 文字來源可保留；它不是音訊-first record container。 |
| 原始音訊、逐字稿、附件、版本 | 官方有從 Voice Memos／Files 匯入音訊／影片並轉成文字；自動 version history 可檢視／恢復。官方未證明原始音訊會留在同一 Draft；file actions 也不等於 Draft 內 durable audio component。1 + 2 + 3／中高 | 若原始音訊不可遺失是硬需求，必須把音檔放在另一個可追蹤位置並建立關聯，或自建 record wrapper。 |
| 離線、同步、匯出、backup、recovery | Drafts 有 iCloud sync、Trash、JSON .draftsExport backup/restore 與 version history；內容可用 Apple ADP 保護。1／高 | 需現場確認音訊檔案、外部 attachment、版本與 JSON backup 的實際包含範圍；官方文件主要描述 Draft 內容。 |
| AI 結果且不覆寫 | Shortcuts 有 Get Draft by UUID、Append to Draft、Save Draft Version；JavaScript 可呼叫 HTTP；官方 AI actions 可用多種 LLM 或 Apple Foundation Models。2／高 | cloud LLM 憑證、資料出境、模型結果 provenance 和「保留來源不替換」仍是 local workflow 決定；Append／new Draft 可做到基本非覆寫。 |
| delete、ownership、iPhone-first | Trash 與 iCloud／本地內容提供實用恢復；快速文字輸入與 automation 很適合 iPhone。1／高 | 內容保留不等於原始音訊保留；若以 Drafts 作基底，要先決定音訊是否外置及其 backup owner。 |

### Bear

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 原始文字、附件 | Bear Note 原生支援文字與照片、影片、PDF、一般檔案附件；TextBundle 可較好保留附件。1／高 | 官方 help 沒有原生「在 Note 錄音並綁 transcript」流程。 |
| 原始音訊、逐字稿、版本 | x-callback add-file 可把外部音檔附加到 Note，Shortcuts 也能加入檔案；Bear Watch 的 voice dictation 是文字。2／中高 | 外部音訊需先由 Voice Memos 等來源產生；逐字稿需外部轉寫；未找到官方 durable revision history，backup 是快照。完整 bundle 是 3。 |
| 離線、同步、匯出、backup、recovery、ownership | Notes out of box 在本機；Bear Pro 用 Apple CloudKit sync；可 export .txt/.md/.textbundle/.bearnote 等，並可做 .bear2bk backup。1／高 | backup restore 會替換目前 notes（含 trash），不可當成無風險 merge；標題／tags 的 CloudKit 隱私處理與 ADP 要依 Apple 設定。 |
| delete、recovery | Shortcuts／x-callback 可 trash；backup 可回復，但官方 restore 的替換語意要求先做現況副本。1 + 2／高 | 沒有被官方文件證明的逐筆 Recently Deleted 版本時間線或 immutable source history。 |
| AI 結果且不覆寫 | Shortcuts、x-callback、macOS bearcli／MCP 可 search/read/create/append/attach；可把 AI 結果 append 到 Note。2／高 | CLI 是 macOS；雲端 LLM 呼叫與選定 record 的 ID／provenance 仍需 glue。Locked notes 也有工具可讀取限制。 |
| iPhone-first/local-first | 文字／附件收錄適合 iPhone，local copy 存在；同步依 Bear Pro／CloudKit。1／高 | 音訊來源、逐字稿與版本歷史讓它不適合作為零 glue 的完整 record store。 |

### Typeless

| 需求 | 官方證據與分類 | 未解決／實作邊界 |
|---|---|---|
| 文字收錄 | Typeless 在目前聚焦的任意文字欄位插入 dictation 結果。作為輸入層是 1／高。 | 文字被目的 App 保存，不是 Typeless 自己形成 durable record。 |
| 原始音訊、逐字稿、附件、版本 | 官方隱私政策說 voice audio 與有限 context 即時雲端處理、轉寫後丟棄；History 是本機，且可設定保留期，過期會自動刪除。3／高 | 不符合原始音訊持久化，也沒有同一筆 record 的附件／版本／AI result 結構。 |
| 離線、同步、匯出、backup、recovery、ownership | Ask anything 明確需要 internet；官方資料控制／隱私文件強調不保留與不訓練，未找到 durable export、backup、sync 或 recovery 文件。3／中高 | 「零保留」是隱私行為，不是使用者可恢復的備份；資料權屬宣稱也不等於本地權威副本。 |
| AI 結果且不覆寫 | Ask anything 可對選取文字改寫／摘要；iOS Speak to edit 的結果會直接替換選取文字。1（AI 功能）+ 3（本需求）／高 | 若要 non-overwriting writeback，必須先複製來源並由目的 App 保存結果；Typeless 本身沒有官方 durable append／version API。 |
| API／plugin／automation | 官方文件說明 system-level keyboard／accessibility 與文字欄位工作方式；本次未找到 public API、plugin、Shortcuts 或 export contract。3／中 | 不應從可在任何 App 輸入推導出可編排 record pipeline；需要產品方文件或現場驗證才能降低不確定性。 |
| iPhone-first/local-first | iPhone-first 輸入體驗很好；因雲端即時轉寫與受限本機 History，不符合 local-first record。1（capture）+ 3（store）／高 | 可當現有容器的語音輸入 glue，不能當唯一收錄／保存基底。 |

## Issue #16 需求對照

| Issue #16 要求 | 研究結論 |
|---|---|
| 保留原始文字、原始音訊、transcript、attachments、AI result | 六者都要組合。Notes 最接近原生音訊＋transcript＋附件；Obsidian 最接近本地檔案所有權；Drafts 最接近文字 automation；Voice Memos 只強在 source audio；Bear 要外接音訊；Typeless 不適合作為 store。 |
| Offline、sync、export、backup、delete、recovery、data ownership | Obsidian／Drafts 的本地檔案或可讀 backup 證據最完整；Apple 產品的同步／恢復最順但資料權威偏 iCloud；Bear 有可讀 export 與 backup 但 restore 是替換；Typeless 的 zero retention 不能替代 backup。 |
| Shortcuts/API/plugin/script glue | Apple Notes／Voice Memos 以 Shortcuts／Share；Drafts 以 Shortcuts／JavaScript／URL；Bear 以 Shortcuts／x-callback／macOS CLI；Obsidian 以 Plugin API；Typeless 沒有被官方證明的 public automation contract。 |
| selected-record cloud LLM | Notes 有 Use Model 與錄音 summary；Drafts 有官方 AI actions；Obsidian／Bear 可用 plugin／CLI glue；Voice Memos 先轉移到容器；Typeless 是選取文字的即時 AI，不是 selected-record pipeline。 |
| AI result 不覆寫來源 | Notes 的 Append to Note、Drafts 的 Append／new Draft、Obsidian／Bear 的 append 都可做基本 glue。完整不可變來源、模型／時間／輸入快照／重試／恢復不是這些 action 自動保證，屬 local product decision 或 self-build。 |
| iPhone-first/local-first 實用性 | 若優先降低第一天收錄摩擦，先測 Notes；若優先資料可讀、可攜與本地權威，先測 Obsidian；若優先文字 automation，先測 Drafts。這是測試排序，不是最終選型。 |

## Research ledger：question → claim → source → gap → action

| question | claim | source | gap | action |
|---|---|---|---|---|
| Apple Notes 能否在同一收錄流程保存原文、原音、transcript、附件？ | Notes 原生保存文字、附件、音訊；錄音可轉寫、搜尋並 Add Transcript to Note。1／高 | [A1](https://support.apple.com/en-euro/guide/iphone/iphbe11247b5/ios)、[A3](https://support.apple.com/en-euro/guide/icloud/-mm2d069f709/icloud)、[A10](https://support.apple.com/en-au/guide/iphone/iph23f4d9aa9/ios)、[A11](https://support.apple.com/en-mide/guide/notes/apdb5106e334/mac)（2026-08-01） | transcript 加入 Note 後的匯出保真度與穩定 ID 未被文件說明。 | 在 fixture 測 Add Transcript、附件、PDF/Markup export 與刪除恢復。 |
| Apple Notes 的 AI result 能否非覆寫持久保存？ | 可生成 summary、Copy/Share；Shortcuts 有 Append to Note，故基本寫回是 2。 | [A2](https://support.apple.com/en-ie/guide/iphone/iph59143007d/ios)、[A6](https://support.apple.com/en-gb/guide/shortcuts/apdaf74d75a5/ios)、[A7](https://support.apple.com/en-us/125148)（2026-08-01） | 官方沒有保證 summary 自動成 Note 欄位、模型 provenance 或 selected-record routing。 | 用固定 AI 整理標題 append，確認來源音訊／transcript 不變；失敗則列為 3。 |
| Apple Notes 的 local-first lifecycle 是否完整？ | iCloud sync、Recently Deleted、device/iCloud backup 與 ADP 有文件。1／中高 | [A3](https://support.apple.com/en-euro/guide/icloud/-mm2d069f709/icloud)、[A4](https://support.apple.com/en-us/108306)、[A5](https://support.apple.com/en-ie/102651)（2026-08-01） | 沒有完整 raw package export 與個人 Note durable revision history 的明確官方保證。 | 將 Notes 候選的下一個 decision ticket 限定為 export fidelity、版本、backup restore，不擴成全架構。 |
| Voice Memos 能否成為完整記錄單位？ | 原始音訊、iPhone transcript、搜尋、同步、M4A/export、30 天 Recently Deleted recovery 原生。 | [V1](https://support.apple.com/en-mide/guide/iphone/-iph4d2a39a3b/ios)、[V2](https://support.apple.com/en-is/guide/iphone/iph00953a982/ios)、[V3](https://support.apple.com/en-sg/guide/iphone/iph3d6dc359/26/ios/26)、[V4](https://support.apple.com/guide/iphone/edit-or-delete-a-recording-iphc9bdaee83/26/ios/26)（2026-08-01） | 無文字／附件／持久 AI result 的同一容器。 | 把 Voice Memos 定義成 source capture 候選；測 Share to Notes/Files 的關聯與非覆寫 append。 |
| Obsidian 能否 local-first 保存來源與附件？ | Vault 是本地 Markdown；Audio recorder 與 attachments 是一般 Vault 檔案，Sync/File recovery 可恢復。1／高 | [O1](https://obsidian.md/help/data-storage)、[O2](https://obsidian.md/help/Plugins/Audio%2Brecorder)、[O3](https://obsidian.md/help/Editing%2Band%2Bformatting/Attachments)、[O4](https://obsidian.md/help/Obsidian%2BSync/Security%2Band%2Bprivacy)（2026-08-01） | 官方 Audio recorder 沒有 transcript；record schema、衝突、AI provenance 不是內建。 | 在 fixture 建最小 Note＋音檔＋transcript＋AI 區塊，測 iPhone/Mac、Sync、zip restore。 |
| Obsidian 的 AI 是否只是小 glue？ | 官方 Plugin API 可讀寫 Vault；Markdown append 可保留來源。基本流程是 2。 | [O5](https://docs.obsidian.md/Plugins/Getting%20started/Build%20a%20plugin)、[O6](https://github.com/obsidianmd/obsidian-sample-plugin)（2026-08-01） | 離線佇列、雲端 LLM、重試、輸入快照、版本 provenance 需要自建。 | 只做單筆 selected-record proof；若需要可靠 pipeline，再另開 implementation ticket。 |
| Drafts 是否能保留文字、版本與可恢復 backup？ | 原生文字 auto-save、version history、Trash、iCloud sync、JSON export/restore。1／高 | [D1](https://docs.getdrafts.com/gettingstarted/)、[D2](https://docs.getdrafts.com/docs/drafts/versionhistory)、[D3](https://docs.getdrafts.com/docs/settings/sync)、[D4](https://docs.getdrafts.com/docs/settings/backups)（2026-08-01） | 官方沒有證明外部原始音訊會留在同一 Draft。 | 以 Drafts 作文字-first 對照；若音訊仍是硬需求，另測音檔外置關聯與 backup。 |
| Drafts 能否用少量 glue 做 selected-record AI？ | Get/Append/Save Version、JavaScript HTTP、AI actions 與多種模型皆有官方文件。2／高 | [D5](https://docs.getdrafts.com/docs/actions/shortcuts)、[D6](https://docs.getdrafts.com/docs/actions/scripting)、[D7](https://docs.getdrafts.com/docs/actions/ai)（2026-08-01） | 雲端 LLM privacy、音檔保存、輸入快照仍需 local policy／測試。 | 以 UUID 取 Draft、append AI result、Save Draft Version，驗證來源不變。 |
| Bear 能否作文字＋附件容器？ | Bear 原生文字與一般附件；TextBundle 與 .bear2bk 支援可讀 export／backup。1／高 | [B1](https://bear.app/faq/working-with-photos-gifs-pdfs-and-other-attachments/)、[B2](https://bear.app/faq/export-your-notes/)、[B3](https://bear.app/faq/backup-restore/)（2026-08-01） | 沒有官方原生錄音／transcript；restore 是整體替換；revision history 未明確文件化。 | 只將 Bear 排在「附件／可攜 export」對照組；測外部音檔 add-file 與恢復前備份。 |
| Bear 的 automation 能否非覆寫寫回？ | Shortcuts、x-callback、macOS bearcli/MCP 能讀、建立、append、attach；基本流程是 2。 | [B4](https://bear.app/faq/how-to-use-siri-shortcuts-with-bear/)、[B5](https://bear.app/faq/x-callback-url-scheme-documentation/)、[B6](https://bear.app/faq/command-line-interface/)（2026-08-01） | CLI 是 macOS；cloud LLM、locked notes、provenance 與可靠重試需另做。 | 只做單筆 append fixture，不把 CLI 存在推成跨平台 pipeline。 |
| Typeless 是否能保存完整記錄？ | 它是聚焦欄位的 dictation；雲端語音即時處理後丟棄，History 本機且可過期刪除。 | [T1](https://www.typeless.com/help/quickstart/first-dictation)、[T2](https://www.typeless.com/privacy)、[T3](https://www.typeless.com/help/troubleshooting/missing-transcript)（2026-08-01） | 沒有原始音訊、長期 transcript、附件、版本、backup/export/recovery 的 official contract。 | 僅視為既有容器的語音輸入 glue；不列為 record store 候選。 |
| Typeless 能否滿足 non-overwriting AI writeback？ | Ask anything／Speak to edit 可即時改寫，官方 iOS 文件描述選取內容會被替換。1（AI）但 3（本需求）。 | [T4](https://www.typeless.com/ask-anything)、[T5](https://www.typeless.com/help/release-notes/ios/speak-to-edit)（2026-08-01） | 沒有官方 durable append、版本或 public automation API。 | 若使用，只先把原文存到目的 App，再把結果另存；不要把 Typeless History 當 backup。 |
| 哪些產品原生具備「來源不覆寫」的版本／append 機制？ | Voice Memos 可 Save as New；Obsidian 可檔案／Sync recovery；Drafts 有版本與 append；Notes/Bear 的基本 append 需 Shortcuts／x-callback。 | [V4](https://support.apple.com/guide/iphone/edit-or-delete-a-recording-iphc9bdaee83/26/ios/26)、[O4](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory)、[D2](https://docs.getdrafts.com/docs/drafts/versionhistory)、[B5](https://bear.app/faq/x-callback-url-scheme-documentation/)（2026-08-01） | 只有 Drafts／Obsidian 的官方文件較直接描述歷史；都未替跨來源 record 定義 provenance。 | 把「source never overwritten」列成 fixture assertion，而不是假設任何 append 都足夠。 |
| 哪個下一步最能降低不確定性？ | Notes、Obsidian、Drafts 分別代表低摩擦收錄、本地所有權、文字 automation；文件證據不足以單獨定案。 | 本文件全部產品來源，見下表（2026-08-01） | 未測 iPhone 實際離線、同步延遲、附件匯出、恢復與 Shortcuts 權限。 | 開一個 bounded fit test／decision ticket；完成後才決定是否進入實作。 |

## 建議的下一動邊界

只做一張小型 fit-test／decision ticket，範圍如下：

1. 固定一個測試記錄：原始文字、約一段原始音訊、官方或外部產生的 transcript、一個附件、一次 AI result。
2. 只比較 Apple Notes、Obsidian、Drafts；Voice Memos 作為音訊 source control，Bear 作為附件／export 對照，Typeless 不列為 store。
3. 驗收四件事：iPhone 離線能否先收錄、來源是否保持不變、AI 結果能否 append 到同一記錄、匯出後能否在另一位置恢復並讀出所有必需組件。
4. 將「通過／不通過」與實際版本、OS、權限、步驟、輸出檔列入下一張 decision ticket；不要在這張研究文件裡先決定 schema、同步供應商或 LLM 供應商。

### 尚未能由官方來源確認的共同問題

- Apple Notes 的完整 raw record package export、個人 Note 的 durable revision history，以及 Shortcuts 是否能無人工步驟取得同一錄音的全部元件。
- Apple Voice Memos transcript 在 export／backup 中的可攜格式，以及跨裝置 sync 失敗時的衝突語意。
- Obsidian／Bear／Drafts 的音檔、外部附件與相關 metadata 是否完整進入各自 backup／version history；文件描述範圍不完全相同。
- Bear 的官方逐筆歷史恢復能力，以及不同平台的 CLI／MCP 可用範圍。
- Typeless 的 public API／plugin／export／offline contract；本次找到的官方文件支持輸入與隱私行為，不支持 durable record workflow。
- 所有產品的目前 OS、地區、語言、方案與 AI feature flags；Apple Intelligence、CloudKit、Sync 版本期限和第三方 LLM privacy 都要在 fixture 中重新確認。

## 官方來源索引（均於 2026-08-01 查閱）

### Apple Notes / Shortcuts / iCloud

- A1 — [Record and transcribe audio in Notes on iPhone](https://support.apple.com/en-euro/guide/iphone/iphbe11247b5/ios)
- A2 — [Use Apple Intelligence in Notes on iPhone](https://support.apple.com/en-ie/guide/iphone/iph59143007d/ios)
- A3 — [Use Notes with iCloud](https://support.apple.com/en-euro/guide/icloud/-mm2d069f709/icloud)
- A4 — [Archive or make copies of the information you store in iCloud](https://support.apple.com/en-us/108306)
- A5 — [iCloud data security overview](https://support.apple.com/en-ie/102651)
- A6 — [Append to Note in Shortcuts](https://support.apple.com/en-gb/guide/shortcuts/apdaf74d75a5/ios)
- A7 — [What’s new in Shortcuts](https://support.apple.com/en-us/125148)
- A8 — [Export or print notes on iPhone](https://support.apple.com/en-euro/guide/iphone/iphdf551cfa2/ios)
- A9 — [Delete and recover notes on iPhone](https://support.apple.com/en-gb/guide/iphone/iph904eee369/ios)
- A10 — [Add photos, video, and more to notes on iPhone](https://support.apple.com/en-au/guide/iphone/iph23f4d9aa9/ios)
- A11 — [Record and transcribe audio in Notes on Mac](https://support.apple.com/en-mide/guide/notes/apdb5106e334/mac)

### Apple Voice Memos

- V1 — [Record in Voice Memos on iPhone](https://support.apple.com/en-mide/guide/iphone/-iph4d2a39a3b/ios)
- V2 — [View a transcription of a recording on iPhone](https://support.apple.com/en-is/guide/iphone/iph00953a982/ios)
- V3 — [Share a recording in Voice Memos on iPhone](https://support.apple.com/en-sg/guide/iphone/iph3d6dc359/26/ios/26)
- V4 — [Edit or delete a recording in Voice Memos on iPhone](https://support.apple.com/guide/iphone/edit-or-delete-a-recording-iphc9bdaee83/26/ios/26)
- V5 — [See your recordings on all your Apple devices](https://support.apple.com/en-ca/guide/iphone/iph38b91c7af/ios)
- V6 — [View a transcription of a recording on Mac](https://support.apple.com/guide/voice-memos/view-a-transcription-of-a-recording-vm4a03609f0d/mac)

### Obsidian

- O1 — [How Obsidian stores data](https://obsidian.md/help/data-storage)
- O2 — [Audio recorder](https://obsidian.md/help/Plugins/Audio%2Brecorder)
- O3 — [Attachments](https://obsidian.md/help/Editing%2Band%2Bformatting/Attachments)
- O4 — [Sync security and privacy](https://obsidian.md/help/Obsidian%2BSync/Security%2Band%2Bprivacy)
- O5 — [Sync version history](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory)
- O6 — [Build a plugin](https://docs.obsidian.md/Plugins/Getting%20started/Build%20a%20plugin)
- O7 — [Official sample plugin repository](https://github.com/obsidianmd/obsidian-sample-plugin)

### Drafts

- D1 — [Getting started](https://docs.getdrafts.com/gettingstarted/)
- D2 — [Version history](https://docs.getdrafts.com/docs/drafts/versionhistory)
- D3 — [Sync](https://docs.getdrafts.com/docs/settings/sync)
- D4 — [Backups](https://docs.getdrafts.com/docs/settings/backups)
- D5 — [Shortcuts actions](https://docs.getdrafts.com/docs/actions/shortcuts)
- D6 — [Scripting](https://docs.getdrafts.com/docs/actions/scripting)
- D7 — [AI actions](https://docs.getdrafts.com/docs/actions/ai)
- D8 — [Transcription](https://docs.getdrafts.com/docs/editor/transcription.html)

### Bear

- B1 — [Working with photos, GIFs, PDFs and other attachments](https://bear.app/faq/working-with-photos-gifs-pdfs-and-other-attachments/)
- B2 — [Export your notes](https://bear.app/faq/export-your-notes/)
- B3 — [Backup and restore](https://bear.app/faq/backup-restore/)
- B4 — [Syncing and privacy](https://bear.app/faq/syncing-privacy/)
- B5 — [Siri Shortcuts](https://bear.app/faq/how-to-use-siri-shortcuts-with-bear/)
- B6 — [x-callback-url scheme documentation](https://bear.app/faq/x-callback-url-scheme-documentation/)
- B7 — [Command-line interface](https://bear.app/faq/command-line-interface/)
- B8 — [Bear for Apple Watch](https://bear.app/faq/bear-for-apple-watch-overview/)
- B9 — [Bear is GDPR compliant](https://bear.app/faq/bear-is-gdpr-compliant/)

### Typeless

- T1 — [First dictation](https://www.typeless.com/help/quickstart/first-dictation)
- T2 — [Privacy](https://www.typeless.com/privacy)
- T3 — [Missing transcript / History](https://www.typeless.com/help/troubleshooting/missing-transcript)
- T4 — [Ask anything](https://www.typeless.com/ask-anything)
- T5 — [iOS Speak to edit](https://www.typeless.com/help/release-notes/ios/speak-to-edit)
- T6 — [iOS release notes](https://www.typeless.com/help/release-notes/ios)

## 與本 repo 產品邊界的關係

本文件沿用 repo 既有語意：來源文字／音訊是權威來源；transcript 是來源音訊的文字表示，不取代音訊；AI 整理結果另存且不覆蓋來源；收錄與整理可以分開。這些是本 repo 的產品邊界，不是上述產品官方承諾的共同資料模型。

研究結果只回答「既有產品現在明確提供什麼，以及接線成本在哪裡」。最終是否選 Apple Notes、Obsidian、Drafts，或自建 record layer，仍要由下一個有實測證據的 decision ticket 決定。
