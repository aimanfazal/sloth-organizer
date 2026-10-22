"""
Scan router — filesystem scanning endpoints + WebSocket progress.

POST /api/scan              Start a scan
GET  /api/scans/{scan_id}   Get scan status + summary
GET  /api/scans/{scan_id}/files  List scanned files (paginated)
WS   /ws/scan/{scan_id}     Real-time progress
"""

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session, select

from sloth_organizer.database import get_session
from sloth_organizer.models import Scan, ScannedFile
from sloth_organizer.scanner import scan_folder
from sloth_organizer.ws import manager, broadcast_sync

router = APIRouter(tags=["scan"])
ws_router = APIRouter(tags=["ws"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    folder: str


class ScanResponse(BaseModel):
    scan_id: str
    file_count: int
    duplicate_groups: int


# ---------------------------------------------------------------------------
# POST /api/scan
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResponse)
async def start_scan(
    body: ScanRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    folder = Path(body.folder).expanduser().resolve()
    if not folder.exists():
        raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder}")

    scan_id = str(uuid4())
    scan = Scan(id=scan_id, folder_path=str(folder), status="scanning")
    session.add(scan)
    session.commit()

    # Run the scan in a background thread (blocking I/O) so the HTTP response
    # is returned immediately, while progress flows over WebSocket.
    loop = asyncio.get_event_loop()
    background_tasks.add_task(
        _run_scan_in_thread, loop, str(folder), scan_id
    )

    return {"scan_id": scan_id, "file_count": 0, "duplicate_groups": 0}


def _run_scan_in_thread(
    loop: asyncio.AbstractEventLoop,
    folder: str,
    scan_id: str,
) -> None:
    """Executed in a BackgroundTask (async context, but scan_folder is sync)."""
    from sloth_organizer.database import engine
    from sqlmodel import Session as _Session

    def _progress(pct: int, label: str) -> None:
        broadcast_sync(scan_id, {"type": "progress", "percent": pct, "stage": label})

    with _Session(engine) as session:
        try:
            scan_folder(str(folder), scan_id, session, progress=_progress)
            # Fetch final counts and broadcast complete
            scan = session.get(Scan, scan_id)
            if scan:
                broadcast_sync(scan_id, {
                    "type": "complete",
                    "summary": {
                        "file_count": scan.file_count,
                        "folder_count": scan.folder_count,
                        "duplicate_groups": scan.duplicate_groups,
                        "total_size_bytes": scan.total_size_bytes,
                    },
                })
        except Exception as exc:
            broadcast_sync(scan_id, {"type": "error", "message": str(exc)})
            # Mark scan as errored
            scan = session.get(Scan, scan_id)
            if scan:
                scan.status = "error"
                session.add(scan)
                session.commit()


# ---------------------------------------------------------------------------
# GET /api/scans/{scan_id}
# ---------------------------------------------------------------------------

@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    scan = session.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "scan_id": scan.id,
        "folder_path": scan.folder_path,
        "status": scan.status,
        "file_count": scan.file_count,
        "folder_count": scan.folder_count,
        "duplicate_groups": scan.duplicate_groups,
        "total_size_bytes": scan.total_size_bytes,
        "created_at": scan.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /api/scans/{scan_id}/files
# ---------------------------------------------------------------------------

@router.get("/scans/{scan_id}/files")
async def get_scan_files(
    scan_id: str,
    offset: int = 0,
    limit: int = 200,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    scan = session.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    stmt = select(ScannedFile).where(ScannedFile.scan_id == scan_id).offset(offset).limit(limit)
    files = session.exec(stmt).all()

    return {
        "scan_id": scan_id,
        "offset": offset,
        "limit": limit,
        "files": [
            {
                "id": f.id,
                "filename": f.filename,
                "relative_path": f.relative_path,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "modified_at": f.modified_at.isoformat(),
                "mime_type": f.mime_type,
                "sha256": f.sha256,
                "content_preview": f.content_preview,
                "is_duplicate": f.is_duplicate,
            }
            for f in files
        ],
    }


# ---------------------------------------------------------------------------
# WS /ws/scan/{scan_id}
# ---------------------------------------------------------------------------

@ws_router.websocket("/ws/scan/{scan_id}")
async def ws_scan_progress(scan_id: str, websocket: WebSocket) -> None:
    await manager.connect(scan_id, websocket)
    try:
        while True:
            # Keep the connection alive; server pushes messages via manager.broadcast
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(scan_id, websocket)
