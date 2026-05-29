# ============================================================
# ai-service/agents/rag_agent.py
# Agente RAG: coordina recuperación + generación con LLM
# ============================================================

import logging
from dataclasses import dataclass

from openai import AsyncOpenAI

from config.settings import get_settings
from rag.vector_store import VectorStore, RetrievedChunk

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """Eres un asistente turístico inteligente especializado en la ciudad de Tarija, Bolivia.
Tu función es ayudar a turistas y visitantes con información sobre lugares turísticos,
rutas seguras, gastronomía, transporte, horarios y planificación de recorridos.

Reglas de comportamiento:
- Responde SIEMPRE en el idioma del usuario (español o inglés).
- Sé amigable, claro y conciso. Máximo 3 párrafos por respuesta.
- Usa SOLO la información del contexto provisto. Si no está en el contexto, dilo honestamente.
- No inventes horarios, precios ni nombres de lugares.
- Si la consulta involucra seguridad o emergencias, incluye el número 110 (Policía Bolivia).
- Cuando el contexto lo permita, explica el motivo de cada recomendación."""


@dataclass
class RAGResponse:
    answer: str
    sources: list[str]
    confidence: float
    fallback_used: bool


class RAGAgent:
    """
    Agente que combina recuperación vectorial con generación del LLM.
    Implementa el pipeline: query → retrieval → augment → generate.
    """

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.llm = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def answer(
        self,
        query: str,
        session_history: list[dict] | None = None,
        category_filter: str | None = None,
        language: str = "es",
    ) -> RAGResponse:
        """
        Responde una consulta usando RAG.
        Si no hay contexto suficiente, responde con conocimiento general del LLM.
        """
        # 1. Recuperar chunks relevantes
        chunks = await self.vector_store.search(
            query=query,
            category_filter=category_filter,
            language=language,
        )

        fallback_used = len(chunks) == 0

        # 2. Construir prompt aumentado
        augmented_prompt, confidence = self.vector_store.build_augmented_prompt(
            query=query,
            chunks=chunks,
            session_history=session_history,
        )

        # 3. Agregar advertencia si se usa fallback
        if fallback_used:
            augmented_prompt = (
                f"No se encontró información específica en la base de conocimiento. "
                f"Responde con lo que sabes sobre turismo en Tarija, Bolivia, "
                f"siendo claro de que es información general. "
                f"Consulta: {query}"
            )

        # 4. Generar respuesta con LLM
        answer = await self._generate(augmented_prompt)

        # 5. Extraer fuentes únicas
        sources = list({c.source for c in chunks})

        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            fallback_used=fallback_used,
        )

    async def _generate(self, prompt: str) -> str:
        """Llama al LLM para generar la respuesta final."""
        try:
            response = await self.llm.chat.completions.create(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error en generación LLM: {e}")
            return "Lo siento, no pude procesar tu consulta en este momento. Por favor intenta de nuevo."