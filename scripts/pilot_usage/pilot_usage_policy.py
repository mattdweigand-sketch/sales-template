"""Read portable JSON policy; copy only explicitly configured local font assets."""
from pathlib import Path
import hashlib
import json
import re
import shutil


def load_pilot_usage_policy(policy_path: Path) -> dict:
    doc = json.loads(policy_path.read_text())
    pdf = doc["pilot_usage"]["pdf"]
    if pdf["week_one_length_days"] < 1:
        raise ValueError("week_one_length_days must be positive")
    if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in pdf["category_palette"]):
        raise ValueError("category colors must be six-digit hex values")
    return {
        **{k: pdf[k] for k in ("report_title", "week_one_length_days", "task_grain",
            "credit_unit", "credit_display_rule", "uncategorized_category_id", "category_palette")},
        "schema_version": 1,
        "internal_domains": doc["identity"]["internal_domains"],
        "report_page_count": pdf["page_count"], "report_page_size": pdf["page_size"],
        "pdf": {
            **{k: pdf[k] for k in ("page_width_points", "page_height_points", "metadata_title",
                "metadata_author", "chromium_timeout_seconds")},
            "required": True, "font_assets": pdf.get("fonts", {}),
        },
    }


def verify_font_bytes(font_path: Path, expected_sha256: str, role: str) -> None:
    if not font_path.is_file():
        raise RuntimeError(f"required {role} font is unavailable: {font_path}")
    data = font_path.read_bytes()
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(f"{role} font is an unhydrated Git LFS pointer")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise RuntimeError(f"required {role} font failed integrity verification")


def ensure_font_assets(policy: dict, font_directory: Path) -> Path:
    fonts = policy["pdf"]["font_assets"]
    for role, font in fonts.items():
        if role not in ("sans", "mono") or Path(font["file_name"]).name != font["file_name"]:
            raise ValueError("invalid font role or file_name")
        source = Path(font["local_path"]).expanduser()
        verify_font_bytes(source, font["sha256"], role)
        font_directory.mkdir(parents=True, exist_ok=True)
        target = font_directory / font["file_name"]
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        verify_font_bytes(target, font["sha256"], role)
    return font_directory
