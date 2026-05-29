# ============================================================
# src/app.py - Asistente Turístico Tarija
# Con animación de escritura (burbuja con tres puntos)
# Mapa persistente, RAG semántico, Routing Agent, Safety Agent
# ============================================================

import sys
import time
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent))
from rag_engine_v2_wrapper import TurismoRAG_v2 as TurismoRAG
from routing_agent import integrate_routing_agent
from safety_agent import SafetyAgent

# ── Configuración de la página ────────────────────────────────

st.set_page_config(
    page_title="Asistente Turístico Tarija",
    page_icon="🏔️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Estilos CSS (incluye animación de tres puntos) ────────────

st.markdown("""
<style>
/* Burbujas de chat */
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

/* Indicador de escritura (tres puntos con onda) */
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
</style>
""", unsafe_allow_html=True)

# ── Cargar motor RAG (cache) ──────────────────────────────────

@st.cache_resource(show_spinner="Cargando base de conocimiento turístico...")
def load_rag():
    knowledge_dir = Path(__file__).parent.parent / "data" / "knowledge"
    return TurismoRAG(str(knowledge_dir))

rag = load_rag()

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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Flag_of_Bolivia.svg/200px-Flag_of_Bolivia.svg.png", width=80)
    st.title("🏔️ Asistente Turístico")
    st.caption("Tarija, Bolivia — IA Híbrida (RAG + Reglas)")

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
    st.caption("Paradigma: RAG semántico + Reglas")
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
st.caption("Sistema RAG con reglas simbólicas + Routing Agent + Safety Agent")

if not st.session_state.messages:
    st.markdown("""
    <div class="bubble-assistant">
    ¡Hola! Soy el asistente turístico inteligente de Tarija 🏔️<br><br>
    Puedo ayudarte con:<br>
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
                f'⚡ {m["elapsed_ms"]}ms</div>',
                unsafe_allow_html=True
            )

# ── Contenedor para la animación de escritura (posición correcta) ──
typing_container = st.empty()

# ── Mostrar mapa si hay coordenadas guardadas ─────────────────

if st.session_state.route_coords:
    origin_coords, dest_coords, origin_name, dest_name = st.session_state.route_coords
    m = folium.Map(location=origin_coords, zoom_start=14)
    folium.Marker(
        location=origin_coords,
        popup=f"Origen: {origin_name}",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    folium.Marker(
        location=dest_coords,
        popup=f"Destino: {dest_name}",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)
    folium.PolyLine(
        locations=[origin_coords, dest_coords],
        color="blue", weight=4, opacity=0.7
    ).add_to(m)
    st.markdown("### 🗺️ Mapa de la última ruta")
    st_folium(m, width=700, height=500, key="route_map")

# ── Input y consultas rápidas ─────────────────────────────────

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
        placeholder="Ej: ¿Qué lugares puedo visitar con 50 bolivianos?",
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("Enviar ➤", use_container_width=True, type="primary")

if submitted and user_input.strip():
    st.session_state.pending_query = user_input.strip()

# ── Procesamiento de la consulta con animación en el contenedor ──

if st.session_state.pending_query and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.messages.append({"role": "user", "content": st.session_state.pending_query})
    st.rerun()

if st.session_state.processing:
    query = st.session_state.pending_query
    st.session_state.pending_query = None

    # Mostrar burbuja animada en el contenedor (ubicado justo después del historial)
    typing_container.markdown(
        '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>',
        unsafe_allow_html=True
    )
    time.sleep(1.2)  # duración de la animación
    typing_container.empty()

    # Detectar si es consulta de ruta
    route_keywords = ["cómo llegar", "ruta a", "distancia", "ir de", "hasta", "desde", "hacia", "llegar a"]
    is_route = any(kw in query.lower() for kw in route_keywords)

    t0 = time.time()

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
    else:
        # No es ruta → limpiar mapa anterior
        st.session_state.route_coords = None
        result = rag.ask(
            query=query,
            hora=hora,
            presupuesto_bob=float(presupuesto) if presupuesto > 0 else None,
            tiempo_disponible_min=int(tiempo_min) if tiempo_min > 0 else None,
            extranjero=extranjero,
        )
        safety = SafetyAgent()
        alerts_safety = safety.check_zone(query, hora=hora)
        result["alerts"].extend(alerts_safety)

    elapsed = round((time.time() - t0) * 1000, 1)

    # Actualizar métricas
    st.session_state.total_queries += 1
    st.session_state.avg_confidence.append(result["confidence"])

    # Agregar respuesta al historial
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
        }
    })

    # Finalizar procesamiento
    st.session_state.processing = False
    st.rerun()