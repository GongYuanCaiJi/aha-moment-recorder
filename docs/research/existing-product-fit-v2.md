# 既有產品能力與個人工作方式適配研究 v2

- 對應 Issue：[#16 重新研究既有產品能力與個人工作方式適配](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/16)
- 研究日期：2026-08-01
- 研究範圍：Apple Notes、Apple Voice Memos、Apple Journal、Obsidian、Drafts、Bear、Typeless
- 研究方法：只採用產品官方網站、官方支援文件、官方 API／自動化文件、官方匯出／同步／隱私說明或官方產品文件；未使用 `agent-reach`，也未以部落格或二手評論作關鍵證據。
- 詞彙基準：依 repo 根目錄的 `CONTEXT.md`。下文的「記錄」是可同時呈現來源內容、逐字稿與 AI 整理稿的最小內容單位；「來源內容」永遠是權威，後續整理不得覆寫它。

## 研究結論：先講答案

沒有一個現成產品同時滿足這個 repo 要的完整邊界：iPhone／Mac 低摩擦收錄、原始文字／錄音／逐字稿／附件在同一邏輯記錄、可追蹤的記錄版本、只選定記錄交給 LLM、結果寫回同一記錄但不覆寫來源、而且資料由使用者掌握並可驗證地備份與恢復。

最實際的選擇分成三層：

1. **若目前只需要低摩擦收錄**：`Apple Journal` 最接近「一個原生入口就是一個多媒體記錄」；它在 iPhone／Mac 的記錄都能放文字、錄音、逐字稿與多媒體。`Apple Notes` 的一般筆記、附件、匯出與 Apple Intelligence 整理較成熟，適合把「收錄」和「基本整理」放在同一個 note，但它沒有被官方文件證明的穩定記錄版本或選定記錄 API。
2. **若要以既有產品為底，加最少可控 glue**：`Obsidian` 最適合作為 canonical store（權威資料庫）：資料是本機普通文字與附件，離線可用，有官方 URI、CLI、plugin API、同步版本歷史，能把單一檔案交給 LLM，再把結果 append 到獨立區塊。代價是「一筆記錄」的 schema、錄音逐字稿與不可覆寫規則要由我們定義。
3. **若要現成的選定記錄 LLM 介面**：`Bear` 的 Mac `bearcli`／MCP server 已提供搜尋、讀取、建立、編輯、append、tag、attach、archive、trash，且可用 tag 限定範圍；它很適合做少量 glue 的 selected-record pipeline。但官方資料沒有證明它原生保留「錄音來源＋逐字稿」及 per-note version history，因此不能把它直接當完整個人記錄系統。

不可由既有產品補齊、需要自建的核心缺口是：**跨入口的穩定 `record_id`、來源內容的不可變保存、逐字稿與 AI 整理稿的同記錄關係、處理模式／狀態／重試／版本、以及只選定記錄的可審計 LLM 寫回流程**。Apple 系列偏向封閉 app 內資料，Obsidian 偏向可組合檔案，Drafts 偏向文字 inbox，Bear 偏向 note 與 Mac automation；它們各自只覆蓋一段。

最小 LLM／glue 邊界應該先收斂成：

```text
明確收錄 → 產生 stable record_id → 保存 source（文字或原始音訊）
       → 必要時產生 transcript → 只選定 record_id → 送 source/transcript 給 LLM
       → 將 AI 整理稿寫入同一記錄的獨立區塊或新版本 → 保留 source、prompt、時間與狀態
```

第一階段不應讓 LLM 自動掃描全部資料，也不應讓模型直接 `replace` 來源內容。若選 `Obsidian`，這條邊界可由一個小型 script／plugin 實作；若選 `Bear`，可由 Mac `bearcli`／MCP 加 tag scope 實作；若選 `Apple Journal`／`Notes`，目前只能接受手動選擇、分享／匯出或等待針對目標 OS 的 Shortcuts runtime 驗證。

## 評估標準與證據標記

每個候選都檢查：

- iPhone／Mac 是否有明確收錄入口。
- 原始文字、原始錄音、逐字稿、附件、版本是否能留在同一邏輯記錄。
- 離線、同步、匯出、備份、刪除恢復、資料所有權。
- Shortcuts、URL API、plugin、CLI、script 或其他 glue。
- 能否只處理選定記錄，以及 LLM 結果能否寫回同一處而不覆寫來源。
- 對「快速收錄，稍後整理；保留來源；只挑重要記錄處理」這種工作方式的適配與缺口。

文內標記的意思如下：

- **官方證據**：官方文件直接寫出來的能力。
- **推論**：由官方能力合理推得，但不是官方對完整產品語意的保證。
- **未知**：本次查到的官方資料沒有回答，不能把它當成不存在。
- **需 runtime 驗證**：能力可能受指定 iOS／macOS／app 版本、語言、地區或帳號設定影響。

## 候選比較總表

| 候選 | iPhone／Mac 收錄與同記錄內容 | 離線、同步、所有權、恢復 | Glue／LLM | 個人工作方式適配 | 邊界判斷 |
|---|---|---|---|---|---|
| Apple Journal | 官方支援文字、錄音、錄音逐字稿、照片／影片／繪圖／位置在同一 Journal entry；iPhone／Mac 都有入口 | iCloud 同步；官方明確說 Journal 不在 iCloud backup，Mac 可用 Time Machine，iPhone 可做加密電腦備份與 ZIP 匯出；Recently Deleted 30 天 | 沒有本次證據可證明的 Journal-specific public API 或 selected-entry LLM；可用匯出／分享／通用 Shortcuts 待驗證 | 最像「快速留下完整事件」，但後續選記錄與不覆寫寫回仍缺 | **現成可用（收錄）／少量 glue（整理）** |
| Apple Notes | note 內可放文字、錄音、逐字稿、照片／PDF／其他附件；iPhone／Mac 都可錄音 | iCloud 同步；iCloud.com 可下載附件；Mac／iPhone 可匯出 PDF／Markdown；Recently Deleted 30 天 | Apple Intelligence 可摘要 transcript／選定文字；Shortcuts 的 Notes-specific action 與讀寫契約需驗證；沒有本次證據可證明的 record version API | 收錄與基本整理最順；跨 note 的選定記錄、版本與流程狀態不足 | **現成可用（收錄）／少量 glue（整理）** |
| Apple Voice Memos | iPhone／Mac 錄音；同一 recording 有 transcript；可另存編輯後副本 | iCloud 同步；Recently Deleted，可恢復或永久刪除；可拖放／分享單一 recording | 沒有文字／附件／AI record container；選定 recording 要手動分享或另接 glue | 很適合當錄音入口，不適合當完整記錄 | **現成可用（音訊元件）／必須 glue（完整記錄）** |
| Obsidian | iPhone 有 Quick Action、Share Sheet、URI；Mac 直接編輯 vault；Audio recorder 將音訊存進 vault 並嵌入 active note | 本機 vault 離線可用；官方 Sync 有 E2EE、版本歷史；普通文字、附件與使用者可讀檔案，所有權與移轉性最佳；trash／File recovery 可復原 | 官方 URI、CLI、Vault API；可對指定 path／file read、append、process；LLM 可只讀選定檔案並 append 結果 | 最適合「來源在本機、稍後挑選整理、結果回同一檔但獨立區塊」；需自行定 schema、transcript 與狀態 | **少量 glue（canonical store）／部分必須自建（record semantics）** |
| Drafts | iPhone／Mac 文字 editor、dictation、Share Extension、Mac capture；可匯入音訊／影片並轉錄 | iCloud sync 與 backup；自動 version history；Trash 超過 30 天永久刪除；可 JSON `.draftsExport` 備份／還原 | URL scheme、50+ Shortcuts actions、JavaScript scripting、Actions；selected draft 可依 UUID／current draft 處理並 append 或建立新版本 | 文字 inbox 與版本很強；官方未證明匯入的原始音訊會留在同一 draft | **少量 glue（文字）／必須自建（原始音訊同記錄）** |
| Bear | iPhone／Mac note、附件、分享與 Apple Watch voice dictation 文字；可放音訊檔附件，但未找到原生錄音＋逐字稿同記錄證據 | CloudKit／iCloud sync；`.bear2bk` 包含加密 notes／attachments；Trash 可取回；大於 250 MB 附件不完整同步 | x-callback-url、Shortcuts；Mac `bearcli`／MCP 可搜尋、讀取、append、tag、attach，且可用 tag scope | UI 與 selected-record Mac automation 很好；原始音訊語意與版本仍是缺口 | **少量 glue（selected-record LLM）／必須自建（完整記錄）** |
| Typeless | iPhone keyboard／任何文字欄位；macOS accessibility＋mic，在任何文字欄位插入整理後文字 | 官方隱私政策說音訊／context 即時送雲端處理後丟棄；transcript history 本機且依 Keep History 期限自動刪除；未找到正式 export／backup／sync history | 是語音輸入與即時潤稿層，不是可選記錄的 API；無官方證據可證明 raw audio、永久 transcript 或 write-back record | 最適合降低收錄摩擦；不適合作為來源所有權或記錄保存層 | **現成可用（語音輸入層）／必須 glue（記錄）** |

## 各候選詳細研究

### 1. Apple Journal

#### 能力與適配

- **收錄入口（官方證據）**：iPhone Journal 可新增文字、照片、影片、繪圖、位置與錄音；官方的多媒體說明明確寫出可錄音並產生 transcription，且能把 transcript 加回 entry。Mac Journal 也能新增 recording，並將 transcription 加回 entry。來源：[iPhone 新增 entry](https://support.apple.com/en-mide/guide/iphone/iph0e5ca7dd3/ios)、[iPhone 多媒體與 transcription](https://support.apple.com/en-mide/guide/iphone/iph492ee70a8/ios)、[Mac 多媒體與 transcription](https://support.apple.com/en-gb/guide/journal/devb7625b2b0/mac)。
- **同一邏輯記錄（官方證據）**：文字、原始錄音、逐字稿與附件被描述為同一 Journal entry 的內容；這是本次候選中最接近 repo `記錄` 定義的原生模型。**版本（未知）**：查到的官方文件說新增、編輯、刪除與匯出，沒有說 meaningful change 會留下可查的 immutable record version。
- **同步／備份／所有權（官方證據）**：Apple 說同一 Apple Account 的 iPhone／iPad／Mac 會同步 entries；Mac 文件明確提醒 Journal 不包含在 iCloud backups，Mac 可用 Time Machine，iPhone 可用加密電腦備份。Apple 也提供 `AppleJournalEntries` ZIP 匯出，包含照片、位置與媒體。來源：[Mac 保護 Journal entries](https://support.apple.com/guide/journal/protect-your-journal-entries-dev90dd74024/mac)、[Apple Journal backup/export 說明](https://support.apple.com/en-ie/121822)。
- **刪除恢復（官方證據）**：Mac 的 Recently Deleted 可在 30 天內復原，之後永久刪除。來源：[Mac 刪除與恢復](https://support.apple.com/en-gb/guide/journal/dev7c1z9b800/mac)。
- **離線（未知／需 runtime 驗證）**：官方資料證明 app 有本機使用介面，但本次沒有找到 Journal 對「無網路新增、稍後同步」的明確承諾；不可把 iCloud 同步等同於離線 acceptance。
- **Shortcuts／LLM（未知）**：Apple Shortcuts 官方文件只說某 app 提供的 actions 會出現在 action list；本次未找到 Journal-specific public read／write／selected-entry API。Apple 的通用 Shortcuts 入口：[瀏覽 action list](https://support.apple.com/guide/shortcuts/navigate-the-action-list-apdc33e4f4da/ios)。可用 PDF／ZIP export 或分享交給外部 glue，但這是推論，不是 Journal 的正式 LLM contract。
- **個人工作方式**：最適合「當下快速留下文字＋聲音＋脈絡」，也最少需要自己先設計資料結構。缺口是後續只挑某一筆 `記錄`、保存 processing mode／status、將 AI 整理稿安全寫回同一 entry 並保留來源，均未被官方文件覆蓋。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| iPhone／Mac 能否在同一處收錄文字、錄音、逐字稿、附件？ | **官方證據**：Journal entry 支援文字、錄音、transcription 及照片等多媒體，iPhone／Mac 都有入口。 | [iPhone multimedia](https://support.apple.com/en-mide/guide/iphone/iph492ee70a8/ios)；[Mac multimedia](https://support.apple.com/en-gb/guide/journal/devb7625b2b0/mac) | 尚未證明所有語言／裝置組合都產生 transcript。 | 以目標 iPhone／Mac、語言做一次實機 acceptance；若只要收錄，可先列為候選。 |
| 資料能否離線同步、備份、匯出、恢復並由使用者掌握？ | **官方證據**：iCloud sync、ZIP export、Mac Time Machine、加密電腦 backup、30 天 Recently Deleted；但 Journal 不在 iCloud backup。 | [Protect entries](https://support.apple.com/guide/journal/protect-your-journal-entries-dev90dd74024/mac)；[Apple Journal backup](https://support.apple.com/en-ie/121822)；[Recover](https://support.apple.com/en-gb/guide/journal/dev7c1z9b800/mac) | 離線行為與匯出後再匯入／選定單筆的 round-trip 尚未證明。 | 把 ZIP／Time Machine／加密 backup／restore drill 放入候選驗證，不以「有 iCloud」作完成證據。 |
| 能否只選定記錄送 LLM，再寫回不覆寫來源？ | **未知**：官方文件沒有找到 Journal-specific API、record_id、版本或 append-only AI 欄位。 | [Shortcuts action list](https://support.apple.com/guide/shortcuts/navigate-the-action-list-apdc33e4f4da/ios)；[Export entries](https://support.apple.com/guide/iphone/print-and-export-entries-iph4cad323fe/ios) | 只能先假設手動分享／匯出；無法聲稱少量 glue 已足夠。 | 若選 Journal，先建小型 export／manual-selected proof；若要可靠自動化，將 record model 與 orchestration 列為自建。 |

### 2. Apple Notes

#### 能力與適配

- **收錄入口（官方證據）**：iPhone 在 note 中可錄音，並產生 transcript；Mac 可直接在 note 內錄音，note body 同時可放 comments、checklists、documents。可搜尋／複製 transcript，也可把 transcript 加回 note。來源：[iPhone record and transcribe](https://support.apple.com/guide/iphone/record-and-transcribe-audio-iphbe11247b5/ios)、[Mac record and transcribe](https://support.apple.com/en-mide/guide/notes/apdb5106e334/mac)。
- **同一邏輯記錄（官方證據）**：文字、錄音、transcript、圖片／PDF／其他附件都可作為一個 note 的內容。**版本（未知）**：本次查到的 Notes 官方文件未提供 per-note immutable version history 或把 AI rerun 記成新版本的契約。
- **同步／匯出／恢復（官方證據）**：iCloud Notes 可在 iPhone、iPad、Mac、iCloud.com 同步；iCloud.com 可以搜尋、下載 attachments、刪除並從 Recently Deleted 在 30 天內復原。Mac／iPhone 可匯出 PDF／Markdown。來源：[iCloud Notes overview](https://support.apple.com/guide/icloud/notes-on-icloudcom-overview-mm6704cac5/icloud)、[iCloud sync](https://support.apple.com/en-gb/guide/icloud/-mm8685520792/icloud)、[Mac export](https://support.apple.com/en-gb/guide/notes/not201900c07/mac)、[iCloud recover](https://support.apple.com/en-au/guide/icloud/-mm2f42f05cb9/icloud)。
- **內建整理（官方證據）**：Apple Intelligence 能摘要 audio transcript；Writing Tools 能對選定文字摘要、列 key points、改成 list／table，但也提供 Replace original，這正是不能直接套到來源內容的風險。來源：[Notes Apple Intelligence](https://support.apple.com/guide/iphone/use-apple-intelligence-in-notes-iph59143007d/ios)、[Writing Tools](https://support.apple.com/en-euro/guide/iphone/iph6f08da1d2/ios)。
- **離線／所有權**：本機 app 可操作是合理推論；官方同步說明沒有給出本專案要的離線 queue、local-authoritative contract。資料主要留在 Apple Notes／iCloud 帳號中，雖可匯出 Markdown／PDF／附件，但 schema、版本與批次 selected-record 仍由 Apple 控制。
- **Shortcuts／LLM**：官方 Shortcuts 文件只描述通用 action list；本次未取得 Notes-specific 可依 `record_id` 讀寫 note 的正式 API 證據。Apple Intelligence 可處理目前 note／選定文字，但不是本專案所需的可追蹤、可重跑、結果獨立保存的通用整理 pipeline。
- **個人工作方式**：比 Journal 更像可長期整理的 notebook；收錄非常好，基本摘要也現成。缺口集中在「選定記錄」、「版本／狀態」、「來源與 AI 整理稿的可程式化關係」。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| 一個 note 是否能保留來源文字、原始錄音、transcript、附件？ | **官方證據**：錄音與 transcript 可留在 note，note 也能容納 documents／photos／PDF 等附件。 | [iPhone audio](https://support.apple.com/guide/iphone/record-and-transcribe-audio-iphbe11247b5/ios)；[Mac audio](https://support.apple.com/en-mide/guide/notes/apdb5106e334/mac)；[Attachments](https://support.apple.com/en-euro/guide/notes/apd9953dabf9/mac) | 尚未證明修改／AI rerun 形成 repo 定義的記錄版本。 | 收錄 proof 可用 Notes；把版本與 AI block 視為外加自建資料，不依賴 note UI。 |
| 能否同步、匯出、下載附件、刪除後恢復？ | **官方證據**：iCloud sync、iCloud.com attachment download、PDF／Markdown export、Recently Deleted 30 天。 | [iCloud overview](https://support.apple.com/guide/icloud/notes-on-icloudcom-overview-mm6704cac5/icloud)；[Download attachments](https://support.apple.com/en-ie/guide/icloud/mm198698c442/icloud)；[Export](https://support.apple.com/en-gb/guide/notes/not201900c07/mac)；[Recover](https://support.apple.com/en-au/guide/icloud/-mm2f42f05cb9/icloud) | 多頁附件的 PDF export 有官方限制；沒有完整 record round-trip／local-authoritative 證據。 | 做 note＋audio＋attachment 的 export／restore drill；明確記錄格式限制。 |
| 能否只對選定 note 做 LLM 整理並安全寫回？ | **官方證據**：Apple Intelligence 能摘要 transcript／選定文字；**未知**：Notes-specific public API 與 selected note append contract。 | [Apple Intelligence](https://support.apple.com/guide/iphone/use-apple-intelligence-in-notes-iph59143007d/ios)；[Shortcuts actions](https://support.apple.com/guide/shortcuts/navigate-the-action-list-apdc33e4f4da/ios) | Writing Tools 可 Replace original，容易破壞來源；無 processing status／retry／版本。 | 若用內建 AI，只能當人工整理輔助；正式 pipeline 仍需 export／glue／自建 record state。 |

### 3. Apple Voice Memos

#### 能力與適配

- **收錄與 transcript（官方證據）**：iPhone 可錄音、編輯並在支援裝置／語言產生 transcript；Mac（macOS 15+、Apple silicon）可查看／複製 transcript。iCloud 可讓同一 Apple Account 的 Apple 裝置看到 recordings。來源：[iPhone recording](https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/ios)、[iPhone transcript](https://support.apple.com/en-gb/guide/iphone/iph00953a982/ios)、[Mac transcript](https://support.apple.com/guide/voice-memos/view-a-transcription-of-a-recording-vm4a03609f0d/mac)、[sync](https://support.apple.com/guide/voice-memos/see-your-recordings-on-all-your-apple-devices-vma6cc4d0571/mac)。
- **來源與版本（官方證據）**：編輯後可儲存為 new recording，保留原件；這是有利於來源不覆寫的產品語意。**但** recording 不是文字／附件／AI 整理稿的一般 record container，沒有本次證據證明可將外部 AI 結果寫回同一 recording。
- **刪除恢復（官方證據）**：Recently Deleted 可復原；永久刪除會從所有裝置移除。保存期限可在設定中調整。來源：[Edit／delete／recover](https://support.apple.com/guide/iphone/edit-or-delete-a-recording-iphc9bdaee83/26/ios/26)、[Mac delete](https://support.apple.com/en-mide/guide/voice-memos/vmc3c0776462/mac)、[settings](https://support.apple.com/guide/voice-memos/change-voice-memos-settings-vm0ba246ff3e/3.2/mac/26)。
- **匯出／glue**：官方支援分享單一 recording、拖到 Finder、email 或 note。這能做「選定一筆 → 外部處理」的人工邊界，但本次未找到 Voice Memos 的 public record API、選定項目 ID 或批次 write-back 契約。
- **個人工作方式**：如果使用者當下只想說話，Voice Memos 是可靠的 capture component；但後續一定要把音訊／transcript 帶入另一個 record container，否則不能滿足「原始資料與 AI 整理稿在同一記錄」。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| iPhone／Mac 是否能收錄原始音訊與 transcript？ | **官方證據**：兩端可錄音；支援裝置可查看／複製 transcript。 | [iPhone transcript](https://support.apple.com/en-gb/guide/iphone/iph00953a982/ios)；[Mac transcript](https://support.apple.com/guide/voice-memos/view-a-transcription-of-a-recording-vm4a03609f0d/mac) | transcript 受裝置、OS、語言限制；未證明可保存 transcript 的版本。 | 對目標裝置／語言做實機 transcription test；不把 Voice Memos 當完整 record store。 |
| 是否保留來源、同步、恢復？ | **官方證據**：Save as New 保留原始 recording；iCloud sync；Recently Deleted 可恢復。 | [Make recording](https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/ios)；[Sync](https://support.apple.com/guide/voice-memos/see-your-recordings-on-all-your-apple-devices-vma6cc4d0571/mac)；[Delete](https://support.apple.com/en-mide/guide/voice-memos/vmc3c0776462/mac) | 同步、備份與 exported recording 的完整 restore drill 仍需由本專案驗證。 | 將原始音訊 export 成為後續 record 的 immutable source；明確保存來源檔與來源 app identifier。 |
| 能否只選一筆送 LLM 並寫回同一處？ | **官方證據**：可分享／拖放單一 recording；**未知**：selected recording API 與 write-back。 | [Share recording](https://support.apple.com/guide/voice-memos/share-a-recording-vm05f9fa82d4/3.2/mac/26) | 沒有文字／附件／AI 欄位；write-back 只能依賴外部 note／vault。 | 只把 Voice Memos 當入口；由 glue 建立 record_id 並把 audio/transcript 搬到 canonical store。 |

### 4. Obsidian

#### 能力與適配

- **收錄入口（官方證據）**：Obsidian iOS 有 widgets／Quick Action；Shortcuts 可 Open、Create、Daily、Capture to Daily Note、Bookmark；iOS Share Sheet 可送到新 note、daily note、既有 note。Mac 直接操作 local vault。來源：[Obsidian mobile](https://obsidian.md/help/mobile)、[Obsidian iOS](https://obsidian.md/help/ios)。
- **原始文字與附件（官方證據）**：note 是 plain text；圖片、音訊、PDF 等是 vault attachments，能嵌入 note。核心 Audio recorder 會把錄音存進 vault 並嵌入 active note。來源：[Create notes](https://obsidian.md/help/create-note)、[Attachments](https://obsidian.md/help/attachments)、[Audio recorder](https://obsidian.md/help/Plugins/Audio%2Brecorder)。
- **逐字稿（未知）**：本次官方核心 plugin 文件只證明錄音保存與嵌入，沒有證明 Audio recorder 會原生產生 transcript。因此要把 transcript 留在同一記錄，必須由外部 transcription glue 或使用者貼入。
- **離線／同步／版本（官方證據）**：local vault 完整離線可用，斷線時變更排隊，重新連線再同步。Obsidian Sync 有版本歷史、刪除／改名復原與 E2EE；Sync 版本保存期限依方案，附件舊版本另有期限。官方也有 File recovery plugin 可保存本機歷史。來源：[Local and remote vaults](https://obsidian.md/help/Obsidian%20Sync/Local%20and%20remote%20vaults)、[Sync version history](https://obsidian.md/help/sync/version-history)、[Sync security](https://obsidian.md/help/Obsidian%20Sync/Security%20and%20privacy)。
- **資料所有權（官方證據／推論）**：plain Markdown 與附件在 local vault，能直接複製、檢查、遷移，不被專有資料庫鎖住。若啟用 E2EE Sync，Obsidian 不能讀內容；忘記加密密碼不可恢復，這是使用者自己承擔的 ownership／recovery trade-off。
- **Glue／LLM（官方證據）**：Obsidian URI 有 `open`、`new`、`append`、`prepend`、`content`、`search` 等操作；CLI 有 `read`、`append`、`create`、`diff` 等；Vault API 有 `read`、`modify`、`process`，其中 `process` 適合安全的 read-modify-write。來源：[URI](https://obsidian.md/help/uri)、[CLI](https://obsidian.md/help/cli)、[Vault API](https://docs.obsidian.md/Plugins/Vault)。這足以讓 glue 只讀指定 path／record_id，再將 `AI 整理稿` append，而不是覆蓋 `來源內容`。
- **個人工作方式**：它最符合「本機權威、快速 capture、稍後只選定記錄、結果回同一檔」；但它不是現成的個人記錄系統。需要明確 frontmatter／body schema、stable `record_id`、source block、transcript block、AI result block、處理狀態與備份／restore drill。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| iPhone／Mac 是否能低摩擦收錄文字與音訊？ | **官方證據**：iOS Quick Action／Share Sheet／Shortcuts 可 create／capture／append；Audio recorder 將音訊存 vault 並嵌入 active note；Mac 直接操作 vault。 | [iOS](https://obsidian.md/help/ios)；[Audio recorder](https://obsidian.md/help/Plugins/Audio%2Brecorder) | 核心 Audio recorder 未證明有 transcript；同一邏輯記錄要靠 schema。 | 先定義 `source`／`transcript`／`ai` block，再做一條 iPhone capture → Mac verify 的 proof。 |
| 來源是否可離線、同步、版本化、匯出與恢復？ | **官方證據**：local vault offline；Sync 有 E2EE、version history、deleted／renamed restore；檔案本身是 plain text。 | [Offline Sync](https://obsidian.md/help/Obsidian%20Sync/Local%20and%20remote%20vaults)；[Version history](https://obsidian.md/help/sync/version-history)；[Security](https://obsidian.md/help/Obsidian%20Sync/Security%20and%20privacy) | Sync retention、加密密碼遺失、附件版本期限要納入實際 restore／ownership policy。 | 執行選定記錄的 local copy、Sync restore、刪除／復原與人工讀取測試；local vault 作 canonical source。 |
| 能否只選定記錄交給 LLM 並安全寫回？ | **官方證據**：URI／CLI／Vault API 支援指定檔案 read、append、process；這是候選中最清楚的 selected-record glue contract。 | [CLI](https://obsidian.md/help/cli)；[URI](https://obsidian.md/help/uri)；[Vault API](https://docs.obsidian.md/Plugins/Vault) | transcript、record_id、processing status、LLM audit trail 仍不是 Obsidian 原生語意。 | 做最小 script：只接受明確 `record_id`，read source/transcript，append AI block；拒絕 source replacement；狀態寫 sidecar 或 metadata。 |

### 5. Drafts

#### 能力與適配

- **收錄入口（官方證據）**：Drafts 在 iPhone／iPad／Mac／Apple Watch 可用，開啟就是 editor；支援 iOS Share Extension、Mac capture、dictation、URL schemes、Shortcuts 與 actions。來源：[Getting started](https://docs.getdrafts.com/gettingstarted/)、[Share extension](https://docs.getdrafts.com/docs/extensions/share)。
- **文字與版本（官方證據）**：Drafts 有 Inbox／Archive／Trash，自動 version history 可檢視、比較與 restore；這對「先收錄、後整理、不能毀掉來源」很有價值。來源：[Version history](https://docs.getdrafts.com/docs/drafts/versionhistory)、[Draft management](https://docs.getdrafts.com/drafts/)。
- **音訊與逐字稿（官方證據／未知）**：官方 transcribe 文件說 iOS 可從 Voice Memos／Files 分享 audio/video，Mac 可拖放／匯入，系統會擷取音訊並轉錄。**未知**：本次文件沒有證明原始 audio 會作為附件保留在同一 draft；因此不能把 Drafts transcription 等同於 repo 的「來源錄音＋逐字稿同記錄」。來源：[Transcription](https://docs.getdrafts.com/docs/editor/transcription.html)。
- **同步／備份／恢復（官方證據）**：iCloud sync 包含 drafts、version history、actions、logs、workspaces、settings；可匯出 JSON `.draftsExport` 並還原。Trash 超過 30 天永久刪除。來源：[Sync](https://docs.getdrafts.com/docs/settings/sync)、[Backups](https://docs.getdrafts.com/docs/settings/backups)。
- **Glue／LLM（官方證據）**：URL scheme 可用 UUID／current draft 做 `get`、`append`、`prepend`、`replaceRange`、`search`、`runAction`；scripting 有完整 JavaScript runtime。只要 pipeline 選擇 append 或建立新 version，就能保留 source；不能無條件使用 `replaceRange`。來源：[URL schemes](https://docs.getdrafts.com/docs/automation/urlschemes)、[Scripting](https://docs.getdrafts.com/docs/actions/scripting)、[Actions](https://docs.getdrafts.com/actions/)。
- **個人工作方式**：對文字 capture 與版本安全極好，對語音輸入也方便；但原始 audio 是否長期留在同一 draft 是不可補的現成能力不確定，需自建附件保存或改用 Voice Memos／Obsidian／Notes 作 source store。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| iPhone／Mac 是否能快速收錄文字、dictation 與匯入語音？ | **官方證據**：兩端 editor、Share Extension、dictation、Mac capture；可匯入 audio/video 做 transcription。 | [Getting started](https://docs.getdrafts.com/gettingstarted/)；[Dictation](https://docs.getdrafts.com/docs/editor/dictation)；[Transcription](https://docs.getdrafts.com/docs/editor/transcription.html) | 原始 audio 是否仍附在 draft 未證明；dictation／transcription 的離線保證也不完整。 | 把 Drafts 定位為文字 inbox；若要保留 audio，先在 source app 保存再匯入 draft。 |
| 是否有版本、同步、備份與恢復？ | **官方證據**：automatic version history、iCloud sync、JSON export／restore、Trash。 | [Version history](https://docs.getdrafts.com/docs/drafts/versionhistory)；[Sync](https://docs.getdrafts.com/docs/settings/sync)；[Backups](https://docs.getdrafts.com/docs/settings/backups) | JSON restore 會影響整體資料，需驗證單筆復原與版本保真。 | 做單筆 draft version／JSON export／restore drill；記錄 Trash 30 天 policy。 |
| 能否只選定 draft 送 LLM 並寫回不覆寫？ | **官方證據**：UUID/current draft URL scheme、append/prepend、JavaScript scripting、actions；**推論**：可組成 selected-record pipeline。 | [URL schemes](https://docs.getdrafts.com/docs/automation/urlschemes)；[Scripting](https://docs.getdrafts.com/docs/actions/scripting) | 沒有 repo-level `record_id`、AI result schema 或跨 source audio identity。 | 只用 append／新 version；將 prompt、model、時間與結果放在可分隔區塊，不用 replace source。 |

### 6. Bear

#### 能力與適配

- **收錄與附件（官方證據）**：Bear iPhone／Mac note 可插入任何檔案；iPhone 可使用 camera／attachments，Mac 可 drag-and-drop；支援 video、PDF、scan 等。官方 Apple Watch 文件支援 voice dictation 建立／append **文字** note。來源：[Insert attachments](https://bear.app/faq/insert-attachments/)、[Photos／videos／PDFs](https://bear.app/faq/working-with-photos-gifs-pdfs-and-other-attachments/)、[Apple Watch](https://bear.app/faq/bear-for-apple-watch-overview/)。
- **原始音訊與逐字稿（未知／缺口）**：本次官方文件沒有找到 Bear iPhone／Mac 原生 audio recorder＋transcript 存入同一 note 的說明；可附加音訊檔，不代表 Bear 會產生並維護 transcript。也沒有找到官方 per-note version history 說明，故版本標為未知，不宣稱不存在。
- **同步／備份／所有權（官方證據）**：Bear Pro 以 CloudKit／iCloud sync notes、edits、attachments；`.bear2bk` backup 包含加密 notes／attachments，能在 iOS／Mac restore；官方說備份 restore 會取代目前全部 notes（含 Trash），所以必須先做獨立 backup。Trash 是最後取回機會；附件大於 250 MB 不同步。來源：[Sync](https://bear.app/faq/sync-troubleshooting/)、[Syncing privacy](https://bear.app/faq/syncing-privacy/)、[Backup／restore](https://bear.app/faq/backup-restore/)、[Trash/sidebar](https://bear.app/faq/about-the-sidebar/)。
- **Glue／LLM（官方證據）**：x-callback-url 可依 note ID／搜尋結果 open、add text、append／prepend、search；官方 Bear Mac CLI 文件現在也描述 `bearcli`、Claude Connector、MCP server，可搜尋／讀取／建立／編輯／append／tag／attach／archive／trash，並可用 `Only tags`／`Exclude tags` scope。加密 notes 不能由 CLI／MCP 讀寫。來源：[x-callback-url](https://bear.app/faq/x-callback-url-scheme-documentation/)、[Command-line interface](https://bear.app/faq/command-line-interface/)、[Bear Shortcuts](https://blog.bear.app/2022/03/automate-your-notes-with-shortcuts-and-bear/)。
- **個人工作方式**：如果 canonical record 是文字／附件 note，Bear 的 UI 很順，Mac selected-record LLM glue 也比 Apple app 清楚；但 raw audio＋transcript 同記錄與版本語意未補齊。更適合做「少量 glue 的 note 整理層」，不適合直接宣稱完成完整系統。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| 能否在 iPhone／Mac 收錄文字、附件與語音來源？ | **官方證據**：note 可放各類附件；Watch voice dictation 產生文字；**未知**：原生錄音＋逐字稿同 note。 | [Attachments](https://bear.app/faq/insert-attachments/)；[Apple Watch](https://bear.app/faq/bear-for-apple-watch-overview/) | 「可附加 audio」不等於「保留 audio、transcript、AI result 的 record model」。 | 先把 Bear candidate scope 限為文字／匯入附件；若要 audio，另保 source file 與 transcript identity。 |
| 是否有同步、備份、刪除恢復與資料移轉？ | **官方證據**：CloudKit／iCloud、`.bear2bk` encrypted backup、Trash；大檔附件有同步限制。 | [Privacy](https://bear.app/faq/syncing-privacy/)；[Backup](https://bear.app/faq/backup-restore/)；[Sidebar／Trash](https://bear.app/faq/about-the-sidebar/) | restore 取代整個資料集；沒有本次證據可證明 per-note version。 | 做 backup copy → selected note change → full restore；記錄加密 note 對 CLI／LLM 不可讀的限制。 |
| 能否只選定 note 送 LLM 並 append 回去？ | **官方證據**：bearcli／MCP、x-callback-url、Shortcuts 支援 search／read／append；tag scope 可縮小選定範圍。 | [CLI](https://bear.app/faq/command-line-interface/)；[x-callback-url](https://bear.app/faq/x-callback-url-scheme-documentation/) | Mac-only automation、加密 note 限制、無 repo record version／audio identity。 | 用明確 tag 或 note ID；LLM 只 read selected note，結果 append 到獨立 `AI 整理稿` 區塊並保留操作紀錄。 |

### 7. Typeless

#### 能力與適配

- **收錄入口（官方證據）**：Typeless 在 macOS／Windows／iOS／Android，能在任何文字欄位使用 mic；macOS 需要 accessibility 與 microphone permission，按 Fn 後將語音轉成整理後文字插入目前欄位。iOS 是 keyboard，可在其他 app 的文字欄位使用。來源：[FAQ](https://www.typeless.com/help/faqs)、[Installation](https://www.typeless.com/help/installation-and-setup)、[First dictation](https://www.typeless.com/help/quickstart/first-dictation)、[iOS release notes](https://www.typeless.com/help/release-notes/ios)。
- **原始來源與 transcript（官方證據）**：隱私政策說 audio／context 會即時送雲端處理並立即丟棄，Typeless／第三方 LLM provider 不保留內容；transcript history 在本機，依使用者的 Keep History 期限自動刪除。這代表它刻意是 ephemeral input／polishing layer，不是來源保存層。來源：[Privacy](https://www.typeless.com/privacy)、[Missing transcript／history](https://www.typeless.com/help/troubleshooting/missing-transcript)。
- **離線／同步／匯出／所有權（官方證據／推論）**：因官方明確說即時 cloud processing，不能把 Typeless 當作可離線完成語音處理的工具；本次未找到 history 的正式 export／backup／cross-device sync contract。雲端 zero-retention 降低供應商留存，但也表示 raw audio 不會成為使用者可 restore 的來源檔。
- **Glue／LLM**：Typeless 本身已使用 LLM／context 做即時潤稿，但本次未找到能指定一筆既有 record、讀取永久 source、再把結果寫回同一記錄的 public API。它把結果插入當前 app 的文字欄位，是收錄 app 的 consumer，不是 record orchestrator。
- **個人工作方式**：它對「不要停下來、直接講進任何目前欄位」非常適合；對「保存來源、稍後挑選、可恢復、同記錄保留 raw audio／transcript」完全不足。可搭配 Notes／Drafts／Obsidian 作 capture accelerator，但不能取代 canonical store。

#### Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| iPhone／Mac 是否能降低文字／語音收錄摩擦？ | **官方證據**：任何文字欄位可啟用 Typeless；iOS keyboard、macOS Fn／accessibility 都有入口。 | [FAQ](https://www.typeless.com/help/faqs)；[Quickstart](https://www.typeless.com/help/quickstart/first-dictation)；[iOS notes](https://www.typeless.com/help/release-notes/ios) | 插入的是整理後文字，不保證原始 audio／完整 transcript。 | 只把 Typeless 放在 capture edge；插入後立刻交由 canonical store 保存 source text。 |
| 是否能離線、同步、匯出、備份及恢復？ | **官方證據**：audio／context cloud real-time processing、即時丟棄；history 本機且依期限清理。 | [Privacy](https://www.typeless.com/privacy)；[History](https://www.typeless.com/help/troubleshooting/missing-transcript) | 未找到 durable history export／backup／sync；離線 acceptance 不成立。 | 不把 Typeless history 當 backup；需要長期留存就由目標記錄系統接住文字／另行收錄音訊。 |
| 能否只選定既有記錄交給 LLM 並寫回？ | **未知／缺口**：官方能力是即時 field insertion，非 selected-record API。 | [Privacy](https://www.typeless.com/privacy)；[FAQ](https://www.typeless.com/help/faqs) | 沒有 record ID、append contract、來源保留或可審計 job state。 | 不把 Typeless 用作後處理；後處理改在 Obsidian／Bear／Drafts 等有明確選定資料介面的層。 |

## 「現成可用／少量 glue／必須自建」邊界

### 現成可用

- `Apple Journal`：最接近原生的多媒體 `記錄` 收錄；iPhone／Mac 的文字、錄音、逐字稿、附件關係最完整。
- `Apple Notes`：一般 note＋audio transcript＋附件＋基本 Apple Intelligence 摘要；對不要求自動化版本與 selected-record pipeline 的使用方式，可以直接使用。
- `Apple Voice Memos`：作為純音訊／transcript 收錄元件。
- `Typeless`：作為跨 app 語音輸入與即時潤稿元件，不是保存層。

### 少量 glue

- `Obsidian`：以一個固定 Markdown schema 加小型 script／plugin，能完成「指定 record → 讀 source/transcript → LLM → append AI 整理稿」的核心流程；需要自己負責 schema、record identity、transcription 與狀態。
- `Bear`：以 tag 或 note ID 限定範圍，利用 `bearcli`／MCP／x-callback-url append AI 整理稿；適合 Mac-first pipeline，但要接受 audio/version 的資料模型缺口。
- `Drafts`：以 URL scheme／JavaScript／Actions 處理 selected text draft，利用 version history 與 append 保留來源；適合文字，不足以成為原始音訊記錄庫。

### 必須自建

以下不是多加一個 wrapper 就會自然出現的能力，而是本產品的核心語意：

1. **Canonical `record_id`**：同一筆內容從 Typeless、Voice Memos、Notes、Journal 或文字入口進來時，仍能被唯一指向。
2. **來源內容不可變保存**：原始文字、原始音訊、匯入時間、來源 app／檔案 identity 與 checksum 不被 AI 或手動整理覆蓋。
3. **同記錄衍生內容**：transcript、AI 整理稿、分類、主題、結構化輸出要和 source 有明確關係，而不是散落在另一個 note。
4. **版本與處理生命週期**：meaningful edit／AI rerun 形成記錄版本；處理模式 `只收錄`／`收錄並整理`、狀態、錯誤、重試、model／prompt／時間要可追蹤。
5. **selected-record LLM orchestration**：只有使用者明確選中的記錄才能送出；輸出 append 到獨立區塊或新版本；需有可重放與可驗證的寫回結果。
6. **跨產品 backup／restore acceptance**：不能以「同步開著」代替 export、remote copy、restore、資料完整性與刪除恢復證據。

## 建議下一張決策票

本次不建立、不修改 GitHub Issue，也不修改 map；以下是應由 owner 決定的下一張票草案：

### 標題

`決定 canonical store 與收錄契約：Apple Journal／Notes、Obsidian 或自建 record store`

### 要決定的問題

在保留「來源內容不可覆寫、音訊與逐字稿同記錄、只選定記錄整理、AI 結果回同一處」的前提下，第一階段要把哪個產品當作收錄入口，哪個產品／格式當作 canonical store？

### 選項

| 選項 | 先得到什麼 | 必須明確接受的代價 |
|---|---|---|
| A. Apple Journal／Notes first | 最低收錄摩擦；Journal 的多媒體同 entry 或 Notes 的成熟 note／附件／Apple Intelligence | Apple-specific data model；selected-record API、版本、狀態與 local-authoritative restore 仍需自建或手動；須先做目標 OS runtime proof |
| B. Obsidian canonical store（建議先驗證） | 本機普通檔案、離線、可讀可搬、URI／CLI／plugin、最小 selected-record glue | 要自行定義 record schema、音訊 transcript pipeline、AI block、狀態與使用者介面；capture 入口不如 Apple 原生整合 |
| C. 立即自建 record store | 從一開始掌握 record_id、版本、來源、處理狀態與 restore contract | 立即承擔 iPhone／Mac capture UX、同步、音訊與逐字稿、backup／restore、所有 app integration 的成本；目前研究還沒有證明這是第一階段必要 |

### 建議 acceptance criteria

- 用一個 iPhone 文字收錄、一個 iPhone 錄音、一個 Mac 收錄，均能產生可追蹤的 `record_id`。
- 能在同一記錄旁讀到 source、transcript（若有）與 AI 整理稿；AI rerun 不改變 source bytes／source text。
- 明確選定一筆才會送 LLM；選定範圍、prompt／model、時間、成功／失敗與重試都有跡可循。
- offline capture、cross-device sync、export、remote copy、delete／restore 各有實際證據，不以設定檔或 status JSON 代替。
- 至少一次 restore drill 能證明來源、附件、逐字稿與 AI 整理稿仍可讀，且可指出任何產品限制。

### 本票的 research ledger 收尾

| question | claim | source | gap | action |
|---|---|---|---|---|
| 第一階段應否直接自建完整產品？ | **研究結論／推論**：現成產品已能覆蓋收錄入口；完整自建只在 record semantics、selected processing、restore contract 無法外掛時才必要。 | 本文件各候選的官方來源與比較表 | 尚未用真實一週工作流做 friction／restore／LLM accuracy proof。 | 先做 A／B 的小型 runtime proof，再決定是否升到 C；不要先決定模型供應商。 |
| 哪個候選最值得做 proof？ | **研究結論／推論**：Obsidian 的檔案所有權與官方 selected-file API 最適合驗證最小 glue；Journal 是最值得驗證收錄 UX 的對照組。 | [Obsidian CLI](https://obsidian.md/help/cli)；[Obsidian Vault API](https://docs.obsidian.md/Plugins/Vault)；[Journal multimedia](https://support.apple.com/en-gb/guide/journal/devb7625b2b/mac) | Journal 的 target OS 行為、Obsidian 的 transcript glue 與一週使用摩擦未知。 | 下一票先做「Journal capture → Obsidian canonical record → selected LLM append」proof，或由 owner 明確拒絕跨產品搬運。 |

## 證據限制

- Apple 文件會依 iOS／macOS 版本、裝置晶片、語言與地區改變；本文件引用的是研究日可取得的官方頁面，仍需以目標裝置做 runtime acceptance。
- 「本次官方資料未找到」只代表 **未知**，不是證明產品絕對沒有該能力；尤其是 Apple Notes／Journal 的 Shortcuts action 與 Bear 的未公開 UI 行為。
- 產品的「同步」不等於 backup，「Recently Deleted」不等於可長期 restore，「可匯出」也不等於可無損匯回同一邏輯記錄；後續驗證應分開測這些 decision surfaces。
- 本研究是 Issue #16 的產品能力與工作方式適配研究；沒有關閉 Issue、沒有修改 map，也沒有把研究推論升格為已決定的架構。
