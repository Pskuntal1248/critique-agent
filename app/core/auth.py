from fastapi import HTTPException, Query, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Enforce API key auth via X-API-Key header. No-op when auth is disabled."""
    if not settings.auth_enabled:
        return
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def require_api_key_sse(
    api_key_header: str | None = Security(_api_key_header),
    api_key_query: str | None = Query(None, alias="api_key", include_in_schema=False),
) -> None:
    """Enforce API key auth for SSE endpoints.

    Accepts the key via the ``X-API-Key`` header **or** as a ``?api_key=``
    query parameter.  The query-param fallback is required because the browser's
    ``EventSource`` API cannot send custom headers.
    """
    if not settings.auth_enabled:
        return
    key = api_key_header or api_key_query
    if not key or key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
