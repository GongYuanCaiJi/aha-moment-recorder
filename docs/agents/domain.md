# Domain Docs

以下規則說明 engineering skills 在探索 codebase 時，應如何使用此 repo 的 domain documentation。

## 探索前先讀取

- Repo 根目錄的 **`CONTEXT.md`**；或
- 若 repo 根目錄存在 **`CONTEXT-MAP.md`**，則依其指向讀取各 context 的 `CONTEXT.md`，但只需讀取與目前主題相關的檔案。
- **`docs/adr/`**：讀取與即將處理區域相關的 ADRs。若為 multi-context repo，還要檢查 `src/<context>/docs/adr/` 中限定於該 context 的 decisions。

若這些檔案不存在，**直接繼續，不需提示**。不要特別指出缺少檔案，也不要預先建議建立。`/domain-modeling` skill（可透過 `/grill-with-docs` 與 `/improve-codebase-architecture` 進入）會在 terms 或 decisions 真正獲得釐清時，按需建立這些檔案。

## 檔案結構

Single-context repo（適用於多數 repos）：

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo（根目錄存在 `CONTEXT-MAP.md`）：

```text
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用 glossary 定義的詞彙

當輸出內容提及 domain concept（例如 issue title、refactor proposal、hypothesis 或 test name）時，使用 `CONTEXT.md` 定義的 term。不要改用 glossary 明確避免的同義詞。

如果需要的 concept 尚未出現在 glossary，這是一個值得注意的訊號：你可能正在發明專案未使用的語言（應重新考慮），也可能確實存在缺口（應記錄並交由 `/domain-modeling` 處理）。

## 標示 ADR 衝突

若輸出內容與既有 ADR 衝突，應明確指出，而非默默覆蓋：

> _與 ADR-0007（event-sourced orders）衝突，但仍值得重新檢視，因為……_
