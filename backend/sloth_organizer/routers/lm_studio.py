"""
LM Studio status router.

GET /api/lm-studio/status   Check whether LM Studio is running and return the loaded model.
"""

from typing import Any

from fastapi import APIRouter

from sloth_organizer.ai_client import check_lm_studio

router = APIRouter(tags=["lm-studio"])


@router.get("/lm-studio/status")
async def lm_studio_status() -> dict[str, Any]:
    return check_lm_studio()
