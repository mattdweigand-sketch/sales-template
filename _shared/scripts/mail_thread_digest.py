#!/usr/bin/env python3
"""Print short newest-body digests without signed attachment URLs or quoted history."""
import argparse
import html
import re
from mail_evidence import load_messages


def clean(text, n):
    text = text or ""
    text = re.split(r"(?is)<blockquote\b|<div[^>]+class=[\"'][^\"']*(?:gmail_quote|yahoo_quoted)", text, maxsplit=1)[0]
    text = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", "", text)
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.split(r"(?im)^\s*(?:On .{1,300}wrote:|[- ]*Original Message[- ]*|>)", text, maxsplit=1)[0]
    # Query parameters often contain signed attachment credentials; omit them in digests.
    text = re.sub(r"https?://[^\s<>]+", lambda m: m[0].split("?")[0].split("#")[0], text)
    return re.sub(r"\s+", " ", text).strip()[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("outputs", nargs="+")
    ap.add_argument("--chars", type=int, default=300)
    args = ap.parse_args()
    if args.chars < 0:
        ap.error("--chars must be non-negative")
    try:
        messages = load_messages(args.outputs)
    except (ValueError, OSError) as exc:
        ap.error(str(exc))
    for message in reversed(messages):
        print(f"{message['date']} | {message['email_id']} | {message['thread_id']} | from {message['from_']}")
        print("  " + clean(message.get("subject"), args.chars))
        print("  " + clean(message.get("body_text") or message.get("body") or message.get("snippet"), args.chars))
        names = [a.get("filename", "") for a in message.get("attachments") or []]
        if names:
            print("  attachments: " + ", ".join(names))
    print(f"{len(messages)} emails; digest is truncated evidence; read full relevant bodies before decisions or drafting")


if __name__ == "__main__":
    main()
