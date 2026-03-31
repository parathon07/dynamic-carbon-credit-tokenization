"""
Application Configuration — Environment-driven settings.
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config sourced from env vars with sensible defaults."""

    # ── App ─────────────────────────────────────────────────────────
    APP_NAME: str = "Carbon Credit Trading Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Security ────────────────────────────────────────────────────
    SECRET_KEY: str = "carbon-credit-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Rate Limiting ───────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Paths ───────────────────────────────────────────────────────
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]  # Distributed_project/
    P1_DIR: Path = PROJECT_ROOT / "phase1_infrastructure"
    P2_DIR: Path = PROJECT_ROOT / "phase2_ai_blockchain"
    P3_DIR: Path = PROJECT_ROOT / "phase3_market_intelligence"
    P4_DIR: Path = PROJECT_ROOT / "phase4_evaluation"

    # ── CORS ────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
