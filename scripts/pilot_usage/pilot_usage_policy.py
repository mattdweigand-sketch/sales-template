"""Read portable JSON policy; copy only explicitly configured local font assets."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from decimal import Decimal, ROUND_HALF_UP


def validate_metric(metric: dict) -> None:
    for key in ("activity_label", "unit"):
        if not isinstance(metric.get(key), str) or not metric[key].strip():
            raise ValueError(f"metric.{key} must be a non-empty label")
    precision = metric.get("decimal_places")
    if type(precision) is not int or not 0 <= precision <= 6:
        raise ValueError("metric.decimal_places must be an integer from 0 to 6")
    if type(metric.get("enforce_allocation_limit")) is not bool:
        raise ValueError("metric.enforce_allocation_limit must be a boolean")


def quantity_to_units(value, metric: dict) -> int:
    """Quantize each activity to fixed-precision units before summing."""
    quantity = Decimal(str(value))
    if not quantity.is_finite() or quantity < 0:
        raise ValueError("quantity must be finite and non-negative")
    return int((quantity * (10 ** metric["decimal_places"])).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def load_pilot_usage_policy(policy_path: Path) -> dict:
    doc = json.loads(policy_path.read_text())
    pdf = doc["pilot_usage"]["pdf"]
    metric = doc["pilot_usage"]["metric"]
    validate_metric(metric)
    if pdf["week_one_length_days"] < 1:
        raise ValueError("week_one_length_days must be positive")
    if any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in pdf["category_palette"]):
        raise ValueError("category colors must be six-digit hex values")
    return {
        **{k: pdf[k] for k in ("report_title", "week_one_length_days",
            "uncategorized_category_id", "category_palette")},
        "metric": metric,
        "schema_version": 2,
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
