#!/usr/bin/env python3
"""Contact counts from complete saved history and source-linked reply classifications."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from coverage_check import address, stamp
from mail_evidence import load_mail_evidence, timestamp


def addrs(values):
    if isinstance(values, str):
        values = [values]
    return {address(value) for value in values or []}


def kind_of(message):
    classification = message.get("classification")
    if isinstance(classification, dict) and classification.get("kind") in {"substantive", "ooo", "bounce", "calendar"}:
        return classification["kind"]
    return "unknown"


def delivery_status(message, recipient):
    statuses = {failure.get("status", "unknown") for failure in message.get("delivery_failures", [])
                if recipient in addrs(failure.get("recipients"))}
    return statuses.pop() if len(statuses) == 1 else "unknown" if statuses else None


def contact_stats(messages, owner, internal_domains, only=None, *, complete=False, history_complete=False):
    """Pure reduction; only a validated loader may establish complete/history_complete."""
    owner = address(owner)
    internal = {d.lower() for d in internal_domains}
    only = {address(a) for a in only} if only is not None else None
    by = defaultdict(list)
    unattributed_delivery = any(kind_of(m) == "bounce" and not m.get("delivery_failures") for m in messages)
    for message in messages:
        parties = addrs(message["from_"]) | addrs(message.get("to")) | addrs(message.get("cc"))
        for failure in message.get("delivery_failures", []):
            parties |= addrs(failure.get("recipients"))
        for recipient in parties:
            if recipient != owner and recipient.rsplit("@", 1)[-1] not in internal and (only is None or recipient in only):
                by[recipient].append(message)
    if only:
        for recipient in only:
            if recipient != owner and recipient.rsplit("@", 1)[-1] not in internal:
                by[recipient]  # A complete empty history is meaningful for a requested contact.
    out = []
    for recipient, rows in sorted(by.items()):
        rows.sort(key=lambda m: (timestamp(m["date"]), m["email_id"]))
        sent = [m for m in rows if owner in addrs(m["from_"])]
        inbound = [m for m in rows if recipient in addrs(m["from_"]) or delivery_status(m,recipient) is not None]
        def inbound_kind(message):
            delivery = delivery_status(message, recipient)
            if delivery is not None:
                return "bounce" if delivery == "failed" else "unknown"
            value = kind_of(message)
            return "unknown" if value == "bounce" else value
        substantive = [m for m in inbound if inbound_kind(m) == "substantive"]
        last_reply = substantive[-1] if substantive else None
        uncertain = [m for m in inbound if inbound_kind(m) == "unknown"
                     and (last_reply is None or timestamp(m["date"]) > timestamp(last_reply["date"]))]
        errors = []
        if not complete:
            errors.append("mail receipt completeness is not established")
        if not history_complete and last_reply is None:
            errors.append("limited history cannot establish the unanswered interval")
        if uncertain:
            errors.append("unresolved inbound classification: " + ", ".join(m["email_id"] for m in uncertain))
        if unattributed_delivery:
            errors.append("delivery report has no identified failed recipient; recipient status needs review")
        newest_rows = [m for m in rows if kind_of(m) != "bounce"] or rows
        newest = newest_rows[-1] if newest_rows else None
        count_known = complete and not uncertain and (history_complete or last_reply is not None)
        out.append({"email":recipient, "ready":not errors, "errors":errors,
            "history_complete":history_complete,
            "sent_count":len(sent) if complete else None, "observed_sent_count":len(sent),
            "last_sent":sent[-1]["date"] if complete and sent else None,
            "last_outbound_message_id":sent[-1]["email_id"] if complete and sent else None,
            "last_inbound":inbound[-1]["date"] if complete and inbound else None,
            "last_inbound_type":inbound_kind(inbound[-1]) if complete and inbound else None,
            "last_inbound_message_id":inbound[-1]["email_id"] if complete and inbound else None,
            "last_substantive_reply":last_reply["date"] if complete and last_reply else None,
            "has_substantive_reply":True if substantive else False if complete and history_complete and not uncertain else None,
            "unanswered_count":sum(last_reply is None or timestamp(m["date"]) > timestamp(last_reply["date"]) for m in sent) if count_known else None,
            "newest_message_id":newest["email_id"] if complete and newest else None,
            "thread_id":newest["thread_id"] if complete and newest else None})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("owner_email")
    ap.add_argument("outputs", nargs="+")
    ap.add_argument("--only", help="comma-separated addresses")
    ap.add_argument("--calls", type=Path, help="paired normalized receipt directory")
    ap.add_argument("--since", help="offset-aware run start")
    ap.add_argument("--policy", type=Path, default=Path("_shared/policy.json"))
    args = ap.parse_args()
    try:
        policy = json.loads(args.policy.read_text())
        if address(args.owner_email) != address(policy["identity"]["owner_email"]):
            raise ValueError("owner_email must match the configured mailbox identity")
        only = {address(x.strip()) for x in args.only.split(",")} if args.only else None
        evidence = load_mail_evidence(args.outputs,args.calls,stamp(args.since) if args.since else None,
            policy["identity"]["owner_id"],only,timezone_name=policy["identity"]["timezone"])
        contacts = contact_stats(evidence["messages"],args.owner_email,policy["identity"]["internal_domains"],
            only or set(evidence["addresses"]) or None, complete=evidence["ready"],history_complete=evidence["history_complete"])
        ready = evidence["ready"] and all(row["ready"] for row in contacts)
        print(json.dumps({"ready":ready,"errors":evidence["errors"],"contacts":contacts},indent=2))
        return int(not ready)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({"ready":False,"errors":[str(exc)],"contacts":[]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
