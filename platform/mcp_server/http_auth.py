"""Shared HTTP Basic Auth for Design 1 MCP servers."""

from __future__ import annotations

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def require_mcp_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    user = os.getenv("MCP_BASIC_USER", "mcp")
    password = os.getenv("MCP_BASIC_PASSWORD", "mcp-secret")
    user_ok = secrets.compare_digest(credentials.username, user)
    pass_ok = secrets.compare_digest(credentials.password, password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MCP credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
