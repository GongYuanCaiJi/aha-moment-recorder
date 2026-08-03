# 可移植記錄管線

`aha_moment_recorder` 將來源掃描、記錄保存、AI 整理、state 與 Git 拆成可替換
的 public modules。最高外部 seam 是 `RecordPipeline.process(group)`；每一個
`RecordGroup` 對應一個 `records/<record-id>/`。文字與音訊可以像真人一樣分開輸入；不同檔名的獨立來源會各自形成一筆記錄，不需要手動準備同名檔案。只有明確同名 sidecar 或來源 adapter 提供穩定識別時才會合併，避免日期／流水號相同造成誤合併。

## Public modules

- `config.py`：`Settings`、`load_settings()`，合併 TOML、environment 與 CLI。
- `sources.py`：`SourceScanner`、`RecordGroup`，處理文字、音訊、逐字稿與附件。
- `storage.py`：`RecordStore`，以 atomic write/copy 保存來源，AI 只能替換標記區塊。
- `organization.py`：`Organization` 與 `OpenAICompatibleOrganizer`；回應必須恰好包含 `classification`、`topic`、`structured_output`、`summary`。
- `transcription.py`：`Transcriber` 與 `WhisperCppTranscriber`；以本機 `ffmpeg`／`whisper-cli` 將 m4a 轉為逐字稿，不把音訊送進文字反代。
- `state.py`：`StateStore`，保存可讀 JSON 並支援 commit pending retry。
- `git_adapter.py`：`GitCommitter`，以注入的 runner 執行 path-scoped Git commands。
- `pipeline.py`：`RecordPipeline` 與 `pipeline_from_settings()`。

所有 runtime dependencies 都來自 Python standard library。HTTP、認證、metadata
reader、時鐘與 Git runner 都能由測試注入；沒有任何作者本機路徑或秘密需要
寫入 repo。

若設定 `stt_model`、`stt_command`、`stt_ffmpeg_command` 且 `auto_transcribe = true`，音訊會在同一筆記錄的
`attachments/transcript-01.txt` 產生逐字稿；下一次掃描會透過 state 與來源簽章
保持冪等。原始音訊、來源文字與逐字稿都不會被 AI 整理取代。

## CLI

```sh
python3 -m aha_moment_recorder init --config /path/to/settings.toml
python3 -m aha_moment_recorder doctor --config /path/to/settings.toml
python3 -m aha_moment_recorder run --config /path/to/settings.toml
python3 -m aha_moment_recorder watch --config /path/to/settings.toml
```

`prototype/record-bridge/record_bridge.py` 是相容 façade；它保留原本的 flags、
輸出目錄與 `Bridge`/`source_groups` import surface，但不再包含另一份 pipeline。
