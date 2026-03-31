"""
Security — JWT Authentication, Password Hashing, Role-Based Access.
"""
from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

# ── Password hashing (SHA-256 + salt) ─────────────────────────────────

def _hash_pw(password: str, salt: str = "") -> str:
    if not salt:
        salt = os.urandom(16).hex()
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(plain: str, hashed: str) -> bool:
    salt = hashed.split("$")[0]
    return _hash_pw(plain, salt) == hashed


def hash_password(password: str) -> str:
    return _hash_pw(password)

# ── Bearer token extractor ────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

# ── In-memory user store (production: replace with DB) ────────────────
_users_db: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "hashed_password": _hash_pw("admin123"),
        "role": "admin",
        "full_name": "System Administrator",
    },
    "operator": {
        "username": "operator",
        "hashed_password": _hash_pw("operator123"),
        "role": "operator",
        "full_name": "Plant Operator",
    },
    "viewer": {
        "username": "viewer",
        "hashed_password": _hash_pw("viewer123"),
        "role": "viewer",
        "full_name": "Data Viewer",
    },
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    user = _users_db.get(username)
    if user and verify_password(password, user["hashed_password"]):
        return user
    return None


def register_user(username: str, password: str, role: str = "viewer",
                  full_name: str = "") -> Dict:
    if username in _users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    _users_db[username] = {
        "username": username,
        "hashed_password": hash_password(password),
        "role": role,
        "full_name": full_name or username,
    }
    return {"username": username, "role": role}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if username not in _users_db:
        raise HTTPException(status_code=401, detail="User not found")
    user = _users_db[username].copy()
    user.pop("hashed_password", None)
    return user


def require_role(*roles: str):
    """Dependency factory for role-based access control."""
    async def _check(user: Dict = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user
    return _check


# ── Rate limiter (simple in-memory) ───────────────────────────────────
_rate_store: Dict[str, list] = {}


async def rate_limiter(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60  # seconds
    limit = settings.RATE_LIMIT_PER_MINUTE

    if ip not in _rate_store:
        _rate_store[ip] = []

    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]

    if len(_rate_store[ip]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    _rate_store[ip].append(now)
