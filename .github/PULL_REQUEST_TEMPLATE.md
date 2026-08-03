## 變更摘要

<!-- 用繁體中文說明做了什麼，以及為什麼需要這個變更。 -->

## 相關 issue

<!-- 例如：Closes #123；若沒有 issue，說明原因。 -->

## 影響範圍

- [ ] core pipeline
- [ ] CLI / 設定
- [ ] macOS LaunchAgent adapter
- [ ] 文件或開源維護
- [ ] 測試 / CI

## 驗證

請列出實際執行的 command 與結果：

```text
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile aha_moment_recorder/*.py build_backend.py
git diff --check
```

## 隱私與相容性確認

- [ ] 沒有提交 Vault、錄音、逐字稿、API key、local config 或 log。
- [ ] 原始來源不會被 AI 結果覆寫。
- [ ] macOS-specific 行為仍限制在 optional adapter。
- [ ] README、SECURITY、CHANGELOG 或相關 domain docs 已同步更新（若適用）。
