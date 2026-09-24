#!/usr/bin/env python3
"""Reduce explicit mail result files to contact counts; never prints message bodies."""
import argparse
from collections import defaultdict
from email.utils import getaddresses
import json
from pathlib import Path
import re

from mail_evidence import load_messages, timestamp

OOO = re.compile(r"out of (the )?office|automatic reply|auto-?reply|on leave|away from", re.I)
BOUNCE = re.compile(r"undeliverable|delivery (status|has failed)|mail delivery|not delivered|bounced", re.I)
CALENDAR = re.compile(r"^\s*(accepted|declined|tentative(ly accepted)?|invitation|updated invitation|canceled event|cancell?ed):", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def addrs(values):
    if isinstance(values, str):
        values = [values]
    return {a.lower().strip() for _, a in getaddresses([v for v in values or [] if v]) if "@" in a}


def kind_of(message):
    # Prefer the newest body; quoted history is not evidence of a current bounce/OOO.
    from mail_thread_digest import clean
    text = str(message.get("subject", "")) + " " + clean(message.get("body_text") or message.get("body") or message.get("snippet"), 10000)
    if BOUNCE.search(text):
        return "bounce"
    if CALENDAR.match(message.get("subject", "")):
        return "calendar"
    return "ooo" if OOO.search(text) else "substantive"


def contact_stats(messages, owner, internal_domains, only=None):
    owner = owner.lower()
    internal = {d.lower() for d in internal_domains}
    def external(address):
        return address != owner and address.rsplit("@", 1)[-1] not in internal and "calendar-notification" not in address
    by = defaultdict(list)
    for message in messages:
        parties = addrs(message["from_"]) | addrs(message.get("to")) | addrs(message.get("cc"))
        bounced = set()
        if kind_of(message) == "bounce":
            text = " ".join(str(message.get(k) or "") for k in ("subject", "snippet", "body", "body_text"))
            bounced = {a.lower() for a in EMAIL_RE.findall(text)} - addrs(message["from_"])
            parties |= bounced
        for address in parties:
            if external(address) and (only is None or address in only):
                by[address].append((message, address in bounced))
    out = []
    for address, rows in sorted(by.items()):
        rows.sort(key=lambda pair: timestamp(pair[0]["date"]))
        sent = [m for m, _ in rows if owner in addrs(m["from_"])]
        inbound = [m for m, bounced in rows if address in addrs(m["from_"]) or bounced]
        substantive = [m for m in inbound if kind_of(m) == "substantive"]
        last_reply = substantive[-1] if substantive else None
        newest = ([m for m, _ in rows if kind_of(m) != "bounce"] or [m for m, _ in rows])[-1]
        out.append({"email": address, "sent_count": len(sent),
            "last_sent": sent[-1]["date"] if sent else None,
            "last_outbound_message_id": sent[-1]["email_id"] if sent else None,
            "last_inbound": inbound[-1]["date"] if inbound else None,
            "last_inbound_type": kind_of(inbound[-1]) if inbound else None,
            "last_inbound_message_id": inbound[-1]["email_id"] if inbound else None,
            "has_substantive_reply": bool(substantive),
            "unanswered_count": sum(not last_reply or timestamp(m["date"]) > timestamp(last_reply["date"]) for m in sent),
            "newest_message_id": newest["email_id"], "thread_id": newest["thread_id"]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("owner_email")
    ap.add_argument("outputs", nargs="+")
    ap.add_argument("--only", help="comma-separated addresses")
    ap.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    a = ap.parse_args()
    pol = json.loads(a.policy.read_text())
    only = {x.strip().lower() for x in a.only.split(",")} if a.only else None
    print(json.dumps(contact_stats(load_messages(a.outputs), a.owner_email, pol["identity"]["internal_domains"], only), indent=2))


if __name__ == "__main__":
    main()
