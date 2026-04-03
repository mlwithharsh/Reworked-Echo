from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


def require_api_token(
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    bearer = authorization.replace("Bearer ", "") if authorization else None
    token = x_api_token or bearer
    if token != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    return token
