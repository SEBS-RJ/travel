# ============================================================
# ai-service/routers/chat.py
# Endpoint del chatbot — recibe mensajes y retorna respuestas IA
# ============================================================

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import asyncpg

from agents.tourism_agent import TourismAgent, TourismResponse
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ── Modelos de Request / Response ────────────────────────────

class UserContextDTO(BaseModel):
    """Contexto opcional del usuario para personalizar la respuesta."""
    hour: int | None = Field(None, ge=0, le=23)
    budget_bob: float | None = Field(None, ge=0)
    available_minutes: int | None = Field(None, ge=0)
    zone_risk: str | None = Field(None, pattern="^(low|moderate|high)$")
    is_foreign: bool = False
    prefers_walking: bool = False
    accessibility_needed: bool = False
    travel_party: str | None = Field(None, pattern="^(solo|pareja|familia|grupo)$")


class MessageDTO(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequestDTO(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[MessageDTO] = Field(default_factory=list, max_length=20)
    user_context: UserContextDTO | None = None
    language: str = Field(default="es", pattern="^(es|en)$")

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """Elimina caracteres de control y limita caracteres especiales."""
        import re
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
        return v.strip()


class ChatResponseDTO(BaseModel):
    session_id: str
    answer: str
    intent: str
    sources: list[str]
    confidence: float
    safety_warnings: list[str]
    quick_replies: list[str]
    fallback_used: bool
    timestamp: str


# ── Dependencias ──────────────────────────────────────────────

async def get_tourism_agent(request: Request) -> TourismAgent:
    """Recupera la instancia del TourismAgent desde el estado de la app."""
    agent = getattr(request.app.state, "tourism_agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Servicio IA no disponible")
    return agent


async def get_db(request: Request) -> asyncpg.Pool:
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return pool


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponseDTO)
async def send_message(
    body: ChatRequestDTO,
    agent: TourismAgent = Depends(get_tourism_agent),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Recibe un mensaje del usuario y retorna la respuesta del asistente IA.
    Registra el mensaje en la base de datos para auditoría.
    """
    try:
        # Construir historial como lista de dicts
        history = [{"role": m.role, "content": m.content} for m in body.history]
        user_ctx = body.user_context.model_dump() if body.user_context else {}

        # Si no se proveyó la hora, usar la hora actual
        if "hour" not in user_ctx or user_ctx.get("hour") is None:
            user_ctx["hour"] = datetime.now(timezone.utc).hour

        # Procesar con el agente
        response: TourismResponse = await agent.process(
            query=body.message,
            session_history=history,
            user_context=user_ctx,
        )

        # Persistir conversación de forma asíncrona (fire-and-forget)
        await _persist_message(pool, body.session_id, body.message, response)

        return ChatResponseDTO(
            session_id=body.session_id,
            answer=response.answer,
            intent=response.intent.value,
            sources=response.sources,
            confidence=round(response.confidence, 4),
            safety_warnings=response.safety_warnings,
            quick_replies=response.quick_replies,
            fallback_used=response.fallback_used,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servicio IA")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "chat"}


# ── Helpers ───────────────────────────────────────────────────

async def _persist_message(
    pool: asyncpg.Pool,
    session_id: str,
    user_message: str,
    response: TourismResponse,
) -> None:
    """Guarda el mensaje del usuario y la respuesta del asistente."""
    try:
        async with pool.acquire() as conn:
            # Verificar o crear conversación
            conversation = await conn.fetchrow(
                "SELECT id FROM conversations WHERE session_id = $1", session_id
            )

            if not conversation:
                conv_id = await conn.fetchval(
                    """
                    INSERT INTO conversations (session_id, channel)
                    VALUES ($1, 'mobile_app') RETURNING id
                    """,
                    session_id,
                )
            else:
                conv_id = conversation["id"]

            # Insertar mensaje del usuario
            await conn.execute(
                """
                INSERT INTO conversation_messages
                    (conversation_id, role, content, intent_detected, agents_used)
                VALUES ($1, 'user', $2, $3, $4)
                """,
                conv_id,
                user_message,
                response.intent.value,
                ["tourism_agent", "rag_agent"],
            )

            # Insertar respuesta del asistente
            await conn.execute(
                """
                INSERT INTO conversation_messages
                    (conversation_id, role, content, agents_used)
                VALUES ($1, 'assistant', $2, $3)
                """,
                conv_id,
                response.answer,
                ["tourism_agent", "rag_agent"],
            )

            # Actualizar contador de mensajes
            await conn.execute(
                "UPDATE conversations SET message_count = message_count + 2 WHERE id = $1",
                conv_id,
            )

    except Exception as e:
        # No propagamos el error: guardar es secundario al responder
        logger.warning(f"No se pudo persistir conversación {session_id}: {e}")