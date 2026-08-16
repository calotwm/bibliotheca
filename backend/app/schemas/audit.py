"""Audit log read schema (REQ-AUD-2)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None = None
    action: str
    changes_json: dict[str, Any] | None = None
    username: str | None = None
    created_at: datetime