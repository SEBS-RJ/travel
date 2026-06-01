# ============================================================
# src/app.py - Asistente Turístico Tarija
# Fase 3: Gemini 2.5 Flash + Fallback a RAG local
# Fase 4 parcial: Soporte multilingüe (dejamos que Gemini detecte el idioma)
# Responsive con botones simétricos (mismo ancho)
# ============================================================

import sys
import time
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium
from langdetect import detect, LangDetectException

# SDK de Gemini
try:
    from google import genai
    USE_GEMINI_SDK = True
except ImportError:
    USE_GEMINI_SDK = False

sys.path.insert(0, str(Path(__file__).parent))
from rag_engine_v2_wrapper import TurismoRAG_v2 as TurismoRAG
from routing_agent import integrate_routing_agent
from safety_agent import SafetyAgent

# ── Configuración de la página ────────────────────────────────

st.set_page_config(
    page_title="Asistente Turístico Tarija",
    page_icon="🏔️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Estilos CSS (original + mejoras responsive + botones simétricos) ──

st.markdown("""
<style>
/* Estilos originales de burbujas y animación */
.bubble-user {
    background: #2563EB;
    color: white;
    padding: 10px 15px;
    border-radius: 16px 16px 4px 16px;
    margin: 6px 0 6px 20%;
    font-size: 14px;
}
.bubble-assistant {
    background: #F3F4F6;
    color: #111827;
    padding: 10px 15px;
    border-radius: 16px 16px 16px 4px;
    margin: 6px 20% 6px 0;
    font-size: 14px;
    border: 1px solid #E5E7EB;
}
.meta {
    font-size: 11px;
    color: #9CA3AF;
    margin: 2px 4px 8px;
}
.alert-box {
    background: #FEF3C7;
    border-left: 4px solid #F59E0B;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
    margin: 4px 0;
    color: #92400E;
}
.typing-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: #F3F4F6;
    padding: 12px 18px;
    border-radius: 20px;
    border: 1px solid #E5E7EB;
    width: fit-content;
    margin: 6px 20% 6px 0;
}
.typing-dot {
    width: 8px;
    height: 8px;
    background-color: #9CA3AF;
    border-radius: 50%;
    animation: wave 1.2s infinite ease-in-out;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes wave {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-10px); opacity: 1; }
}

/* Mejoras responsive y botones simétricos */
@media (max-width: 768px) {
    /* Hacer que las 5 columnas tengan el mismo ancho */
    div[data-testid="column"] {
        flex: 1 1 90px !important;   /* base igual para todas */
        min-width: 80px !important;
        max-width: 120px !important;
        text-align: center;
    }
    /* Botones ocupan toda la columna y el texto se ajusta */
    .stButton button {
        width: 100% !important;
        white-space: normal !important;
        word-break: break-word;
        font-size: 11px !important;
        padding: 6px 4px !important;
    }
    /* Mapa más pequeño */
    iframe {
        height: 300px !important;
    }
    /* Ajustar márgenes de burbujas en móvil */
    .bubble-user {
        margin-left: 10% !important;
    }
    .bubble-assistant {
        margin-right: 10% !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Función para detectar idioma solo para metadatos (no influye en respuesta) ──
def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return 'es'

# ── Configuración de Gemini (Plan A) ──────────────────────────

GEMINI_CLIENT = None
USE_GEMINI = False

if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_key = st.secrets["GEMINI_API_KEY"]
    if USE_GEMINI_SDK:
        try:
            GEMINI_CLIENT = genai.Client(api_key=api_key)
            USE_GEMINI = True
        except Exception as e:
            st.warning(f"⚠️ Error configurando Gemini: {e}")
    else:
        st.warning("⚠️ SDK google-genai no instalado. Ejecuta: pip install google-genai")
else:
    st.info("🔑 Sin API key de Gemini. El asistente usará modo local (RAG).")

# ── Cargar motor RAG (Plan B) ─────────────────────────────────

@st.cache_resource(show_spinner="Cargando base de conocimiento turístico...")
def load_rag():
    knowledge_dir = Path(__file__).parent.parent / "data" / "knowledge"
    return TurismoRAG(str(knowledge_dir))

rag = load_rag()

# ── Funciones para Gemini con reintentos (multilingüe natural) ──

def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    if not USE_GEMINI or GEMINI_CLIENT is None:
        raise Exception("Gemini no disponible")
    for attempt in range(max_retries):
        try:
            response = GEMINI_CLIENT.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                raise e
    raise Exception("No se pudo obtener respuesta de Gemini")

def generate_response_with_fallback(query: str, context_chunks: list, user_context: dict) -> tuple:
    """Plan A -> Plan B -> Plan C. Retorna (respuesta, fuente, idioma_detectado_para_meta)."""
    # Construir contexto
    context_text = "\n".join([chunk["text"][:800] for chunk in context_chunks[:5]])
    
    # Prompt sin forzar un idioma específico; Gemini lo detectará automáticamente
    prompt = f"""
Eres un asistente turístico experto en Tarija, Bolivia.
**Debes responder en el mismo idioma que la pregunta del usuario.**
Usa el siguiente contexto para responder de forma amable, concisa y útil.
Si la respuesta no está en el contexto, di que no lo sabes, pero intenta ayudar con lo que sabes.
No inventes información.

Contexto (en español, pero responde en el idioma de la pregunta):
{context_text}

Pregunta del usuario: {query}

Respuesta (en el mismo idioma que la pregunta):
"""
    # PLAN A: Gemini
    try:
        answer = call_gemini_with_retry(prompt)
        # Detectar el idioma de la respuesta solo para los metadatos (puede fallar, no importa)
        try:
            meta_lang = detect_language(answer)
        except:
            meta_lang = 'auto'
        return answer, "gemini", meta_lang
    except Exception as e:
        # PLAN B: RAG local (solo español)
        try:
            st.warning(f"⚠️ Modo avanzado no disponible. Usando motor local (solo español). Error: {str(e)[:80]}")
            result = rag.ask(
                query=query,
                hora=user_context.get("hora", 12),
                presupuesto_bob=user_context.get("presupuesto"),
                tiempo_disponible_min=user_context.get("tiempo_min"),
                extranjero=user_context.get("extranjero", False)
            )
            answer = result["answer"]
            # Añadir aviso si el usuario parece no hablar español (detectado de la query)
            try:
                query_lang = detect_language(query)
                if query_lang != 'es':
                    answer = f"[El modo local solo responde en español. Tu pregunta parecía estar en {query_lang}]\n\n{answer}"
            except:
                pass
            return answer, "rag", 'es'
        except Exception:
            default_msgs = {
                'es': "Lo siento, estoy teniendo problemas técnicos. Por favor, intenta de nuevo en unos minutos. Mientras tanto, puedes consultar la Secretaría de Turismo de Tarija.",
                'en': "I'm sorry, I'm having technical issues. Please try again in a few minutes. Meanwhile, you can check the Tarija Tourism Office.",
                'pt': "Desculpe, estou tendo problemas técnicos. Por favor, tente novamente em alguns minutos. Enquanto isso, você pode consultar a Secretaria de Turismo de Tarija."
            }
            return default_msgs.get('es'), "default", 'es'

# ── Estado de la sesión ───────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0
if "avg_confidence" not in st.session_state:
    st.session_state.avg_confidence = []
if "route_coords" not in st.session_state:
    st.session_state.route_coords = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# ── Sidebar (contexto) ────────────────────────────────────────

with st.sidebar:
    col1, col2 = st.columns(2)
    with col1:
        st.image("entregable/assets/bandera_bolivia.png", width=60)
    with col2:
        st.image("entregable/assets/bandera_tarija.png", width=60)
    st.title("🏔️ Asistente Turístico")
    st.caption("Tarija, Bolivia — IA Híbrida (Gemini + RAG) + Multilingüe")

    st.divider()
    st.subheader("Tu contexto de viaje")
    hora = st.slider("Hora actual", 0, 23, 12)
    presupuesto = st.number_input("Presupuesto disponible (BOB)", min_value=0, max_value=5000, value=0, step=10)
    tiempo_min = st.selectbox(
        "Tiempo disponible",
        options=[0, 60, 90, 120, 180, 240, 360, 480],
        format_func=lambda x: "Sin límite" if x == 0 else f"{x} minutos",
        index=0
    )
    extranjero = st.checkbox("Soy turista extranjero")

    st.divider()
    st.subheader("Métricas de sesión")
    col1, col2 = st.columns(2)
    col1.metric("Consultas", st.session_state.total_queries)
    avg = round(sum(st.session_state.avg_confidence) / len(st.session_state.avg_confidence), 3) if st.session_state.avg_confidence else 0.0
    col2.metric("Confianza prom.", avg)

    st.divider()
    st.caption(f"Chunks indexados: {rag.retriever.n_docs}")
    st.caption("Plan A: Gemini | Plan B: RAG local | Plan C: Respuesta por defecto")
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.total_queries = 0
        st.session_state.avg_confidence = []
        st.session_state.route_coords = None
        st.session_state.processing = False
        st.session_state.pending_query = None
        st.rerun()

# ── Header principal ──────────────────────────────────────────

st.title("🏔️ Asistente Turístico de Tarija")
st.caption("Sistema híbrido: Gemini 2.5 Flash + RAG semántico + Routing Agent + Safety Agent + Multilingüe")

if not st.session_state.messages:
    st.markdown("""
    <div class="bubble-assistant">
    ¡Hola! Soy el asistente turístico inteligente de Tarija 🏔️<br><br>
    Puedo ayudarte en.<br>
    • 📍 Lugares turísticos y qué visitar<br>
    • 🍽️ Gastronomía típica tarijeña<br>
    • 🚌 Transporte y cómo moverte<br>
    • 🔒 Seguridad y zonas recomendadas<br>
    • 🗺️ Rutas (ej: "¿Cómo llegar de la plaza central a la bodega Campos de Solana?")<br><br>
    Configura tu contexto en el panel izquierdo y escribe tu consulta.
    </div>
    """, unsafe_allow_html=True)

# ── Historial de mensajes ────────────────────────────────────

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-assistant">{msg["content"]}</div>', unsafe_allow_html=True)
        if msg.get("meta"):
            m = msg["meta"]
            alerts_html = "".join(f'<div class="alert-box">{a}</div>' for a in m.get("alerts", []))
            if alerts_html:
                st.markdown(alerts_html, unsafe_allow_html=True)
            st.markdown(
                f'<div class="meta">🎯 Intent: {m["intent"]} &nbsp;|&nbsp; '
                f'📊 Confianza: {m["confidence"]:.4f} &nbsp;|&nbsp; '
                f'🧩 Chunks: {m["n_chunks"]} &nbsp;|&nbsp; '
                f'⚡ {m["elapsed_ms"]}ms &nbsp;|&nbsp; '
                f'🤖 Fuente: {m.get("source", "rag")} &nbsp;|&nbsp; '
                f'🌍 Idioma: {m.get("language", "es")}</div>',
                unsafe_allow_html=True
            )

# ── Contenedor para la animación (se mostrará durante el procesamiento) ──
typing_container = st.empty()

# ── Mostrar mapa si hay coordenadas guardadas (responsivo) ────

if st.session_state.route_coords:
    origin_coords, dest_coords, origin_name, dest_name = st.session_state.route_coords
    m = folium.Map(location=origin_coords, zoom_start=14)
    folium.Marker(origin_coords, popup=f"Origen: {origin_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(dest_coords, popup=f"Destino: {dest_name}", icon=folium.Icon(color="red", icon="stop")).add_to(m)
    folium.PolyLine([origin_coords, dest_coords], color="blue", weight=4, opacity=0.7).add_to(m)
    st.markdown("### 🗺️ Mapa de la última ruta")
    st_folium(m, width=700, height=500, key="route_map", use_container_width=True)

# ── Input y consultas rápidas (botones simétricos) ────────────

st.divider()
st.caption("Consultas rápidas:")

cols = st.columns(5)
quick = [
    "¿Qué visitar en Tarija?",
    "Comida típica",
    "¿Es seguro el centro de noche?",
    "¿Cuándo es el Carnaval?",
    "¿Cómo llegar de la plaza a una bodega?"
]
for i, (col, text) in enumerate(zip(cols, quick)):
    if col.button(text, key=f"quick_{i}", use_container_width=True):
        st.session_state.pending_query = text

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Escribe tu consulta:",
        placeholder="Ej: What places can I visit in Tarija?",
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("Enviar ➤", use_container_width=True, type="primary")

if submitted and user_input.strip():
    st.session_state.pending_query = user_input.strip()

# ── Procesamiento de la consulta ───────────────────────────────

if st.session_state.pending_query and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.messages.append({"role": "user", "content": st.session_state.pending_query})
    st.rerun()

if st.session_state.processing:
    query = st.session_state.pending_query
    st.session_state.pending_query = None

    if query is None or not isinstance(query, str) or query.strip() == "":
        st.session_state.processing = False
        st.rerun()

    typing_container.markdown(
        '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>',
        unsafe_allow_html=True
    )

    route_keywords = ["cómo llegar", "ruta a", "distancia", "ir de", "hasta", "desde", "hacia", "llegar a"]
    is_route = any(kw in query.lower() for kw in route_keywords)

    t0 = time.time()
    detected_lang = 'es'

    if is_route:
        route, answer = integrate_routing_agent(query)
        if route is None:
            result = {
                "answer": answer,
                "intent": "ruta",
                "confidence": 0.0,
                "n_chunks_retrieved": 0,
                "alerts": [],
                "sources": []
            }
            st.session_state.route_coords = None
        else:
            st.session_state.route_coords = (
                route["origin_coords"], route["destination_coords"],
                route["origin_name"], route["destination_name"]
            )
            result = {
                "answer": answer,
                "intent": "ruta",
                "confidence": 0.9,
                "n_chunks_retrieved": 0,
                "alerts": route["warnings"],
                "sources": []
            }
        source = "routing_agent"
    else:
        context_results = rag.engine.search(query, top_k=5)
        user_context = {
            "hora": hora,
            "presupuesto": float(presupuesto) if presupuesto > 0 else None,
            "tiempo_min": int(tiempo_min) if tiempo_min > 0 else None,
            "extranjero": extranjero,
        }
        answer, source, detected_lang = generate_response_with_fallback(query, context_results, user_context)
        intent = rag.engine.classify_intent(query)
        result = {
            "answer": answer,
            "intent": intent,
            "confidence": 0.9 if source == "gemini" else 0.6 if source == "rag" else 0.3,
            "n_chunks_retrieved": len(context_results),
            "alerts": [],
            "sources": [f"Generado por {source}"]
        }
        safety = SafetyAgent()
        alerts_safety = safety.check_zone(query, hora=hora)
        result["alerts"].extend(alerts_safety)
        st.session_state.route_coords = None

    elapsed = round((time.time() - t0) * 1000, 1)

    st.session_state.total_queries += 1
    st.session_state.avg_confidence.append(result["confidence"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "meta": {
            "intent": result["intent"],
            "confidence": result["confidence"],
            "n_chunks": result["n_chunks_retrieved"],
            "elapsed_ms": elapsed,
            "alerts": result["alerts"],
            "sources": result.get("sources", []),
            "source": source if not is_route else "routing_agent",
            "language": detected_lang
        }
    })

    typing_container.empty()
    st.session_state.processing = False
    st.rerun()