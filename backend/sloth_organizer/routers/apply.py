"""
Apply router — execute approved plan items against the filesystem.

POST /api/plans/{plan_id}/apply
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from sloth_organizer.database import get_session
from sloth_organizer.executor import execute_item
from sloth_organizer.models import Plan, PlanItem, Scan

router = APIRouter(tags=["apply"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class ApplyRequest(BaseModel):
    approved_items: list[str]   # PlanItem IDs to apply
    dry_run: bool = False


# ---------------------------------------------------------------------------
# POST /api/plans/{plan_id}/apply
# ---------------------------------------------------------------------------

@router.post("/plans/{plan_id}/apply")
async def apply_plan(
    plan_id: str,
    body: ApplyRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status == "applied" and not body.dry_run:
        raise HTTPException(status_code=400, detail="Plan has already been applied")

    # Load the originating scan to get the root folder
    scan = session.get(Scan, plan.scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Originating scan not found")

    root = Path(scan.folder_path)
    if not root.exists():
        raise HTTPException(status_code=400, detail=f"Scan root folder no longer exists: {root}")

    # Load only the requested items that are approved in the DB
    requested_ids = set(body.approved_items)
    items: list[PlanItem] = list(
        session.exec(
            select(PlanItem).where(
                PlanItem.plan_id == plan_id,
                PlanItem.approved == True,  # noqa: E712
            )
        ).all()
    )

    # Filter to the caller-supplied subset (intersection of approved + requested)
    items = [i for i in items if i.id in requested_ids]

    moved = 0
    renamed = 0
    skipped = 0
    errors: list[dict[str, str]] = []

    for item in items:
        result = execute_item(root, item, dry_run=body.dry_run)

        if result["status"] == "error":
            errors.append({"item_id": item.id, "detail": result["detail"]})
            skipped += 1
        else:
            if result["status"] == "moved":
                moved += 1
            elif result["status"] == "renamed":
                renamed += 1

            # Persist applied=True only on a real (non-dry) run
            if not body.dry_run:
                item.applied = True
                session.add(item)

    if not body.dry_run:
        # Mark plan as applied when at least one item was successfully executed
        if moved + renamed > 0:
            plan.status = "applied"
            session.add(plan)
        session.commit()

    return {
        "moved": moved,
        "renamed": renamed,
        "skipped": skipped,
        "errors": errors,
        "dry_run": body.dry_run,
    }
