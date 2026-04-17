"""
Authentication Module — API Key + JWT Support

Supports two auth methods:
  1. API Key via X-API-Key header (simple, for B2B/internal)
  2. JWT Bearer token via Authorization header (advanced, for user-facing)

Usage:
    from app.auth import verify_api_key
    @app.post("/ask")
    def ask(_key: str = Depends(verify_api_key)):
        ...
"""
import os
import jwt
import time
import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Security, Header
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# API Key Authentication
# ─────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from X-API-Key header.
    Returns the API key if valid.
    Raises HTTPException(401) if invalid or missing.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <your-key>",
        )
    if api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )
    return api_key


# ─────────────────────────────────────────────
# JWT Authentication
# ─────────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Demo users (in production, use database)
DEMO_USERS = {
    "student": {"password": "demo123", "role": "user"},
    "teacher": {"password": "teach456", "role": "admin"},
}

security = HTTPBearer(auto_error=False)


def create_token(username: str, role: str) -> str:
    """Create JWT token with expiry."""
    payload = {
        "sub": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify JWT token from Authorization: Bearer <token> header.
    Returns user info dict with 'username' and 'role'.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Include: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        return {"username": payload["sub"], "role": payload["role"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token.")


def authenticate_user(username: str, password: str) -> dict:
    """Authenticate username/password, return user info if valid."""
    user = DEMO_USERS.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}
