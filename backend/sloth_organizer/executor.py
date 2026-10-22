"""
Safe file executor.

Responsibilities:
- Resolve the destination path for a plan item (always inside the scan root)
- Prevent silent overwrites by appending (2), (3), … to the filename
- Validate every item against the 10-step safety model before touching the FS
- Execute (or simulate) a single move/rename, returning a result dict
"""

import re
import shutil
from pathlib import Path
from typing import Any

from sloth_organizer.models import PlanItem


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def resolve_destination(
    root: Path,
    destination_folder: str,
    new_name: str | None,
    original_name: str,
) -> Path:
    """
    Build the absolute target path for a file.

    - Strips path separators from destination_folder so it stays one level deep.
    - Uses new_name if provided, otherwise keeps original_name.
    - The returned path is NOT yet checked for existence; call prevent_overwrite next.
    """
    # Sanitize folder name — no separators, no traversal
    safe_folder = re.sub(r"[/\\]", "", destination_folder).strip()
    if not safe_folder:
        safe_folder = "Review"

    # Choose filename
    filename = new_name.strip() if new_name else original_name

    return root / safe_folder / filename


def prevent_overwrite(path: Path) -> Path:
    """
    Return a path that does not exist by appending (2), (3), … before the extension.
    If path does not exist, returns it unchanged.
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# ---------------------------------------------------------------------------
# Validation (10-step safety model from Section 25 of mvp.md)
# ---------------------------------------------------------------------------

class SafetyError(ValueError):
    """Raised when a plan item fails a safety check."""


def validate_item(root: Path, item: PlanItem) -> None:
    """
    Run all safety checks before any filesystem operation.
    Raises SafetyError describing the first violated constraint.
    """
    resolved_root = root.resolve()

    # Step 1 — item must be approved
    if item.approved is not True:
        raise SafetyError(f"Item {item.id} is not approved (approved={item.approved!r})")

    # Step 2 — item must not already be applied
    if item.applied:
        raise SafetyError(f"Item {item.id} has already been applied")

    # Step 3 — source path must not be empty
    if not item.source_path:
        raise SafetyError("source_path is empty")

    source = (root / item.source_path).resolve()

    # Step 4 — source must reside inside root
    if not source.is_relative_to(resolved_root):
        raise SafetyError(f"Source path escapes root: {source}")

    # Step 5 — source file must exist
    if not source.exists():
        raise SafetyError(f"Source file does not exist: {source}")

    # Step 6 — destination folder name must be non-empty after sanitization
    safe_folder = re.sub(r"[/\\]", "", item.destination).strip()
    if not safe_folder:
        raise SafetyError("destination folder name is empty after sanitization")

    # Step 7 — destination must reside inside root
    dest = resolve_destination(resolved_root, item.destination, item.new_name, source.name)
    if not dest.parent.resolve().is_relative_to(resolved_root):
        raise SafetyError(f"Destination folder escapes root: {dest.parent}")

    # Step 8 — destination must not be the same file (no-op move)
    if dest.resolve() == source:
        raise SafetyError(f"Source and destination are the same file: {source}")

    # Steps 9 & 10 — path traversal and overwrite are handled by prevent_overwrite
    # and the is_relative_to checks above; nothing extra needed here.


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def execute_item(root: Path, item: PlanItem, dry_run: bool) -> dict[str, Any]:
    """
    Execute (or simulate) a single plan item.

    Returns a result dict:
        {"status": "moved"|"renamed"|"skipped"|"error", "detail": str}
    """
    try:
        validate_item(root, item)
    except SafetyError as exc:
        return {"status": "error", "detail": str(exc)}

    resolved_root = root.resolve()
    source = (root / item.source_path).resolve()
    dest = resolve_destination(resolved_root, item.destination, item.new_name, source.name)
    dest = prevent_overwrite(dest)

    # Determine whether this is a rename, a move, or both
    same_folder = dest.parent.resolve() == source.parent.resolve()
    is_rename = item.new_name is not None
    status = "renamed" if (is_rename and same_folder) else "moved"

    if dry_run:
        return {
            "status": status,
            "detail": f"[dry-run] {source} → {dest}",
            "source": str(source),
            "destination": str(dest),
        }

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))

    return {
        "status": status,
        "detail": f"{source} → {dest}",
        "source": str(source),
        "destination": str(dest),
    }
