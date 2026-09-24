#!/usr/bin/env python3
"""Render validated two-page HTML with verified relative custom font assets.

Usage:
    python render_pilot_usage_report.py --input input.json --policy _shared/policy.json --report report.json --output /tmp/pilot-usage/report.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path
from typing import cast

from compute_pilot_usage_report import (
    PilotUsageInput,
    PilotUsagePolicy,
    PilotUsageReport,
    PilotUsageUserRow,
)
from pilot_usage_local_storage import require_local_only_output_path
from pilot_usage_policy import ensure_font_assets, load_pilot_usage_policy
from validate_pilot_usage_report import validate_computed_pilot_usage_report

FONT_OUTPUT_DIRECTORY = Path("assets") / "fonts"
# Page 1 is a fixed Letter page with overflow hidden. Roughly 24 table rows fit beside the
# highlights column, so the table names this many users by credits and folds the rest into one row.
USER_TABLE_MAX_ROWS = 20


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _format_date(value: str, include_year: bool = True) -> str:
    parsed = date.fromisoformat(value)
    rendered = f"{parsed.strftime('%b')} {parsed.day}"
    return f"{rendered}, {parsed.year}" if include_year else rendered


def _format_date_range(start: str, end: str, include_year: bool = True) -> str:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if start_date.year == end_date.year and start_date.month == end_date.month:
        suffix = f", {end_date.year}" if include_year else ""
        return f"{start_date.strftime('%b')} {start_date.day}–{end_date.day}{suffix}"
    if start_date.year == end_date.year:
        suffix = f", {end_date.year}" if include_year else ""
        return f"{start_date.strftime('%b')} {start_date.day} – {end_date.strftime('%b')} {end_date.day}{suffix}"
    return f"{_format_date(start, include_year)} – {_format_date(end, include_year)}"


def _format_number(value: int) -> str:
    return f"{value:,}"


def _render_user_rows(users: list[PilotUsageUserRow]) -> str:
    rows: list[str] = []
    for user in users[:USER_TABLE_MAX_ROWS]:
        marker = "*" if user["undated_tasks"] else ""
        muted = " muted" if user["task_count"] == 0 else ""
        rows.append(
            '<tr class="user-row{muted}"><td>{name}</td><td>{tasks}</td>'
            "<td>{week_one}{marker}</td><td>{week_two}</td><td>{credits}</td></tr>".format(
                muted=muted,
                name=_escape(user["display_name"]),
                tasks=user["task_count"],
                week_one=user["week_one_tasks"],
                marker=marker,
                week_two=user["week_two_tasks"],
                credits=_format_number(user["credits"]),
            )
        )
    folded = users[USER_TABLE_MAX_ROWS:]
    if folded:
        idle = sum(1 for user in folded if user["task_count"] == 0)
        idle_note = f", {idle} with no tasks" if idle else ""
        marker = "*" if any(user["undated_tasks"] for user in folded) else ""
        rows.append(
            '<tr class="user-row"><td>{name}</td><td>{tasks}</td>'
            "<td>{week_one}{marker}</td><td>{week_two}</td><td>{credits}</td></tr>".format(
                name=_escape(f"Other ({_plural(len(folded), 'seat', 'seats')}{idle_note})"),
                tasks=sum(user["task_count"] for user in folded),
                week_one=sum(user["week_one_tasks"] for user in folded),
                marker=marker,
                week_two=sum(user["week_two_tasks"] for user in folded),
                credits=_format_number(sum(user["credits"] for user in folded)),
            )
        )
    return "".join(rows)


def _day_label(day: date, first: bool) -> str:
    """Day number, with the month named on the first bar and on each first of month."""
    if first or day.day == 1:
        return f"{day.day}<br>{day.strftime('%b')}"
    return str(day.day)


def _render_daily_bars(computed_report: PilotUsageReport) -> str:
    daily_tasks = computed_report["daily_tasks"]
    maximum = max((row["task_count"] for row in daily_tasks), default=1)
    chart_rows: list[str] = []
    # Short pilots (up to 16 days) sit beside the table. Longer ones take one
    # full-width row so the page keeps its two-column balance.
    wide = len(daily_tasks) > 16
    chunk = len(daily_tasks) if wide else 16
    bar_scale = 76 if wide else 58
    for start in range(0, len(daily_tasks), chunk):
        bars: list[str] = []
        for row in daily_tasks[start : start + chunk]:
            height = (
                max(4, round(row["task_count"] / maximum * bar_scale))
                if row["task_count"]
                else 2
            )
            color_class = " peak" if row["task_count"] == maximum else ""
            bars.append(
                '<div class="day"><span class="bar-value">{value}</span>'
                '<div class="bar{color}" style="height:{height}px"></div>'
                '<span class="day-label">{day}</span></div>'.format(
                    value=row["task_count"],
                    color=color_class,
                    height=height,
                    day=_day_label(date.fromisoformat(row["date"]), start == 0 and row is daily_tasks[0]),
                )
            )
        chart_rows.append(f'<div class="chart-row">{"".join(bars)}</div>')
    return "".join(chart_rows)


def _render_labeled_bullets(items: list[dict[str, str]]) -> str:
    return "".join(
        f"<li><strong>{_escape(item['label'])}.</strong> {_escape(item['text'])}</li>"
        for item in items
    )


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _font_css(policy: PilotUsagePolicy) -> str:
    rules = []
    for role, asset in policy["pdf"]["font_assets"].items():
        name = asset["file_name"]
        if role not in ("sans", "mono") or Path(name).name != name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("invalid font asset name")
        family = "Report Sans" if role == "sans" else "Report Mono"
        url = (FONT_OUTPUT_DIRECTORY / name).as_posix()
        rules.append(f'@font-face{{font-family:"{family}";src:url("{url}");font-style:normal;font-weight:100 900}}')
    return "\n".join(rules)


def _copy_verified_font_assets(
    policy: PilotUsagePolicy, output_directory: Path
) -> None:
    ensure_font_assets(policy, output_directory / FONT_OUTPUT_DIRECTORY)


def _render_pilot_usage_report_html(
    computed_report: PilotUsageReport, policy: PilotUsagePolicy
) -> str:
    report = computed_report["report"]
    report_title = computed_report["report_title"]
    headline = computed_report["headline"]
    periods = computed_report["periods"]
    narratives = computed_report["reviewed_narratives"]
    highlights = computed_report["computed_highlights"]
    users_by_id = {user["user_id"]: user for user in computed_report["users"]}
    most_consistent = (
        users_by_id.get(highlights["most_consistent_user_id"] or "")
        if highlights["most_consistent_user_id"]
        else None
    )

    computed_bullets = [
        {
            "label": "Engagement is concentrated",
            "text": (
                f"The top {highlights['top_user_count']} users account for "
                f"~{highlights['top_user_credit_share_percent']}% of consumption"
            ),
        }
    ]
    if most_consistent:
        computed_bullets.append(
            {
                "label": "Most consistent user",
                "text": (
                    f"{most_consistent['display_name']}, active "
                    f"{most_consistent['active_days']} of {headline['elapsed_days']} days "
                    f"({most_consistent['task_count']} tasks)"
                ),
            }
        )
    computed_bullets.extend(narratives["usage_highlights"])
    inactive_users = highlights["inactive_user_count"]
    day_one_only_users = highlights["day_one_only_user_count"]
    if inactive_users and day_one_only_users:
        reengagement_text = (
            f"{_plural(inactive_users, 'user has', 'users have')} no recorded task; "
            f"{_plural(day_one_only_users, 'other has', 'others have')} not returned since Day 1"
        )
    elif inactive_users:
        reengagement_text = f"{_plural(inactive_users, 'user has', 'users have')} no recorded task"
    elif day_one_only_users:
        reengagement_text = (
            f"{_plural(day_one_only_users, 'user has', 'users have')} not returned since Day 1 onboarding"
        )
    else:
        reengagement_text = "no users are inactive or limited to Day 1"
    computed_bullets.append(
        {"label": "Re-engagement opportunity", "text": reengagement_text}
    )
    computed_bullets.append(
        {
            "label": "Credit runway",
            "text": (
                f"{_format_number(headline['remaining_credits'])} of "
                f"{_format_number(headline['granted_credits'])} granted credits remain available"
            ),
        }
    )

    undated_note = ""
    if highlights["undated_task_count"]:
        undated_note = (
            f" *{highlights['undated_task_count']} reviewed undated tasks count toward totals, "
            "not the weekly split."
        )
    participation_notes = " ".join(
        _escape(user["participation_note"])
        for user in computed_report["users"]
        if user["participation_note"]
    )
    daily_note = ""
    if highlights["undated_task_count"]:
        daily_note = (
            f" {highlights['undated_task_count']} tasks without timestamps "
            f"({_format_number(highlights['undated_credits'])} credits) are not charted."
        )

    category_segments = "".join(
        '<span style="background:{color};width:{width}%"></span>'.format(
            color=_escape(category["color"]),
            width=category["share_percent_precise"],
        )
        for category in computed_report["categories"]
        if category["category_id"] != "uncategorized"
        if category["credits"] > 0
    )
    category_rows = "".join(
        '<div class="category-row"><span class="swatch" style="background:{color}"></span>'
        "<strong>{label}</strong><span>{tasks} tasks</span><span>{credits} cr</span>"
        "<b>{share}%</b><em>{description}</em></div>".format(
            color=_escape(category["color"]),
            label=_escape(category["label"]),
            tasks=category["task_count"],
            credits=_format_number(category["credits"]),
            share=category["share_percent"],
            description=_escape(category["description"]),
        )
        for category in computed_report["categories"]
    )
    uncategorized = next(
        (
            category
            for category in computed_report["categories"]
            if category["category_id"] == "uncategorized"
        ),
        None,
    )
    uncategorized_note = ""
    if uncategorized and uncategorized["task_count"]:
        uncategorized_note = (
            f"{uncategorized['task_count']} untitled or insufficient-evidence tasks "
            f"({_format_number(uncategorized['credits'])} credits, "
            f"{uncategorized['share_percent_precise']}%) remain uncategorized. "
        )

    representative_cards = "".join(
        '<article class="work-card"><h3>{title}</h3><span>{people}</span><p>{summary}</p></article>'.format(
            title=_escape(card["title"]),
            people=_escape(
                ", ".join(
                    users_by_id[user_id]["display_name"] for user_id in card["user_ids"]
                )
            ),
            summary=_escape(card["summary"]),
        )
        for card in narratives["representative_work"]
    )
    work_interpretation = "".join(
        f"<p>{_escape(paragraph)}</p>"
        for paragraph in narratives["work_interpretation"]
    )

    pilot_window = _format_date_range(report["pilot_start"], report["pilot_end"])
    through_range = _format_date_range(report["pilot_start"], report["data_through"])
    week_one_range = _format_date_range(
        periods["week_one_start"], periods["week_one_end"], include_year=False
    )
    week_two_range = _format_date_range(
        periods["week_two_start"], periods["week_two_end"], include_year=False
    )
    chart_block = (
        f'<h2>Tasks started per day</h2><div class="chart">{_render_daily_bars(computed_report)}</div>'
        f'<p class="fineprint">{through_range}. Daily chart excludes reviewed undated tasks.{_escape(daily_note)}</p>'
    )
    highlights_block = f'<div class="highlights"><h2>Usage highlights</h2><ul>{_render_labeled_bullets(computed_bullets)}</ul></div>'
    if len(computed_report["daily_tasks"]) <= 16:
        side_column = f"<div>{chart_block}{highlights_block}</div>"
        full_width_chart = ""
    else:
        side_column = f"<div>{highlights_block}</div>"
        full_width_chart = f'<div class="chart-wide">{chart_block}</div>'
    user_table_note = (
        f" Top {USER_TABLE_MAX_ROWS} users shown; the rest are combined in the Other row."
        if len(computed_report["users"]) > USER_TABLE_MAX_ROWS
        else ""
    )
    footer = (
        f"Prepared by {_escape(report['prepared_by'])} &nbsp;·&nbsp; "
        f"{_escape(report['confidentiality_label'])}. For "
        f"{_escape(report['customer_name'])} internal use."
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_escape(policy["pdf"]["metadata_title"])}</title>
<meta name="author" content="{_escape(policy["pdf"]["metadata_author"])}">
<style>
{_font_css(policy)}
:root{{--paper:#f7f7f4;--ink:#272621;--muted:#777770;--line:#d9d6cf;--teal:#00717a;--soft:#e8f0ef}}
*{{box-sizing:border-box}} html,body{{margin:0;background:#ecebe7;color:var(--ink);font-family:"Report Sans",Arial,sans-serif}}
body{{font-size:11px;line-height:1.28}} .report-page{{position:relative;width:8.5in;height:11in;margin:18px auto;padding:.48in .5in .42in;background:var(--paper);overflow:hidden;page-break-after:always}}
.report-page:last-child{{page-break-after:auto}} .eyebrow{{font-size:11px;font-weight:800;letter-spacing:.01em;color:var(--teal)}}
h1{{font-size:29px;line-height:1.05;margin:5px 0 13px;letter-spacing:.01em}} h2{{font-size:15px;margin:0 0 8px}} h3{{margin:0;color:var(--teal);font-size:12px}}
.header{{border-bottom:1px solid var(--line);position:relative}} .header-meta{{position:absolute;right:0;top:-3px;text-align:right;color:var(--muted);font-family:"Report Mono",monospace;font-size:12px;line-height:1.45}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:15px 0}} .metric{{border:1px solid var(--line);border-radius:8px;padding:12px 13px;height:90px;background:#fbfbf9}}
.metric b{{display:block;color:var(--teal);font-size:25px;line-height:1}} .metric strong{{display:block;margin-top:7px;font-size:11px}} .metric span{{display:block;color:var(--muted);margin-top:5px;font-size:9px}}
.scope-note{{border-left:4px solid var(--teal);padding:10px 13px;background:var(--soft);border-radius:0 7px 7px 0;margin:0 0 20px}} .scope-note strong{{display:block;margin-bottom:4px}}
.page-one-grid{{display:grid;grid-template-columns:minmax(0, 58fr) minmax(0, 42fr);gap:28px}} .section-title-note{{font-size:9px;color:var(--muted);font-weight:400;margin-left:8px}}
table{{border-collapse:collapse;width:100%;font-size:10px}} th{{background:#ebeae6;color:var(--muted);text-align:right;padding:4px 7px;font-size:9px}} th:first-child,td:first-child{{text-align:left}} td{{padding:3px 7px;text-align:right}} tr:nth-child(even){{background:#fbfbf9}} .user-row td:first-child{{font-weight:600}} .user-row.muted{{color:var(--muted)}} tfoot{{border-top:1px solid var(--line);font-weight:800}}
    .fineprint{{font-size:9px;color:var(--muted);margin-top:7px}} .chart{{display:flex;flex-direction:column;gap:7px;margin:12px 5px 4px}} .chart-row{{height:76px;display:flex;align-items:flex-end;gap:3px}} .day{{height:76px;min-width:0;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}} .bar-value{{font-size:7px;margin-bottom:2px}} .bar{{width:100%;max-width:13px;background:#79b5b9}} .bar.peak{{background:#218a91}} .day-label{{font-size:7px;color:var(--muted);margin-top:3px;white-space:nowrap}} .chart-wide{{margin-top:14px}} .chart-wide .chart{{margin:12px 0 4px}} .chart-wide .chart-row,.chart-wide .day{{height:110px}} .chart-wide .bar{{max-width:11px}} .chart-wide .day-label{{height:16px;line-height:8px;text-align:center}}
ul{{padding-left:17px;margin:4px 0}} li{{margin:0 0 7px}} li::marker{{color:var(--teal)}} .highlights{{margin-top:21px;font-size:10px}}
.footer{{position:absolute;bottom:.28in;left:.5in;right:.5in;border-top:1px solid var(--line);padding-top:7px;color:var(--muted);font-size:9px}}
.page-two h1{{font-size:27px;margin-bottom:15px}} .work-distribution{{margin-top:22px}} .stacked{{height:18px;display:flex;margin:10px 0 14px;overflow:hidden}} .stacked span{{display:block;height:100%}}
.category-row{{display:grid;grid-template-columns:14px 2.7fr .9fr 1fr .55fr 3fr;gap:8px;align-items:center;margin:0 0 12px}} .swatch{{width:11px;height:11px}} .category-row span:nth-of-type(n+2){{text-align:right}} .category-row b{{color:var(--teal);text-align:right}} .category-row em{{font-style:normal;color:var(--muted);font-size:9px}}
.work-grid{{display:grid;grid-template-columns:1fr 1fr;gap:13px 16px}} .work-card{{border:1px solid var(--line);border-radius:8px;background:#fbfbf9;padding:11px 13px;min-height:99px}} .work-card span{{display:block;color:var(--muted);font-size:9px;margin:3px 0 5px}} .work-card p{{margin:0}}
.bottom-grid{{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:20px}} .bottom-grid p{{margin:0 0 11px}}
@page{{size:Letter;margin:0}} @media print{{html,body{{background:white}}.report-page{{margin:0}}}}
</style>
</head>
<body>
<section class="report-page page-one">
  <header class="header"><div class="eyebrow">{_escape(report_title)}</div><h1>{_escape(report["customer_name"])}</h1>
    <div class="header-meta">Prepared {_format_date(report["prepared_date"])}<br>Pilot window: {pilot_window}<br>Data through {_format_date(report["data_through"])} (Day {periods["pilot_day_number"]} of {periods["pilot_total_days"]})</div></header>
  <div class="cards">
    <div class="metric"><b>{headline["active_users"]} of {headline["seat_count"]}</b><strong>users active</strong><span>seats with task activity</span></div>
    <div class="metric"><b>{headline["task_count"]}</b><strong>tasks</strong><span>tasks started to date</span></div>
    <div class="metric"><b>{_format_number(headline["credits_used"])}</b><strong>credits used</strong><span>across reviewed workspace scope</span></div>
    <div class="metric"><b>{headline["active_days"]} of {headline["elapsed_days"]}</b><strong>days with activity</strong><span>dated task activity</span></div>
  </div>
  <div class="scope-note"><strong>Scope.</strong> {_escape(narratives["scope_note"])}</div>
  <div class="page-one-grid"><div><h2>Usage by user <span class="section-title-note">(sorted by credits consumed)</span></h2>
    <table><thead><tr><th>USER</th><th>TASKS</th><th>WK 1</th><th>AFTER</th><th>CREDITS</th></tr></thead><tbody>{_render_user_rows(computed_report["users"])}</tbody>
    <tfoot><tr><td>Total ({headline["seat_count"]} seats)</td><td>{headline["task_count"]}</td><td></td><td></td><td>{_format_number(headline["credits_used"])}</td></tr></tfoot></table>
    <p class="fineprint">Wk 1 = {week_one_range}, After = {week_two_range}.{_escape(undated_note)}{user_table_note}<br>{participation_notes}</p></div>
    {side_column}</div>{full_width_chart}
  <footer class="footer">Scope: Task usage and credit consumption across all {headline["seat_count"]} seats, reviewed workspaces, {through_range}.<br>{footer} &nbsp;·&nbsp; Page 1 of 2</footer>
</section>
<section class="report-page page-two">
  <header class="header"><div class="eyebrow">{_escape(report_title)}</div><h1>What the team is doing</h1><div class="header-meta">{through_range}</div></header>
  <section class="work-distribution"><h2>Where the work went <span class="section-title-note">(all {headline["task_count"]} tasks, by share of credits consumed)</span></h2>
    <div class="stacked">{category_segments}</div>{category_rows}<p class="fineprint">{_escape(uncategorized_note)}Shares are of the {_format_number(headline["credits_used"])} credits consumed to date.</p></section>
  <section><h2 style="margin-top:21px">Representative work</h2><div class="work-grid">{representative_cards}</div></section>
  <div class="bottom-grid"><section><h2>What the pattern shows</h2>{work_interpretation}</section><section><h2>Business value delivered</h2><ul>{_render_labeled_bullets(narratives["business_value"])}</ul></section></div>
  <footer class="footer">{_escape(narratives["source_note"])}<br>{footer} &nbsp;·&nbsp; Page 2 of 2</footer>
</section>
</body>
</html>
"""


def render_validated_pilot_usage_report_html(
    normalized_input: PilotUsageInput,
    policy: PilotUsagePolicy,
    computed_report: PilotUsageReport,
) -> str:
    """Validate all deterministic fields, then return escaped two-page HTML."""
    problems = validate_computed_pilot_usage_report(
        normalized_input, policy, computed_report
    )
    if problems:
        raise ValueError("report validation failed: " + ", ".join(problems))
    return _render_pilot_usage_report_html(computed_report, policy)


def write_validated_pilot_usage_report_html(
    normalized_input: PilotUsageInput,
    policy: PilotUsagePolicy,
    computed_report: PilotUsageReport,
    output_path: Path,
) -> None:
    """Write validated HTML and its integrity-checked relative font assets."""
    output_path = require_local_only_output_path(output_path)
    rendered_html = render_validated_pilot_usage_report_html(
        normalized_input, policy, computed_report
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _copy_verified_font_assets(policy, output_path.parent)
    output_path.write_text(rendered_html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render validated pilot usage HTML with relative custom font assets."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    normalized_input = cast(
        PilotUsageInput, json.loads(args.input.read_text(encoding="utf-8"))
    )
    policy = cast(PilotUsagePolicy, load_pilot_usage_policy(args.policy))
    computed_report = cast(
        PilotUsageReport, json.loads(args.report.read_text(encoding="utf-8"))
    )
    write_validated_pilot_usage_report_html(
        normalized_input, policy, computed_report, args.output
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
