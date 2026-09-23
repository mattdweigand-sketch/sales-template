"""Keep generated customer artifacts in a private run or outside the repository."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def require_local_only_output_path(path: Path) -> Path:
    path = Path(path).absolute()
    if path.is_symlink() or (path.is_relative_to(ROOT) and any(
        parent.is_symlink() for parent in path.parents if parent.is_relative_to(ROOT)
    )):
        raise ValueError("output path must not contain symlinks")
    resolved = path.resolve()
    if resolved.is_relative_to(ROOT):
        rel = resolved.relative_to(ROOT)
        if len(rel.parts) < 3 or rel.parts[0] != "output":
            raise ValueError("repository outputs must be under output/{run-id}/")
    return resolved
