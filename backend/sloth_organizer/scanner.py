"""
Core filesystem scanner.

Walks a folder recursively, collects metadata + SHA-256 + content previews,
detects duplicates, and persists everything to SQLite.
Progress is broadcast over WebSocket at key milestones.
"""

import hashlib
import mimetypes
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlmodel import Session, select

from sloth_organizer.extractors import extract_preview
from sloth_organizer.models import Scan, ScannedFile

# Fallback MIME when python-magic is unavailable
_magic_available = False
try:
    import magic  # type: ignore
    _magic_available = True
except Exception:
    pass


ProgressCallback = Callable[[int, str], None]  # (percent 0-100, stage label)

_SUPPORTED_PREVIEW_EXTS = {".txt", ".md", ".csv", ".json", ".pdf", ".docx", ".xlsx"}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_folder(
    folder_path: str,
    scan_id: str,
    session: Session,
    progress: ProgressCallback | None = None,
) -> None:
    """
    Synchronously scan *folder_path*, populate SQLite, and update the Scan record.
    Call *progress(percent, label)* at each stage milestone.
    """

    def _emit(pct: int, label: str) -> None:
        if progress:
            progress(pct, label)

    root = Path(folder_path)

    # -----------------------------------------------------------------------
    # Stage 1 — Collect all file paths (5 %)
    # -----------------------------------------------------------------------
    _emit(0, "Finding files…")
    all_paths = [p for p in root.rglob("*") if p.is_file()]
    total = len(all_paths)
    folder_count = len({p.parent for p in all_paths})
    _emit(5, "Finding files…")

    if total == 0:
        _finish(scan_id, session, file_count=0, folder_count=0, duplicate_groups=0, total_size=0)
        _emit(100, "Complete")
        return

    # -----------------------------------------------------------------------
    # Stage 2 — Metadata + MIME (5 → 40 %)
    # -----------------------------------------------------------------------
    _emit(5, "Reading metadata…")
    raw_files: list[dict[str, Any]] = []
    for idx, path in enumerate(all_paths):
        raw_files.append(_collect_metadata(path, root))
        if idx % max(1, total // 20) == 0:
            pct = 5 + int((idx / total) * 35)
            _emit(pct, "Reading metadata…")

    # -----------------------------------------------------------------------
    # Stage 3 — SHA-256 hashing (40 → 70 %)
    # -----------------------------------------------------------------------
    _emit(40, "Hashing files…")
    for idx, meta in enumerate(raw_files):
        meta["sha256"] = _sha256(Path(meta["_abs_path"]))
        if idx % max(1, total // 20) == 0:
            pct = 40 + int((idx / total) * 30)
            _emit(pct, "Hashing files…")

    # -----------------------------------------------------------------------
    # Stage 4 — Content previews (70 → 85 %)
    # -----------------------------------------------------------------------
    _emit(70, "Reading file contents…")
    for idx, meta in enumerate(raw_files):
        ext = meta["extension"]
        if ext in _SUPPORTED_PREVIEW_EXTS:
            meta["content_preview"] = extract_preview(Path(meta["_abs_path"]), ext)
        else:
            meta["content_preview"] = None
        if idx % max(1, total // 20) == 0:
            pct = 70 + int((idx / total) * 15)
            _emit(pct, "Reading file contents…")

    # -----------------------------------------------------------------------
    # Stage 5 — Duplicate detection (85 → 90 %)
    # -----------------------------------------------------------------------
    _emit(85, "Detecting duplicates…")
    hash_groups: dict[str, list[int]] = defaultdict(list)
    for idx, meta in enumerate(raw_files):
        hash_groups[meta["sha256"]].append(idx)
    duplicate_hashes = {h for h, idxs in hash_groups.items() if len(idxs) > 1}
    for meta in raw_files:
        meta["is_duplicate"] = meta["sha256"] in duplicate_hashes
    duplicate_groups = len(duplicate_hashes)

    # -----------------------------------------------------------------------
    # Stage 6 — Persist to SQLite (90 → 99 %)
    # -----------------------------------------------------------------------
    _emit(90, "Preparing AI context…")
    total_size = 0
    for meta in raw_files:
        total_size += meta["size_bytes"]
        row = ScannedFile(
            scan_id=scan_id,
            filename=meta["filename"],
            relative_path=meta["relative_path"],
            extension=meta["extension"],
            size_bytes=meta["size_bytes"],
            created_at=meta["created_at"],
            modified_at=meta["modified_at"],
            mime_type=meta["mime_type"],
            sha256=meta["sha256"],
            content_preview=meta["content_preview"],
            is_duplicate=meta["is_duplicate"],
        )
        session.add(row)

    session.commit()
    _emit(99, "Preparing AI context…")

    # -----------------------------------------------------------------------
    # Finalise Scan record
    # -----------------------------------------------------------------------
    _finish(scan_id, session, total, folder_count, duplicate_groups, total_size)
    _emit(100, "Complete")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_metadata(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    extension = path.suffix.lower()
    mime = _detect_mime(path, extension)

    return {
        "_abs_path": str(path),
        "filename": path.name,
        "relative_path": str(path.relative_to(root)),
        "extension": extension,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime),
        "modified_at": datetime.fromtimestamp(stat.st_mtime),
        "mime_type": mime,
        "sha256": "",           # filled in Stage 3
        "content_preview": None,
        "is_duplicate": False,
    }


def _detect_mime(path: Path, extension: str) -> str:
    if _magic_available:
        try:
            return magic.from_file(str(path), mime=True)
        except Exception:
            pass
    # stdlib fallback
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        pass
    return h.hexdigest()


def _finish(
    scan_id: str,
    session: Session,
    file_count: int,
    folder_count: int,
    duplicate_groups: int,
    total_size: int,
) -> None:
    scan = session.get(Scan, scan_id)
    if scan:
        scan.status = "complete"
        scan.file_count = file_count
        scan.folder_count = folder_count
        scan.duplicate_groups = duplicate_groups
        scan.total_size_bytes = total_size
        session.add(scan)
        session.commit()
