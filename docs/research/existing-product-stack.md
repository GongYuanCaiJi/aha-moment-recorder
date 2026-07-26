# 現有產品能否拼成個人記錄系統

> 研究日期：2026-07-27
> 對應問題：[研究現有產品能否拼成個人記錄系統](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/4)

## 結論

**沒有任何一個受查的現成產品，也沒有完全免寫程式的產品組合，能滿足目前定義的全部需求。** 最接近的兩條路是：

1. **Apple 備忘錄方案**最適合做低成本體驗驗證：同一則備忘錄可以同時保存文字、錄音、逐字稿與 Apple Intelligence 摘要，iPhone 與 Mac 也能透過 iCloud 同步。但官方沒有提供足以支撐「每筆記錄有處理模式、背景自動送指定雲端 AI、可靠寫回同一筆記錄」的完整自動化介面；資料也不是使用者可直接管理的本地檔案庫。
2. **Obsidian 混合方案**最符合目標架構：以本地 Markdown vault 為權威記錄庫，每筆記錄用一份 Markdown 呈現，來源錄音作為同一記錄內嵌的附件；再以 iPhone 捷徑負責明確收錄、Mac 上的薄型背景處理器負責逐字稿與可選 AI 整理。它能保留來源、離線讀寫及本地掌控，但「一鍵收錄、可靠背景佇列、AI 寫回」必須自行實作與驗證，不能只靠 Obsidian 設定完成。

因此，後續選路時應以 **混合方案作為 v1 的首選候選**，並用兩個小型 prototype 驗證最危險的假設：

- Action Button → iPhone 捷徑能否在離線時可靠建立一筆含文字或錄音附件的記錄，之後再同步到 Mac。
- Mac 背景處理器能否只處理標為「收錄並整理」的記錄，保留來源內容，並把逐字稿、AI 結果與狀態寫回同一筆記錄且可重試、不重複處理。

若這兩項成立，沒有理由先做完整原生 App；若 iOS 背景限制或檔案同步競態使流程不可靠，再升級為自建 App。

## 驗證基準

本研究使用 repo 已確立的產品語意，不把「有錄音」或「有 AI」誤當成整套個人記錄系統：

| 基準 | 判定方式 |
| --- | --- |
| 明確收錄 | 只有使用者主動送入的內容成為記錄，不掃描整個外部資料庫 |
| 同一筆記錄 | 來源、逐字稿與 AI 結果在使用體驗上屬於同一識別、同一項目 |
| 來源保留 | 原始文字或原始錄音不被逐字稿、改寫稿或摘要覆寫 |
| 可選 AI 整理 | 有預設處理模式，但每筆可改為「只收錄」或「收錄並整理」，之後也能重跑 |
| 離線 | 無網路時仍先保存來源；同步與 AI 可延後並顯示狀態 |
| 本地優先 | 裝置上的資料是可完整存取的權威副本；雲端只負責同步、備份或受控處理 |
| iPhone／Mac | 兩端可查看同一記錄，iPhone 能低摩擦收錄，Mac 能搜尋、整理與處理 |

符號：✅ 直接具備；△ 部分具備或需要額外組裝；❌ 與需求衝突；「未證實」表示官方資料不足，不把猜測當成能力。

## 產品逐項比較

| 產品 | 明確收錄 | 同一筆記錄 | 來源保留 | 可選 AI 整理 | 離線／本地優先 | iPhone／Mac | 結論 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Apple 備忘錄 | ✅ 手動建立、專用資料夾或 tag | ✅ 文字、錄音與逐字稿可在同一則備忘錄 | ✅ 錄音保留；逐字稿不取代錄音 | △ 有手動摘要、改寫與整理，沒有已記錄的每筆背景處理模式 | △ 可用「我的 iPhone」完全本地，但無跨裝置；跨裝置需 iCloud | ✅ 原生體驗完整 | 最接近的純現成 prototype，但不符合自訂背景 AI 與透明本地權威庫 |
| 語音備忘錄 | ✅ Action Button 可直接啟動 | △ 一筆錄音內有逐字稿，但無一般文字記錄 | ✅ 錄音與逐字稿並存，可匯出 `.m4a` | △ Apple Intelligence 可手動整理逐字稿 | △ 本地錄音加 iCloud 同步；非統一記錄庫 | ✅ 兩端原生同步 | 適合緊急錄音入口或 fallback，不適合作為整套系統的權威記錄庫 |
| Typeless | ✅ 在任意文字欄主動口述 | ❌ 只把處理後文字插入目的 App，沒有完整記錄模型 | ❌ 官方說音訊經雲端即時處理後丟棄；無法把來源錄音留在同一記錄 | △ 擅長即時整理，但不是每筆記錄的可追蹤背景模式 | ❌ AI 在雲端處理；離線無法完成核心功能 | ✅ iOS、macOS 均支援 | 保留為可選輸入法，不可當來源保存層或權威記錄庫 |
| Obsidian | △ App、URI 與外部檔案可明確建立記錄；Action Button 流程要組裝 | ✅ 一份 Markdown 可內嵌同 vault 的錄音附件 | ✅ Markdown 與音訊檔都由使用者持有 | △ core 沒有轉寫／AI；可由自訂處理器寫回同一 Markdown | ✅ 本地檔案、離線可用；同步另選 | ✅ 兩端 App；iOS 同步選項有限 | 最符合權威記錄庫，但必須補一層收錄與處理 orchestration |
| Drafts | ✅ 快速文字、dictation、widget、share sheet、Shortcuts | △ 每個 draft 是一筆文字；官方沒有音訊附件記錄模型 | ❌ 匯入音訊可轉寫，但沒有證據顯示原始音訊會留在同一 draft | △ action 可在使用者執行時呼叫外部服務；不是可靠背景佇列 | △ draft 存本機並以 iCloud/CloudKit 同步，但不是使用者可直接管理的檔案庫 | ✅ iPhone、Mac、Apple Watch | 很好的文字 inbox，但會增加第二個 datastore，且錄音來源保留不合格 |

## 第一方能力與缺口

### Apple 備忘錄：最接近需求的純現成方案

Apple 已經把過去分散的能力收進同一則備忘錄：iPhone 可以直接在備忘錄內錄音，顯示、搜尋、複製逐字稿，或把逐字稿加入備忘錄；刪除錄音時逐字稿也會一併刪除，表示兩者在產品模型中確實相連。[Apple：在 iPhone 備忘錄中錄音及轉錄](https://support.apple.com/en-gb/guide/iphone/iphbe11247b5/26/ios/26)

Apple Intelligence 可以針對備忘錄中的錄音產生摘要；Writing Tools 也能對選取文字做 proofread、rewrite、summary、key points、list 或 table。這證明「來源旁邊附加整理結果」的低階版本已可行，但官方流程是使用者開啟功能後操作，沒有記錄級的 `只收錄／收錄並整理` 狀態與背景佇列。[Apple：在備忘錄中使用 Apple Intelligence](https://support.apple.com/en-mide/guide/iphone/iph59143007d/ios)；[Apple：Writing Tools](https://support.apple.com/en-lamr/guide/iphone/iph6f08da1d2/ios)

備忘錄可以用 tag 和 Smart Folder 篩選，因此 `#只收錄`、`#待整理` 類標記可以作為人工作業視圖；但 tag 本身不會觸發第三方 AI，也不等於可靠的狀態機。[Apple：用 tag 整理備忘錄](https://support.apple.com/en-mide/guide/iphone/iphedddbfdf9/ios)；[Apple：Smart Folder](https://support.apple.com/guide/iphone/use-smart-folders-iphc43adabc2/26/ios/26)

儲存方面，「我的 iPhone」帳號只留在該手機；iCloud 備忘錄才會出現在同 Apple Account 的 iPhone、iPad 與 Mac。換句話說，原生方案要在「完全裝置本地」與「自動跨裝置」之間選 iCloud 作同步橋樑。[Apple：加入或移除備忘錄帳號](https://support.apple.com/en-gb/guide/iphone/iph7262fd4fe/ios) 若開啟 Advanced Data Protection，備忘錄與語音備忘錄可改為端對端加密，只有受信任裝置持有解密金鑰；但使用者也要自己負責 recovery contact 或 recovery key。[Apple：iCloud Advanced Data Protection](https://support.apple.com/en-euro/guide/iphone/iph584ea27f5/ios)

**不能由設定補上的缺口：** 在受查的第一方文件中，沒有發現可以可靠讀取一則備忘錄的錄音附件及系統逐字稿、維護自訂處理狀態、呼叫指定 AI 後再原位寫回的公開完整介面。這不是「已證實做不到」，而是 **未證實且會阻擋核心流程**；必須用 prototype 實測 Shortcuts 可見的 Notes actions，不能把它當成既有能力承諾。

### 語音備忘錄：最佳緊急入口，但會製造第二種記錄

支援 Action Button 的 iPhone 可把 Voice Memo 直接設為按鈕功能；也可把 Action Button 設為執行 Shortcut。[Apple：Action Button 可執行 Shortcut](https://support.apple.com/en-in/guide/shortcuts/apdfea15680b/ios)；[Apple：iPhone Action Button 功能包含 Voice Memo](https://support.apple.com/en-us/125089)

語音備忘錄會保存錄音與逐字稿，支援繁體中文的條件是 iPhone 12 或更新機型及相符語言／地區；Apple Intelligence 可再以 Writing Tools 摘要或整理逐字稿。[Apple：查看語音備忘錄逐字稿](https://support.apple.com/en-gb/guide/iphone/iph00953a982/26/ios/26) 錄音可透過 iCloud 自動出現在 Mac 與其他 Apple 裝置，也能手動匯出為 `.m4a` 至 Files。[Apple：在所有裝置查看錄音](https://support.apple.com/guide/voice-memos/see-your-recordings-on-all-your-apple-devices-vma6cc4d0571/mac)；[Apple：匯出錄音至 Files](https://support.apple.com/en-ie/guide/iphone/iph831c37815/ios)

**不能由設定補上的缺口：** 它的最小單位是錄音，不是可容納一般文字、處理模式與多種 AI 結果的「記錄」。把錄音匯出後再建立另一則備忘錄或 Markdown，會產生兩份 identity 與刪除／同步責任。若 v1 要守住「同一筆記錄」，語音備忘錄只能當故障時的 fallback，或由自動化在收錄後把來源搬入 canonical record 並明確處理重複檔。

### Typeless：輸入加速器，不是保存系統

Typeless 的定位是 AI voice keyboard：它在任何文字欄接收語音，將想法整理、格式化後插入目前 App 的文字欄；目前支援 iOS 與 macOS。[Typeless：第一次 dictation](https://www.typeless.com/help/quickstart/first-dictation)；[Typeless：iOS 2.0 release notes](https://www.typeless.com/help/release-notes/ios)

它的隱私文件說明，音訊與有限上下文會送到雲端伺服器即時處理，結果返回裝置後立即丟棄；第三方 LLM 供應商配置為 zero retention，內容不拿來訓練。History 留在裝置，但這不等於保存來源錄音。[Typeless Privacy Policy](https://www.typeless.com/privacy)；[Typeless：Ask Anything privacy](https://www.typeless.com/ask-anything)

目前 Free 為每週 8,000 words；Pro 為年繳每位每月 USD 12，月繳 USD 30，提供 unlimited words。定價頁同時宣稱 on-device history 與 zero cloud data retention。[Typeless Pricing](https://www.typeless.com/pricing)

**不能由設定補上的缺口：** Typeless 的核心價值就是在輸入時整理並輸出乾淨文字；原始音訊會被丟棄，也沒有一個包含來源、逐字稿、處理狀態和 AI 結果的 record model。它可以留在 iPhone／Mac 上作為「快速輸入已整理文字」的選配入口，但任何由 Typeless 直接輸出的記錄都不能被誤稱為保留了來源錄音。

### Obsidian：最合適的本地權威記錄庫

Obsidian vault 是本地檔案系統中的資料夾，筆記是 Markdown 純文字；其他 editor 和檔案管理器也能直接操作，Obsidian 會偵測外部變更。[Obsidian：資料如何儲存](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata) 官方明確說本地筆記即使離線也能存取；使用 Obsidian Sync 時，每個裝置仍保有本地副本。[Obsidian：跨裝置同步](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices)

Audio recorder 是 core plugin：在當前 note 內錄音後，音訊檔存入 vault，並嵌入該 note 尾端。這符合已確立的產品語意——使用上是一筆記錄，底層允許 Markdown 與附件分開；但從 note 移除 embed 不會刪除音訊檔，因此生命週期清理必須另外設計。[Obsidian：Audio recorder](https://obsidian.md/help/plugins/audio-recorder)

Obsidian URI 能建立、append 或開啟指定 note，適合讓 Shortcuts 或其他 App 進行文字收錄；官方 plugin API 也能讀寫 vault 檔案，證明同一 Markdown 可以被自訂處理器擴充。[Obsidian URI](https://help.obsidian.md/Extending%2BObsidian/Obsidian%2BURI)；[Obsidian developer docs：Vault API](https://docs.obsidian.md/Plugins/Vault)

同步有兩個符合 Apple 裝置情境的第一方支持選擇：

- Obsidian Sync：本地副本一直保留，remote vault 預設端對端加密；目前年繳 USD 4/月或月繳 USD 5/月，包含 version history。Standard 的單檔上限為 5 MB，對錄音過小；含錄音時實務上需 Plus（200 MB 單檔上限）或另一個同步方案。[Obsidian Sync security](https://obsidian.md/help/sync/security)；[Obsidian pricing](https://obsidian.md/pricing)；[Obsidian Sync limits](https://obsidian.md/help/sync/plans)
- iCloud Drive：官方支援 macOS／iOS vault，但建議在 macOS 設為 Keep Downloaded；搭配 iCloud Advanced Data Protection 可讓 iCloud Drive 端對端加密。Google Drive **不受官方支援用於 iOS vault**，不應列為 v1 的可靠候選。[Obsidian：跨裝置同步](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices)；[Apple：iCloud security overview](https://support.apple.com/en-mide/102651)

Obsidian 本體免費、不需登入，個人與商業使用皆不強制購買 license；付費的是可選 Sync／Publish 等服務。[Obsidian Pricing](https://obsidian.md/pricing)

**不能由設定補上的缺口：** core Obsidian 沒有錄音逐字稿、指定雲端 AI、每筆可選背景處理與離線工作佇列。社群 plugins 即使有相似功能，也不能把多個 plugins 的維護與資料行為當成已驗證產品保證。需要一個 repo-owned、可測試的薄型收錄／處理層。

### Drafts：強大的文字 inbox，但不應成為第二個記錄庫

Drafts 啟動即進入新 draft，支援 keyboard dictation、自訂 dictation、widget、share extension、Shortcuts 與 URL scheme；很適合把文字快速送往下游。[Drafts：Getting Started](https://docs.getdrafts.com/gettingstarted/)；[Drafts：Dictation](https://docs.getdrafts.com/docs/editor/dictation)；[Drafts：Shortcuts reference](https://docs.getdrafts.com/docs/automation/shortcuts-reference)

Drafts 將 drafts 存在裝置本地，並以私有 iCloud/CloudKit database 在 iOS、macOS 間同步；對外 service integration 只有在使用者執行 action 時才送出資料。Draft content 支援 iCloud Advanced Data Protection 的端對端加密欄位，但 metadata 不在該承諾內。[Drafts Privacy](https://getdrafts.com/support/privacy)；[Drafts iCloud Sync](https://docs.getdrafts.com/docs/settings/sync)

它可以從 Voice Memos 或 Files 接收音訊並轉寫，但官方描述的結果是建立文字 draft，沒有音訊附件仍留在同一 draft 的記錄模型；長音訊還會切成約一分鐘 segments。[Drafts：Transcribing Audio & Video](https://docs.getdrafts.com/docs/editor/transcription.html) 基本建立、編輯、同步與內建 actions 免費；自訂 actions 等進階功能需 Pro，目前 USD 19.99/年或 USD 1.99/月。[Drafts Pro](https://docs.getdrafts.com/draftspro)

**不能由設定補上的缺口：** 若 Drafts 只當 inbox，再匯出到 Obsidian 或另一個記錄庫，就會多出一份要處理同步、刪除與 identity 的 datastore；若直接當記錄庫，來源錄音保留又不合格。除非 prototype 證明 Drafts 能顯著降低 iPhone 收錄摩擦且具備可靠單向 handoff，否則 v1 不應加入它。

## 三條候選路線

### A. 拼裝：Apple 備忘錄為唯一記錄庫

**組合**：Action Button／鎖定畫面 → Apple 備忘錄或語音備忘錄 → iCloud + Advanced Data Protection → Apple Intelligence／Typeless 手動整理。

**優點**：幾乎零開發、iPhone／Mac 原生、備忘錄內已可把錄音、逐字稿與摘要放在一起。

**硬缺口**：無法從官方能力證明自訂雲端 AI 能依每筆處理模式在背景可靠運行並原位寫回；「我的 iPhone」與跨裝置同步不能同時成立；資料不是透明可攜的本地檔案庫。Typeless 也無法補上來源音訊，因為它會丟棄音訊。

**適用判斷**：只適合用來驗證「單一記錄頁面是否好用」；若核心需求可以降級成手動摘要，它甚至可能就是夠用的產品。以目前需求則不能當完整 v1 結論。

### B. 混合（建議）：Obsidian 本地庫 + Apple 收錄面 + 薄型背景處理器

**組合**：

1. iPhone Action Button 執行 Shortcut，讓使用者選文字／錄音及沿用預設處理模式或改為「只收錄」。
2. Shortcut 在 Obsidian vault 的 inbox 建立一筆 stable-id record：一份 Markdown 加來源附件；Markdown 只保存對附件的 embed/reference，使用體驗仍是一筆記錄。
3. iCloud Drive + Advanced Data Protection 或 Obsidian Sync 將 vault 同步到 Mac；實際同步選擇交由「研究本地優先的儲存、同步與備份方案」決定。
4. Mac 背景處理器只讀取要求整理的 pending records；先產生逐字稿，再呼叫選定雲端 AI，最後把整理結果與狀態 append 到同一 Markdown。來源區與附件永不覆寫。
5. Typeless 僅作為選配文字輸入法；語音備忘錄只作 fallback，成功匯入後需有明確去重與來源生命週期規則。

**優點**：最符合本地優先、離線、來源保存、單一記錄與未來可攜性；自寫範圍只剩真正不存在的 orchestration，而不是重做 editor、search、sync UI。

**風險**：iOS Shortcut 對 Obsidian/iCloud 檔案的離線寫入、音訊檔命名與 atomicity；同步到 Mac 前後的 partial files；Mac worker 的 idempotency、失敗恢復與同時編輯衝突。這些全部必須由 prototype 和 characterization tests 收斂。

### C. 自建：原生 iPhone／Mac App

**組合**：自行做 capture UI、local database/file package、sync、background queue、AI pipeline 與查閱介面。

**優點**：能完整控制一鍵收錄、狀態機、record identity、來源生命週期與 privacy boundary。

**代價**：必須重新承擔儲存格式遷移、同步衝突、背景執行限制、搜尋、備份、還原與雙平台 UI；這些都不是產品差異化的核心。

**升級條件**：只有當混合 prototype 證明 Action Button → vault 或 vault → reliable background worker 無法達到可接受的可靠度，才選自建。不能只因為「最後可能會做 App」就提前承擔完整成本。

## 不可用設定補上的共同缺口

| 缺口 | 哪些產品受影響 | 需要的 action |
| --- | --- | --- |
| 同一 record identity 橫跨文字、音訊、逐字稿與 AI 結果 | 語音備忘錄、Typeless、Drafts | 由 canonical store 定義 stable id 與附件關係 |
| 每筆 `只收錄／收錄並整理`、預設值、可重跑 | 所有受查產品 | 自訂 record metadata 與狀態機 |
| 離線收錄後的可靠 AI queue、retry、idempotency | 所有受查產品 | repo-owned worker、錯誤狀態及測試 |
| 保證 AI 永不覆寫來源 | Typeless、Apple Writing Tools 的 replace 流程 | 將來源與衍生區段設成不可混淆的 schema |
| 從 Voice Memos 或其他 inbox 搬入後不重複、不孤兒 | 語音備忘錄、Drafts | import receipt、dedupe key、明確刪除策略 |
| 可稽核的雲端 AI consent boundary | Apple Intelligence／Typeless 提供自己的 fixed flow | 只有明確處理模式允許 worker 送出；保留 provider/model/status metadata |

## 建議交給後續 ticket 的決策

- 「製作並比較 v1 收錄與回顧流程原型」：以 Apple 備忘錄和 Obsidian 混合方案各做一個低成本 prototype，實測步數、離線、同步時間、失敗可見性與同一筆記錄感受。
- 「定義 AI 整理結果與處理設定」：定義 record metadata、來源不可變區、逐字稿區、AI 衍生區及 `pending/running/completed/failed` 狀態；不要把 UI label 當真正狀態。
- 「定義記錄的編輯、刪除、版本與失敗恢復行為」：特別處理 Obsidian note 與音訊附件不同步刪除、worker retry、重複匯入及 Sync version history 不等於 backup。
- 「選定 v1 的拼裝、自建或混合路線」：預設採混合；只有 prototype evidence 能把它推翻。

## Research ledger

| Question | Claim | Source | Gap | Action |
| --- | --- | --- | --- | --- |
| Apple 備忘錄能否讓來源與衍生內容留在同一筆記錄？ | 一則備忘錄可含錄音、逐字稿、可搜尋文字及 AI 摘要 | [Apple Notes audio/transcript](https://support.apple.com/en-gb/guide/iphone/iphbe11247b5/26/ios/26)、[Apple Intelligence in Notes](https://support.apple.com/en-mide/guide/iphone/iph59143007d/ios) | 自訂 AI 的背景觸發與寫回 API 未證實 | 做 Shortcuts action inventory prototype；未證實前不選為完整 v1 |
| Apple 備忘錄是否 local-first？ | 「我的 iPhone」只在單機；iCloud 才跨裝置；ADP 可讓 Notes E2EE | [Notes accounts](https://support.apple.com/en-gb/guide/iphone/iph7262fd4fe/ios)、[ADP](https://support.apple.com/en-euro/guide/iphone/iph584ea27f5/ios) | 無透明檔案庫；單機 local 與 sync 是不同模式 | 只把它當產品 prototype，或明確接受 Apple-managed store |
| 語音備忘錄是否能作最低摩擦入口？ | Action Button 可直接啟動 Voice Memo；錄音可轉錄並跨 Apple 裝置同步 | [Action Button](https://support.apple.com/en-us/125089)、[transcript](https://support.apple.com/en-gb/guide/iphone/iph00953a982/26/ios/26)、[sync](https://support.apple.com/guide/voice-memos/see-your-recordings-on-all-your-apple-devices-vma6cc4d0571/mac) | 其 identity 是錄音，不能容納完整文字 record 與處理狀態 | 僅當 fallback；若匯入 canonical store，必須設計 receipt 與 dedupe |
| Typeless 能否兼任來源保存與 AI 整理？ | 能在任意文字欄輸出整理後文字，但音訊經雲端處理後丟棄 | [Typeless first dictation](https://www.typeless.com/help/quickstart/first-dictation)、[Privacy](https://www.typeless.com/privacy) | 來源錄音不可保留；也不是 record store | 僅列為選配輸入法，不進 canonical pipeline |
| Typeless 的成本與 privacy boundary 是什麼？ | Free 每週 8,000 words；Pro 年繳 USD 12/月；zero cloud retention、on-device history | [Typeless Pricing](https://www.typeless.com/pricing) | 仍需把音訊與 context 送上雲端；history 不等於來源音訊 | 使用時視為雲端 AI 輸入，不能套用「只收錄」語意 |
| Obsidian 能否當 local-first canonical store？ | vault 是本地 Markdown folder，離線可用；Sync 時裝置仍保有 local copy | [How Obsidian stores data](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)、[Sync across devices](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices) | iPhone 收錄與背景 AI 不是 core 能力 | 用 thin custom capture/worker 補缺，不重做 editor/search |
| Obsidian 如何呈現同一筆錄音記錄？ | Audio recorder 把音訊存入 vault 並 embed 進目前 note | [Audio recorder](https://obsidian.md/help/plugins/audio-recorder) | 移除 embed 不會刪附件；底層是兩個檔案 | product 視為同一 record，技術上定義 attachment lifecycle |
| Obsidian 的同步隱私與限制？ | Sync 預設 E2EE；iCloud 可搭 ADP；Google Drive 不受官方支援用於 iOS vault | [Sync security](https://obsidian.md/help/sync/security)、[sync methods](https://obsidian.md/help/Getting%2Bstarted/Sync%2Byour%2Bnotes%2Bacross%2Bdevices)、[Apple iCloud security](https://support.apple.com/en-mide/102651) | Sync Standard 單檔 5 MB 對錄音不足；iCloud 有 offload/競態風險 | 交同步研究 ticket 比較 Plus 與 iCloud ADP，並做實機壓力測試 |
| Drafts 能否成為快速 capture front end？ | 文字 capture、dictation、Shortcuts、action 很完整，資料 local + iCloud sync | [Drafts Getting Started](https://docs.getdrafts.com/gettingstarted/)、[Shortcuts](https://docs.getdrafts.com/docs/automation/shortcuts-reference)、[Privacy](https://getdrafts.com/support/privacy) | 會多一個 datastore 與 identity handoff | 除非 prototype 證明顯著勝過直接 Shortcut → vault，否則不加入 v1 |
| Drafts 能否保留錄音來源？ | 官方只記載從音訊抽取並建立轉寫文字，沒有同 draft 音訊附件模型 | [Drafts transcription](https://docs.getdrafts.com/docs/editor/transcription.html) | 不能從 primary docs 證明符合來源保留 | 判定不合格；不靠假設或社群 workaround 補分 |
| 現成產品是否已完整滿足需求？ | 依上述矩陣，沒有產品同時通過全部七項基準 | 上述 Apple、Typeless、Obsidian、Drafts 第一方來源 | 結論是跨來源比較所得 inference，不是某家廠商的宣稱 | 進行 Apple Notes 與 Obsidian hybrid 雙 prototype |
| 何時應自建完整 App？ | 只有 hybrid 的 iOS 離線收錄或 Mac reliable worker 被 evidence 證明不可行時才合理 | 本研究的 gap analysis | 尚無 prototype evidence | 先驗證兩個危險假設，再由選路 ticket 決定 |

## 研究邊界

- 僅採官方文件、官方 pricing/privacy 頁面與官方 developer docs；沒有把評測文章、論壇 anecdote 或未驗證社群 plugin 當產品能力。
- 本 ticket 不選定 transcription／LLM provider，也不比較 API 成本；由「研究雲端語音轉寫與 AI 整理方案」處理。
- 本 ticket 不選定 Obsidian Sync 或 iCloud；只排除官方明示不支援 iOS vault 的 Google Drive，最終選擇由同步研究 ticket 處理。
- `未發現官方介面` 只代表目前不能把能力寫進規格，不等於形式證明技術上永遠不可能；需以 prototype 補證。
