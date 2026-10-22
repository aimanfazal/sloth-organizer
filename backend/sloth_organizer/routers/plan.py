"""
Plan router — AI plan generation and human review endpoints.

POST  /api/scans/{scan_id}/plan            Generate AI plan
GET   /api/plans/{plan_id}                 Get plan + all items
PATCH /api/plans/{plan_id}/items/{item_id} Approve or reject an item
"""

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from sloth_organizer.ai_client import generate_plan
from sloth_organizer.database import get_session
from sloth_organizer.models import Plan, PlanItem, Scan, ScannedFile

router = APIRouter(tags=["plan"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ApprovalUpdate(BaseModel):
    approved: bool


# ---------------------------------------------------------------------------
# POST /api/scans/{scan_id}/plan
# ---------------------------------------------------------------------------

@router.post("/scans/{scan_id}/plan")
async def create_plan(
    scan_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    scan = session.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != "complete":
        raise HTTPException(status_code=400, detail=f"Scan is not complete (status: {scan.status})")

    # Load all scanned files for this scan
    files = session.exec(
        select(ScannedFile).where(ScannedFile.scan_id == scan_id)
    ).all()
    if not files:
        raise HTTPException(status_code=400, detail="No files found for this scan")

    # Call AI — may raise ValueError if LM Studio is unreachable or returns bad JSON
    try:
        ai_result = generate_plan(list(files))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI plan generation failed: {exc}")

    # Build a lookup from relative_path → ScannedFile.id
    path_to_file: dict[str, str] = {f.relative_path: f.id for f in files}

    # Persist Plan
    plan_id = str(uuid4())
    plan = Plan(
        id=plan_id,
        scan_id=scan_id,
        summary=ai_result.get("summary", ""),
        status="pending",
    )
    session.add(plan)

    # Persist PlanItems
    plan_items: list[dict[str, Any]] = []
    for item in ai_result.get("items", []):
        file_id = path_to_file.get(item["path"], "")
        if not file_id:
            # Try matching by filename only as fallback
            for f in files:
                if f.filename == item["path"].split("/")[-1]:
                    file_id = f.id
                    break

        plan_item = PlanItem(
            plan_id=plan_id,
            file_id=file_id,
            source_path=item["path"],
            destination=item["destination"],
            new_name=item.get("new_name"),
            reason=item.get("reason", ""),
            task=item.get("task"),
            priority=item.get("priority"),
            confidence=item.get("confidence", 0.5),
        )
        session.add(plan_item)
        plan_items.append(_serialize_item(plan_item))

    session.commit()
    session.refresh(plan)

    return {
        "plan_id": plan.id,
        "scan_id": scan_id,
        "summary": plan.summary,
        "folders": ai_result.get("folders", []),
        "items": plan_items,
    }


# ---------------------------------------------------------------------------
# GET /api/plans/{plan_id}
# ---------------------------------------------------------------------------

@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == plan_id)
    ).all()

    return {
        "plan_id": plan.id,
        "scan_id": plan.scan_id,
        "summary": plan.summary,
        "status": plan.status,
        "created_at": plan.created_at.isoformat(),
        "items": [_serialize_item(i) for i in items],
    }


# ---------------------------------------------------------------------------
# PATCH /api/plans/{plan_id}/items/{item_id}
# ---------------------------------------------------------------------------

@router.patch("/plans/{plan_id}/items/{item_id}")
async def update_item_approval(
    plan_id: str,
    item_id: str,
    body: ApprovalUpdate,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    item = session.get(PlanItem, item_id)
    if not item or item.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="Plan item not found")
    if item.applied:
        raise HTTPException(status_code=400, detail="Item has already been applied")

    item.approved = body.approved
    session.add(item)
    session.commit()
    session.refresh(item)
    return _serialize_item(item)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_item(item: PlanItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "plan_id": item.plan_id,
        "file_id": item.file_id,
        "source_path": item.source_path,
        "destination": item.destination,
        "new_name": item.new_name,
        "reason": item.reason,
        "task": item.task,
        "priority": item.priority,
        "confidence": item.confidence,
        "approved": item.approved,
        "applied": item.applied,
    }
