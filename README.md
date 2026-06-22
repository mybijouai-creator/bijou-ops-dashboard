# Bijou AI Operations Dashboard

Single-screen command center for Bijou AI's autonomous agent operations.

## Features

- **LinkedIn Posts**: Scheduled posts via Publora
- **GitHub Commits**: Recent activity on `mybijouai-creator/bijou-autonomous-ops`
- **Monday Tasks**: Active tasks from Bijou AI board
- **AgentMail Inbox**: Unread message count + latest

## Run locally

### Windows (one-click)
```batch
bijou_dashboard.bat
```

### Linux/macOS / Cron
```bash
bash bijou_dashboard_cron.sh
```

### Manual
```bash
cd bijou-ops-dashboard
uv pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8765 --reload
```

Open http://localhost:8765

## Credentials

Credentials are read from `C:\Users\W3jde\AppData\Local\hermes\.env`.
