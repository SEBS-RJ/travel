# ============================================================
# ai-service/inference/engine.py
# Motor de inferencia simbólica — Reglas del dominio turístico
# Implementa las reglas definidas en la metodología CommonKADS
# ============================================================

from dataclasses import dataclass
from enum import Enum
from datetime import time


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class TransportMode(str, Enum):
    WALKING = "walking"
    TAXI = "taxi"
    PUBLIC_TRANSPORT = "public_transport"
    CAR = "car"


@dataclass
class InferenceContext:
    """Contexto de entrada para el motor de inferencia."""
    hour: int                          # 0–23
    budget_bob: float | None           # Presupuesto en bolivianos
    available_minutes: int | None      # Tiempo disponible
    zone_risk: RiskLevel               # Nivel de riesgo de la zona
    is_foreign: bool = False
    prefers_walking: bool = False
    accessibility_needed: bool = False
    travel_party: str = "solo"         # solo | pareja | familia | grupo


@dataclass
class InferenceResult:
    """Resultado de la evaluación de reglas."""
    avoid_route: bool = False
    recommend_cheap_options: bool = False
    itinerary_type: str = "normal"     # normal | short | nearby
    transport_suggestions: list[TransportMode] = None
    safety_warnings: list[str] = None
    personalization_flags: list[str] = None

    def __post_init__(self):
        if self.transport_suggestions is None:
            self.transport_suggestions = []
        if self.safety_warnings is None:
            self.safety_warnings = []
        if self.personalization_flags is None:
            self.personalization_flags = []


class InferenceEngine:
    """
    Motor de inferencia simbólica basado en reglas IF/THEN.
    Implementa el Modelo de Conocimiento de la metodología CommonKADS.
    """

    NIGHT_START = 22
    NIGHT_END = 6
    MAX_WALKING_MINUTES = 60      # ~5 km caminando
    SHORT_ITINERARY_THRESHOLD = 240    # 4 horas
    NEARBY_ITINERARY_THRESHOLD = 120   # 2 horas
    LOW_BUDGET_THRESHOLD = 50.0        # BOB

    def evaluate(self, ctx: InferenceContext) -> InferenceResult:
        result = InferenceResult()

        self._apply_safety_rules(ctx, result)
        self._apply_budget_rules(ctx, result)
        self._apply_time_rules(ctx, result)
        self._apply_transport_rules(ctx, result)
        self._apply_profile_rules(ctx, result)

        return result

    # ── Reglas de Seguridad ──────────────────────────────────────

    def _apply_safety_rules(self, ctx: InferenceContext, result: InferenceResult):
        is_night = ctx.hour >= self.NIGHT_START or ctx.hour < self.NIGHT_END

        # IF horario = noche AND zona = riesgo alto THEN evitar ruta
        if is_night and ctx.zone_risk == RiskLevel.HIGH:
            result.avoid_route = True
            result.safety_warnings.append(
                "Zona de alto riesgo en horario nocturno. Se recomienda no transitar."
            )

        # IF horario = noche AND zona = riesgo moderado THEN advertir
        if is_night and ctx.zone_risk == RiskLevel.MODERATE:
            result.safety_warnings.append(
                "Zona con riesgo moderado por la noche. Prefiera calles iluminadas y transporte seguro."
            )

        # IF horario = noche THEN recomendar taxi sobre caminata
        if is_night:
            if TransportMode.TAXI not in result.transport_suggestions:
                result.transport_suggestions.insert(0, TransportMode.TAXI)
            result.safety_warnings.append(
                "Por la noche se recomienda solicitar taxi por aplicación y compartir la ruta."
            )

    # ── Reglas de Presupuesto ────────────────────────────────────

    def _apply_budget_rules(self, ctx: InferenceContext, result: InferenceResult):
        if ctx.budget_bob is None:
            return

        # IF presupuesto = bajo THEN recomendar opciones económicas
        if ctx.budget_bob < self.LOW_BUDGET_THRESHOLD:
            result.recommend_cheap_options = True
            result.personalization_flags.append("filter_free_places")
            result.transport_suggestions.append(TransportMode.PUBLIC_TRANSPORT)
            result.transport_suggestions.append(TransportMode.WALKING)

        # IF presupuesto = muy bajo THEN solo opciones gratuitas
        if ctx.budget_bob < 10.0:
            result.personalization_flags.append("only_free_places")

    # ── Reglas de Tiempo ──────────────────────────────────────────

    def _apply_time_rules(self, ctx: InferenceContext, result: InferenceResult):
        if ctx.available_minutes is None:
            return

        # IF tiempo < 2 horas THEN itinerario muy corto y cercano
        if ctx.available_minutes < self.NEARBY_ITINERARY_THRESHOLD:
            result.itinerary_type = "nearby"
            result.personalization_flags.append("max_2_places")

        # IF tiempo < 4 horas THEN generar itinerario corto
        elif ctx.available_minutes < self.SHORT_ITINERARY_THRESHOLD:
            result.itinerary_type = "short"
            result.personalization_flags.append("max_4_places")

    # ── Reglas de Transporte ─────────────────────────────────────

    def _apply_transport_rules(self, ctx: InferenceContext, result: InferenceResult):

        # IF usuario prefiere caminata THEN priorizar rutas peatonales
        if ctx.prefers_walking:
            result.transport_suggestions.insert(0, TransportMode.WALKING)
            result.personalization_flags.append("pedestrian_routes")

        # IF accesibilidad requerida THEN filtrar rutas con obstáculos
        if ctx.accessibility_needed:
            result.personalization_flags.append("accessible_routes_only")
            result.personalization_flags.append("avoid_stairs")

    # ── Reglas de Perfil ──────────────────────────────────────────

    def _apply_profile_rules(self, ctx: InferenceContext, result: InferenceResult):

        # IF usuario = turista extranjero THEN priorizar lugares populares y seguros
        if ctx.is_foreign:
            result.personalization_flags.append("popular_places_first")
            result.personalization_flags.append("include_cultural_context")
            result.personalization_flags.append("add_emergency_contacts")

        # IF viaje en familia THEN excluir lugares solo adultos
        if ctx.travel_party == "familia":
            result.personalization_flags.append("family_friendly_only")
            result.personalization_flags.append("include_parks_and_museums")

        # IF viaje en pareja THEN incluir opciones románticas
        if ctx.travel_party == "pareja":
            result.personalization_flags.append("include_romantic_options")