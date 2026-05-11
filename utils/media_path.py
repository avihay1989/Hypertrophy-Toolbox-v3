"""Path-shape validation for `exercises.media_path` values.

`media_path` stores a relative path under
`static/vendor/free-exercise-db/exercises/` (e.g. `Squat_Barbell/0.jpg`).
Because the value interpolates into a frontend URL, every value is treated
as untrusted until proven safe by these rules. The same rules are applied
on write (apply script) and read (`resolveExerciseMediaSrc()` in JS, which
mirrors `is_valid_media_path_shape` exactly).

Rules (per docs/workout_cool_integration/PLANNING.md §4.3):

  - Non-empty.
  - No leading `/` or `\\` (must be a relative path).
  - No backslashes anywhere (forward slashes only).
  - No `:` anywhere (blocks Windows drive prefixes like `C:/...` or `C:foo`).
  - No `..` or `.` segments anywhere (blocks parent-dir escape and no-op
    cwd refs that would normalise away).
  - No empty segments (e.g. `dir//file.jpg`).
  - Extension matches `^\\.(jpg|jpeg|png|gif|webp)$` (case-insensitive).

`media_path_resolves()` additionally checks the file exists under the
vendor base directory; this is a write-time check only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

ALLOWED_EXTENSIONS: tuple[str, ...] = ("jpg", "jpeg", "png", "gif", "webp")
EXTENSION_RE = re.compile(
    r"^\.(?:" + "|".join(ALLOWED_EXTENSIONS) + r")$",
    re.IGNORECASE,
)
VENDOR_BASE_REL = Path("static") / "vendor" / "free-exercise-db" / "exercises"


def is_valid_media_path_shape(value: object) -> bool:
    """Return True iff `value` satisfies the path-shape rules.

    Pure function — does not touch the filesystem. Mirrored verbatim by
    the JS `resolveExerciseMediaSrc()` helper in checkpoint 5.
    """
    if not isinstance(value, str):
        return False
    if value == "":
        return False
    if value.startswith("/") or value.startswith("\\"):
        return False
    if "\\" in value:
        return False
    if ":" in value:
        return False
    parts = value.split("/")
    if any(part in ("..", ".") for part in parts):
        return False
    if any(part == "" for part in parts):
        return False
    suffix = Path(value).suffix
    if not EXTENSION_RE.match(suffix):
        return False
    return True


def explain_media_path_shape_failure(value: object) -> str | None:
    """Return a short reason why `value` fails shape validation, else None.

    Used by the apply script to emit per-row error messages that point at
    the precise rule that was violated.
    """
    if not isinstance(value, str):
        return f"must be a string (got {type(value).__name__})"
    if value == "":
        return "must be non-empty"
    if value.startswith("/") or value.startswith("\\"):
        return "must be relative (no leading slash or backslash)"
    if "\\" in value:
        return "must not contain backslashes (forward slashes only)"
    if ":" in value:
        return "must not contain `:` (blocks Windows drive prefixes)"
    parts = value.split("/")
    if any(part == ".." for part in parts):
        return "must not contain `..` segments"
    if any(part == "." for part in parts):
        return "must not contain `.` segments (no-op cwd refs)"
    if any(part == "" for part in parts):
        return "must not contain empty segments (e.g. `dir//file.jpg`)"
    suffix = Path(value).suffix
    if not EXTENSION_RE.match(suffix):
        return (
            f"extension {suffix!r} not in allowlist "
            f"({', '.join('.' + e for e in ALLOWED_EXTENSIONS)})"
        )
    return None


def media_path_resolves(
    value: str,
    vendor_base: Path | str | None = None,
) -> bool:
    """Return True iff `value` resolves to an existing file under `vendor_base`.

    Defaults to the repo-relative vendor base directory. The candidate is
    re-rooted under the resolved base and required to remain inside it
    (defense-in-depth against shape-validator bugs).
    """
    if not is_valid_media_path_shape(value):
        return False

    if vendor_base is None:
        # Resolve relative to repo root: this module lives at utils/media_path.py
        repo_root = Path(__file__).resolve().parent.parent
        base = repo_root / VENDOR_BASE_REL
    else:
        base = Path(vendor_base)

    try:
        base_resolved = base.resolve()
    except OSError:
        return False

    candidate = (base / value).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError:
        return False
    return candidate.is_file()


__all__: Iterable[str] = (
    "ALLOWED_EXTENSIONS",
    "EXTENSION_RE",
    "VENDOR_BASE_REL",
    "is_valid_media_path_shape",
    "explain_media_path_shape_failure",
    "media_path_resolves",
)
