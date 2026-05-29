# ============================================================
# ai-service/config/settings.py
# Configuración centralizada del microservicio IA
# Usa variables de entorno — NUNCA hardcodear credenciales
# ============================================================

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Entorno ──────────────────────────────────────────────
    APP_ENV: str = "development"               # development | production
    APP_NAME: str = "turismo-tarija-ia"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── API Keys (solo desde .env, nunca hardcodeadas) ───────
    OPENAI_API_KEY: str                        # Para embeddings y LLM
    GOOGLE_MAPS_API_KEY: str                   # Para rutas y geocodificación

    # ── Base de datos ─────────────────────────────────────────
    DATABASE_URL: str                          # postgresql+asyncpg://user:pass@host/db
    PGVECTOR_DIMENSION: int = 1536             # Dimensión del modelo de embeddings

    # ── Backend (comunicación interna) ────────────────────────
    BACKEND_URL: str = "http://backend:8080"
    INTERNAL_API_KEY: str                      # Key para comunicación backend ↔ IA

    # ── LLM ───────────────────────────────────────────────────
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000

    # ── RAG ───────────────────────────────────────────────────
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.70
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 50

    # ── Rate limiting ──────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30

    # ── Seguridad ─────────────────────────────────────────────
    JWT_SECRET_KEY: str                        # Compartido con backend
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()