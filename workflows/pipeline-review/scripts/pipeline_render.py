#!/usr/bin/env python3
"""Render the pipeline-review report, question walk, write receipt, and notification.

Usage (run from the repository root with explicit external input paths):
  pipeline_render.py report       --run REVIEW.json --coverage COVERAGE.json [--policy PATH]
  pipeline_render.py question     --run REVIEW.json --label Q1 [--policy PATH]
  pipeline_render.py receipt      --run REVIEW.json [--labels 1,Q1-a,A] [--final] [--policy PATH]
  pipeline_render.py notification --run REVIEW.json --coverage COVERAGE.json [--policy PATH]

This file owns the exact presentation. REVIEW.json is outputs/pipeline-review.json,
separate from the existing external run.json identity file. Notification mode returns
chat status only; it never sends or schedules anything. The workflow writes one reviewed run file per run
in the external run directory, and passes the saved `coverage_check --json` output for this run and scope.
The helper validates structure, reconciles counts, and checks labels. Approval/status fields are reviewed assertions,
not proof of permission; preserve exact approval and independent readbacks in the run. It never infers sales
facts, chooses actions, grants approval, or writes to any system. A clean render is not a
ready run: coverage and process status come from the inputs and are printed as given.

Exit 0 rendered to stdout. Exit 1 validation failed, errors on stderr, nothing on stdout.
Exit 2 unreadable input or usage error.

Run file keys
  run        id, date (YYYY-MM-DD), branch (daily|extended), coverage_scope
             (pipeline-daily on daily, pipeline on Extended), process_status (complete|incomplete),
             process_gaps (list, required when incomplete), optional thread_url and schedule (notification)
  counts     open (snapshot), in_scope, reviewed, skipped, not_checked; in_scope = last three summed
  deals      every reviewed candidate once: native id, name, flags (trigger names; empty for unflagged input)
  withheld   list of {deal, reason}; required, possibly empty, when coverage is not ready
  blocks     clear recommendations: label ("1", "2"...), deal, status, next_step {current,
             proposed or null, optional current_full and proposed_full for a history change},
             changes (list), evidence (list), optional depends_on_unknown, superseded_by
  questions  label ("Q1"...), deal, status, context, question, next_step_current, evidence,
             options: label ("Q1-a"...), text, status, changes (empty for a factual answer)
  extended   Extended only: rollup {stages [{stage, count, amount}], forecast {category: amount},
             this_quarter {count, amount}, later {count, amount}},
             since ("M/D"), delta [{kind, deal, text}], letters [{label "A"..., deal,
             deal_name, status, change, evidence, basis}]
  writes     one per record field attempted: label, object, id, field ("create" for a Task
             create), outcome (written|rejected|unverified|not_attempted), detail. Each write
             must match an approved change of its label; a change with no write is not attempted.
A change is {object Opportunity|Task, id, field, current, proposed, name}. Task updates add
task_kind (reschedule|rename|complete|update|close_duplicate) and same_action true; complete adds
completion_evidence; close_duplicate adds duplicate_of and appears only in question options.
mode "prepend" marks a new first line kept above existing text; question options and letters may
carry NextSteps only this way. A Task create
is {object Task, action create, fields {Subject, ActivityDate, Status, WhoId, WhatId}, who_name,
linkage_verified true, candidates_refreshed true}. Evidence is {date, source, who, title, link,
fact, source_id}; source_id stays in the external run directory and is never rendered.
Statuses: proposed, approved, written, partial, failed, skipped, deferred, superseded; questions
use open, answered, skipped, deferred, superseded.
"""
import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "_shared" / "policy.yaml"

ITEM_STATUSES = {"proposed", "approved", "written", "partial", "failed", "skipped", "deferred", "superseded"}
QUESTION_STATUSES = {"open", "answered", "skipped", "deferred", "superseded"}
WRITE_OUTCOMES = {"written", "rejected", "unverified", "not_attempted"}
OUTCOME_RANK = ("rejected", "unverified", "not_attempted", "written")
OUTCOME_TEXT = {"written": "Written", "rejected": "Rejected", "unverified": "Unverified", "not_attempted": "Not attempted"}
TASK_KINDS = {"reschedule", "rename", "complete", "update", "close_duplicate"}
SCOPE_FOR_BRANCH = {"daily": "pipeline-daily", "extended": "pipeline"}
CREATE_FIELDS = ("Subject", "ActivityDate", "Status", "WhoId", "WhatId")
RECORD_OBJECTS = {"Opportunity", "Task", "Contact"}
BLOCK_LABEL = re.compile(r"^[1-9]\d*$")
QUESTION_LABEL = re.compile(r"^Q[1-9]\d*$")
LETTER_LABEL = re.compile(r"^[A-Z]{1,2}$")
EVIDENCE_SOURCES = {"Mail", "Calendar", "CRM", "User", "Pilot report"}
RETRIEVED_SOURCES = {"Mail", "Calendar"}

LIMITATION = "Email and Calendar evidence is the retrieved set, not full history."
HISTORY_NOTE = "Only the latest next-step entry is shown. Older history stays unchanged."
LEGACY_NOTE = "Legacy `Next:` entries appear as stored."
EMPTY_BLOCKS = "No clear recommendations."
EMPTY_QUESTIONS = "No questions."
WALK_NOTE = "I walk these one at a time after the clear recommendations."
NO_CHANGES = "No CRM changes proposed."
NO_NEXT_STEP_CHANGE = "No next-step change."
SKIP_OPTION = "skip · Leave unchanged. Named at close."
APPROVE_DAILY = "**Reply with numbers, ranges, all, or skip. all covers the numbered clear recommendations only.**"
APPROVE_EXTENDED = ("**Reply with numbers, ranges, all, letters, or skip. all covers the numbered clear "
                  "recommendations only. Each letter approves one record.**")
TITLE_DAILY = "Pipeline review · {d}"
TITLE_EXTENDED = {"ready": "Extended pipeline review ready for approval",
                "complete": "Extended pipeline review complete",
                "incomplete": "Extended pipeline review incomplete"}


class RenderError(Exception):
    pass


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise RenderError(f"cannot read {path}: {exc}") from exc


def md(d):
    return f"{d.month}/{d.day}/{d.strftime('%y')}"


def display(text):
    """Readable display only: HTML paragraph and break boundaries become newlines, entities decode."""
    if text is None:
        return "Empty"
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(text))
    s = re.sub(r"(?i)</p>\s*<p[^>]*>", "\n", s)
    s = re.sub(r"(?i)</?p[^>]*>", "", s)
    s = html.unescape(s).strip()
    return s if s else "Empty"


def n(count, one, many):
    return f"{count} {one if count == 1 else many}"


def exact(text):
    return "Empty" if text in (None, "") else str(text)


def change_key(c):
    if c.get("action") == "create":
        return ("Task", None, "create")
    return (c.get("object"), c.get("id"), c.get("field"))


def write_key(w):
    return (w.get("object"), None if w.get("field") == "create" else w.get("id"), w.get("field"))


def expected_keys(item):
    """Record fields a label approves: a block's next step and changes, a letter's change, an option's changes."""
    keys = [change_key(c) for c in ([item["change"]] if isinstance(item.get("change"), dict) else item.get("changes") or [])]
    if (item.get("next_step") or {}).get("proposed") is not None:
        keys.insert(0, ("Opportunity", item.get("deal"), "NextSteps"))
    return keys


def record_outcomes(rows):
    """One outcome per (label, object, id) record: written only when every field row for it is written."""
    grouped = {}
    for w in rows:
        grouped.setdefault((str(w.get("label")), w.get("object"), w.get("id")), []).append(w.get("outcome"))
    return [min(v, key=OUTCOME_RANK.index) if all(o in OUTCOME_RANK for o in v) else "unverified"
            for v in grouped.values()]


class Run:
    def __init__(self, data, policy, coverage=None):
        self.data = data
        self.policy = policy
        self.coverage = coverage
        self.errors = []
        sf = policy.get("crm", {})
        self.record_url = sf.get("record_url", "").replace("{instance_url}", sf.get("instance_url", ""))
        self.url_objects = RECORD_OBJECTS
        prefix = sf.get("note_prefix", "M/D/YY SELLER - ")
        self.run = data.get("run") or {}
        self.counts = data.get("counts") or {}
        self.deals = {d.get("id"): d for d in data.get("deals") or []}
        self.blocks = data.get("blocks") or []
        self.questions = data.get("questions") or []
        self.extended = data.get("extended") or {}
        self.letters = self.extended.get("letters") or []
        self.writes = data.get("writes") or []
        try:
            self.date = date.fromisoformat(str(self.run.get("date")))
        except ValueError:
            self.date = None
        self.entry_prefix = prefix.replace("M/D/YY", md(self.date)) if self.date else None

    # ---- helpers
    def err(self, msg):
        self.errors.append(msg)

    def url(self, obj, rid):
        if obj in self.url_objects and rid:
            return self.record_url.replace("{Object}", obj).replace("{Id}", quote(rid, safe=""))
        return None

    def link(self, obj, rid, text):
        u = self.url(obj, rid)
        return f"[{text}]({u})" if u else f"{text} ({rid})"

    def deal_link(self, deal_id):
        d = self.deals.get(deal_id, {})
        return self.link("Opportunity", deal_id, d.get("name") or deal_id)

    def active(self, items):
        return [i for i in items if i.get("status") != "superseded"]

    def live_options(self, q):
        return [o for o in q.get("options") or [] if o.get("status") != "superseded"]

    def coverage_ready(self):
        c = self.coverage or {}
        return c.get("ready") is True and c.get("process_status") == "complete"

    def process_complete(self):
        return self.run.get("process_status") == "complete"

    # ---- validation
    def check_id(self, obj, rid, where):
        if not isinstance(rid, str) or not rid.strip() or any(ord(c) < 32 for c in rid):
            self.err(f"{where}: {obj} id must be a nonempty native record ID")

    def check_evidence(self, items, where, required=True):
        if required and not items:
            self.err(f"{where}: needs at least one evidence item")
        for n, e in enumerate(items or [], 1):
            w = f"{where} evidence {n}"
            if not e.get("date") or not e.get("fact"):
                self.err(f"{w}: date and fact are required")
            if e.get("source") not in EVIDENCE_SOURCES:
                self.err(f"{w}: source must be one of {sorted(EVIDENCE_SOURCES)}")
            link = e.get("link")
            if link and not re.match(r"^https://\S+$", link):
                self.err(f"{w}: link must be a returned https URL, never constructed")
            if link and not e.get("title"):
                self.err(f"{w}: a link needs a title to display")

    def check_change(self, c, where, letter=False, option=False):
        obj = c.get("object")
        if obj not in ("Opportunity", "Task"):
            self.err(f"{where}: object must be Opportunity or Task")
            return
        if c.get("action") == "create":
            if obj != "Task":
                self.err(f"{where}: only a Task can be created")
                return
            f = c.get("fields") or {}
            for key in CREATE_FIELDS:
                if not f.get(key):
                    self.err(f"{where}: Task create needs {key}")
            extra = sorted(set(f) - set(CREATE_FIELDS))
            if extra:
                self.err(f"{where}: Task create fields {extra} are not displayed; remove them or propose them separately")
            if f.get("WhoId"):
                self.check_id("Contact", f["WhoId"], where)
            if f.get("WhatId"):
                self.check_id("Opportunity", f["WhatId"], where)
            if c.get("linkage_verified") is not True:
                self.err(f"{where}: Task create needs linkage_verified true")
            if c.get("candidates_refreshed") is not True:
                self.err(f"{where}: Task create needs candidates_refreshed true, refresh open Tasks first")
            if not c.get("who_name"):
                self.err(f"{where}: Task create needs who_name")
            return
        if obj == "Opportunity" and c.get("field") in {"StageName", "CloseDate", "Amount"}:
            if self.run.get("branch") != "extended" or not (letter or option):
                self.err(f"{where}: commercial changes need a separate extended letter or question option")
        self.check_id(obj, c.get("id"), where)
        if not c.get("field"):
            self.err(f"{where}: field is required")
        if "proposed" not in c or c.get("proposed") in (None, ""):
            self.err(f"{where}: proposed value is required")
        if c.get("mode") not in (None, "prepend"):
            self.err(f"{where}: mode must be prepend when set")
        if c.get("mode") != "prepend" and "current" not in c:
            self.err(f"{where}: current value is required, use null for empty")
        if obj == "Opportunity" and c.get("field") == "NextSteps":
            if not (letter or option):
                self.err(f"{where}: put NextSteps in next_step, not changes")
            elif c.get("mode") != "prepend":
                self.err(f"{where}: a NextSteps change adds a first entry with mode prepend, history unchanged")
        if obj == "Task":
            kind = c.get("task_kind")
            if kind not in TASK_KINDS:
                self.err(f"{where}: Task update needs task_kind {sorted(TASK_KINDS)}")
            if c.get("same_action") is not True:
                self.err(f"{where}: Task update needs same_action true, never retarget a Task to another action")
            if kind == "complete" and not c.get("completion_evidence"):
                self.err(f"{where}: Task complete needs completion_evidence")
            if kind == "close_duplicate":
                if not option:
                    self.err(f"{where}: closing a duplicate Task is a question option, never a clear recommendation")
                self.check_id("Task", c.get("duplicate_of"), where)
                if c.get("duplicate_of") == c.get("id"):
                    self.err(f"{where}: duplicate_of must name a different Task")
            if not c.get("name"):
                self.err(f"{where}: Task update needs name (Subject)")

    def record_key(self, c):
        if c.get("action") == "create":
            f = c.get("fields") or {}
            return ("Task:create", f.get("WhatId"), (f.get("Subject") or "").strip().lower())
        return (c.get("object"), c.get("id"), c.get("field"))

    def check_next_step(self, ns, where):
        if not isinstance(ns, dict) or "current" not in ns or "proposed" not in ns:
            self.err(f"{where}: next_step needs current and proposed (null when unchanged)")
            return
        p = ns.get("proposed")
        if p is not None and self.entry_prefix and not str(p).startswith(self.entry_prefix):
            self.err(f"{where}: proposed next step must start with {self.entry_prefix!r}")
        if ns.get("proposed_full") is not None:
            if ns.get("current_full") is None or p is None:
                self.err(f"{where}: full-field changes need current_full and the proposed first entry")
            elif not str(ns["proposed_full"]).startswith(str(p)):
                self.err(f"{where}: proposed_full must begin with the displayed proposed entry")

    def validate(self, mode):
        r = self.run
        if r.get("branch") not in SCOPE_FOR_BRANCH:
            self.err("run.branch must be daily or extended")
        if self.date is None:
            self.err("run.date must be YYYY-MM-DD")
        if not r.get("id"):
            self.err("run.id is required")
        if r.get("process_status") not in ("complete", "incomplete"):
            self.err("run.process_status must be complete or incomplete")
        if r.get("process_status") == "incomplete" and not r.get("process_gaps"):
            self.err("run.process_gaps must name each failed or unfinished step")
        if mode in ("report", "notification"):
            if self.coverage is None or not isinstance(self.coverage, dict) or "lines" not in self.coverage:
                self.err("coverage must be the saved coverage_check --json output")
            if r.get("coverage_scope") != SCOPE_FOR_BRANCH.get(r.get("branch")):
                self.err(f"run.coverage_scope must be {SCOPE_FOR_BRANCH.get(r.get('branch'))} for {r.get('branch')}")
            if self.coverage is not None and not self.coverage_ready() and "withheld" not in self.data:
                self.err("coverage is not ready: list withheld proposals, or an empty list")
        for key in ("open", "in_scope", "reviewed", "skipped", "not_checked"):
            if type(self.counts.get(key)) is not int or self.counts.get(key) < 0:
                self.err(f"counts.{key} must be a non-negative integer")
        ids = [d.get("id") for d in self.data.get("deals") or []]
        if len(ids) != len(set(ids)):
            self.err("deals: each flagged deal appears once")
        for d in self.data.get("deals") or []:
            self.check_id("Opportunity", d.get("id"), f"deal {d.get('name')}")
            if not d.get("name") or not isinstance(d.get("flags"), list):
                self.err(f"deal {d.get('id')}: name and a flags list are required (empty for an unflagged candidate)")
        for w in self.data.get("withheld") or []:
            if w.get("deal") not in self.deals or not w.get("reason"):
                self.err(f"withheld {w.get('deal')}: must name a flagged deal and a reason")

        labels = {}

        def claim(label, where):
            if label in labels:
                self.err(f"{where}: label {label} is already used by {labels[label]}; never recycle a label")
            labels[label] = where

        block_deals = set()
        for b in self.blocks:
            lab = str(b.get("label"))
            where = f"block {lab}"
            if not BLOCK_LABEL.match(lab):
                self.err(f"{where}: label must be a positive number")
            claim(lab, where)
            if b.get("status") not in ITEM_STATUSES:
                self.err(f"{where}: status must be one of {sorted(ITEM_STATUSES)}")
            if b.get("deal") not in self.deals:
                self.err(f"{where}: deal {b.get('deal')} is not a flagged deal")
            if b.get("status") != "superseded":
                if b.get("deal") in block_deals:
                    self.err(f"{where}: one active clear recommendation per deal")
                block_deals.add(b.get("deal"))
            if b.get("depends_on_unknown"):
                self.err(f"{where}: rests on an unknown; move it to Needs your input (rules#evidence)")
            self.check_next_step(b.get("next_step"), where)
            ns = b.get("next_step") or {}
            if ns.get("proposed") is None and not b.get("changes"):
                self.err(f"{where}: a clear recommendation needs at least one change")
            for n, c in enumerate(b.get("changes") or [], 1):
                self.check_change(c, f"{where} change {n}")
            self.check_evidence(b.get("evidence"), where)

        question_deals = set()
        for q in self.questions:
            lab = str(q.get("label"))
            where = f"question {lab}"
            if not QUESTION_LABEL.match(lab):
                self.err(f"{where}: label must look like Q1")
            claim(lab, where)
            if q.get("status") not in QUESTION_STATUSES:
                self.err(f"{where}: status must be one of {sorted(QUESTION_STATUSES)}")
            if q.get("deal") not in self.deals:
                self.err(f"{where}: deal {q.get('deal')} is not a flagged deal")
            if q.get("status") != "superseded":
                question_deals.add(q.get("deal"))
            for key in ("context", "question"):
                if not q.get(key):
                    self.err(f"{where}: {key} is required")
            if "next_step_current" not in q:
                self.err(f"{where}: next_step_current is required, use null for empty")
            live = self.live_options(q)
            if len(live) > 3:
                self.err(f"{where}: at most three live options")
            selected = [o for o in live if o.get("status") in {"approved", "written", "partial", "failed"}]
            if len(selected) > 1:
                self.err(f"{where}: only one alternative can be approved or applied")
            for o in q.get("options") or []:
                olab = str(o.get("label"))
                owhere = f"option {olab}"
                if not re.match(rf"^{re.escape(lab)}-[a-z]+$", olab):
                    self.err(f"{owhere}: option labels look like {lab}-a")
                claim(olab, owhere)
                if o.get("status") not in ITEM_STATUSES:
                    self.err(f"{owhere}: status must be one of {sorted(ITEM_STATUSES)}")
                if not o.get("text"):
                    self.err(f"{owhere}: text is required")
                for n, c in enumerate(o.get("changes") or [], 1):
                    self.check_change(c, f"{owhere} change {n}", option=True)
            self.check_evidence(q.get("evidence"), where)

        if self.letters and r.get("branch") != "extended":
            self.err("lettered record proposals are Extended only")
        if r.get("branch") == "extended" and mode == "report":
            for key in ("rollup", "since", "delta"):
                if key not in self.extended:
                    self.err(f"extended.{key} is required on Extended")
        expected = 0
        for l in self.letters:
            lab = str(l.get("label"))
            where = f"letter {lab}"
            if not LETTER_LABEL.match(lab):
                self.err(f"{where}: label must be a capital letter")
            claim(lab, where)
            if l.get("status") not in ITEM_STATUSES:
                self.err(f"{where}: status must be one of {sorted(ITEM_STATUSES)}")
            if isinstance(l.get("change"), dict):
                self.check_change(l["change"], where, letter=True)
            else:
                self.err(f"{where}: one change, one record per letter")
            if not l.get("basis"):
                self.err(f"{where}: basis is required")
            self.check_evidence(l.get("evidence"), where)
            if len(lab) == 1:
                if ord(lab) - ord("A") != expected:
                    self.err(f"{where}: letters run A, B, C in order with no gaps")
                expected += 1

        for item in self.blocks + self.letters + [o for q in self.questions for o in q.get("options") or []] + self.questions:
            sup = item.get("superseded_by")
            if item.get("status") == "superseded":
                if not sup or sup not in labels:
                    self.err(f"label {item.get('label')}: superseded_by must name the new label")
                elif sup == str(item.get("label")):
                    self.err(f"label {item.get('label')}: cannot supersede itself")
                elif re.fullmatch(r"Q[1-9]\d*-[a-z]+", str(item.get("label"))):
                    old = str(item["label"])
                    if not sup.startswith(old.split("-")[0] + "-") or (len(sup), sup) <= (len(old), old):
                        self.err(f"label {old}: revised option needs the next unused suffix in the same question")
            elif sup:
                self.err(f"label {item.get('label')}: superseded_by is set but status is {item.get('status')}")

        # One owner per record field across independently approvable proposals.
        # Options inside one question are alternatives, so they may repeat each other.
        seen = {}

        def own(key, owner, where):
            if key in seen and (seen[key][0] != owner or where in seen[key][1]):
                self.err(f"{where}: {key[0]} {key[1]} {key[2]} is already proposed in {seen[key][0]}")
            seen.setdefault(key, (owner, set()))[1].add(where)

        for b in self.active(self.blocks):
            owner = f"block {b.get('label')}"
            if (b.get("next_step") or {}).get("proposed") is not None:
                own(("Opportunity", b.get("deal"), "NextSteps"), owner, owner)
            for c in b.get("changes") or []:
                own(self.record_key(c), owner, owner)
        for l in self.active(self.letters):
            owner = f"letter {l.get('label')}"
            own(self.record_key(l.get("change") or {}), owner, owner)
        for q in self.active(self.questions):
            for o in self.live_options(q):
                for c in o.get("changes") or []:
                    own(self.record_key(c), f"question {q.get('label')}", f"option {o.get('label')}")

        for item in self.blocks + self.letters + [o for q in self.questions for o in q.get("options") or []]:
            if expected_keys(item).count(("Task", None, "create")) > 1:
                self.err(f"label {item.get('label')}: at most one Task create per approval label")

        # Every change targets the deal its heading or letter names.
        def targets(changes, deal, where):
            for c in changes:
                target = c.get("id") if c.get("object") == "Opportunity" else (c.get("fields") or {}).get("WhatId")
                if target and target != deal:
                    self.err(f"{where}: change targets {target}, not the deal it is shown under ({deal})")
        for b in self.active(self.blocks):
            targets(b.get("changes") or [], b.get("deal"), f"block {b.get('label')}")
        for q in self.active(self.questions):
            for o in self.live_options(q):
                targets(o.get("changes") or [], q.get("deal"), f"option {o.get('label')}")
        for l in self.active(self.letters):
            where = f"letter {l.get('label')}"
            self.check_id("Opportunity", l.get("deal"), where)
            if not l.get("deal_name"):
                self.err(f"{where}: deal_name is required")
            targets([l.get("change") or {}], l.get("deal"), where)

        # A withheld deal has nothing approvable.
        held = {w.get("deal") for w in self.data.get("withheld") or []}
        for item, deal in ([(b, b.get("deal")) for b in self.active(self.blocks)]
                           + [(l, l.get("deal")) for l in self.active(self.letters)]
                           + [(o, q.get("deal")) for q in self.active(self.questions) for o in self.live_options(q)
                              if o.get("changes")]):
            if deal in held:
                self.err(f"label {item.get('label')}: deal {deal} is withheld; remove the proposal or the withheld entry")

        flagged = {key for key, deal in self.deals.items() if deal.get("flags")}
        covered = block_deals | question_deals | {w.get("deal") for w in self.data.get("withheld") or []} | {l.get("deal") for l in self.active(self.letters)}
        missing = flagged - covered
        if missing:
            self.err(f"flagged deals with no clear recommendation, question, or withheld entry: {sorted(missing)}")
        if all(type(self.counts.get(key)) is int for key in ("open", "in_scope", "reviewed", "skipped", "not_checked")):
            c = self.counts
            if c["in_scope"] != c["reviewed"] + c["skipped"] + c["not_checked"]:
                self.err("counts: in_scope must equal reviewed + skipped + not_checked")
            if c["in_scope"] > c["open"] or len(flagged) > c["reviewed"]:
                self.err("counts: in_scope exceeds open or flagged exceeds reviewed")
        if mode in ("report", "notification") and isinstance(self.coverage, dict):
            if self.coverage.get("scope") != r.get("coverage_scope"):
                self.err("coverage.scope must match this run's coverage_scope")
            for source, target in (("open_count", "open"), ("in_scope", "in_scope")):
                if self.coverage.get(source) != self.counts.get(target):
                    self.err(f"coverage.{source} must match counts.{target}")

        by_label = {str(b.get("label")): b for b in self.blocks}
        by_label.update({str(l.get("label")): l for l in self.letters})
        by_label.update({str(o.get("label")): o for q in self.questions for o in q.get("options") or []})
        done = set()
        for n, w in enumerate(self.writes, 1):
            where = f"write {n}"
            lab = str(w.get("label"))
            item = by_label.get(lab)
            if item is None:
                self.err(f"{where}: label {lab} is not a clear recommendation, option, or letter")
                continue
            if item.get("status") in ("superseded", "proposed", "skipped", "deferred"):
                self.err(f"{where}: label {lab} is {item.get('status')}; only approved labels are written")
            if w.get("outcome") not in WRITE_OUTCOMES:
                self.err(f"{where}: outcome must be one of {sorted(WRITE_OUTCOMES)}")
            if w.get("outcome") in ("rejected", "unverified", "not_attempted") and not w.get("detail"):
                self.err(f"{where}: {w.get('outcome')} needs detail")
            if w.get("object") not in RECORD_OBJECTS:
                self.err(f"{where}: object must be Opportunity, Task, or Contact")
            elif not (w.get("field") == "create" and not w.get("id") and w.get("outcome") != "written"):
                self.check_id(w.get("object"), w.get("id"), where)
            if write_key(w) not in expected_keys(item):
                self.err(f"{where}: {w.get('object')} {w.get('id')} {w.get('field')} is not an approved change of {lab}")
            key = (lab, *write_key(w))
            if key in done:
                self.err(f"{where}: {w.get('object')} {w.get('id')} {w.get('field')} was already written for {lab}; never repeat a successful write")
            if w.get("outcome") == "written":
                done.add(key)
        return self.errors

    # ---- counts
    def count_values(self):
        blocks = self.active(self.blocks)
        questions = self.active(self.questions)
        k, u = self.counts["reviewed"], self.counts["not_checked"]
        f = sum(bool(d.get("flags")) for d in self.deals.values())
        return {"open": self.counts["open"], "reviewed": k, "flagged": f, "not_checked": u,
                "no_trigger": k - f, "blocks": len(blocks), "questions": len(questions),
                "letters": len(self.active(self.letters)),
                "written": record_outcomes([w for lab in self.approved_labels() for w in self.reconciled_rows(lab)]).count("written")}

    def counts_line(self):
        c = self.count_values()
        return (f"{n(c['open'], 'open deal', 'open deals')} · {self.counts['in_scope']} in scope · {c['reviewed']} reviewed · {c['flagged']} flagged · "
                f"{n(c['blocks'], 'clear recommendation', 'clear recommendations')} · "
                f"{n(c['questions'], 'question', 'questions')} · {n(c['written'], 'record fully written', 'records fully written')}")

    # ---- pieces
    def change_line(self, c):
        if c.get("action") == "create":
            f = c["fields"]
            who = self.link("Contact", f["WhoId"], c["who_name"])
            return (f"New Task · {f['Subject']} · ActivityDate {f['ActivityDate']} · Status {f['Status']} · "
                    f"Contact {who} · Opportunity {self.deal_link(f['WhatId'])}")
        if c["object"] == "Task":
            head = f"Task · {self.link('Task', c['id'], display(c.get('name')))}"
        else:
            head = "Opportunity"
        if c.get("mode") == "prepend":
            return f"{head} · {c['field']} · new first entry · {exact(c['proposed'])}"
        line = f"{head} · {c['field']} · {display(c.get('current'))} → {exact(c['proposed'])}"
        if c.get("task_kind") == "close_duplicate":
            line += f" · duplicate of {self.link('Task', c['duplicate_of'], 'Task ' + c['duplicate_of'])}"
        return line

    def evidence_line(self, e):
        parts = [str(e["date"]), e["source"]]
        if e.get("who"):
            parts.append(display(e["who"]))
        if e.get("title"):
            t = display(e["title"])
            parts.append(f"[{t}]({e['link']})" if e.get("link") else f"\"{t}\"")
        parts.append(display(e["fact"]))
        return "- " + " · ".join(parts)

    def uses_retrieved(self, evidence_lists):
        return any(e.get("source") in RETRIEVED_SOURCES for ev in evidence_lists for e in ev or [])

    def block_lines(self, b):
        ns = b["next_step"]
        out = [f"{b['label']}. {self.deal_link(b['deal'])}", "", "### Current next steps"]
        full = ns.get("proposed_full") is not None
        if full:
            out.insert(2, "Full field comparison · history change proposed.")
        out.append(display(ns.get("current_full") if full else ns.get("current")))
        out += ["", "### Recommended next steps"]
        if full:
            out.append(exact(ns["proposed_full"]))
        else:
            out.append(exact(ns["proposed"]) if ns.get("proposed") is not None else NO_NEXT_STEP_CHANGE)
        changes = b.get("changes") or []
        if changes:
            out.append("")
            out += ["- " + self.change_line(c) for c in changes]
        out += ["", "### Evidence"] + [self.evidence_line(e) for e in b["evidence"]]
        return out

    def shows_legacy(self):
        currents = [(b.get("next_step") or {}).get("current") for b in self.active(self.blocks)]
        currents += [q.get("next_step_current") for q in self.active(self.questions)]
        return any(display(c).startswith("Next:") for c in currents if c)

    def shown_coverage(self):
        """Preserve the portable coverage checker's summary and explicit gaps."""
        return [str(line) for line in self.coverage.get("lines") or []]

    def coverage_lines(self):
        lines = []
        if not self.coverage_ready():
            lines.append("Coverage incomplete · affected proposals withheld")
        lines += self.shown_coverage()
        for w in self.data.get("withheld") or []:
            lines.append(f"Withheld · {self.deal_link(w['deal'])} · {w['reason']}")
        if not self.process_complete():
            lines += [f"Run incomplete · {g}" for g in self.run.get("process_gaps") or []]
        return lines

    def report_date(self, value):
        fmt = self.policy.get("reporting", {}).get("date_format", "YYYY-MM-DD")
        for token, text in (("YYYY", str(value.year)), ("YY", value.strftime("%y")),
                            ("MM", f"{value.month:02d}"), ("DD", f"{value.day:02d}"),
                            ("M", str(value.month)), ("D", str(value.day))):
            fmt = fmt.replace(token, text)
        return fmt

    def amount(self, value):
        cfg = self.policy["reporting"]
        number = Decimal(str(value))
        if not number.is_finite():
            raise RenderError("rollup amounts must be finite")
        return f"{cfg['currency']} {number:,.{cfg['amount_decimal_places']}f}"

    def extended_lines(self):
        fr = self.extended
        roll = fr.get("rollup") or {}
        stages = " | ".join(f"{s['stage']} {s['count']} · {self.amount(s['amount'])}" for s in roll.get("stages") or [])
        fc = roll.get("forecast") or {}
        tq, later = roll.get("this_quarter") or {}, roll.get("later") or {}
        out = ["## Rollup", stages or "No open deals.",
               " · ".join(f"{category} {self.amount(value)}" for category, value in fc.items()) or "No forecast categories.",
               f"Closing this quarter {tq.get('count', 0)}, {self.amount(tq.get('amount', 0))}. "
               f"Later {later.get('count', 0)}, {self.amount(later.get('amount', 0))}.", "",
               f"## Since {fr.get('since')}"]
        delta = fr.get("delta") or []
        out += [f"- {d['kind']} · {self.deal_link(d['deal']) if d.get('deal') in self.deals else self.link('Opportunity', d.get('deal'), d.get('name') or d.get('deal'))} · {d['text']}" for d in delta] or ["No changes."]
        out += ["", "## Record proposals"]
        letters = self.active(self.letters)
        if not letters:
            out.append("No record proposals.")
        for l in letters:
            ev = " ".join(self.evidence_line(e)[2:] for e in l["evidence"])
            deal = self.link("Opportunity", l["deal"], display(l["deal_name"]))
            out.append(f"{l['label']}. {deal} · {self.change_line(l['change'])} · {l['basis']} · {ev}")
        return out

    # ---- modes
    def report(self):
        c = self.count_values()
        d = self.report_date(self.date)
        head = [self.counts_line()] + self.coverage_lines()
        blocks, questions = self.active(self.blocks), self.active(self.questions)
        if blocks or questions:
            history = ("Full fields are shown for marked history changes; other blocks show the latest entry with older history unchanged."
                       if any((b.get("next_step") or {}).get("proposed_full") is not None for b in blocks) else HISTORY_NOTE)
            head.append(history + (" " + LEGACY_NOTE if self.shows_legacy() else ""))
        out = [f"# Pipeline review · {d}", "", "  \n".join(head), "", "## Clear recommendations", ""]
        if blocks:
            for b in blocks:
                out += self.block_lines(b) + [""]
            if self.uses_retrieved([b["evidence"] for b in blocks]):
                out += [LIMITATION, ""]
        else:
            out += [EMPTY_BLOCKS, ""]
        out += ["## Needs your input", ""]
        if questions:
            out += ["  \n".join(f"{q['label']} · {self.deal_link(q['deal'])} · {display(q['context'])}" for q in questions), ""]
            if self.uses_retrieved([q["evidence"] for q in questions]):
                out += [LIMITATION, ""]
            out += [WALK_NOTE, ""]
        else:
            out += [EMPTY_QUESTIONS, ""]
        if self.run["branch"] == "extended":
            out += self.extended_lines() + [""]
        out += [f"{n(c['no_trigger'], 'reviewed deal', 'reviewed deals')} had no trigger · {self.counts['skipped']} skipped · {c['not_checked']} not checked", ""]
        if c["blocks"] or c["letters"]:
            out.append(APPROVE_EXTENDED if self.run["branch"] == "extended" and c["letters"] else APPROVE_DAILY)
        else:
            out.append(NO_CHANGES)
        return "\n".join(out).rstrip() + "\n"

    def question(self, label):
        questions = self.active(self.questions)
        q = next((x for x in questions if x.get("label") == label), None)
        if q is None:
            raise RenderError(f"question {label} is not an active question")
        if q.get("status") != "open":
            raise RenderError(f"question {label} is {q.get('status')}, not open")
        pos = questions.index(q) + 1
        out = [f"{q['label']} · {pos} of {len(questions)} · {self.deal_link(q['deal'])} · {display(q['context'])}", "",
               "### Current next steps", display(q.get("next_step_current")), "", "### Question", display(q["question"])]
        opts = [o for o in self.live_options(q) if o.get("status") == "proposed"]
        lines = []
        for o in opts:
            changes = o.get("changes") or []
            lines.append(f"- {o['label']} · {display(o['text'])}" + ("" if changes else " · no write"))
            lines += [f"  - {self.change_line(ch)}" for ch in changes]
        lines.append(f"- {SKIP_OPTION}")
        out += [""] + lines + ["", "### Evidence"] + [self.evidence_line(e) for e in q["evidence"]]
        if self.uses_retrieved([q["evidence"]]):
            out += ["", LIMITATION]
        labels = ", ".join(o["label"] for o in opts)
        reply = f"Reply {labels}, or skip." if labels else "Reply with your answer, or skip."
        out += ["", f"**{reply} Any other answer becomes a new option before anything is written.**"]
        return "\n".join(out) + "\n"

    def item_for(self, label):
        for b in self.blocks:
            if str(b.get("label")) == label:
                return b, self.deal_link(b["deal"])
        for l in self.letters:
            if str(l.get("label")) == label:
                return l, self.link("Opportunity", l.get("deal"), display(l.get("deal_name")))
        for q in self.questions:
            for o in q.get("options") or []:
                if str(o.get("label")) == label:
                    return o, self.deal_link(q["deal"])
        return None, label

    def approved_labels(self):
        items = self.active(self.blocks) + self.active(self.letters) + [o for q in self.active(self.questions) for o in self.live_options(q)]
        return [str(i["label"]) for i in items if i.get("status") in {"approved", "written", "partial", "failed"}]

    def reconciled_rows(self, label):
        item, _ = self.item_for(label)
        if item is None or label not in self.approved_labels():
            raise RenderError(f"label {label} is not approved in this review")
        # Receipts keep the latest result for each field; validation prevents a
        # second attempt after success. Failed attempts can precede a valid retry.
        rows = {}
        for write in self.writes:
            if str(write["label"]) == label:
                rows[write_key(write)] = write
        return [rows.get(key, {"label": label, "object": key[0], "id": key[1] or "",
                              "field": key[2], "outcome": "not_attempted", "detail": "no write recorded"})
                for key in expected_keys(item)]

    def receipt(self, labels, final):
        wanted = labels or self.approved_labels()
        out = ["**Receipt**", ""]
        totals = {k: 0 for k in WRITE_OUTCOMES}
        for lab in wanted:
            rows = [w for w in self.writes if str(w["label"]) == lab]
            item, where = self.item_for(lab)
            if item is None:
                raise RenderError(f"label {lab} is not in this run")
            rows = self.reconciled_rows(lab)
            records = record_outcomes(rows)
            n_ok = records.count("written")
            state = "written" if records and n_ok == len(records) else ("partial" if any(w["outcome"] == "written" for w in rows) else "not attempted" if all(w["outcome"] == "not_attempted" for w in rows) else "failed")
            out.append(f"{lab} · {where} · {state}")
            for outcome in records:
                totals[outcome] += 1
            for w in rows:
                target = self.link(w["object"], w["id"], w["object"]) if w["id"] else w["object"]
                line = f"- {OUTCOME_TEXT[w['outcome']]} · {target} · {w['field']}"
                if w.get("detail"):
                    line += f" · {display(w['detail'])}"
                out.append(line)
            if state == "partial":
                out.append(f"- {n_ok} of {len(records)} records fully written. Successful field changes are kept and not repeated.")
            out.append("")
        out.append(f"{n(totals['written'], 'record fully written', 'records fully written')} · {totals['rejected']} rejected · "
                   f"{totals['unverified']} unverified · {totals['not_attempted']} not attempted · "
                   f"{n(self.counts['open'], 'open deal', 'open deals')} at run start")
        if final:
            out += ["", "**Close**", ""] + self.close_lines()
        return "\n".join(out).rstrip() + "\n"

    def close_lines(self):
        c = self.count_values()
        skipped = [x for x in self.active(self.blocks) + self.active(self.letters) if x.get("status") == "skipped"]
        lines = [f"{n(c['open'], 'open deal', 'open deals')} · {self.counts['in_scope']} in scope · {c['reviewed']} reviewed · {c['flagged']} flagged · "
                 f"{c['blocks'] + c['letters']} proposed · {n(c['written'], 'record fully written', 'records fully written')} · "
                 f"{len(skipped)} skipped · {c['not_checked']} not checked"]
        named = []
        for b in self.active(self.blocks):
            if b.get("status") in ("skipped", "deferred", "proposed"):
                word = {"skipped": "Skipped", "deferred": "Deferred", "proposed": "Unanswered"}[b["status"]]
                named.append(f"{word} · {b['label']} · {self.deal_link(b['deal'])}")
        for l in self.active(self.letters):
            if l.get("status") in ("skipped", "deferred", "proposed"):
                word = {"skipped": "Skipped", "deferred": "Deferred", "proposed": "Unanswered"}[l["status"]]
                named.append(f"{word} · {l['label']} · {self.item_for(str(l['label']))[1]}")
        for q in self.active(self.questions):
            if q.get("status") in ("open", "skipped", "deferred"):
                word = {"open": "Unanswered", "skipped": "Skipped", "deferred": "Deferred"}[q["status"]]
                named.append(f"{word} · {q['label']} · {self.deal_link(q['deal'])}")
        return ["  \n".join(lines + named)] if named else lines

    def notification(self):
        c = self.count_values()
        d = self.report_date(self.date)
        ready = self.coverage_ready() and self.process_complete()
        url = self.run.get("thread_url", "")
        proposals = c["blocks"] + c["letters"]
        if self.run["branch"] == "daily":
            if ready and proposals == 0 and c["questions"] == 0:
                return {"send": False, "status": "clean",
                        "reason": "No clear recommendations, no questions, and coverage ready."}
            status = "action" if ready else "incomplete"
            body = self.counts_line()
            if not ready:
                body = "Incomplete · " + " ".join(self.gap_summary()) + " · " + body
            payload = {"title": TITLE_DAILY.format(d=d), "body": " · ".join(p for p in (body, url) if p), "delivery": "chat"}
        else:
            open_q = sum(1 for q in self.active(self.questions) if q.get("status") == "open")
            if ready and open_q == 0:
                status = "ready" if proposals else "complete"
            else:
                status = "incomplete"
            parts = [self.counts_line()]
            if status == "incomplete":
                gaps = self.gap_summary()
                if open_q:
                    gaps.append(f"Needs input · {n(open_q, 'open question', 'open questions')}")
                parts = gaps + parts
            payload = {"title": TITLE_EXTENDED[status], "body": " · ".join(parts + ([url] if url else [])), "delivery": "chat"}
        if self.run.get("schedule"):
            payload["schedule_description"] = self.run["schedule"]
        return {"send": True, "status": status, **payload}

    def gap_summary(self):
        gaps = []
        if not self.coverage_ready():
            gaps.append("Coverage incomplete · " + " ".join(self.shown_coverage()))
        if not self.process_complete():
            gaps += [f"Run incomplete · {g}" for g in self.run.get("process_gaps") or []]
        return gaps


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render pipeline-review output from the reviewed run file.")
    ap.add_argument("mode", choices=["report", "question", "receipt", "notification"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--coverage")
    ap.add_argument("--label")
    ap.add_argument("--labels")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--policy", default=str(DEFAULT_POLICY))
    args = ap.parse_args(argv)
    try:
        policy = yaml.safe_load(Path(args.policy).read_text())
        data = load_json(args.run)
        coverage = load_json(args.coverage) if args.coverage else None
    except (OSError, yaml.YAMLError, RenderError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.mode in ("report", "notification") and not args.coverage:
        print(f"{args.mode} needs --coverage", file=sys.stderr)
        return 2
    if args.mode == "question" and not args.label:
        print("question needs --label", file=sys.stderr)
        return 2
    try:
        run = Run(data, policy, coverage)
        errors = run.validate(args.mode)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        print(f"invalid review input: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    try:
        if args.mode == "report":
            out = run.report()
        elif args.mode == "question":
            out = run.question(args.label)
        elif args.mode == "receipt":
            labels = [x.strip() for x in args.labels.split(",")] if args.labels else None
            out = run.receipt(labels, args.final)
        else:
            out = json.dumps(run.notification(), ensure_ascii=False) + "\n"
    except (RenderError, KeyError, TypeError, ValueError, InvalidOperation) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
