#!/usr/bin/env python3
"""Bijou AI LinkedIn content engine: generate, approve, schedule posts via Publora.

Key scheduling logic (2025 best-practice):
- LinkedIn engagement peak = Tuesday-Thursday 10:00-12:00 in the audience's LOCAL timezone.
- Bijou AI's primary audiences are Dubai/UAE (UTC+4, GST) and Southeast Asia (UTC+8, SGT).
- The "best global compromise" window for both regions is 10:00 GST / 14:00 SGT.
- This engine therefore targets 10:00 GST (06:00 UTC) for the daily post.
- If the chosen day is not Tue-Thu, it advances to the next Tuesday-Thursday window.
"""
import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


def get_env(key):
    env_path = Path(r"C:\Users\W3jde\AppData\Local\hermes\.env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line[len(key) + 1:].strip().strip('"').strip("'")
    return os.environ.get(key, "")


# --- Content constants ---

CONTENT_PILLARS = [
    {
        "theme": "AI automation for SMEs",
        "topics": [
            "WhatsApp-first AI agents for customer service",
            "Automating payroll and HR ops",
            "AI scheduling assistants",
            "ROI of AI automation for small business",
        ],
    },
    {
        "theme": "Founder/builder journey",
        "topics": [
            "Lessons from shipping production AI systems",
            "What 40+ hours saved monthly looks like",
            "Why we build AI agents in SEA + UAE",
            "From prototype to production: real talk",
        ],
    },
    {
        "theme": "Dubai/UAE + SEA market focus",
        "topics": [
            "SME digital transformation in Dubai",
            "AI adoption in Southeast Asia",
            "Building for multilingual customers",
            "Regulatory and compliance considerations",
        ],
    },
    {
        "theme": "AI industry insights",
        "topics": [
            "RAG pipelines that actually work",
            "When to use agents vs traditional automation",
            "Cost of AI hallucinations in production",
            "Voice AI and conversational interfaces",
        ],
    },
]

# Flatten topics with their pillar so we can rotate across all of them.
EVERGREEN_TOPICS = []
for pillar in CONTENT_PILLARS:
    for topic in pillar["topics"]:
        EVERGREEN_TOPICS.append({"pillar": pillar["theme"], "topic": topic})

# --- Scheduling constants ---

# Audience timezones (Dubai/GST + ASEAN/SGT)
AUDIENCE_TIMEZONES = ["Asia/Dubai", "Asia/Singapore"]

# Best-practice LinkedIn window: Tuesday-Thursday, 10:00-12:00 local.
# The compromise point that lands in the peak window for BOTH audiences is
# 10:00 GST (Asia/Dubai) which equals 14:00 SGT (Asia/Singapore).
PRIMARY_AUDIENCE_TZ = "Asia/Dubai"
TARGET_LOCAL_HOUR = 10
TARGET_LOCAL_MINUTE = 0


def _get_topic_index_for_date(date: datetime) -> int:
    """Deterministic, stable topic index for a given date.

    Uses the ordinal day so the same calendar date always picks the same topic,
    but different topics rotate each day. This makes the rotation testable and
    evergreen-content friendly.
    """
    return date.toordinal() % len(EVERGREEN_TOPICS)


def find_next_best_post_time(
    from_dt: datetime | None = None,
    tz_name: str = PRIMARY_AUDIENCE_TZ,
    target_hour: int = TARGET_LOCAL_HOUR,
    target_minute: int = TARGET_LOCAL_MINUTE,
) -> datetime:
    """Return the next Tue-Thu scheduling slot at the target local time, in UTC.

    Args:
        from_dt: start searching from this UTC time (defaults to now).
        tz_name: audience timezone used to decide the target local hour.
        target_hour: desired local hour (default 10 for 10:00 AM).
        target_minute: desired local minute.

    Returns:
        Timezone-aware datetime in UTC representing the next best slot.
    """
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    if from_dt is None:
        from_dt = datetime.now(timezone.utc)
    elif from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=timezone.utc)

    # Start with today's target local time.
    local_now = from_dt.astimezone(tz)
    candidate_local = local_now.replace(
        hour=target_hour,
        minute=target_minute,
        second=0,
        microsecond=0,
    )

    # If today's slot already passed, move to tomorrow.
    if candidate_local <= local_now:
        candidate_local = candidate_local + timedelta(days=1)

    # Advance until we land on a Tuesday (1) - Thursday (3).
    while candidate_local.weekday() not in (1, 2, 3):
        candidate_local = candidate_local + timedelta(days=1)

    return candidate_local.astimezone(timezone.utc)


def generate_post(topic, tone="founder"):
    """Generate a LinkedIn post for Bijou AI / W3J LLC."""
    intros = [
        "Muhammad Nurunnabi here — building W3J LLC / Bijou AI.",
        "Quick take from the W3J LLC lab:",
        "We shipped another AI automation this week.",
        "A founder asked me this yesterday:",
    ]
    closers = [
        "What automation are you exploring this quarter?",
        "DM if you want the playbook.",
        "Building in public at mybijou.xyz.",
        "Would love your thoughts below.",
    ]
    intro = intros[hash(topic) % len(intros)]
    closer = closers[hash(topic + "closer") % len(closers)]

    body_templates = {
        "AI automation for SMEs": f"""{intro}

{topic}.

Most SMEs don't need another dashboard. They need a system that actually answers customers, schedules staff, and chases invoices — while they sleep.

That's what we're building at Bijou AI.

{closer}""",
        "Founder/builder journey": f"""{intro}

{topic}.

The pattern is always the same: start with a manual process, find the 20% that eats 80% of the time, then automate that part first.

Ship the boring win before chasing the shiny demo.

{closer}""",
        "Dubai/UAE + SEA market focus": f"""{intro}

{topic}.

The opportunity isn't replacing humans. It's giving small teams the leverage that only enterprises had before.

That's the bet we're making in Dubai/UAE and Southeast Asia.

{closer}""",
        "AI industry insights": f"""{intro}

{topic}.

The teams winning with AI right now aren't the ones with the biggest models. They're the ones with the tightest feedback loops.

Build. Measure. Fix. Repeat.

{closer}""",
    }

    pillar = None
    for p in CONTENT_PILLARS:
        if topic in p["topics"]:
            pillar = p["theme"]
            break
    pillar = pillar or "AI automation for SMEs"

    return body_templates[pillar]


def schedule_post(text, platform_id, scheduled_at=None):
    """Schedule via Publora API."""
    token = get_env("PUBLORA_API_KEY")
    if not token:
        raise SystemExit("PUBLORA_API_KEY not found")

    if scheduled_at is None:
        scheduled_at = find_next_best_post_time().isoformat()

    url = "https://api.publora.com/api/v1/create-post"
    payload = {
        "content": text,
        "platforms": [platform_id],
        "scheduledTime": scheduled_at,
    }
    headers = {
        "Content-Type": "application/json",
        "x-publora-key": token,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"Publora response: {r.status_code}")
    print(r.text[:500])
    return r


def list_scheduled():
    token = get_env("PUBLORA_API_KEY")
    url = "https://api.publora.com/api/v1/list-posts"
    headers = {"x-publora-key": token}
    r = requests.get(url, headers=headers, params={"limit": 50, "status": "scheduled"}, timeout=30)
    print(r.status_code)
    print(json.dumps(r.json(), indent=2)[:2000])


def get_platform_connections():
    token = get_env("PUBLORA_API_KEY")
    if not token:
        raise SystemExit("PUBLORA_API_KEY not found")
    url = "https://api.publora.com/api/v1/platform-connections"
    headers = {"x-publora-key": token}
    r = requests.get(url, headers=headers, timeout=30)
    return r


def get_post(post_group_id: str):
    token = get_env("PUBLORA_API_KEY")
    if not token:
        raise SystemExit("PUBLORA_API_KEY not found")
    url = f"https://api.publora.com/api/v1/get-post/{post_group_id}"
    headers = {"x-publora-key": token}
    r = requests.get(url, headers=headers, timeout=30)
    return r


def delete_post(post_group_id: str):
    token = get_env("PUBLORA_API_KEY")
    if not token:
        raise SystemExit("PUBLORA_API_KEY not found")
    url = f"https://api.publora.com/api/v1/delete-post/{post_group_id}"
    headers = {"x-publora-key": token}
    r = requests.delete(url, headers=headers, timeout=30)
    return r


def build_weekly_calendar(
    platform_id,
    weeks: int = 1,
    posts_per_week: int = 3,
    from_dt: datetime | None = None,
):
    """Build a timezone-aware weekly calendar of evergreen posts.

    Posts are spaced across the best-practice Tue-Thu window and topics rotate
    deterministically so no pillar is over-used.
    """
    slots = []
    current = from_dt or datetime.now(timezone.utc)

    while len(slots) < weeks * posts_per_week:
        slot = find_next_best_post_time(from_dt=current)
        slots.append(slot)
        # Advance to the next day so find_next_best_post_time does not return
        # the same slot again.
        current = slot + timedelta(days=1)

    posts = []
    for slot in slots:
        topic_meta = EVERGREEN_TOPICS[_get_topic_index_for_date(slot)]
        post = generate_post(topic_meta["topic"])
        posts.append({
            "topic": topic_meta["topic"],
            "pillar": topic_meta["pillar"],
            "scheduled_utc": slot.isoformat(),
            "scheduled_local_dubai": slot.astimezone(
                __import__("zoneinfo").ZoneInfo("Asia/Dubai")
            ).strftime("%Y-%m-%d %H:%M %Z"),
            "scheduled_local_singapore": slot.astimezone(
                __import__("zoneinfo").ZoneInfo("Asia/Singapore")
            ).strftime("%Y-%m-%d %H:%M %Z"),
            "content": post,
        })
    return posts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "generate",
            "schedule",
            "calendar",
            "list",
            "connections",
            "get-post",
            "delete-post",
        ],
    )
    parser.add_argument("--topic", default="WhatsApp-first AI agents for customer service")
    parser.add_argument("--platform-id", default="linkedin-asZgv9imjx")
    parser.add_argument("--schedule", default=None)
    parser.add_argument("--post-group-id", default=None)
    parser.add_argument("--weeks", type=int, default=1)
    parser.add_argument("--posts-per-week", type=int, default=3)
    parser.add_argument("--commit", action="store_true", help="Actually schedule posts instead of dry-run preview")
    args = parser.parse_args()

    if args.action == "generate":
        post = generate_post(args.topic)
        print(post)
    elif args.action == "schedule":
        post = generate_post(args.topic)
        if args.schedule:
            scheduled_at = args.schedule
        else:
            scheduled_at = find_next_best_post_time().isoformat()
            print(f"Next best slot (UTC): {scheduled_at}")
        schedule_post(post, args.platform_id, scheduled_at)
    elif args.action == "calendar":
        posts = build_weekly_calendar(
            args.platform_id,
            weeks=args.weeks,
            posts_per_week=args.posts_per_week,
        )
        print(json.dumps(posts, indent=2))
        if args.commit:
            for p in posts:
                print(f"\nScheduling: {p['topic']} at {p['scheduled_utc']}")
                schedule_post(p["content"], args.platform_id, p["scheduled_utc"])
        else:
            print("\nDry-run: pass --commit to schedule these posts via Publora.")
    elif args.action == "list":
        list_scheduled()
    elif args.action == "connections":
        r = get_platform_connections()
        print(r.status_code)
        print(json.dumps(r.json() if r.status_code == 200 else r.text, indent=2)[:2000])
    elif args.action == "get-post":
        if not args.post_group_id:
            raise SystemExit("--post-group-id required")
        r = get_post(args.post_group_id)
        print(r.status_code)
        print(json.dumps(r.json() if r.status_code == 200 else r.text, indent=2)[:2000])
    elif args.action == "delete-post":
        if not args.post_group_id:
            raise SystemExit("--post-group-id required")
        r = delete_post(args.post_group_id)
        print(r.status_code)
        print(json.dumps(r.json() if r.status_code == 200 else r.text, indent=2)[:2000])


if __name__ == "__main__":
    main()
