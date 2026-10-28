"""Shared slowapi rate limiter (single instance across the app)."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Rate-limit key: the real client address behind Railway's edge.

    The socket peer is the proxy (shared by every client) and X-Forwarded-For
    is client-controlled, so trust only X-Real-IP, which the edge sets.
    """
    real_ip = request.headers.get("x-real-ip", "").strip()
    return real_ip or get_remote_address(request)


limiter = Limiter(key_func=client_ip)
