from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Scan — represents one folder scan session
# ---------------------------------------------------------------------------

class Scan(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    folder_path: str
    status: str = "scanning"          # "scanning" | "complete" | "error"
    file_count: int = 0
    folder_count: int = 0
    duplicate_groups: int = 0
    total_size_bytes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# ScannedFile — one file found during a scan
# ---------------------------------------------------------------------------

class ScannedFile(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    scan_id: str = Field(foreign_key="scan.id", index=True)
    filename: str
    relative_path: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    mime_type: str
    sha256: str
    content_preview: Optional[str] = None
    is_duplicate: bool = False


# ---------------------------------------------------------------------------
# Plan — AI-generated organization plan for a scan
# ---------------------------------------------------------------------------

class Plan(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    scan_id: str = Field(foreign_key="scan.id", index=True)
    summary: str
    status: str = "pending"           # "pending" | "applied" | "error"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# PlanItem — one proposed file action inside a plan
# ---------------------------------------------------------------------------

class PlanItem(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    plan_id: str = Field(foreign_key="plan.id", index=True)
    file_id: str = Field(foreign_key="scannedfile.id", index=True)
    source_path: str
    destination: str
    new_name: Optional[str] = None
    reason: str
    task: Optional[str] = None
    priority: Optional[str] = None    # "high" | "medium" | "low" | None
    confidence: float
    approved: Optional[bool] = None   # None=unreviewed, True=approved, False=rejected
    applied: bool = False
