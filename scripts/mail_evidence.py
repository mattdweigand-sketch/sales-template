"""Shared strict reader for saved mail results; no network or global account state."""
from datetime import datetime, timezone
from pathlib import Path
import json


def timestamp(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("mail date needs a timezone offset")
    return stamp.astimezone(timezone.utc)


def load_messages(paths):
    messages = {}
    for path in paths:
        doc = json.loads(Path(path).read_text())
        result = doc.get("result", doc)
        if isinstance(result, str):
            result = json.loads(result)
        if result.get("error") or result.get("authenticated") is False:
            raise ValueError(f"failed mail result: {path}")
        rows = result.get("email_results", {}).get("emails")
        if not isinstance(rows, list):
            raise ValueError(f"missing mail rows: {path}")
        for row in rows:
            for field in ("email_id", "thread_id", "date", "from_"):
                if not isinstance(row.get(field), str) or not row[field]:
                    raise ValueError(f"mail row missing {field}")
            timestamp(row["date"])
            key = row["email_id"]
            if key in messages and messages[key] != row:
                raise ValueError(f"conflicting copies of message {key}")
            messages[key] = row
    return sorted(messages.values(), key=lambda row: timestamp(row["date"]))
