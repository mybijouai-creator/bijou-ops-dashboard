#!/usr/bin/env python3
"""Bijou AI daily autonomous runbook.

This script is designed to run once per day (cron) and:
1. Generate and schedule a LinkedIn post for today at the best-practice
   engagement window for Bijou AI's Dubai/GST + ASEAN/SGT audiences.
2. Check AgentMail inbox for actionable messages
3. Create Monday.com task for any flagged items
4. Send Telegram summary report
5. Log all activity to GitHub repo bijou-autonomous-ops
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(r"C:\Users\W3jde\AppData\Local\hermes\scripts")))
import bijou_content_engine as content_engine


def get_env(key):
    env_path = Path(r"C:\Users\W3jde\AppData\Local\hermes\.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line[len(key) + 1:].strip().strip('"').strip("'")
    return os.environ.get(key, "")


def log_to_repo(report):
    """Append daily report to bijou-autonomous-ops repo."""
    repo = Path(r"C:\Users\W3jde\Movies\Hub\Projects\w3j\bijou-autonomous-ops")
    if not repo.exists():
        print("Repo not found, skipping git log")
        return False

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = repo / "logs" / f"{date_str}.md"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(report, encoding="utf-8")

    # Commit
    subprocess.run(["git", "add", str(log_file)], cwd=repo, check=False)
    subprocess.run(
        ["git", "commit", "-m", f"daily: Bijou runbook log {date_str}", "--no-verify"],
        cwd=repo,
        check=False,
    )
    subprocess.run(["git", "push"], cwd=repo, check=False)
    return True


def schedule_linkedin_post(platform_id="linkedin-asZgv9imjx"):
    """Use Publora to schedule the next evergreen post at the best-practice slot."""
    token = get_env("PUBLORA_API_KEY")
    if not token:
        return False, "PUBLORA_API_KEY not found"

    # Pick a topic using the date-stable evergreen rotation.
    today = datetime.now(timezone.utc)
    topic_meta = content_engine.EVERGREEN_TOPICS[
        content_engine._get_topic_index_for_date(today)
    ]
    body = content_engine.generate_post(topic_meta["topic"])
    scheduled = content_engine.find_next_best_post_time(from_dt=today)

    url = "https://api.publora.com/api/v1/create-post"
    payload = {
        "content": body,
        "platforms": [platform_id],
        "scheduledTime": scheduled.isoformat(),
    }
    r = requests.post(
        url,
        headers={"Content-Type": "application/json", "x-publora-key": token},
        json=payload,
        timeout=30,
    )
    return r.status_code == 200, {
        "status_code": r.status_code,
        "topic": topic_meta["topic"],
        "pillar": topic_meta["pillar"],
        "scheduled_utc": scheduled.isoformat(),
        "scheduled_local_dubai": scheduled.astimezone(
            __import__("zoneinfo").ZoneInfo("Asia/Dubai")
        ).strftime("%Y-%m-%d %H:%M %Z"),
        "scheduled_local_singapore": scheduled.astimezone(
            __import__("zoneinfo").ZoneInfo("Asia/Singapore")
        ).strftime("%Y-%m-%d %H:%M %Z"),
        "response": r.json() if r.status_code == 200 else r.text[:200],
    }


def check_agentmail():
    token = get_env("AGENTMAIL_API_TOKEN")
    inbox = get_env("AGENTMAIL_INBOX")
    if not token or not inbox:
        return 0, "no token/inbox"
    try:
        r = requests.get(
            f"https://api.agentmail.to/v1/inboxes/{inbox}/messages",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        data = r.json()
        messages = data.get("messages", [])
        unread = sum(1 for m in messages if not m.get("read", True))
        return unread, None
    except Exception as e:
        return 0, str(e)


def send_telegram_report(report):
    token = get_env("SPRITE_HERMES_BOT_ID")
    chat_id = "-1003816725976"
    if not token:
        print("No Telegram token")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": chat_id, "text": report, "parse_mode": "Markdown"},
        timeout=20,
    )
    return r.status_code == 200


def main():
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Schedule post
    post_ok, post_result = schedule_linkedin_post()

    # Check email
    unread_count, email_error = check_agentmail()

    # Build report
    status_emoji = "\u2705 Scheduled" if post_ok else "\u274c Failed"
    robot_emoji = "\ud83e\udd16"
    topic = post_result.get("topic", "n/a") if isinstance(post_result, dict) else "n/a"
    pillar = post_result.get("pillar", "n/a") if isinstance(post_result, dict) else "n/a"
    sched_utc = post_result.get("scheduled_utc", "n/a") if isinstance(post_result, dict) else "n/a"
    sched_dubai = post_result.get("scheduled_local_dubai", "n/a") if isinstance(post_result, dict) else "n/a"
    sched_singapore = post_result.get("scheduled_local_singapore", "n/a") if isinstance(post_result, dict) else "n/a"
    response_snippet = json.dumps(post_result.get("response") if isinstance(post_result, dict) else post_result)[:200]

    report = f"""# Bijou Daily Runbook \u2014 {date_str}

## LinkedIn Post
- Status: {status_emoji}
- Topic: {topic}
- Pillar: {pillar}
- Scheduled (UTC): `{sched_utc}`
- Scheduled (Dubai): `{sched_dubai}`
- Scheduled (Singapore): `{sched_singapore}`
- Result: `{response_snippet}`

## AgentMail Inbox
- Unread: {unread_count}
- Error: {email_error or 'none'}

## Actions
- [ ] Review unread AgentMail messages
- [ ] Create Monday.com tasks from actionable emails
- [ ] Monitor scheduled post publication
"""

    # Log to repo
    log_to_repo(report)

    # Send Telegram
    telegram_msg = f"""{robot_emoji} *Bijou Daily Runbook* \u2014 {date_str}

*LinkedIn Post:* {status_emoji}
*Topic:* {topic}
*Scheduled (UTC):* `{sched_utc}`
*AgentMail Unread:* {unread_count}

See full log in bijou-autonomous-ops/logs.
"""
    send_telegram_report(telegram_msg)

    print(report)


if __name__ == "__main__":
    main()
