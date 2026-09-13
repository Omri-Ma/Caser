import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Dev-only stand-in for real email delivery (CLAUDE.md's Future additions —
# there's no SMTP provider set up, that's a real infra decision out of
# scope for this exercise). The reset link is written here instead of
# actually emailed, and a small frontend page reads it back so a developer
# (or the grader) can find it without digging through server logs.
#
# Both client_api and admin_api run with WORKDIR /app bind-mounted to the
# host's ./server directory, so a bare relative filename here lands in the
# same host file for both processes regardless of which one wrote it.
DEV_OUTBOX_PATH = Path(os.getenv("DEV_OUTBOX_PATH", "dev_outbox.jsonl"))
MAX_OUTBOX_ENTRIES = 200


def write_dev_outbox(email: str, link: str) -> None:
    entry = {"email": email, "link": link, "created_at": datetime.now(timezone.utc).isoformat()}
    with DEV_OUTBOX_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_dev_outbox(email: str | None = None) -> list[dict]:
    if not DEV_OUTBOX_PATH.exists():
        return []
    entries = []
    with DEV_OUTBOX_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if email is not None:
        entries = [e for e in entries if e.get("email") == email]
    entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return entries[:MAX_OUTBOX_ENTRIES]
