# Obsidian 唯一長期記錄簿：相近流程與較少自製的路徑

> 研究日期：2026-08-01。這份文件只研究產品可行性，不決定本 repo 的資料模型，也不開始實作。

## 先講結論

這條路**可行，但目前只能說「文字已接近可直接採用；音訊、附件與跨 App 封裝仍須做小型實測」**。

- **Obsidian 可以當唯一、可讀的長期記錄簿。** 官方將 Vault 定義為本地檔案夾，筆記是 plain-text Markdown；附件是 Vault 中的一般檔案。官方 iOS Shortcuts 已提供建立筆記、把文字 capture 到 Daily Note 或 bookmarked note 的能力，官方 Sync 可把 Vault 同步到電腦。
- **Action Button 可以成為入口，但不會自動解決資料封裝。** Apple 官方只保證支援機型的 Action Button 能執行指定 shortcut；shortcut 如何取得文字、錄音與附件，以及如何把它們組成一筆 Obsidian 記錄，仍是流程本身的責任。
- **Apple Notes 最適合「文字＋音訊＋逐字稿」的低摩擦捕捉；Voice Memos 最適合保留原始音訊。** Apple 官方文件確認 Notes 可在同一則 Note 錄音、轉寫、複製逐字稿；Voice Memos 可轉寫、複製逐字稿、分享 `.m4a` 或 editable audio，也可在開啟 iCloud 時出現在 Mac。但 Apple 沒有提供「把選定的 Note／錄音連同原始文字、原始音訊、逐字稿、附件與 AI 結果，以穩定 record ID 一次寫入 Obsidian」的官方契約。
- **最少自製的第一條路徑**是：文字直接用 Obsidian 官方 iOS Shortcuts；音訊用 Voice Memos（或 Notes）捕捉後，透過 iOS Share Sheet／Files 把原音訊與逐字稿放入同一個 Obsidian 測試記錄；AI 結果先只做獨立追加區塊。不要一開始就寫 plugin 或背景服務。
- **不能把「append」誤當成不可覆寫保證。** Obsidian URI 和 iOS capture 都能 append，但它們不會替產品保證輸入快照、模型、重試、去重、來源與 AI 結果的 provenance。這是待實測及日後 local policy，不是官方已完成的 record contract。

因此，建議先做一個 bounded fixture fit test：若文字、原音訊、逐字稿、附件、AI 追加與電腦同步全部通過，再決定是否需要少量 glue；若音訊橋接失敗，先保留「Obsidian 唯一 store、Apple 僅 capture」的產品邊界，不要倒回讓 Apple Notes 或 Voice Memos 成為第二個長期資料庫。

## 能力判定

| 需求 | 已由官方文件確認的部分 | 判定 |
|---|---|---|
| Obsidian 作唯一可讀 store | Vault 是本地 Markdown；附件是可由檔案系統存取的一般檔案，可嵌入音訊。 | **可行**；「一筆記錄」的欄位與來源關聯仍非官方 schema。 |
| Action Button 入口 | 支援的 iPhone（官方頁面列為 iPhone 15 Pro 或後續機型）可指定 shortcut。 | **可行**；Action Button 只是 launcher。 |
| 文字快速收錄 | Obsidian iOS 有 `Create a new note`、`Capture to Daily Note`、`Capture to Bookmark`，後兩者可在不開啟 Obsidian 的情況追加／前置文字。 | **最接近現成流程**。 |
| Apple Notes 作 capture | Notes 可在 Note 內錄音、轉寫、搜尋並 `Add Transcript to Note`／複製逐字稿。 | **可行作 capture**；送入 Obsidian 的完整匯出需測。 |
| Voice Memos 作 capture | 可保留錄音、看／複製逐字稿、分享 rendered `.m4a` 或 editable audio、存到 Files；開啟 iCloud 時可在 iPhone、iPad、Mac 出現。 | **可行作 source capture**；不等於完整記錄容器。 |
| 原始音訊／附件進 Obsidian | Obsidian 支援 Vault 內的音訊與其他附件；但 iOS Share Sheet 官方說明主要描述網頁、YouTube 與社群內容，沒有保證 Voice Memos 任意音檔的一步寫入。 | **待實測**。 |
| AI 結果追加且原始不變 | URI 支援 `content`、`clipboard`、`append`；原始 Markdown／附件本身可留在 Vault。 | **機械上可做**；不可覆寫、輸入快照與重跑規則未被保證。 |
| 同步到電腦 | Obsidian Sync 可跨裝置同步；也有 note／attachment version history。 | **可行**；檔案大小、版本保留與衝突要按方案實測。 |

## 現成相近流程

### 1. 官方能力拼成的最小流程：最推薦

這條路不需要先安裝第三方 plugin：

1. Action Button 執行 shortcut。
2. 文字輸入直接交給 Obsidian 的 `Capture to Daily Note`、`Capture to Bookmark` 或 `Create a new note`。
3. Voice Memos 錄完後取得兩個獨立來源：原始 audio file 與 transcript；以 Share／Save to Files／Obsidian Share Sheet 嘗試放入同一個 Obsidian 測試記錄。
4. 附件也先以原始檔案放進 Vault，再在 Markdown 中保留可讀連結或嵌入。
5. AI 整理只以新的區塊或新的檔案追加；先用固定測試文字也可以，不必為了驗證而引入 LLM。
6. 只選一種同步方案。優先測 Obsidian Sync；若改用 iCloud Drive，遵守 Obsidian 的 `iCloud Drive/Obsidian/[Vault]` 位置規則，且不要同一 Vault 同時跑多個同步服務。

這是目前最少自製的路徑。官方沒有說明「Voice Memos 選定錄音 → Obsidian 同一筆 note」這個完整動作，所以第 3 步不是已證明能力。

### 2. Apple Notes 作捕捉容器，再轉到 Obsidian

Notes 比 Voice Memos 更接近使用者想要的 capture 形狀：一則 Note 可同時放文字、附件、錄音與逐字稿，且 Apple Intelligence 可產生摘要並複製／分享。缺口在於，Apple 官方文件說明的是 Note 內操作，並沒有提供可依穩定 ID 從 Shortcuts 取出「原音訊＋逐字稿＋其他附件」並寫成 Obsidian 記錄的完整流程。這條路可作第二個 fixture，不能當作現成整合已完成。

### 3. Voice Memos 作原始音訊 source

Voice Memos 的官方能力更直接對準「不要丟原音」：錄音可分享成 rendered `.m4a` 或 editable file，逐字稿可複製，錄音也可保存到 Files。它適合作為 source capture，再由 Obsidian 保存原檔與逐字稿；但文字、附件、AI 結果及其關聯必須由後續流程補上。

### 4. 已有的開源／社群流程

以下是專案 README 或 GitHub 原始頁面**自述的能力**，不是本 repo 已驗證，也不是 Obsidian 官方承諾：

| 專案 | README／source 自述 | 對本需求的價值與限制 |
|---|---|---|
| [Voice MD](https://github.com/DenizOkcu/voice-md) | Obsidian mobile plugin；可用 iOS Shortcut／Action Button 觸發；停止錄音後先本地保存、失敗可重試；每筆可選擇 post-processing，並保存 raw transcript 與 structured note。 | 這是目前最接近「收錄並整理／只收錄」切換的現成實作。它自述成功後會刪除本地 audio，raw 與 structured 是不同 Markdown 檔；沒有證明原始音訊會長期留在 Vault，故不符合本案的完整原始保存要求。 |
| [QuickAdd](https://github.com/chhoumann/quickadd) | 提供 templates、captures、macros、multis；Capture 可把內容加入預定檔案。 | 可減少文字路由與模板 glue；不負責 Apple 原始音訊保存、跨裝置 backup 或不可覆寫 record。先不裝也不影響文字 fixture。 |
| [Advanced URI](https://github.com/Vinzent03/obsidian-advanced-uri) | 以 URI 控制 Obsidian，可 create、append、prepend、寫入 clipboard、呼叫 plugin command。 | 比官方 URI 更強，但增加 community plugin 依賴；其 [issue #160](https://github.com/Vinzent03/obsidian-advanced-uri/issues/160) 記錄 iOS／Shortcuts append 在部分情況失敗或需重試，故不應作第一個可靠性基礎。 |
| [Whisper — Speech-to-text for Obsidian](https://github.com/nikdanilov/whisper-obsidian-plugin) | 自述可在 desktop/mobile 錄音或上傳 audio、用 Whisper 轉寫；可由 iOS Shortcuts URL 觸發；note template 可同時嵌入 audio file 與 transcription。 | 若願意把 capture 移進 Obsidian，這是相近流程；README 要求 API key／Whisper-compatible API，與 Apple Notes／Voice Memos 僅作 capture、local-first 的目標不同。 |
| [Epiphany plugin](https://community.obsidian.md/plugins/epiphany) | 自述可從 iPhone／Apple Watch 錄音、附帶連結／圖片／檔案、離線排隊，完成後把轉寫 Markdown 寫入 Obsidian。 | 很接近「隨時捕捉 → 自動進 Vault」，但它是自己的雲端服務；頁面沒有證明 raw audio、AI 結果 provenance 或完整版本會留在同一筆記錄。 |
| [Minutes](https://github.com/silverstein/minutes) | 自述的流程是 iPhone Voice Memos → Shortcuts `Save File` → 同步 inbox → Mac watcher；本地 transcribe、可選雲端 LLM，再寫 structured Markdown；保留 WAV，並可同步到 Obsidian／Logseq。 | 它證明「手機只負責丟檔，電腦背景處理」是可行的既有模式，且比依賴 iOS 長時間背景執行更穩。它是獨立的 desktop memory layer，需再確認如何把結果寫成你的單一 Obsidian record。 |
| [Aiko](https://sindresorhus.com/aiko) | 自述在裝置上執行 Whisper；提供 Action Button 錄音／轉寫 shortcut，也能處理 Voice Memos／Files；錄音保存在 Files 的 Aiko 資料夾。 | 可作 local/private transcription layer，不必把原音送雲端；但它不是 Obsidian store，也沒有你的分類／主題／摘要／結構化記錄 contract。 |
| [Voicenotes Sync](https://github.com/voicenotes-community/voicenotes-sync) | 自述可從 VoiceNotes web/mobile 同步，下載轉寫用的音訊（預設關閉），把 AI summaries/actions 寫成 note sections。 | 是「少自製」的替代產品路徑，但改用 VoiceNotes.com、帳號與 access token；不符合「Apple Notes／Voice Memos 作為唯一 capture 媒介」的原始假設，且 cloud retention／privacy 需另查。 |

### 5. 研究推論：背景 AI 應放在 Mac

Apple 官方保證的是 Action Button／Shortcuts 的觸發和檔案／文字傳遞；iOS App 長時間在背景執行則有系統限制。Aiko 也明確提醒 iOS app 不能長時間背景處理。Minutes 的既有做法正好把工作拆成「手機把檔案放進同步 inbox → Mac watcher 偵測穩定檔案 → 轉寫／整理 → 寫回 Markdown」。因此，對本案最少風險的路徑是：

`iPhone capture → Shortcuts/同步 inbox → Mac 背景處理 → Obsidian 同一筆記錄`

這是依來源做出的設計推論，不是 Apple 或 Obsidian 的單一官方整合保證。它保留了 Obsidian 作唯一 store，也讓離線、重試、去重和雲端 AI 選擇留在電腦端處理；第一個 fixture 應先驗證這條路，而不是先寫 iOS plugin。

## 最推薦的最小驗證路徑

只用一個暫時 Vault 與一組測試資料，不建立產品架構：

1. **先驗證文字。** 用 Action Button 執行 shortcut，輸入含特殊字元與多行的原始文字，走 Obsidian 官方 `Capture to Daily Note` 或 `Create a new note`。確認檔案在 Vault 中可直接讀取，且沒有被 Apple Notes 取代。
2. **再驗證 Voice Memos。** 錄一段短音訊；在支援的機型／語言前提下複製 transcript，另存或分享原始 `.m4a`。嘗試用 Share Sheet 或 Files 把兩者放進同一個 Obsidian 測試記錄。若 Obsidian Share Sheet 不接受音檔，就明確記錄為 bridge gap，不用猜測它「應該可以」。
3. **補一個附件。** 以 PDF 或圖片測試同樣路徑，確認原檔可在 iPhone 與 Mac 開啟，且 Markdown 只保存指向原檔的連結／嵌入，不把附件轉成不可還原的摘要。
4. **測非覆寫。** 在同一測試記錄中追加一段固定的 `AI 整理` 文字；再次追加另一個結果。驗證原始文字、原始音訊、逐字稿與附件 byte／內容仍在，並能分辨兩次結果。這一步先不需要真正呼叫 AI。
5. **測電腦同步與恢復。** 使用單一同步方案，在 Mac 端確認 note、audio、transcript、attachment 都可讀；再測一次手機離線後恢復連線。確認 Obsidian version history／File recovery 能找回 note 與 attachment，並記錄同步延遲、衝突與重複結果。

### 通過條件

- 原始文字可逐字核對，沒有被整理稿覆蓋。
- 原始音訊仍可獨立播放；逐字稿是可讀文字，不取代音訊。
- 附件在 Vault 內有穩定、可讀的檔案位置。
- AI 結果只新增，不會修改或刪除三種原始資訊；重跑不會靜默覆蓋舊結果。
- Mac 端可讀取同一組 Markdown 與附件；離線／重試不造成遺失。
- 任何未通過的部分都能指出是 Apple bridge、Obsidian mobile、同步方案或資料規則問題，而不是以「看起來已同步」代替驗證。

## 主要風險與未決問題

1. **Apple bridge 沒有單一官方契約。** Notes 與 Voice Memos 的「複製 transcript」及「分享 audio」是分開的動作；官方沒有證明 Shortcuts 能從一個選定來源保留兩者的同一 ID、順序與附件關係。
2. **Obsidian iOS Share Sheet 的文件範圍有限。** 官方目前明確描述的是網頁等 shared content 與 note locations；任意 Voice Memos audio、PDF、圖片是否能一次被正確放入指定 Vault，必須在目標 iOS／Obsidian 版本實測。
3. **同步大小與版本保留會影響原始音訊。** Obsidian Sync Standard 的單檔上限是 5 MB、Plus 是 200 MB；note version history 為 1／12 個月，attachment history 為兩週。長錄音可能先撞到檔案上限，且附件的恢復窗口短於 Markdown。
4. **同步衝突不是 record provenance。** Obsidian 文件說 Markdown 會合併，其他檔案採 last-modified-wins；離線時同一 note 的多端追加仍要測是否產生重複、遺失或衝突檔。
5. **AI 追加仍需產品規則。** `append` 只描述寫入方式，不會自動記錄輸入快照、模型、時間、錯誤、重試或結果與來源的關聯。若這些欄位後來成為硬需求，就已超出「少量 glue」的範圍。
6. **裝置、語言與隱私條件會變動。** Apple 的音訊轉寫有 iPhone、語言與地區條件；Whisper／Voicenotes 類開源流程還會引入 API key、雲端傳輸、第三方帳號或外掛權限。

## Research ledger：question → claim → source → gap → action

| question | claim | source | gap | action |
|---|---|---|---|---|
| Obsidian 能否作唯一、可讀的長期 store？ | 官方確認 Vault 是本地 plain-text Markdown；附件是 Vault 中可由檔案系統存取的一般檔案，包含 audio。 | [How Obsidian stores data](https://obsidian.md/help/data-storage)、[Attachments](https://obsidian.md/help/Editing%2Band%2Bformatting/Attachments)、[Audio recorder](https://obsidian.md/help/plugins/audio-recorder)（**官方承諾**） | 官方沒有定義「原始文字／原音／逐字稿／AI」的一筆 record schema。 | 用一個 fixture note＋原音訊檔＋逐字稿檔／區塊驗證可讀性與來源關聯。 |
| Action Button 能否作 iPhone 入口？ | 支援機型可在 Settings → Action Button 指定 shortcut。 | [Run shortcuts with the Action button](https://support.apple.com/guide/shortcuts/run-shortcuts-with-the-action-button-apdfea15680b/ios)（**官方承諾**） | Action Button 不保證 shortcut 能取得或封裝任意 App 的 audio／attachment。 | 只測 launcher；把輸入與寫入結果分別驗證。 |
| 文字是否已有少自製流程？ | Obsidian iOS 已提供建立筆記、Capture to Daily Note、Capture to Bookmark；capture 可在背景追加／前置文字。 | [Obsidian for iOS and iPadOS](https://obsidian.md/help/ios)（**官方承諾**） | 文件未替音訊與附件的同樣流程作保證。 | 文字先走官方 shortcut，不先引入 QuickAdd。 |
| Notes 能否保留原始音訊與逐字稿？ | Notes 可錄音、轉寫、搜尋，並將 transcript 加入 Note 或複製。 | [Record and transcribe audio in Notes](https://support.apple.com/guide/iphone/record-and-transcribe-audio-iphbe11247b5/ios)（**官方承諾**） | 沒有官方的完整 Obsidian export、穩定 ID 或 record package contract。 | 做一次 Notes → Obsidian fixture；若需多步匯出，記錄為 bridge cost。 |
| Voice Memos 能否作原始音訊 source？ | 可看／複製 transcript，分享 rendered `.m4a` 或 editable audio，也可存到 Files；iCloud 可讓錄音出現在 Mac。 | [View a Voice Memos transcription](https://support.apple.com/en-gb/guide/iphone/iph00953a982/ios)、[Share a recording](https://support.apple.com/en-is/guide/iphone/iph3d6dc359/ios)、[Export to Files](https://support.apple.com/en-ae/guide/iphone/iph831c37815/ios)、[Make a recording](https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/ios)（**官方承諾**） | 原音訊與逐字稿是可分別取得的輸出，官方未證明可自動綁成 Obsidian 一筆記錄。 | 以同一段短錄音實測檔案、transcript、命名與關聯。 |
| Obsidian 是否能接收跨 App audio／attachments？ | Obsidian 支援 Vault 內附件，官方 iOS Share Sheet 支援 shared content 與多種 note locations。 | [Attachments](https://obsidian.md/help/Editing%2Band%2Bformatting/Attachments)、[Obsidian iOS](https://obsidian.md/help/ios)（**官方承諾，但範圍有限**） | iOS 文件沒有把 Voice Memos 任意音檔列成保證案例。 | 測 Share Sheet、Files 寫入 Vault、音檔播放與 Mac 端讀取；不以推測替代結果。 |
| AI 結果能否追加而不覆蓋？ | Obsidian URI 的 `new` 支援 `content`、`clipboard`、`append`；社群工具也提供更廣的 append／capture。 | [Obsidian URI](https://obsidian.md/help/uri)（**官方機械能力**）；[Advanced URI README](https://github.com/Vinzent03/obsidian-advanced-uri)（**開源專案自述**） | append 不等於不可變來源、去重、輸入快照或 retry safety；Advanced URI 還有 iOS append issue。 | 用固定結果連續追加兩次，逐項比較原始內容；未通過前不做 AI 自動化。 |
| 所有筆記與音檔能否同步到電腦並恢復？ | Obsidian Sync 提供跨裝置同步與 version history；官方公開檔案大小、保留期限與衝突規則。 | [Introduction to Obsidian Sync](https://obsidian.md/help/Obsidian%20Sync/Introduction%20to%20Obsidian%20Sync)、[Plans and storage limits](https://obsidian.md/help/sync/plans)、[Version history](https://obsidian.md/help/sync/version-history)、[Troubleshoot Sync](https://obsidian.md/help/sync/troubleshoot)（**官方承諾**） | 實際結果受方案、檔案大小、離線時間與多端同時寫入影響。 | 用含 audio／attachment 的 fixture 在 iPhone、Mac、離線、恢復與衝突情境實測。 |
| 是否已有更少自製的相近產品／流程？ | Voice MD、Epiphany、Minutes、Aiko，以及 QuickAdd、Advanced URI、Whisper、Voicenotes Sync 的原始頁面，分別自述 Action Button／mobile capture、離線排隊、桌面 watcher、on-device transcription、文字 capture 與 Obsidian automation。 | [Voice MD](https://github.com/DenizOkcu/voice-md)、[Epiphany](https://community.obsidian.md/plugins/epiphany)、[Minutes](https://github.com/silverstein/minutes)、[Aiko](https://sindresorhus.com/aiko)（**產品／專案自述**） | README／產品頁不是本 repo 的 runtime proof；部分方案改變 capture app、引入 cloud/API 或把 raw audio 放在 Vault 外。 | 先跑官方 text/audio fixture；只有明確缺口才挑一個 plugin 或 watcher 做 bounded comparison。 |

## 直接來源索引

### Apple 官方

- [Action Button 執行 shortcut](https://support.apple.com/guide/shortcuts/run-shortcuts-with-the-action-button-apdfea15680b/ios)
- [Shortcuts share actions／Append to Note／Open URLs](https://support.apple.com/en-gb/guide/shortcuts/apdaf74d75a5/ios)
- [Notes 錄音與轉寫](https://support.apple.com/guide/iphone/record-and-transcribe-audio-iphbe11247b5/ios)
- [Voice Memos 錄音](https://support.apple.com/guide/iphone/make-a-recording-iph4d2a39a3b/ios)
- [Voice Memos 查看逐字稿](https://support.apple.com/en-gb/guide/iphone/iph00953a982/ios)
- [Voice Memos 分享錄音](https://support.apple.com/en-is/guide/iphone/iph3d6dc359/ios)
- [Voice Memos 匯出到 Files](https://support.apple.com/en-ae/guide/iphone/iph831c37815/ios)

### Obsidian 官方

- [How Obsidian stores data](https://obsidian.md/help/data-storage)
- [Obsidian for iOS and iPadOS](https://obsidian.md/help/ios)
- [Obsidian URI](https://obsidian.md/help/uri)
- [Attachments](https://obsidian.md/help/Editing%2Band%2Bformatting/Attachments)
- [Audio recorder](https://obsidian.md/help/plugins/audio-recorder)
- [Introduction to Obsidian Sync](https://obsidian.md/help/Obsidian%20Sync/Introduction%20to%20Obsidian%20Sync)
- [Plans and storage limits](https://obsidian.md/help/sync/plans)
- [Version history](https://obsidian.md/help/sync/version-history)
- [Sync conflict troubleshooting](https://obsidian.md/help/sync/troubleshoot)
- [iCloud vault location](https://obsidian.md/help/Getting%20started/Sync%20your%20notes%20across%20devices)

### GitHub 原始專案／issue

- [Voice MD](https://github.com/DenizOkcu/voice-md)
- [QuickAdd README](https://github.com/chhoumann/quickadd)
- [Advanced URI README](https://github.com/Vinzent03/obsidian-advanced-uri)
- [Advanced URI iOS append issue #160](https://github.com/Vinzent03/obsidian-advanced-uri/issues/160)
- [Whisper Obsidian plugin README](https://github.com/nikdanilov/whisper-obsidian-plugin)
- [Minutes](https://github.com/silverstein/minutes)
- [Voicenotes Sync README](https://github.com/voicenotes-community/voicenotes-sync)

### 其他第一方產品頁面

- [Epiphany Obsidian plugin](https://community.obsidian.md/plugins/epiphany)
- [Aiko](https://sindresorhus.com/aiko)
