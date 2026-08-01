# Codex Desktop：Fate Lens 與 aha-moment-recorder 的初始 subagent runtime 差異

研究日期：2026-08-01

## 結論

兩條 task 的第一個 turn 就已經選到不同的 model/backend：

- Fate Lens：`gpt-5.6-luna`、`multi_agent_version: v1`。
- aha-moment-recorder：`gpt-5.6-sol`、`multi_agent_version: v2`。

`multi_agent_version` 會在 task/session 建立時決定並釘住。之後只切換 model，不會把既有 task 從 V2 變回 V1；這正是 aha 後來切到 Luna 仍沒有 `multi_agent_v1__spawn_agent` 的原因。

## 直接證據

| task | 建立時間（UTC） | 建立時 Codex CLI | 第一個 turn | 後續切換觀察 |
|---|---|---|---|---|
| Fate Lens (`019f9236-c235-7d72-806d-5b4d31c8c9de`) | 2026-07-24 03:41:30 | `0.145.0-alpha.30` | Luna / medium / V1 | 後來切成 Sol / high，仍是 V1 |
| aha-moment-recorder (`019f9f6b-493f-7a93-81b9-ac4aeb0d024c`) | 2026-07-26 17:13:56 | `0.146.0-alpha.3.1` | Sol / high / V2；`explicitRequestOnly` | 2026-08-01 切成 Luna / max，仍是 V2 |

來源是兩條 task 的原始 rollout `session_meta` / `turn_context`，不是從側欄名稱推測：

- Fate Lens：`/Users/shuaige/.codex/path-move-backups/thread-019f9236-20260727-023340/rollout-2026-07-24T11-41-30-019f9236-c235-7d72-806d-5b4d31c8c9de.jsonl`
- aha：`/Volumes/PS3000/AI_Generated_Data/Codex/storage-relocation/2026-04-21-live-cutover/sessions/2026/07/27/rollout-2026-07-27T01-13-56-019f9f6b-493f-7a93-81b9-ac4aeb0d024c.jsonl`

本機 `codex debug models` 目前也顯示：`gpt-5.6-luna → v1`，`gpt-5.6-sol → v2`。Codex source 將這個欄位描述為「此 model 建立新 thread 時選用的 multi-agent backend」：
<https://github.com/openai/codex/blob/main/codex-rs/protocol/src/openai_models.rs#L2635-L2642>

## Research ledger

### 1. question

為什麼兩條 task 一開始暴露不同的 subagent 工具？

**claim**：第一個分流是 task 建立時的 effective model；不是 repo、cwd 或 AGENTS.md。Sol 的 model metadata 選 V2，Luna 的 metadata 選 V1。

**source**：兩條 rollout 的第一個 `turn_context`；本機 `codex debug models`；Codex model source（上方連結）。

**gap**：rollout 記錄了最後選到的 model，沒有記錄 Desktop UI 是因為「預設值、使用者點選、還是 app-server 舊設定」而選到 Sol。

**action**：把「建立新 task 前先固定 Luna」列為必要的建立前條件，不能等 task 建立後再切換。

### 2. question

為什麼後來切換 model 仍不會改變工具面？

**claim**：backend/runtime 是 session-pinned。既有 V2 task 改成 Luna 仍留在 V2；既有 V1 task 改成 Sol 仍留在 V1。

**source**：本地兩條 rollout 的 model/version transition；官方 issue #31097 明確記錄「切換既有 thread 的 model 不會恢復 V1，必須建立 fresh thread」：
<https://github.com/openai/codex/issues/31097#L237-L257>

**gap**：官方目前仍未提供一個 Desktop UI 內可讀取、可重設既有 task backend 的操作。

**action**：只對 fresh parent task 做 V1 gate；既有 task 若第一個 turn 不是 V1，就不要把它當成可修復的 V1 parent。

### 3. question

為什麼兩條 task 的建立結果剛好不同？

**claim**：可證明的直接原因是建立時 effective model 不同；兩條 task 也跨了不同的 bundled CLI 版本（`0.145.0-alpha.30` → `0.146.0-alpha.3.1`）。官方 Desktop issue 也把較新的 task 使用 V2、較舊 task 使用 V1 視為 V1/V2 workflow boundary。

**source**：兩條 rollout 的 `cli_version` 與第一個 `turn_context`；官方 issue #34591：
<https://github.com/openai/codex/issues/34591#L248-L258>

**gap**：沒有一筆本機 metadata 能證明「CLI 升級本身自動把 UI 預設從 Luna 改成 Sol」；這部分只能標成可能的版本／UI default 來源，不能當成已證實的單一原因。

**action**：不要依賴 Desktop 的隱含 default；建立 task 時明確選 Luna，並在第一個 turn 立即驗證工具面。

### 4. question

把 `features.multi_agent_v2 = false` 寫進 config 是否足夠？

**claim**：不夠。`features list` 可能顯示 V2 disabled，但 model metadata 仍可在新 thread 選 V2；這也是為什麼只改 config 或在既有 task 切 model 不能保證結果。

**source**：官方 issue #31097 的 reproduced behavior 與 configuration-precedence 說明：
<https://github.com/openai/codex/issues/31097#L222-L246>

**gap**：這是目前 Codex 的已知行為／bug surface，不能由 repo 內的設定消除。

**action**：把 config 當成必要但非充分條件；以新 task 的實際 `multi_agent_v1__spawn_agent` 是否存在作為 acceptance gate。

## 穩定建立 V1/Luna Max parent 的操作契約

1. **建立前**：在啟動 Desktop/app-server 前，設定有效 default 為 `gpt-5.6-luna`，reasoning 為 `max`；不要只在既有 task 內切換 model。
2. **重啟 runtime**：修改設定後重啟 Codex Desktop/app-server，避免新 task 繼承舊 process 的設定。只改 `config.toml` 而不重啟，不算已套用。
3. **建立 fresh parent**：新建 task 後，第一個 turn 就必須是 Luna；不要先用 Sol 開一輪再切 Luna。
4. **第一輪 gate**：在任何研究／實作前，確認工具清單含有 `multi_agent_v1__spawn_agent` 與 `multi_agent_v1__wait_agent`。沒有就停止使用這個 parent，重新建立，不要用 V2 的 `collaboration.spawn_agent` 冒充 V1。
5. **派工時**：在 V1 工具允許的欄位中明確指定 child 為 `gpt-5.6-luna`、reasoning `max`，並用 V1 的 wait 工具等待；不要混用 V2 schema。
6. **可重現的 CLI diagnostic**：

   ```sh
   codex exec --ephemeral \
     -C /Users/shuaige/Documents/aha-moment-recorder \
     -m gpt-5.6-luna \
     -c model_reasoning_effort='max' \
     --disable multi_agent_v2 \
     --enable multi_agent
   ```

   這是診斷／驗證路徑，不會把 child 顯示到目前 Desktop parent 的側欄；Desktop 要可見，仍必須從正確的 Desktop V1 parent 建立。

## 最小 acceptance

新 task 在開始任何正式工作前，必須能回答：

```text
model = gpt-5.6-luna
reasoning = max
multi_agent_version = v1
tools include multi_agent_v1__spawn_agent + multi_agent_v1__wait_agent
```

這四項缺任何一項，就不能宣稱「一開始已穩定載入 Luna Max/V1」。
