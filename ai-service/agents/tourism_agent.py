# ============================================================
# ai-service/agents/tourism_agent.py
# Agente orquestador principal — detecta intención y delega
# ============================================================

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

from openai import AsyncOpenAI

from config.settings import get_settings
from agents.rag_agent import RAGAgent, RAGResponse
from inference.engine import InferenceEngine, InferenceContext, RiskLevel

logger = logging.getLogger(__name__)
settings = get_settings()


class Intent(str, Enum):
    EXPLORE_PLACES     = "explorar_lugares"
    REQUEST_ROUTE      = "solicitar_ruta"
    CHECK_SAFETY       = "consultar_seguridad"
    PLAN_ITINERARY     = "planificar_itinerario"
    CHECK_HOURS        = "consultar_horarios"
    CHECK_PRICES       = "consultar_precios"
    GENERAL_INFO       = "informacion_general"
    GREETING_FAREWELL  = "saludo_despedida"
    OUT_OF_DOMAIN      = "fuera_de_dominio"


@dataclass
class TourismResponse:
    answer: str
    intent: Intent
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    safety_warnings: list[str] = field(default_factory=list)
    quick_replies: list[str] = field(default_factory=list)
    fallback_used: bool = False


# Patrones simples para detección de intención sin LLM (rápido)
INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.CHECK_SAFETY: [
        r"\bsegur[oa]\b", r"\briesgo\b", r"\bpeligro\b", r"\bevitar\b",
        r"\bnoche\b.*\bzona\b", r"\bzona\b.*\bnoche\b",
    ],
    Intent.REQUEST_ROUTE: [
        r"\bc[oó]mo llego\b", r"\bc[oó]mo ir\b", r"\bruta\b",
        r"\bcamino\b", r"\bllegar a\b", r"\bdirecci[oó]n\b",
    ],
    Intent.PLAN_ITINERARY: [
        r"\bitinerario\b", r"\bplanif\b", r"\bqu[eé] hago\b",
        r"\btengo \d+ hora", r"\bpoco tiempo\b",
    ],
    Intent.EXPLORE_PLACES: [
        r"\bvisitar\b", r"\bqu[eé] hay\b", r"\blugar\b", r"\bsitio\b",
        r"\bver en tarija\b", r"\btur[ií]stico\b",
    ],
    Intent.CHECK_HOURS: [
        r"\bhorario\b", r"\ba qu[eé] hora\b", r"\babierto\b", r"\bcierra\b",
    ],
    Intent.CHECK_PRICES: [
        r"\bprecio\b", r"\bcuánto cuesta\b", r"\bcu[aá]nto sale\b",
        r"\bentrada\b.*\bcosto\b", r"\bbarato\b",
    ],
    Intent.GREETING_FAREWELL: [
        r"^\s*(hola|hi|buenas|buenos|hey|chau|adi[oó]s|gracias)\s*[!.]?\s*$",
    ],
}

QUICK_REPLIES_MAP: dict[Intent, list[str]] = {
    Intent.EXPLORE_PLACES:    ["Lugares gratuitos", "Gastronomía típica", "Con poco tiempo", "Para familias"],
    Intent.REQUEST_ROUTE:     ["Caminando", "En taxi", "Transporte público", "Más segura"],
    Intent.CHECK_SAFETY:      ["Zona centro", "Horario nocturno", "Para extranjeros", "Números de emergencia"],
    Intent.PLAN_ITINERARY:    ["1 día completo", "Medio día", "Con niños", "Bajo presupuesto"],
    Intent.GENERAL_INFO:      ["Carnaval de Tarija", "Gastronomía", "Historia", "Transporte urbano"],
}

OUT_OF_DOMAIN_RESPONSE = (
    "Soy el asistente de turismo de Tarija y puedo ayudarte con lugares para visitar, "
    "rutas, seguridad, itinerarios y todo lo relacionado con tu visita a la ciudad. "
    "¿En qué puedo orientarte?"
)

GREETING_RESPONSE = (
    "¡Hola! Bienvenido/a al asistente turístico de Tarija 🏔️ "
    "Estoy aquí para ayudarte con recomendaciones de lugares, rutas seguras, "
    "itinerarios y todo lo que necesites para disfrutar la ciudad. "
    "¿Qué te gustaría saber?"
)


class TourismAgent:
    """
    Agente orquestador principal.
    Detecta la intención del usuario y coordina los agentes especializados.
    """

    def __init__(self, rag_agent: RAGAgent, inference_engine: InferenceEngine):
        self.rag = rag_agent
        self.engine = inference_engine
        self.llm = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def process(
        self,
        query: str,
        session_history: list[dict] | None = None,
        user_context: dict | None = None,
    ) -> TourismResponse:
        """
        Punto de entrada principal. Procesa una consulta y retorna respuesta.

        user_context puede incluir:
            hour, budget_bob, available_minutes, zone_risk,
            is_foreign, prefers_walking, travel_party
        """
        ctx = user_context or {}

        # 1. Detectar intención
        intent = self._detect_intent(query)
        logger.info(f"Intent detectado: {intent} | Query: '{query[:60]}'")

        # 2. Casos especiales sin necesidad de RAG
        if intent == Intent.GREETING_FAREWELL:
            return TourismResponse(
                answer=GREETING_RESPONSE,
                intent=intent,
                quick_replies=["¿Qué visitar?", "Rutas seguras", "Planificar día", "Gastronomía"],
            )

        if intent == Intent.OUT_OF_DOMAIN:
            return TourismResponse(
                answer=OUT_OF_DOMAIN_RESPONSE,
                intent=intent,
                quick_replies=["Lugares turísticos", "Rutas", "Seguridad", "Itinerarios"],
            )

        # 3. Evaluar reglas de inferencia si hay contexto disponible
        inference_result = None
        safety_warnings = []
        if ctx:
            inference_ctx = InferenceContext(
                hour=ctx.get("hour", 12),
                budget_bob=ctx.get("budget_bob"),
                available_minutes=ctx.get("available_minutes"),
                zone_risk=RiskLevel(ctx.get("zone_risk", "low")),
                is_foreign=ctx.get("is_foreign", False),
                prefers_walking=ctx.get("prefers_walking", False),
                accessibility_needed=ctx.get("accessibility_needed", False),
                travel_party=ctx.get("travel_party", "solo"),
            )
            inference_result = self.engine.evaluate(inference_ctx)
            safety_warnings = inference_result.safety_warnings

        # 4. Enriquecer la query con el contexto de inferencia
        enriched_query = self._enrich_query(query, ctx, inference_result)

        # 5. Recuperar conocimiento con RAG
        rag_response: RAGResponse = await self.rag.answer(
            query=enriched_query,
            session_history=session_history,
            category_filter=self._intent_to_category(intent),
        )

        # 6. Añadir advertencias de seguridad a la respuesta si aplica
        answer = rag_response.answer
        if safety_warnings and intent in (Intent.REQUEST_ROUTE, Intent.PLAN_ITINERARY, Intent.EXPLORE_PLACES):
            warnings_text = " ".join(safety_warnings)
            answer = f"{answer}\n\n⚠️ {warnings_text}"

        return TourismResponse(
            answer=answer,
            intent=intent,
            sources=rag_response.sources,
            confidence=rag_response.confidence,
            safety_warnings=safety_warnings,
            quick_replies=QUICK_REPLIES_MAP.get(intent, []),
            fallback_used=rag_response.fallback_used,
        )

    def _detect_intent(self, query: str) -> Intent:
        """Detección de intención por patrones regex (rápido, sin LLM)."""
        query_lower = query.lower().strip()

        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        # Si ningún patrón turístico coincide, verificar si es fuera de dominio
        tourism_keywords = [
            "tarija", "visitar", "lugar", "ruta", "hotel", "restaurant",
            "museo", "bodega", "viñedo", "mercado", "plaza", "turismo",
            "viaje", "transporte", "micro", "taxi", "segur", "itinerary",
        ]
        if not any(kw in query_lower for kw in tourism_keywords):
            return Intent.OUT_OF_DOMAIN

        return Intent.GENERAL_INFO

    def _enrich_query(self, query: str, ctx: dict, inference_result) -> str:
        """Enriquece la query con contexto del usuario para mejorar el RAG."""
        additions = []
        if ctx.get("budget_bob") and ctx["budget_bob"] < 50:
            additions.append("con presupuesto bajo")
        if ctx.get("available_minutes") and ctx["available_minutes"] < 240:
            additions.append(f"con {ctx['available_minutes']} minutos disponibles")
        if ctx.get("travel_party") == "familia":
            additions.append("viajando en familia")
        if ctx.get("is_foreign"):
            additions.append("siendo turista extranjero")
        if inference_result and inference_result.itinerary_type == "nearby":
            additions.append("buscando lugares muy cercanos")

        if additions:
            return f"{query} ({', '.join(additions)})"
        return query

    def _intent_to_category(self, intent: Intent) -> str | None:
        """Mapea intención a categoría de la base vectorial."""
        mapping = {
            Intent.EXPLORE_PLACES:   "lugares_turisticos",
            Intent.GENERAL_INFO:     None,
            Intent.CHECK_SAFETY:     "seguridad",
            Intent.REQUEST_ROUTE:    "transporte",
            Intent.PLAN_ITINERARY:   None,
            Intent.CHECK_HOURS:      "lugares_turisticos",
            Intent.CHECK_PRICES:     "lugares_turisticos",
        }
        return mapping.get(intent)