# Ollama Night Watch Summary

- Status: SKIPPED
- Reason: ENABLE_OLLAMA_NIGHT_WATCH is not set to 1.
- Deterministic digest: reports\night_watch\latest_digest.md

Run manually when wanted:

```powershell
$env:ENABLE_OLLAMA_NIGHT_WATCH="1"
venv312\Scripts\python.exe Scripts\ollama_night_watch_summary.py --model llama3:latest --timeout 180
```
