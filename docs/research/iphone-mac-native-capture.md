# 研究：iPhone 與 Mac 的原生收錄入口

研究日期：2026-07-27
對應 ticket：[研究 iPhone 與 Mac 的原生收錄入口](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/2)

## 結論

v1 最值得驗證的原生入口是 **Action Button → 自訂 Shortcut → 檔案型 inbox**。Shortcut 應在收錄當下產生自己的 `record_id`、時間、來源類型與處理模式，將來源內容與 manifest 寫成同一個 record bundle；跨裝置通道可先用 iCloud Drive，但同步與備份的最終選型仍交給另一張 storage ticket。

Apple 備忘錄與語音備忘錄都可保留為人類友善的替代入口：

- 備忘錄最接近「同一筆記錄包含文字、錄音、逐字稿」的產品語意，但 Apple 公開文件目前只提供逐筆、互動式的 Markdown 與附件匯出，沒有可據以設計可靠背景 ingest 的批次附件匯出契約。
- 語音備忘錄提供最短的單鍵錄音路徑、原生逐字稿與 iCloud 同步，但公開的音訊匯出也是逐筆分享／存到 Files；它不是文字與錄音的統一記錄庫。
- Share Sheet 與 Quick Note 適合從其他 App 明確收錄既有文字或附件，應是第二入口，不應取代 Action Button 的快速收錄。

因此，**不要先把備忘錄資料庫或語音備忘錄資料庫當成唯一權威來源**。先做一個真機 prototype，驗證 Shortcut 能否在目標 iPhone 上，於鎖定、離線、長錄音與被電話／其他音訊打斷等情境下，可靠產生完整 record bundle；通過後才把它定為 v1 主入口。

## 候選比較

| 候選 | 收錄速度 | 同一筆記錄語意 | Mac 背景流程可讀性 | 離線／失敗可觀測性 | v1 判斷 |
| --- | --- | --- | --- | --- | --- |
| Action Button → Shortcut → 檔案型 inbox | 高；一個實體按鈕可執行指定 Shortcut | 可由自有 manifest 與資料夾維持 | 高；Mac 可監看一般檔案，Shortcuts CLI 也可接檔案／文字 | 可設計本地先寫與狀態檔，但需真機驗證鎖定與中斷 | **首選 prototype** |
| 備忘錄（文字＋內建錄音） | 中；需進入或打開 note | **最高**；錄音與逐字稿就在 note 中 | 低至中；macOS 26 可逐筆匯出 Markdown、另存附件，但官方未提供背景批次匯出契約 | iCloud 同步容易使用，但 ingest 是否完成不易由外部流程判定 | 人類檢視／備援入口，不先當 pipeline boundary |
| Action Button → 語音備忘錄 | **最高（純錄音）** | 低；只有錄音與原生逐字稿 | 低至中；可同步到 Mac、可手動匯出 `.m4a`，但未見官方事件或 watch-folder 契約 | 原始錄音本地先產生；同步狀態與外部 ingest 狀態仍分離 | 純錄音 fallback；不作唯一入口 |
| Share Sheet → 收錄 Shortcut | 中；需選內容、Share、再選 Shortcut | 可將既有內容包成同一筆記錄 | 高；輸入類型與輸出檔可自行定義 | Shortcut 不匹配輸入類型時不會出現；權限也可能先詢問 | 必要的第二入口 |
| Quick Note | 中；Control Center 或支援 App 的 Share | 文字、連結、圖片可同處 | 低；仍受 Notes 的匯出邊界限制 | 需要使用者按 Save；適合快速文字，較不適合無感背景 ingest | 可選便利入口 |

## 第一方證據與限制

### 1. Action Button 可直接錄音，也可執行自訂 Shortcut

Apple 允許 Action Button 直接選擇 Voice Memo，或選擇 Shortcut 來開啟 App／執行指定 shortcut；Shortcut 類型若沒有再指定具體 shortcut，按鈕不會有作用。[Apple：Use and customize the Action button on iPhone](https://support.apple.com/guide/iphone/iphe89d61d66/ios)、[Apple：Run shortcuts with the Action button](https://support.apple.com/guide/shortcuts/apdfea15680b/ios)

這使兩條路都成立：

- 追求最少摩擦的純錄音：Action Button 直接綁 Voice Memo。
- 追求文字／錄音統一、可選 `處理模式` 與可觀測交付：Action Button 綁自訂 Shortcut。

後者更符合本產品，但 Apple 的公開指南沒有保證所有 shortcut action 都能在鎖定畫面執行。Apple 明確指出：若 Siri 執行的 shortcut 需要開啟 App，裝置鎖定時會要求解鎖；Shortcuts 也會按所需資料顯示 Allow Once／Always Allow 等權限提示。[Apple：Use Siri to run shortcuts with your voice](https://support.apple.com/guide/shortcuts/apd07c25bb38/ios)、[Apple：Adjust basic privacy settings in Shortcuts](https://support.apple.com/guide/shortcuts/apd961a4fc65/ios)

所以「鎖定時是否能完整錄音並存檔」不能只靠文件推定，必須用目標 iPhone 實測。

### 2. Shortcuts 能承接多入口，但輸入與權限必須明確配置

Shortcut 可啟用 `Show in Share Sheet`，並限制可接受的輸入類型；若來源 App 沒有相符內容，該 shortcut 可能不會出現在 Share Sheet。Apple 也明列 `Save File` 與 `Append to Note` 等 share actions。[Apple：Launch a shortcut from another app](https://support.apple.com/guide/shortcuts/apd163eb9f95/ios)、[Apple：About share actions in Shortcuts](https://support.apple.com/guide/shortcuts/apdaf74d75a5/ios)

Apple 的 Shortcuts 更新紀錄另確認 Notes 有 Create／Find／Move／Add Tags 等 actions，Voice Memos 有 Search Voice Memos 與 Create Recording 等 actions。[Apple：What’s new in Shortcuts](https://support.apple.com/101583)

這些能力足以建立原型，但更新紀錄不是完整的 action I/O 規格；尤其 `Create Recording` 是否能在 Action Button 路徑中直接交出可供 `Save File` 使用的音訊物件，官方公開文件沒有說清楚。若輸出只能留在 Voice Memos，仍會回到「錄完後再匯出」的斷點。

### 3. 備忘錄最符合單一記錄 UX，但自動匯出邊界不夠強

在 iPhone 12 或更新機型，且裝置語言設為支援語言（包含繁體中文）時，備忘錄可在同一 note 中錄音並自動產生逐字稿；使用者可搜尋逐字稿、將逐字稿加入 note、複製逐字稿、保存音訊。刪除錄音也會一併刪除逐字稿。[Apple：Record and transcribe audio in Notes on iPhone](https://support.apple.com/guide/iphone/iphbe11247b5/ios)

這正好符合 `記錄` 的呈現語意，但輸出仍偏人工：macOS Tahoe 26 支援將單筆 note 匯出 Markdown，音訊附件則可在 Notes 中另存；Apple 指南沒有描述批次、無人值守或增量匯出。[Apple：Import, export, and print notes on Mac](https://support.apple.com/guide/notes/not201900c07/mac)、[Apple：Record and transcribe audio in Notes on Mac](https://support.apple.com/guide/notes/apdb5106e334/mac)、[Apple：View attachments in Notes on Mac](https://support.apple.com/guide/notes/apd9953dabf9/mac)

Notes 的帳號位置也有重要取捨：`On My iPhone` 只存在該 iPhone；iCloud Notes 才會出現在同 Apple Account 的 iPhone、iPad 與 Mac。[Apple：Add or remove accounts in Notes on iPhone](https://support.apple.com/guide/iphone/iph7262fd4fe/ios)

因此 Notes 可作為體驗參考或人工入口，但若 v1 要在 Mac 上自動 AI 處理，不能把未公開的內部資料庫格式或 UI automation 當成穩定契約。

### 4. 語音備忘錄是可靠的純錄音入口，但不是統一 ingest

Voice Memos 會先建立來源錄音；啟用 iCloud 後，錄音會自動出現在使用同 Apple Account 的 iPhone、iPad 與 Mac。初始名稱是 `New Recording`，或在允許 Location Services 時使用地點名稱。錄音可放進 folders、標成 favorite，並可依標題與逐字稿搜尋。[Apple：Make a recording in Voice Memos on iPhone](https://support.apple.com/guide/iphone/iph4d2a39a3b/ios)、[Apple：Keep recordings up to date](https://support.apple.com/guide/iphone/iph38b91c7af/ios)、[Apple：Organize recordings](https://support.apple.com/guide/iphone/iph73bfaba07/ios)

Voice Memos 的逐字稿同樣要求 iPhone 12 或更新機型、支援語言／地區；可複製全部逐字稿，但 Apple 沒有描述逐字稿與音訊一起批次輸出的 API。[Apple：View a Voice Memos transcription on iPhone](https://support.apple.com/guide/iphone/iph00953a982/ios)

音訊可人工匯出到 Files，預設是 `.m4a`；分層錄音會被攤平、Spatial Audio 會轉成 stereo，除非分享時另選 editable 選項。[Apple：Export a Voice Memos recording to Files on iPhone](https://support.apple.com/guide/iphone/iph831c37815/ios)

已知失敗模式包含：錄音期間若另一個 App 開始播放音訊，Voice Memos 會停止錄音；不同 OS 世代也可能因加密格式變更而無法同步標題。[Apple：Make a recording in Voice Memos on iPhone](https://support.apple.com/guide/iphone/iph4d2a39a3b/ios)、[Apple：If your Voice Memos titles changed to dates](https://support.apple.com/105006)

### 5. iCloud Drive 是可觀測的原生橋接候選，不等於權威備份

Files 可將指定檔案設為 `Keep Downloaded`；Apple 明確說明，離線修改會在重新上線後與 iCloud 同步。Mac Finder 會顯示 `Waiting to Upload`、`Out of Space`、`Ineligible`、`Downloaded` 等狀態；`Keep Downloaded` 可避免 Mac 因空間最佳化只留下雲端 placeholder。[Apple：Transfer files from iPhone to a storage device, a server, or the cloud](https://support.apple.com/guide/iphone/iphe9aff429a/ios)、[Apple：Check your iCloud Drive file and folder status on Mac](https://support.apple.com/guide/mac-help/mchlc994344b/mac)

這讓檔案型 inbox 比 Notes／Voice Memos 更適合 Mac 背景流程：處理器可以等完整 manifest 與來源檔都出現後才 claim，而不是把「iCloud 中看得到」誤當成「完整收錄成功」。不過 iCloud Drive 的選用、備份與復原策略仍需由 storage research 決定。

Mac 端還可用官方 `shortcuts` CLI 接收文件、文字或圖片並輸出檔案；CLI 成功時 exit code 為 `0`、錯誤為 `1`，但任何會顯示 alert 或詢問輸入的 shortcut 都會阻塞，因此背景流程必須完全非互動。[Apple：Run shortcuts from the command line](https://support.apple.com/guide/shortcuts-mac/apd455c82f02/mac)

### 6. iCloud 隱私要明確設定，不能把「Apple 原生」等同端對端加密

在預設 Standard Data Protection 下，iCloud Drive、Notes、Shortcuts 與 Voice Memos 是傳輸中及伺服器上加密，但金鑰由 Apple 保管；啟用 Advanced Data Protection 後，這些類別才改為端對端加密、金鑰只在 trusted devices。[Apple：iCloud data security overview](https://support.apple.com/102651)

因此若 v1 使用 iCloud 作為橋接，應把是否啟用 Advanced Data Protection 納入部署 checklist；同時要設 recovery contact 或 recovery key，因為啟用後 Apple 無法代為復原資料。

## 建議的 v1 capture contract

這是本 ticket 對後續 prototype 的輸入，不是最終 storage ADR：

1. 建立一個「收錄」Shortcut，並綁定 Action Button；預設使用全域 `處理模式`，只有需要覆寫時才顯示 `只收錄`／`收錄並整理` 選項。
2. 文字由 Shortcut 的輸入或 Share Sheet 取得；錄音路徑先比較「Shortcut 直接產生音訊檔」與「Voice Memos Create Recording 後取得 recording」兩種，只有能產生可驗證來源檔的路徑才通過。
3. 收錄一開始就在 iPhone 產生 UUID `record_id`，不要依賴 Notes title、Voice Memos 地點名稱或檔名當 identity。
4. 每筆記錄寫入單一資料夾，例如 `inbox/<record_id>/`；至少包含來源檔與 `record.json`。manifest 最少含 `schema_version`、`record_id`、`captured_at`、`source_type`、`capture_surface`、`processing_mode`、`source_filename`。
5. 最後才以原子方式產生 `ready` marker；Mac 只處理具有 marker 且來源檔存在的 record bundle，並將 inbox 設為 `Keep Downloaded`。
6. 備忘錄、語音備忘錄與其他 App 透過 Share Sheet 明確送入同一 Shortcut；未送入的內容不算 `收錄`。
7. 原生逐字稿只作為可選附加來源，不能取代來源錄音；若無法可靠匯出，就由後續 transcription pipeline 重新產生。

## 真機 prototype 的通過條件

在決定主入口前，至少執行以下測試並保存結果：

- iPhone 鎖定與解鎖各收錄一次文字、一次短錄音。
- 飛航模式收錄，重開機後確認來源仍在，再上線確認 Mac 收到完整 bundle。
- 30 分鐘錄音，以及 iCloud 空間不足情境；失敗不得產生 `ready` marker。
- 收錄中接電話、開啟會播放音訊的 App、鎖屏、切換 App；確認來源是否完整及狀態是否可判讀。
- 第一次執行的 microphone、Files、Notes／Voice Memos 權限提示，以及之後的穩定行為。
- 繁體中文與中英夾雜錄音，確認 Apple 原生逐字稿的可用性，但不以準確率作為來源保存成功的 gate。
- Share Sheet 分別輸入純文字與 `.m4a`，驗證不支援的 input type 會清楚失敗。
- Mac 關機時連續收錄多筆，之後開機確認不重複、不漏件，且處理順序不依賴檔名排序。

## 未決 gaps

- 目標 iPhone 型號、iOS 版本，以及是否願意啟用 Advanced Data Protection 尚未確定。
- Apple 公開文件沒有完整定義 Shortcuts `Create Recording` 的 output type，以及從鎖定畫面執行時的行為。
- 尚未證實 Shortcut 可在中斷與長錄音下，直接產生可交付到 Files 的完整音訊檔。
- Notes／Voice Memos 沒有在所查官方資料中提供適合背景增量 ingest 的公開附件 API 或事件通知。
- iCloud Drive、其他同步服務或自建同步的最終選擇，必須等待 storage research；本研究只確認 iCloud Drive 是 Apple 原生且可觀測的候選。

## Research ledger

| Question | Claim | Source | Gap | Action |
| --- | --- | --- | --- | --- |
| Action Button 能否作為統一入口？ | 可直接啟動 Voice Memo，也可執行指定 Shortcut。 | [Action Button guide](https://support.apple.com/guide/iphone/iphe89d61d66/ios) | 鎖定畫面下各 action 的實際限制未完整記載。 | 真機測試鎖定／解鎖與首次權限。 |
| 能否從任何 App 明確收錄？ | Share Sheet 可把支援的內容類型交給 Shortcut；不相容時 shortcut 可能不顯示。 | [Launch from another app](https://support.apple.com/guide/shortcuts/apd163eb9f95/ios) | 各來源 App 實際送出的 UTI／metadata 未列全。 | 以文字與 `.m4a` 建立輸入矩陣測試。 |
| Shortcut 能否寫入可被 Mac 讀取的資料？ | 有 `Save File`；Mac 的 `shortcuts` CLI 可收／出檔案並回報 exit code。 | [Share actions](https://support.apple.com/guide/shortcuts/apdaf74d75a5/ios)、[Shortcuts CLI](https://support.apple.com/guide/shortcuts-mac/apd455c82f02/mac) | iPhone 錄音 action 是否直接輸出檔案未公開說清楚。 | prototype 兩種錄音路徑，要求產出可驗證來源檔。 |
| 備忘錄能否維持同一筆記錄？ | 一個 note 可同時保有音訊、逐字稿與文字，繁中在支援範圍。 | [Notes audio transcription](https://support.apple.com/guide/iphone/iphbe11247b5/ios) | 缺少可靠背景批次附件匯出契約。 | 將 Notes 定位為 UX／人工入口，不先作 pipeline authority。 |
| 語音備忘錄能否自動交給 Mac？ | iCloud 可讓錄音自動出現在 Mac；人工可匯出 `.m4a`。 | [Voice Memos sync](https://support.apple.com/guide/iphone/iph38b91c7af/ios)、[export to Files](https://support.apple.com/guide/iphone/iph831c37815/ios) | 未找到官方事件通知或 watch-folder API；逐字稿也沒有批次輸出規格。 | 保留為純錄音 fallback，另驗證 Shortcut ingest。 |
| 離線收錄後能否延後同步？ | Keep Downloaded 的 iCloud Drive 檔案可離線修改，回線後同步；Finder 有 waiting／out-of-space 狀態。 | [Files offline](https://support.apple.com/guide/iphone/iphe9aff429a/ios)、[iCloud status](https://support.apple.com/guide/mac-help/mchlc994344b/mac) | 尚未針對 Shortcut 新建大型音訊檔實測。 | 以飛航模式、重開機與 30 分鐘錄音驗證。 |
| Apple 原生同步是否端對端加密？ | 預設不是；開啟 Advanced Data Protection 後，iCloud Drive、Notes、Shortcuts、Voice Memos 才是 E2EE。 | [iCloud security](https://support.apple.com/102651) | 使用者是否願意承擔 recovery key／contact 責任未定。 | storage 決策與部署 checklist 必須處理。 |
| 哪些 metadata 可當永久 identity？ | Voice Memos title 可能是地點或 `New Recording`，且跨舊 OS 曾有 title 相容問題。 | [Voice Memos recording](https://support.apple.com/guide/iphone/iph4d2a39a3b/ios)、[title compatibility](https://support.apple.com/105006) | Apple App 內部 identity 並非公開跨 App 契約。 | 收錄當下自行生成 UUID 與 manifest，不以 title／filename 去重。 |
