# Obsidian 能力盤點與需求對照

日期：2026-08-03
範圍：只盤點 Obsidian 已存在的能力，再對照目前已確認的需求；不新增產品需求，也不把本 repo 目前的 prototype 當成產品決策。

## 先講結論

Obsidian 比我們先前假設的「一個 Markdown 編輯器」完整很多。它已經可以作為本地唯一記錄簿的主要候選：Vault 是本機檔案夾，筆記是可由檔案系統直接讀寫的 Markdown，音訊與其他附件是 Vault 裡的一般檔案，還有 Properties、Templates、Search、Bases、iOS capture、URI、CLI、Sync 版本歷史與 File recovery。

因此在 fixture 驗證前，不應先另建一套平行的儲存、索引、同步或記錄檔格式；但如果 record contract、provenance 或跨檔案恢復無法由 Obsidian 承接，這些仍是 repo 必須擁有的邊界。真正需要驗證／可能需要少量 glue 的部分，集中在：

1. iPhone 來源能不能低摩擦地進入指定的同一則 note，尤其是音訊與逐字稿的關聯。
2. AI 整理稿如何追加到同一則 note、保留原始內容，並讓每筆記錄可選 `只收錄` 或 `收錄並整理`。
3. 如果仍要「每次編輯都有 Git commit」，如何把外部 Git 自動化與 Obsidian 的寫入、Sync、衝突處理接起來。

這三項不是 Obsidian 沒有資料能力，而是官方沒有替我們定義完整的「錄音 → 逐字稿 → AI 整理」工作流契約；必須用隔離 Vault 做小型 fixture 測試，不能靠想像補完。

## 能力分級

- **原生已確認**：Obsidian 官方文件直接承諾的能力。
- **原生但要實測**：官方提供機械能力，但尚未證明符合我們的完整操作順序或手機來源。
- **需要 glue**：可以接，但要用 Shortcut、URI、CLI、社群外掛或外部程式把步驟串起來。
- **目前不能當成保證**：官方文件沒有提供這個契約，不能把推論寫成需求或完成條件。

## 1. 儲存與「同一個東西放在同一個地方」

| 我們需要的能力 | Obsidian 現有能力 | 判定 | 尚未證實的部分 |
|---|---|---|---|
| 所有筆記有一個本地權威位置 | Vault 是本地資料夾；Markdown 是 plain-text 檔案，外部編輯器或檔案管理器可直接讀寫，Obsidian 會刷新外部變更 | 原生已確認 | 哪個 Vault 路徑作為正式權威仍是部署選擇 |
| 一則記錄同時放文字、音訊、附件 | 附件是 Vault 裡的普通檔案；官方支援音訊格式並可在 note 內嵌。Audio recorder 會把錄音存入 Vault 並嵌入目前 note | 原生已確認 | 從 iPhone 其他 App 來的音訊是否能一次進入指定 note，要實測 |
| 原始內容不可被 AI 取代 | Markdown 原文與音訊檔可分別保存；AI 是否只追加、不覆寫，取決於我們使用的寫入流程 | 原生但要實測 | Obsidian 沒有一個內建的 immutable-source / provenance 契約 |
| 逐字稿與音訊同屬一筆記錄 | note 可以有逐字稿文字與音訊 embed | 原生但要實測 | Audio recorder 官方頁面沒有承諾自動轉寫；逐字稿來源、檔名、時間戳與重試需由外部流程處理 |

官方依據：[How Obsidian stores data](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)、[Attachments](https://obsidian.md/help/attachments)、[Accepted file formats](https://obsidian.md/help/file-formats)、[Audio recorder](https://obsidian.md/help/Plugins/Audio%2Brecorder)。

## 2. 結構化內容、分類與查找

| 我們需要的能力 | Obsidian 現有能力 | 判定 | 尚未證實的部分 |
|---|---|---|---|
| 分類、主題、處理模式可被機器讀取 | Properties 是 YAML frontmatter 的結構化資料，支援文字、清單、數字、checkbox、日期、日期時間、tags | 原生已確認 | 欄位名稱與允許值仍應以實際 fixture 決定，不先擴張 taxonomy |
| 摘要、結構化輸出與原始內容在同一處可讀 | Markdown note 可以放固定區段；Properties 放短欄位，長內容放 note body | 原生已確認 | 區段格式、AI 輸出 schema、provenance 不是 Obsidian 內建規格 |
| 預設「收錄並整理」，個別記錄改為「只收錄」 | Properties 可以保存 `processing_mode` 之類的狀態，Templates 可以預填欄位 | 需要 glue | Obsidian 不會因某個 property 自動執行或跳過 AI；行為要由 Shortcut、CLI、外掛或外部 worker 實作 |
| 後續找到「只收錄」並再整理 | Search 可用 property/value 查找；Bases 可篩選、排序、分組並編輯 note properties | 原生已確認 | 由查詢結果觸發批次 AI、去重、失敗重試仍需 glue |

官方依據：[Properties](https://obsidian.md/help/properties)、[Templates](https://obsidian.md/help/Plugins/Templates)、[Search](https://obsidian.md/help/Plugins/Search)、[Introduction to Bases](https://obsidian.md/help/bases)、[Bases syntax](https://obsidian.md/help/bases/syntax)。

## 3. iPhone 收錄與跨裝置同步

| 我們需要的能力 | Obsidian 現有能力 | 判定 | 尚未證實的部分 |
|---|---|---|---|
| 手機快速建立或追加文字 | iOS app 有 widget 與 Shortcuts；官方列出 Create new note、Open daily、Capture to Daily Note、Capture to Bookmark，capture 可在不開啟 app 的情況下追加／前置 | 原生已確認 | 需要測試我們指定的 note 命名、欄位和離線行為 |
| 其他 App 的音訊進入 Vault | Obsidian 支援 iOS 附件選擇、Vault 內音訊嵌入；外部檔案可透過檔案系統或分享流程匯入 | 原生但要實測 | 官方 iOS 文件沒有保證「任意錄音來源 + 逐字稿 + 指定同一則 note」的一步流程 |
| iPhone 與 Mac 都看到同一批筆記、音檔 | Obsidian Sync 可同步 notes 與 attachments，並有 selective sync | 原生已確認 | 實際延遲、離線追加、同時編輯衝突、長音檔方案限制要實測 |
| 私密、local-first | Vault 可完全在本地使用；Sync 可選 E2E encryption | 原生已確認 | E2E 密碼遺失會失去連線能力；Sync 不是唯一備份 |

官方依據：[Obsidian for iOS and iPadOS](https://obsidian.md/help/ios)、[Introduction to Obsidian Sync](https://obsidian.md/help/Obsidian%2BSync/Introduction%2Bto%2BObsidian%2BSync)、[Sync security and privacy](https://help.obsidian.md/Obsidian%20Sync/Security%20and%20privacy)、[Back up your Obsidian files](https://obsidian.md/help/backup)。

## 4. 版本、恢復與 Git 的差別

Obsidian 的版本能力已經比我們原先假設的完整，但它不等於 Git：

- **File recovery** 會在本機保存 Markdown／Canvas snapshots，可比較和恢復；它是裝置級、有限保留的復原機制，並非完整備份，且不涵蓋音訊附件的同等版本契約。
- **Obsidian Sync version history** 可以恢復 notes 與 attachments，但保留期限依方案而定，恢復會替換檔案內容。
- **Git** 是 Vault 外部的版本控制選擇。官方文件承認 Vault 可與 Git 等服務搭配，但沒有「每次 Obsidian 編輯自動產生一個語意完整 Git commit」的原生承諾。
- Sync、iCloud、Dropbox、OneDrive 等同步服務不應在沒有衝突測試的情況下混用；官方明確提醒可能產生衝突。

官方依據：[File recovery](https://obsidian.md/help/plugins/file-recovery)、[Sync version history](https://help.obsidian.md/Obsidian%2BSync/Version%2Bhistory)、[How Obsidian stores data](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)。

## 5. 自動化與 AI 接入面

| 入口 | 官方能力 | 對本案的意義 |
|---|---|---|
| iOS Shortcuts | 建立、開啟、Capture 到 Daily Note／Bookmark 等動作 | 先測 native capture，再決定是否需要自訂橋接 |
| Obsidian URI | 可 open、new、append／prepend、帶 content 或 clipboard，並可回傳 x-success／x-error | 可把外部捕捉或 AI 結果寫回既有 note；但 append 本身不提供去重、來源快照或 retry safety |
| Obsidian CLI | 可從終端 read、search、daily append/prepend、建立 note、查詢 Bases、讀取 diff；官方說明需要已安裝且執行中的 Obsidian | 可取代部分自建檔案 watcher／寫回程式；要實測背景執行與錯誤處理 |
| 官方 Plugin API／外部程式 | 官方 Developer Docs 提供 TypeScript plugin、Vault 讀寫、檔案事件與 HTTP request 能力；這些能支撐外部 transcription／LLM 的接線 | 官方 Help／Docs／API 沒有提供 AI 整理、轉寫、selected-record、queue、retry 或品質保證的核心資料契約；這些必須由 plugin／script／外部 worker 定義 |

官方依據：[Obsidian URI](https://obsidian.md/help/Extending%2BObsidian/Obsidian%2BURI)、[Obsidian CLI](https://obsidian.md/help/cli)、[Vault API](https://docs.obsidian.md/Plugins/Vault)、[Events](https://docs.obsidian.md/Plugins/Events)、[request API](https://docs.obsidian.md/Reference/TypeScript%20API/request)、[Obsidian API official GitHub repository](https://github.com/obsidianmd/obsidian-api)。

## 對照目前已確認的需求

| 已確認需求 | Obsidian 能否直接承擔 | 我們真正要補的最小部分 |
|---|---|---|
| 所有筆記（包含錄音）都保存、同步 | **大部分可以**：Vault + attachments + Sync | 只需驗證 iPhone 來源、同步衝突、音檔大小與恢復 |
| 原始音訊、原始文字、逐字稿、AI 整理稿在同一個地方 | **容器可以**：一則 note 可放文字、embed 與附件 | 逐字稿取得、固定區段、追加不覆寫、來源關聯 |
| AI 處理可選；預設可為「收錄並整理」，個別改「只收錄」 | **資料欄位可以，行為不原生** | 用 property 表達狀態，再由外部 worker／CLI／plugin 執行 |
| 四個最小結果：分類、主題、結構化輸出、摘要 | **可以承載與查找** | 只定最小欄位與寫回規則，不另造資料庫 |
| 本地作唯一紀錄簿、雲端 AI 可選 | **可以** | AI provider 與隱私選項仍是外部整合，不把 Vault 必然上雲 |
| 每個變動自動 Git commit | **Obsidian 原生沒有這個承諾** | 若這仍是硬需求，另做小型 Git adapter；先測 commit 邊界、衝突與音檔策略 |

## 目前最重要的限制，不是「Obsidian 沒功能」

真正的限制是「Obsidian 沒有替我們把多個原生能力組成同一條錄音工作流」：

1. Audio recorder 解決的是錄音檔進 Vault 與嵌入 note，不等於轉寫服務。
2. Properties／Bases 解決的是結構化欄位、查詢和視圖，不等於 AI pipeline。
3. Sync／File recovery 解決的是同步與復原，不等於 Git commit 語意。
4. iOS Shortcuts／URI／CLI 解決的是可呼叫的入口，不等於任意錄音來源都能一次建立完整 record。

所以目前 repo 內自建的儲存／掃描／索引邏輯應先視為**待縮減的 prototype**，而不是已確定的產品核心。若 fixture 證明 Obsidian 已經涵蓋某一段，就刪掉那段自建程式，不再維護平行真相。

## 下一步：只做能力驗證，不新增產品規格

用一個全新的測試 Vault，逐項跑同一筆 fixture：

1. 建立一則 note，放入原始文字、真實短音訊、逐字稿文字、附件與 Properties。
2. 用 iOS 官方 capture／分享能力把文字與音訊送進 Vault，確認是否仍落在同一則 note。
3. 用 Sync 在 iPhone 與 Mac 間同步，測離線追加、同時編輯、音訊附件恢復與衝突。
4. 用 Search／Properties／Bases 找到 `只收錄` 的記錄，再對同一 note 追加四個 AI 結果，確認原始區塊 byte-for-byte 不變。
5. 用 URI／CLI 做一次 append、重試與失敗，確認實際錯誤、去重和 app-running 限制。
6. 若 Git 仍為必要條件，再把同一 fixture 放進 Git Vault，測一筆人類編輯、一筆 AI 追加、附件加入和同步衝突各產生什麼 diff／commit。

只有這組測試指出明確缺口後，才建立一張精準的 integration ticket；在此之前不再擴張資料模型、AI schema 或自建同步層。

## Research ledger

| question | claim | source | gap | action |
|---|---|---|---|---|
| Vault 能否當本地權威記錄簿？ | Markdown 與附件是本地檔案，可由檔案系統管理 | [How Obsidian stores data](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)、[Attachments](https://obsidian.md/help/attachments) | 尚未用新 Vault 驗證完整 record fixture | 跑文字＋音訊＋逐字稿＋附件 fixture |
| 音訊能否與 note 放在一起？ | Audio recorder 將錄音存入 Vault 並嵌入 note；音訊也可作一般附件 | [Audio recorder](https://obsidian.md/help/Plugins/Audio%2Brecorder)、[Accepted file formats](https://obsidian.md/help/file-formats) | 外部 iPhone 錄音進入指定 note 的一步流程未被官方保證 | 實測 iOS 分享／附件流程 |
| 分類與主題能否結構化？ | Properties 支援結構化 YAML 欄位，Search／Bases 可查詢與視圖化 | [Properties](https://obsidian.md/help/properties)、[Search](https://obsidian.md/help/Plugins/Search)、[Bases](https://obsidian.md/help/bases) | 欄位命名與 AI 結果 schema 尚未定義 | 只用最小 fixture，不先擴 taxonomy |
| `只收錄`／`收錄並整理` 能否成為可選狀態？ | Property 可保存狀態，Templates 可預填 | [Properties](https://obsidian.md/help/properties)、[Templates](https://obsidian.md/help/Plugins/Templates) | Obsidian 不會自動依 property 執行 AI | 用 CLI／plugin 做最小 policy adapter |
| iPhone 與 Mac 能否同步完整記錄？ | Sync 支援 notes、attachments、selective sync 與歷史 | [Introduction to Obsidian Sync](https://obsidian.md/help/Obsidian%2BSync/Introduction%2Bto%2BObsidian%2BSync)、[Sync version history](https://help.obsidian.md/Obsidian%2BSync/Version%2Bhistory) | 延遲、衝突、檔案大小與保留期限尚未在本案 fixture 驗證 | 雙裝置 offline／online restore test |
| Git 是否由 Obsidian 原生提供？ | 官方提供檔案與 Sync 版本能力，但沒有每次編輯自動 commit 的契約 | [How Obsidian stores data](https://obsidian.md/help/Files%2Band%2Bfolders/How%2BObsidian%2Bstores%2Bdata)、[Back up your Obsidian files](https://obsidian.md/help/backup) | commit 粒度、衝突、二進位音檔策略未知 | 只有確認仍需要時才做 Git adapter fixture |
| 是否需要自建 watcher／寫回層？ | URI 與 CLI 已提供 open／append／read／search／diff 等入口 | [Obsidian URI](https://obsidian.md/help/Extending%2BObsidian/Obsidian%2BURI)、[Obsidian CLI](https://obsidian.md/help/cli) | CLI 需要 app running；錯誤與 retry 行為尚未測 | 先做 native automation probe，再決定刪減現有程式 |
| Plugin／script 能否承接外部 transcription／LLM 接線？ | 官方 Plugin API 提供 Vault 讀寫、檔案事件與 HTTP request；可作為單筆 selected-record glue 的基礎 | [Vault API](https://docs.obsidian.md/Plugins/Vault)、[Events](https://docs.obsidian.md/Plugins/Events)、[request API](https://docs.obsidian.md/Reference/TypeScript%20API/request)、[Obsidian API official GitHub repository](https://github.com/obsidianmd/obsidian-api) | 官方沒有 AI／transcription、queue、retry、provenance 或 cloud-consent 契約 | 先做明確授權的單筆 append proof，再決定哪些可靠流程由 repo 自建 |
