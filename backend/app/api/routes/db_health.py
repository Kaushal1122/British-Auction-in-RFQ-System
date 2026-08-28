from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter()


class DatabaseHealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"


class DatabaseErrorResponse(BaseModel):
    status: str = "error"
    database: str = "disconnected"
    detail: str


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    responses={
        503: {
            "model": DatabaseErrorResponse,
            "description": "Database connection failed",
        }
    },
)
def get_db_health(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    """
    Tests database connectivity by executing a lightweight query.
    Returns 200 OK if the database is reachable, or 503 if unreachable.
    """
    try:
        # Execute standard connection check
        db.execute(text("SELECT 1"))
        return DatabaseHealthResponse(status="ok", database="connected")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failure",
        )
