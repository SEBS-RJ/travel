# ============================================================
# ai-service/main.py
# Punto de entrada del microservicio IA — FastAPI
# ============================================================

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from config.settings import get_settings
from routers import chat, recommendations, routes, safety

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza de recursos al arrancar/detener."""
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    # Aquí: inicializar conexión a base vectorial, cargar modelos, etc.
    yield
    logger.info("Deteniendo microservicio IA...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,   # Ocultar Swagger en producción
    redoc_url=None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://backend:8080"],          # Solo el backend interno
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────

app.include_router(chat.router,            prefix="/api/v1/chat",            tags=["chat"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations",  tags=["recommendations"])
app.include_router(routes.router,          prefix="/api/v1/routes",           tags=["routes"])
app.include_router(safety.router,          prefix="/api/v1/safety",           tags=["safety"])


# ── Health check ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}