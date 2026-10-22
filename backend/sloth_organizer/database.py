from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from sloth_organizer.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _resolve_db_path() -> str:
    path = Path(settings.DB_PATH).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


engine = create_engine(
    _resolve_db_path(),
    echo=False,
    connect_args={"check_same_thread": False},
)


# ---------------------------------------------------------------------------
# Initialise tables
# ---------------------------------------------------------------------------

def init_db() -> None:
    # Import models so SQLModel's metadata is populated before create_all
    import sloth_organizer.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# Session dependency (FastAPI)
# ---------------------------------------------------------------------------

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
