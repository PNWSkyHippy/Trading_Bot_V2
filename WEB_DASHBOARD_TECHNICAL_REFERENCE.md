# HTML Dashboard Technical Reference

## Stage-2 Contract (PR #2)

Current migration entrypoint:

- `GET /` serves `Html-Files/index.html`
- Frontend bootstrap script: `/static/src/App.jsx`

Minimum migrated API contract:

- `GET /api/snapshot`
- `POST /api/control`

Status: hybrid migration. Stage-2 is active in the HTML dashboard. Streamlit remains available for non-migrated scope until Stage-3 parity is complete.

## Runtime Notes

- Bridge process: `python web_dashboard.py`
- Default URL: `http://localhost:8125`
- Static files are served from `Html-Files/` (or `HTML-Files/` fallback on case-sensitive filesystem differences).

## `/api/control` Actions

Current actions accepted by `POST /api/control`:

- `pause_trading`
- `resume_trading`
- `start_bot`
- `stop_bot`
- `restart_bot`
- `refresh_scan`

Request body format:

```json
{"action": "start_bot"}
```

Response format:

```json
{"ok": true, "message": "Bot start requested."}
```
