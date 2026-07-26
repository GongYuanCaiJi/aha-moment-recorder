# 本地優先的儲存、同步與備份方案研究

研究日期：2026-07-27
對應 ticket：[研究本地優先的儲存、同步與備份方案](https://github.com/GongYuanCaiJi/aha-moment-recorder/issues/3)

## 問題

哪些儲存、跨裝置同步與備份方案能同時滿足：本地資料為權威來源、iPhone 與 Mac 離線可用、支援文字與錄音、可察覺同步失敗、具備合理的加密與衝突處理，並保留未來與 Obsidian 互通的可能？

本研究只比較決策所需能力，不決定最終資料模型，也不進行產品實作。

## 結論

v1 最值得優先驗證的路線是：

> **以每台裝置都有完整本地副本的檔案型記錄庫為權威資料，先用 Obsidian Sync 做 iPhone／Mac 同步，再以 Mac 上的獨立版本化備份保護資料。**

理由不是「一定要用 Obsidian」，而是它目前最完整地同時滿足以下條件：

- 每台裝置保留 local vault，離線仍可使用；離線變更會排隊，在重新連線且 Obsidian 開啟後同步。
- 文字以 Markdown 純文字檔保存，錄音可作為附件，格式可攜性高；即使未來不用 Obsidian，也不必先搬出封閉資料庫。
- Obsidian Sync 預設可選端對端加密（E2EE），遠端服務無法讀取內容。
- iPhone 與 Mac 都有同步狀態；活動紀錄會列出上傳、下載、刪除、衝突與連線問題。
- 提供筆記與附件的版本歷史，但附件舊版本目前只保留兩週，因此 **Sync 與版本歷史仍不能取代獨立備份**。

第二順位是 **iCloud Drive 檔案庫**：若在 iPhone 與 Mac 明確使用 `Keep Downloaded`，並啟用 Advanced Data Protection，它能形成 Apple 生態內的本地副本與端對端加密同步，且 Obsidian 官方支援 iOS／macOS 的 iCloud vault。不過同步衝突與錯誤的產品可見性較弱，必須另做驗收測試。

若後續決定自行開發 App，最合理的 Apple-native 基線是 **本地持久層 + CloudKit mirror**，不是把 CloudKit 當唯一資料庫。Apple 明確把 `NSPersistentCloudKitContainer` 描述為維持 local replica 的方案；需要更強控制時可用 `CKSyncEngine`，但衝突、帳號變更、不可自動恢復的錯誤、匯出與同步狀態都會變成自有產品責任，因此不應在 research 階段直接假設要走這條路。

Google Drive、Nextcloud 與 Syncthing 都有用途，但不適合直接成為這個 iPhone-first v1 的首選權威記錄庫：

- Google Drive 的 Mac mirroring 很完整，但 Obsidian 官方明確標示 Google Drive 在 iOS 上只有有限功能、不是受支援的 vault 同步方式；一般個人 Drive 只有傳輸中與靜態加密，不是使用者持有金鑰的 E2EE。
- Nextcloud 可自管且有官方 iOS／macOS clients，也能選 E2EE，但官方 restore 文件把 server 視為預設權威來源；完整備份需要同時保護設定、資料、資料庫等元件，維運面明顯超過 v1 所需。
- Syncthing 是直接裝置對裝置同步，傳輸加密、衝突副本與 file versioning 都清楚；但官方明確不支援 iOS，且指出 iOS 背景執行限制會影響可靠性，因此不能當 iPhone-first 主路線。

## 「本地資料為權威來源」的驗收定義

這裡的「本地優先」不等於「完全不用雲端」，而是同步服務不能成為唯一可讀的一份資料。建議後續規格用以下可測條件定義：

1. **先本地落盤**：收錄成功的判定只依賴來源內容已安全寫入本機；沒有網路時仍能建立記錄。
2. **完整本地副本**：iPhone 與 Mac 至少各有一份可離線讀取的記錄；Mac 需能保有完整文字與錄音，而不是只留雲端 placeholder 或暫存 cache。
3. **背景同步可重試**：同步失敗不會刪除本地來源內容；恢復網路後能自動或明確手動重試。
4. **失敗可察覺**：每筆記錄或至少全域必須有等待、同步中、已同步、失敗／衝突等狀態，不能只靠「過一陣子應該會到」。
5. **衝突不靜默覆寫來源內容**：兩台裝置離線修改同一筆記錄後，兩邊資訊都必須可恢復。
6. **同步與備份分離**：跨裝置刪除會被同步傳播，因此另需一份有歷史版本、能做還原驗證的備份。
7. **可攜性**：能把記錄的來源內容、逐字稿、AI 整理結果、metadata 與錄音附件完整匯出，不依賴特定供應商才能讀取。

## 候選比較

評等：`佳` 表示官方能力直接滿足；`可` 表示需要設定或補強；`弱` 表示有明顯缺口；`不適合` 表示違反本次核心條件。

| 候選 | 本地權威與離線 | iPhone／Mac | 文字與錄音 | 同步失敗可見性 | 加密 | 衝突處理 | 備份 | 可攜性／Obsidian |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Obsidian Sync + local vault** | **佳**：每台裝置保留 local vault；離線變更排隊 | **佳**：官方支援 iOS、macOS | **佳**：Markdown + 任意附件 | **佳**：狀態 icon、activity log、errors、skipped、merge conflicts | **佳**：remote vault 預設可用 E2EE；本地檔案本身不由 Obsidian 加密 | **佳／可**：可合併衝突、保留歷史並顯示 log；仍需測同時離線編輯 | **可**：有版本歷史但附件只保留兩週，仍需獨立備份 | **佳**：原生就是 Obsidian vault 與普通檔案 |
| **iCloud Drive 檔案庫** | **佳／可**：兩端 `Keep Downloaded` 後可離線；未固定下載時可能只在雲端 | **佳**：Apple 原生整合 | **佳**：一般檔案皆可 | **可**：Mac Finder 顯示 waiting、out of space、transfer progress；產品內整體狀態需另驗證 | **佳／可**：啟用 Advanced Data Protection 後 iCloud Drive、Notes、Voice Memos 可 E2EE；預設保護不是同等 E2EE | **可／弱**：本次官方文件沒有提供足夠的跨 App 衝突保證，必須實測 | **可**：Recently Deleted 與 Time Machine 可補強，但同步本身不是備份 | **佳**：Obsidian 官方支援 Apple 平台的 iCloud vault；需固定下載 |
| **本地持久層 + CloudKit（自製 App）** | **佳**：Core Data 可離線持久化；CloudKit 作 mirror | **佳**：Apple 平台原生 | **佳**：結構資料 + `CKAsset`／檔案可設計 | **取決於實作**：框架提供 pending changes、成功／失敗 events，使用者介面需自行建立 | **佳／可**：受 iCloud 保護模式影響；仍要設計本地裝置保護 | **取決於實作**：`serverRecordChanged` 需 App 合併 client/server/ancestor | **弱／可**：CloudKit 可作遠端副本，但匯出與獨立備份需自行做 | **弱／可**：需另做 Markdown／附件匯出或雙向橋接 |
| **Google Drive 檔案庫** | **可**：Mac mirroring 有完整 local copy；iPhone 需逐項標示 offline | **弱**：Drive 可在兩端使用，但 Obsidian 不支援 iOS Google Drive vault | **佳**：一般檔案皆可 | **佳／可**：Mac 有 sync status、activity 與重要錯誤通知；iOS 整體可見性需驗證 | **可／弱**：一般個人資料為傳輸中與靜態加密；client-side encryption 限受管理的 Workspace 情境 | **可／未知**：文件顯示部分情境會保留兩份，但一般同時編輯語意仍需驗證 | **可**：雲端副本不等於獨立備份 | **佳／弱**：檔案可攜，但 iOS Obsidian 整合不適合作主路徑 |
| **Nextcloud（自管）** | **可**：desktop client 有本地同步資料；但官方 restore 語意預設 server 為權威 | **可**：官方 desktop／iOS clients | **佳**：一般檔案皆可 | **佳／可**：desktop client 有 status、log 與 conflict 通知；iOS 背景可靠性仍需驗證 | **佳／可**：可用 client E2EE；Web 對 E2EE folder 目前唯讀且金鑰遺失不可恢復 | **佳／可**：建立 conflicted copy 並通知使用者；需人工合併 | **弱**：自管者必須備份 config、data、database 等並驗證 restore | **佳／可**：檔案可攜；與 iOS Obsidian 的完整體驗需 prototype |
| **Syncthing** | **佳**：裝置間直接同步，不把雲端當權威 | **不適合**：官方沒有 iOS client，官方指出背景限制影響可靠性 | **佳**：一般檔案皆可 | **佳／可**：GUI、logs、audit log 可見 | **佳／可**：裝置間 TLS；本地 at-rest 保護另處理 | **佳**：產生並同步 `sync-conflict` 副本 | **可／弱**：versioning 預設關閉，且只保存來自其他裝置造成的替換／刪除 | **佳／弱**：檔案可攜，但 iPhone-first 條件不成立 |

## 候選詳解

### 1. Obsidian Sync：最適合先做 v1 驗證

Obsidian 官方說明指出，notes 存在裝置本地，即使離線也可存取；Obsidian Sync 會在每台裝置保留 local copy，遠端 vault 是同步副本。離線變更會在重新連線且 Obsidian 開啟時自動同步。這和「本地資料是權威來源、雲端只作輔助」最接近。[同步方法](https://obsidian.md/help/sync-notes)、[local 與 remote vault](https://obsidian.md/help/Obsidian%2BSync/Local%2Band%2Bremote%2Bvaults)

記錄可保留為 Markdown 純文字，錄音則作附件；這並不要求來源錄音、逐字稿與 AI 結果在底層必須硬塞進單一實體檔案，而是要求它們在同一個記錄識別與同一個使用者介面下被管理。底層可先保留「一份 Markdown + 相鄰附件」或「一個 record folder」的可逆選項。[Obsidian 資料儲存方式](https://obsidian.md/help/data-storage)

隱私方面，Obsidian Sync 的 remote vault 可用預設 E2EE；官方說明其內容離開裝置時即加密，只有持有密碼的裝置能解密。不過 Obsidian 不加密 local vault，所以仍要靠 iPhone passcode／Data Protection 與 Mac FileVault 保護裝置遺失風險。此外，遺失 E2EE 密碼時 Obsidian 無法復原 remote vault，因此 recovery secret 必須獨立保存。[安全與隱私](https://obsidian.md/help/Obsidian%2BSync/Security%2Band%2Bprivacy)

同步可觀測性是此候選的明顯優勢：desktop 與 mobile 都有 synced、syncing、paused、disconnected 狀態；activity log 可篩選 errors、skipped 與 merge conflicts。限制是 activity log 在 App 關閉後不保留，因此產品若需要長期、逐筆的同步稽核，仍需自建 metadata 或 log。[同步狀態與訊息](https://obsidian.md/help/Obsidian%2BSync/Status%2Bicon%2Band%2Bmessages)

版本歷史可還原筆記、刪除項目與附件，但官方目前只為附件保留兩週舊版本；筆記依方案保留一個月或十二個月。這足以處理近期誤刪或衝突，但不能當長期備份。[版本歷史](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory)

### 2. iCloud Drive：Apple-only 的低摩擦次選

iCloud Drive 可同步一般檔案。Apple 在 iPhone 與 Mac 都提供 `Keep Downloaded`：iPhone 離線修改會在恢復連線後同步；Mac Finder 也能標示 `In iCloud`、`Downloaded`、`Keep Downloaded`、`Waiting to Upload`、`Out of Space` 與傳輸進度。[iPhone 保持下載](https://support.apple.com/en-ie/guide/iphone/iphe9aff429a/ios)、[Mac iCloud 狀態](https://support.apple.com/en-euro/guide/mac-help/mchlc994344b/mac)

因此，若走 iCloud Drive，完整 vault 在 iPhone 與 Mac 都必須固定下載，不能依賴系統按需 offload。Obsidian 官方也要求 iCloud vault 在 Apple 平台使用正確的 `iCloud Drive/Obsidian/` 位置，並在支援的 macOS 上對 vault 使用 `Keep Downloaded`；Google Drive、Dropbox、OneDrive 與 Syncthing 則不是 Obsidian iOS 的正式支援同步路線。[Obsidian 跨裝置同步](https://obsidian.md/help/sync-notes)

iCloud 預設會加密傳輸中與靜態資料，但部分金鑰由 Apple 保存。啟用 Advanced Data Protection 後，iCloud Drive、Notes 與 Voice Memos 等類別改為 E2EE，Apple 無法解密；代價是使用者負責 account recovery。[iCloud security overview](https://support.apple.com/guide/security/icloud-security-overview-secacde2d0da/web)、[Advanced Data Protection](https://support.apple.com/en-euro/guide/iphone/iph584ea27f5/ios)

主要缺口是：本次找到的 Apple 文件能證明離線副本與狀態 icon，但沒有提供足夠細緻、可直接轉成產品保證的 concurrent edit／conflict 語意。因此必須以真機 prototype 驗證「兩端離線改同一 Markdown、同名錄音附件、刪除與重新命名、iCloud 空間不足」等情境，再決定是否可當唯一同步層。

### 3. CloudKit：若自製 App，應採 local store mirrored to cloud

Apple 明確說明 `NSPersistentCloudKitContainer` 會維持資料的 local replica；Core Data 本身可保存永久資料供 offline 使用。若需要精細控制，`CKSyncEngine` 會追蹤 pending changes，依系統條件排程同步，並透過 events 回報 batch 成功或失敗。[選擇 CloudKit 方案](https://developer.apple.com/documentation/cloudkit/deciding-whether-cloudkit-is-right-for-your-app)、[Core Data](https://developer.apple.com/documentation/coredata/)、[CKSyncEngine](https://developer.apple.com/documentation/cloudkit/cksyncengine-5sie5)

但 CloudKit 並不替產品完成所有語意：暫時性網路或服務錯誤可自動重試，`serverRecordChanged` 等需要 App-specific logic 的錯誤仍需自行解決；CloudKit 會提供 ancestor、client 與 server records 供合併。帳號登出、iCloud 關閉、quota、局部失敗、刪除傳播、錄音 asset 上傳，以及使用者可看見的逐筆狀態，也都必須自行定義。[CloudKit errors](https://developer.apple.com/documentation/cloudkit/ckerror)、[serverRecordChanged](https://developer.apple.com/documentation/cloudkit/ckerror/serverrecordchanged)

它可以最精準地實現「同一筆記錄包含來源內容、逐字稿與 AI 結果」，但也最容易造成 Apple lock-in。若走這條路，Markdown + attachments 的完整匯出必須是 v1 規格的一部分，而不是未來再補。

### 4. Google Drive：Mac 能力足，iPhone-first 整合不足

Google Drive for desktop 的 `Mirror files` 會在 Mac 與 cloud 都保存完整副本，永遠可離線；`Stream files` 則主要把檔案放在 cloud，只有使用過或手動標示的項目可離線。Drive desktop 也有同步狀態、近期活動與重要錯誤通知。[stream 與 mirror](https://support.google.com/drive/answer/13401938?hl=en)、[Drive for desktop](https://support.google.com/drive/answer/10838124?hl=en)

Google 官方表示一般 Drive 內容有傳輸中與靜態加密；額外的 client-side encryption 需要 Workspace account 且由管理員啟用，不是一般個人 Drive 的預設能力。[Drive privacy](https://support.google.com/drive/answer/10375054?hl=en)、[client-side encryption](https://support.google.com/drive/answer/10519333?hl=en)

即使只把它當普通檔案庫，Obsidian 官方仍明確說 Google Drive 不支援 iOS vault sync。因此它可作未來的獨立 encrypted backup backend，或非 Obsidian 的匯出目的地，但不該作 v1 的主同步層。

### 5. Nextcloud：控制力高，但會把 server lifecycle 帶進產品

Nextcloud desktop client 會同步本地資料夾與 server；若同一檔案兩邊都修改，client 會保留 remote 版、另建 local conflicted copy，並透過 notification、tray icon 與 unresolved conflicts badge 提醒使用者。[desktop client](https://docs.nextcloud.com/server/latest/user_manual/en/desktop/index.html)、[conflicts](https://docs.nextcloud.com/server/latest/user_manual/en/desktop/conflicts.html)

Nextcloud 的 E2EE 在 client 端加密、server 看不到明文；但 E2EE folder 在 Web 目前唯讀，且 mnemonic 遺失就無法恢復。這對單人私密資料有價值，但也增加 recovery 與 client compatibility 的責任。[Nextcloud E2EE](https://docs.nextcloud.com/server/latest/user_manual/en/files/using_e2ee.html)

更重要的是，官方 restore 文件明確說復原後預設由 server 作 authoritative source；若 client 更新、server backup 較舊，需額外執行 `maintenance:data-fingerprint` 才會盡力從 clients 回收資料，而且可能造成 conflict dialogues。完整 server backup 又必須涵蓋 config、data、database 等元件。[backup](https://docs.nextcloud.com/server/latest/admin_manual/maintenance/backup.html)、[restore](https://docs.nextcloud.com/server/latest/admin_manual/maintenance/restore.html)

這和本專案的「本地裝置為權威」原則不完全一致。除非後續有不依賴商用同步服務、且願意長期維護 server 的明確需求，否則 v1 不應先承擔此複雜度。

### 6. Syncthing：架構理念合適，但 iOS 是阻斷缺口

Syncthing 不把資料上傳到中央 cloud，只有被雙方接受的 devices 直接交換資料；device-to-device traffic 使用 TLS。它會把同時修改產生的另一版本改名為 `sync-conflict` 並傳播到各裝置，因此不會靜默抹掉其中一邊。[FAQ](https://docs.syncthing.net/users/faq)、[security principles](https://docs.syncthing.net/users/security)、[synchronization](https://docs.syncthing.net/users/syncing)

File versioning 可保存遠端裝置造成的替換或刪除，但預設關閉，而且不保存同一裝置自己的 local edit 舊版，所以仍不是完整備份。[file versioning](https://docs.syncthing.net/users/versioning)

官方 FAQ 表示沒有計畫正式支援 iOS，原因是 iOS 背景執行限制使可靠同步與系統整合困難。第三方 iOS clients 可以列入未來 prototype，但不能據此承諾 v1 的「錄完後背景自動同步」。

## 建議的 v1 分層

### 權威記錄庫

- 每筆**記錄**保有一個穩定 ID。
- 同一筆記錄在使用者眼中包含來源文字或來源錄音、逐字稿、處理模式與可選的 AI 整理結果。
- 若採檔案型儲存，優先維持可搬移的 Markdown + audio attachment；實體上是否一個 folder、sidecar files 或其他 bundle，留待 prototype 決定。
- AI 只能新增或更新衍生區塊，不能覆寫來源內容。

### 同步層

優先順序：

1. **Obsidian Sync**：先驗證最完整的 local-first／E2EE／status／Obsidian 閉環。
2. **iCloud Drive**：若希望減少外部服務，驗證 `Keep Downloaded` + Advanced Data Protection 的 Apple-only 路線。
3. **CloudKit custom app**：只有在現成工具無法達成收錄與記錄生命週期時才升級到自製。

不要在同一個 active vault 上同時啟用 Obsidian Sync 與 iCloud／Google Drive 等另一套 file sync。Obsidian 官方明確警告混用同步服務可能造成衝突或資料損壞。

### 備份層

不論同步選哪一個，Mac 必須保有完整下載副本，才能做獨立備份：

- 最低基線：使用 encrypted Time Machine disk。Apple 說明 Time Machine 會自動保留過去 24 小時的 hourly backups、過去一個月的 daily backups，以及更早月份的 weekly backups，直到磁碟空間不足。[Time Machine](https://support.apple.com/en-us/104984)
- 若要 off-site：可另用 restic 對完整 local vault 建立 encrypted snapshots，存到另一個 storage backend；restic 可列出／還原 snapshots，並用 `check` 或 `check --read-data` 驗證 repository 完整性。[restic quickstart](https://restic.readthedocs.io/en/stable/010_introduction.html)、[integrity checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html)
- 備份完成不等於可恢復；後續 implementation plan 必須包含實際還原文字與錄音附件的 drill，以及備份密碼／recovery key 的離線保存。

備份頻率、保留期與 off-site backend 尚未有業務或容量依據；不在此研究任意發明數字，交由後續規格按資料量、可接受損失時間與成本決定。

## 必須先 prototype 的風險

在選定同步層前，應以同一組真機情境比較 Obsidian Sync 與 iCloud Drive：

1. iPhone 離線建立一筆文字記錄與一筆長錄音，關閉 App 後恢復網路。
2. Mac 離線修改同一筆文字；兩端之後上線，確認兩邊內容可恢復且衝突可見。
3. 在 iPhone 刪除錄音附件、Mac 同時修改逐字稿，確認刪除與修改結果。
4. 模擬 iCloud／remote vault 容量不足、帳號登出、低電量與 App 長時間未開啟。
5. 確認 Mac 的完整 vault 沒有 placeholder，並能在無網路時讀取所有錄音。
6. 從獨立備份還原一整筆記錄，驗證來源錄音、逐字稿、AI 結果、metadata 與 record ID 都一致。

## Research ledger

| question | claim | source | gap | action |
| --- | --- | --- | --- | --- |
| 怎樣才算本地權威？ | 同步服務可以存在，但 iPhone／Mac 必須有完整 local copy；離線變更排隊，cloud 不能是唯一可讀副本。 | [Obsidian local/remote vaults](https://obsidian.md/help/Obsidian%2BSync/Local%2Band%2Bremote%2Bvaults)、[Apple Keep Downloaded](https://support.apple.com/en-ie/guide/iphone/iphe9aff429a/ios)、[Google mirror](https://support.google.com/drive/answer/13401938?hl=en) | 各產品對「完成落盤」的底層保證不同。 | 把先本地落盤、完整副本、離線可讀與失敗可見列為共同 acceptance tests。 |
| 哪個現成方案最接近全部條件？ | Obsidian Sync 同時提供 local vault、離線佇列、iOS/macOS、E2EE、狀態/log、衝突與版本歷史，且資料為 Markdown + attachments。 | [sync methods](https://obsidian.md/help/sync-notes)、[security](https://obsidian.md/help/Obsidian%2BSync/Security%2Band%2Bprivacy)、[status](https://obsidian.md/help/Obsidian%2BSync/Status%2Bicon%2Band%2Bmessages)、[version history](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory) | Activity log 不持久；附件歷史只保留兩週；實際收錄入口尚未驗證。 | 以 Obsidian Sync 作第一個 end-to-end prototype，但另設獨立 backup。 |
| iCloud Drive 能否作 Apple-only 路線？ | 可以固定下載、離線修改後再同步，Mac 能顯示 upload/out-of-space 狀態；ADP 可讓 iCloud Drive E2EE。 | [iPhone Files](https://support.apple.com/en-ie/guide/iphone/iphe9aff429a/ios)、[Mac status](https://support.apple.com/en-euro/guide/mac-help/mchlc994344b/mac)、[iCloud security](https://support.apple.com/guide/security/icloud-security-overview-secacde2d0da/web) | 官方文件未充分描述跨 App concurrent edit 的衝突語意與背景完成時間。 | 對 Obsidian vault 做雙端離線、同名附件、刪除與容量不足測試。 |
| 自製 Apple App 的正確同步基線是什麼？ | 本地 Core Data／檔案持久層作來源，`NSPersistentCloudKitContainer` 或 `CKSyncEngine` 作 mirror；不可把 CloudKit 當本地資料物件的替代品。 | [CloudKit options](https://developer.apple.com/documentation/cloudkit/deciding-whether-cloudkit-is-right-for-your-app)、[CKSyncEngine](https://developer.apple.com/documentation/cloudkit/cksyncengine-5sie5) | UI 狀態、account change、quota、partial failure、record conflict、export 都要自行設計。 | 只有現成方案 prototype 失敗後才建立自製 App decision ticket。 |
| Google Drive 是否適合主同步？ | Mac mirror 可完整離線且錯誤可見；但 Obsidian 不支援 iOS Google Drive vault，個人 Drive 也沒有預設 client-held-key E2EE。 | [Drive mirror](https://support.google.com/drive/answer/13401938?hl=en)、[Drive status](https://support.google.com/drive/answer/10838124?hl=en)、[Drive encryption](https://support.google.com/drive/answer/10519333?hl=en)、[Obsidian iOS support](https://obsidian.md/help/sync-notes) | 非 Obsidian 自製 UI 是否能改善 iOS 體驗尚未研究。 | v1 不選作主同步；只保留為匯出或 encrypted backup backend 候選。 |
| 自管 Nextcloud 是否更符合 local-first？ | 可自管、可 E2EE、可保留 conflict copy；但 restore 後 server 預設是 authoritative source，且備份要維護多個 server 元件。 | [E2EE](https://docs.nextcloud.com/server/latest/user_manual/en/files/using_e2ee.html)、[conflicts](https://docs.nextcloud.com/server/latest/user_manual/en/desktop/conflicts.html)、[backup](https://docs.nextcloud.com/server/latest/admin_manual/maintenance/backup.html)、[restore](https://docs.nextcloud.com/server/latest/admin_manual/maintenance/restore.html) | iOS background 與 Obsidian vault 體驗尚未有本專案真機 evidence。 | 除非出現明確自管需求，先 defer；若重啟評估，需連同 server restore drill 一起 prototype。 |
| Syncthing 是否能避免 cloud？ | 可以直接 device-to-device、TLS、產生 conflict copies 且支援 file versioning。 | [security](https://docs.syncthing.net/users/security)、[sync conflicts](https://docs.syncthing.net/users/syncing)、[versioning](https://docs.syncthing.net/users/versioning) | 官方不支援 iOS，背景限制使自動同步可靠性不足。 | 不作 iPhone-first v1 主同步；只保留為 Mac/NAS 額外 replication 候選。 |
| 同步服務能否代替備份？ | 不能；刪除與損壞可能被同步傳播，供應商版本歷史也有保留期限。Time Machine 與 restic 可建立獨立、可還原且可檢查的歷史副本。 | [Obsidian version history](https://obsidian.md/help/Obsidian%2BSync/Version%2Bhistory)、[Time Machine](https://support.apple.com/en-us/104984)、[restic](https://restic.readthedocs.io/en/stable/010_introduction.html)、[restic integrity](https://restic.readthedocs.io/en/stable/045_working_with_repos.html) | 備份頻率、保留期、off-site backend 與 recovery secret 管理未決。 | 後續規格新增 backup/restore acceptance criteria；選定方案後執行 restore drill。 |

## 決策建議

Wayfinder 後續可以把本 ticket 的結果濃縮成以下決策輸入：

1. **先 prototype：Obsidian Sync local vault。**
2. **同場對照：iCloud Drive local vault，強制 `Keep Downloaded` 並啟用 Advanced Data Protection。**
3. **v1 必須另有 Mac 完整副本與獨立版本化備份；Sync 不算 backup。**
4. **Google Drive、Nextcloud、Syncthing 不進入首輪主同步 prototype。**
5. **只有現成方案無法滿足記錄生命週期、收錄入口或 AI 回寫時，才研究 local store + CloudKit 的自製 App。**

這份研究不決定 Obsidian 最終是唯一記錄庫、匯出目標或暫時驗證介面；它只確認 Obsidian Sync 是目前最小風險的第一個同步／儲存 prototype。
