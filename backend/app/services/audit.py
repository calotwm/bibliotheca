"""Audit logging for mutating operations."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


async def log_audit(
    session: AsyncSession,
    *,
    user_id: int | None,
    entity_type: str,
    entity_id: int | None,
    action: str,
    changes: dict[str, Any],
) -> None:
    """Record a mutating operation to ``audit_log`` (caller commits)."""
    session.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changes_json=changes,
            user_id=user_id,
        )
    )
