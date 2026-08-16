"""Shared slowapi rate limiter (single instance across the app)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
