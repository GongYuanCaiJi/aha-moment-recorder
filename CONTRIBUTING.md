# 貢獻指南

本 repo 以 Python standard library 維持 macOS-first、local-first 的個人記錄管線。對外文件與使用者訊息以繁體中文為主；CLI/API/field 名稱維持原文。

## 開始前

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
```

請不要把個人 Vault、錄音、逐字稿、API key、reverse proxy 設定或 LaunchAgent log 放入 checkout。

## 變更原則

- 先讀 `CONTEXT.md` 與相關 `docs/`，維持 `RecordPipeline` 的來源不可覆寫與 public adapter seam。
- 測試應穿過 public interface；HTTP、clock、Git runner 與 LaunchAgent command runner 從 system boundary 注入。
- macOS-specific 行為放在 optional adapter，不能讓 core pipeline 依賴 macOS GUI 或私人路徑。
- 新的 CLI 行為要同時更新 README 的操作、隱私與故障排查說明。

## 本地檢查

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile aha_moment_recorder/*.py build_backend.py
git diff --check
python3 -m pip wheel . --no-deps --no-cache-dir --wheel-dir /tmp/aha-moment-recorder-wheel
```

LaunchAgent 測試必須使用 injected command runner；不要讓測試對使用者目前的 `launchctl` job、`~/Library/LaunchAgents` 或真實 log 發出 mutation。真正安裝前先執行 `plutil -lint`，並在需要時驗證 loaded、running、last exit 與 stdout/stderr。

Issue 與 PR 請依 `docs/agents/issue-tracker.md` 和 `docs/agents/triage-labels.md` 使用既有流程；不要在本 repo 內另造 tracker 規則。
