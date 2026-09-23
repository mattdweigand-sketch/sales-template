#!/usr/bin/env python3
"""Print and verify the required two-page Letter pilot usage PDF.

Usage:
    python print_pilot_usage_pdf.py --html /tmp/pilot-usage/report.html --policy _shared/policy.json --output /tmp/pilot-usage/<customer>-pilot-usage.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from pypdf import PdfReader, PdfWriter

from compute_pilot_usage_report import PilotUsagePolicy
from pilot_usage_local_storage import require_local_only_output_path
from pilot_usage_policy import load_pilot_usage_policy, verify_font_bytes


@dataclass(frozen=True)
class PilotUsagePdfInspection:
    page_count: int
    media_boxes: tuple[tuple[float, float], ...]
    title: str
    author: str
    embedded_font_tokens: tuple[str, ...]


def inspect_pilot_usage_pdf(
    pdf_path: Path, font_tokens: tuple[str, ...]
) -> PilotUsagePdfInspection:
    """Read page, metadata, and embedded-font invariants with a PDF parser."""
    reader = PdfReader(pdf_path)
    font_names: set[str] = set()
    media_boxes: list[tuple[float, float]] = []
    for page in reader.pages:
        media_boxes.append((float(page.mediabox.width), float(page.mediabox.height)))
        font_resources = page.get("/Resources", {}).get("/Font", {})
        for font_reference in font_resources.values():
            font_object = font_reference.get_object()
            font_names.add(str(font_object.get("/BaseFont", "")))
            # Chromium embeds variable WOFF2 fonts as Type3 with the family on the descriptor only.
            descriptor = font_object.get("/FontDescriptor")
            if descriptor is not None:
                descriptor = descriptor.get_object()
                font_names.add(str(descriptor.get("/FontFamily", "")))
                font_names.add(str(descriptor.get("/FontName", "")))
    def normalized_font_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower()).replace("beta", "")

    embedded_tokens = tuple(
        token
        for token in font_tokens
        if any(
            normalized_font_name(token) in normalized_font_name(name)
            for name in font_names
        )
    )
    metadata = reader.metadata or {}
    return PilotUsagePdfInspection(
        page_count=len(reader.pages),
        media_boxes=tuple(media_boxes),
        title=str(metadata.get("/Title", "")),
        author=str(metadata.get("/Author", "")),
        embedded_font_tokens=embedded_tokens,
    )


def _validate_font_assets(policy: PilotUsagePolicy, font_directory: Path) -> None:
    for role, expected in policy["pdf"]["font_assets"].items():
        verify_font_bytes(font_directory / expected["file_name"], expected["sha256"], role)


def _write_pdf_metadata(
    source_path: Path, output_path: Path, title: str, author: str
) -> None:
    reader = PdfReader(source_path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_metadata({"/Title": title, "/Author": author, "/Creator": author})
    with output_path.open("wb") as output_file:
        writer.write(output_file)


def _pdf_render_command(
    renderer_binary: str,
    html_path: Path,
    pdf_path: Path,
) -> list[str]:
    if renderer_binary != "auto":
        resolved = shutil.which(renderer_binary)
        if resolved is None:
            raise RuntimeError(
                f"Chromium PDF tooling is unavailable: {renderer_binary}"
            )
        return _chromium_command(resolved, html_path, pdf_path)

    for candidate in ("chromium", "google-chrome", "chromium-browser"):
        resolved = shutil.which(candidate)
        if resolved is not None:
            return _chromium_command(resolved, html_path, pdf_path)
    for playwright_chrome in sorted(
        Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux*/chrome")
    ):
        if playwright_chrome.is_file():
            return _chromium_command(str(playwright_chrome), html_path, pdf_path)

    raise RuntimeError("Chromium PDF tooling is unavailable; install it or pass --renderer /path/to/chromium")


def _chromium_command(
    chromium_path: str,
    html_path: Path,
    pdf_path: Path,
) -> list[str]:
    return [
        chromium_path,
        "--headless",
        f"--user-data-dir={pdf_path.parent / 'browser-profile'}",
        "--disable-background-networking",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=1000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]


def _validate_inspection(
    inspection: PilotUsagePdfInspection, policy: PilotUsagePolicy
) -> None:
    pdf_policy = policy["pdf"]
    problems: list[str] = []
    if not pdf_policy["required"]:
        problems.append("policy must require PDF delivery")
    if inspection.page_count != policy["report_page_count"]:
        problems.append(
            f"expected {policy['report_page_count']} pages, got {inspection.page_count}"
        )
    expected_box = (
        float(pdf_policy["page_width_points"]),
        float(pdf_policy["page_height_points"]),
    )
    if len(inspection.media_boxes) != inspection.page_count:
        problems.append("each PDF page must declare a media box")
    if any(box != expected_box for box in inspection.media_boxes):
        problems.append("every PDF page must be US Letter (612 × 792 points)")
    if inspection.title != pdf_policy["metadata_title"]:
        problems.append("PDF title metadata is incorrect")
    if inspection.author != pdf_policy["metadata_author"]:
        problems.append("PDF author metadata is incorrect")
    expected_tokens = tuple(
        font["pdf_name_token"] for font in pdf_policy["font_assets"].values()
    )
    if set(inspection.embedded_font_tokens) != set(expected_tokens):
        problems.append("official Report Sans and Mono fonts are not both embedded")
    if problems:
        raise RuntimeError("; ".join(problems))


def print_pilot_usage_pdf(
    html_path: Path,
    output_path: Path,
    policy: PilotUsagePolicy,
    chromium_binary: str = "auto",
    font_directory: Path | None = None,
) -> PilotUsagePdfInspection:
    """Print HTML, set metadata, verify two Letter pages and embedded fonts."""
    output_path = require_local_only_output_path(output_path)
    if not html_path.is_file():
        raise RuntimeError(f"validated HTML is unavailable: {html_path}")
    resolved_font_directory = font_directory or (html_path.parent / "assets" / "fonts")
    _validate_font_assets(policy, resolved_font_directory)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="pilot-usage-pdf-", dir=output_path.parent
    ) as temporary_directory:
        chromium_pdf = Path(temporary_directory) / "chromium.pdf"
        candidate_pdf = Path(temporary_directory) / "verified.pdf"
        command = _pdf_render_command(chromium_binary, html_path, chromium_pdf)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=policy["pdf"]["chromium_timeout_seconds"],
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("PDF generation timed out") from exc
        if completed.returncode != 0 or not chromium_pdf.is_file():
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"PDF generation failed: {detail}")
        _write_pdf_metadata(
            chromium_pdf,
            candidate_pdf,
            policy["pdf"]["metadata_title"],
            policy["pdf"]["metadata_author"],
        )

        font_tokens = tuple(
            font["pdf_name_token"] for font in policy["pdf"]["font_assets"].values()
        )
        inspection = inspect_pilot_usage_pdf(candidate_pdf, font_tokens)
        _validate_inspection(inspection, policy)
        candidate_pdf.replace(output_path)
    return inspection


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print verified two-page Letter pilot usage PDF from validated HTML."
    )
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--renderer",
        default="auto",
        help="installed Chromium-compatible binary; no automatic dependency downloads",
    )
    args = parser.parse_args()
    policy = cast(PilotUsagePolicy, load_pilot_usage_policy(args.policy))
    inspection = print_pilot_usage_pdf(
        args.html, args.output, policy, chromium_binary=args.renderer
    )
    print(
        json.dumps(
            {
                "valid": True,
                "page_count": inspection.page_count,
                "page_size": policy["report_page_size"],
                "title": inspection.title,
                "author": inspection.author,
                "embedded_font_tokens": inspection.embedded_font_tokens,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
