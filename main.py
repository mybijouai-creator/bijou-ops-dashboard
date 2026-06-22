from pathlib import Path
from datetime import datetime, timezone
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx


def get_env(key: str) -> str:
    env_path = Path(r"C:\Users\W3jde\AppData\Local\hermes\.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line[len(key) + 1:].strip().strip('"').strip("'")
    return os.environ.get(key, "")


app = FastAPI(title="Bijou Operations Dashboard")

REPO = "mybijouai-creator/bijou-autonomous-ops"
MONDAY_BOARD_ID = "18375781201"
LINKEDIN_PLATFORM_ID = "linkedin-asZgv9imjx"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@app.get("/api/health")
def health():
    return {"ok": True, "time": now_iso()}


@app.get("/api/publora/posts")
async def publora_posts():
    token = get_env("PUBLORA_API_KEY")
    if not token:
        return {"error": "PUBLORA_API_KEY not found", "time": now_iso()}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                "https://api.publora.com/api/v1/list-posts",
                headers={"x-publora-key": token},
                params={"limit": 20},
            )
            data = r.json()
        posts = []
        for p in data.get("posts", []):
            posts.append({
                "id": p.get("postGroupId"),
                "content": p.get("content", "")[:180],
                "scheduledTime": p.get("scheduledTime"),
                "status": p.get("status"),
                "platforms": [x.get("platform") for x in p.get("posts", [])],
            })
        return {"posts": posts, "time": now_iso()}
    except Exception as e:
        return {"error": str(e), "time": now_iso()}


@app.get("/api/github/commits")
async def github_commits():
    token = get_env("HERMES_BIJOU_OWN_GITHUB_PAT")
    if not token:
        return {"error": "HERMES_BIJOU_OWN_GITHUB_PAT not found", "time": now_iso()}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"https://api.github.com/repos/{REPO}/commits",
                headers={"Authorization": f"Bearer {token}"},
                params={"per_page": 10},
            )
            data = r.json()
        commits = []
        for c in data:
            commits.append({
                "sha": c.get("sha", "")[:7],
                "message": c.get("commit", {}).get("message", "").split("\n")[0],
                "author": c.get("commit", {}).get("author", {}).get("name", "Unknown"),
                "date": c.get("commit", {}).get("author", {}).get("date"),
            })
        return {"commits": commits, "time": now_iso()}
    except Exception as e:
        return {"error": str(e), "time": now_iso()}


@app.get("/api/monday/tasks")
async def monday_tasks():
    token = get_env("MONDAY_API_TOKEN")
    if not token:
        return {"error": "MONDAY_API_TOKEN not found", "time": now_iso()}
    try:
        query = """
        query {
            boards(ids: %s) {
                items_page(limit: 20) {
                    items {
                        id
                        name
                        updated_at
                        column_values {
                            id
                            text
                        }
                    }
                }
            }
        }
        """ % MONDAY_BOARD_ID
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                "https://api.monday.com/v2",
                headers={"Authorization": token, "Content-Type": "application/json"},
                json={"query": query},
            )
            data = r.json()
        items = []
        for board in data.get("data", {}).get("boards", []):
            for item in board.get("items_page", {}).get("items", []):
                status = next((cv.get("text", "") for cv in item.get("column_values", []) if cv.get("id") == "status"), "")
                items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": status,
                    "updated_at": item.get("updated_at"),
                })
        return {"tasks": items, "time": now_iso()}
    except Exception as e:
        return {"error": str(e), "time": now_iso()}


@app.get("/api/agentmail/unread")
async def agentmail_unread():
    token = get_env("AGENTMAIL_API_TOKEN")
    inbox = get_env("AGENTMAIL_INBOX")
    if not token or not inbox:
        return {"error": "AGENTMAIL_API_TOKEN or AGENTMAIL_INBOX not found", "time": now_iso()}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"https://api.agentmail.to/v1/inboxes/{inbox}/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 100},
            )
            data = r.json()
        messages = data.get("messages", [])
        unread = [m for m in messages if not m.get("read", True)]
        return {
            "unread_count": len(unread),
            "total": len(messages),
            "latest": [
                {"from": m.get("from", ""), "subject": m.get("subject", ""), "date": m.get("created_at")}
                for m in unread[:5]
            ],
            "time": now_iso(),
        }
    except Exception as e:
        return {"error": str(e), "time": now_iso()}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/{full_path:path}")
def index(full_path: str):
    return FileResponse("static/index.html")
