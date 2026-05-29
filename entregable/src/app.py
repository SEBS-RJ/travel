# ============================================================
# src/app.py
# Sprint 3 — Interfaz Streamlit del Asistente Turístico Tarija
# Ejecutar: streamlit run src/app.py
# ============================================================

import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from rag_engine import TurismoRAG

# ── Configuración de la página ────────────────────────────────

st.set_page_config(
    page_title="Asistente Turístico Tarija",
    page_icon="🏔️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Estilos CSS ───────────────────────────────────────────────

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
    line-height: 1.5;
}
.bubble-assistant {
    background: #F3F4F6;
    color: #111827;
    padding: 10px 15px;
    border-radius: 16px 16px 16px 4px;
    margin: 6px 20% 6px 0;
    font-size: 14px;
    line-height: 1.5;
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
.metric-row {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: #6B7280;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── Inicialización del RAG (una sola vez) ─────────────────────

@st.cache_resource(show_spinner="Cargando base de conocimiento turístico...")
def load_rag() -> TurismoRAG:
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


# ── Sidebar: contexto del usuario ────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Flag_of_Bolivia.svg/200px-Flag_of_Bolivia.svg.png", width=80)
    st.title("🏔️ Asistente Turístico")
    st.caption("Tarija, Bolivia — IA Híbrida (RAG + Reglas)")

    st.divider()
    st.subheader("Tu contexto de viaje")

    hora = st.slider("Hora actual", 0, 23, 12, help="Afecta las recomendaciones de seguridad")
    presupuesto = st.number_input("Presupuesto disponible (BOB)", min_value=0, max_value=5000, value=0, step=10)
    tiempo_min = st.selectbox(
        "Tiempo disponible",
        options=[0, 60, 90, 120, 180, 240, 360, 480],
        format_func=lambda x: "Sin límite" if x == 0 else f"{x} minutos ({x//60}h {x%60}min)" if x >= 60 else f"{x} minutos",
        index=0
    )
    extranjero = st.checkbox("Soy turista extranjero")

    st.divider()

    # Métricas de sesión
    st.subheader("Métricas de sesión")
    col1, col2 = st.columns(2)
    col1.metric("Consultas", st.session_state.total_queries)
    avg = round(sum(st.session_state.avg_confidence) / len(st.session_state.avg_confidence), 3) \
        if st.session_state.avg_confidence else 0.0
    col2.metric("Confianza prom.", avg)

    st.divider()
    st.caption(f"Chunks indexados: {rag.retriever.n_docs}")
    st.caption(f"Términos únicos: {len(rag.retriever.idf)}")
    st.caption("Paradigma: RAG + Reglas Simbólicas")

    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.total_queries = 0
        st.session_state.avg_confidence = []
        st.rerun()


# ── Header principal ──────────────────────────────────────────

st.title("🏔️ Asistente Turístico de Tarija")
st.caption("Sistema RAG con reglas simbólicas · Proyecto IA · ODS 10 — Reducción de desigualdades")

# Mensaje de bienvenida si no hay historial
if not st.session_state.messages:
    st.markdown("""
    <div class="bubble-assistant">
    ¡Hola! Soy el asistente turístico inteligente de Tarija 🏔️<br><br>
    Puedo ayudarte con:<br>
    • 📍 Lugares turísticos y qué visitar<br>
    • 🍽️ Gastronomía típica tarijeña<br>
    • 🚌 Transporte y cómo moverse<br>
    • 🔒 Seguridad y zonas recomendadas<br>
    • 🎉 Festividades y eventos culturales<br><br>
    Configura tu contexto de viaje en el panel izquierdo y escribe tu consulta abajo.
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

# ── Input del usuario ─────────────────────────────────────────

st.divider()

# Quick replies como botones
st.caption("Consultas rápidas:")
cols = st.columns(4)
quick = [
    "¿Qué visitar en Tarija?",
    "Comida típica tarijeña",
    "¿Es seguro el centro de noche?",
    "¿Cuándo es el Carnaval?"
]
for i, (col, text) in enumerate(zip(cols, quick)):
    if col.button(text, key=f"quick_{i}", use_container_width=True):
        st.session_state._pending_query = text

# Input principal
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Escribe tu consulta:",
        placeholder="Ej: ¿Qué lugares puedo visitar con 50 bolivianos?",
        label_visibility="collapsed"
    )
    submitted = st.form_submit_button("Enviar ➤", use_container_width=True, type="primary")

# Procesar query (desde form o quick reply)
query_to_process = None
if submitted and user_input.strip():
    query_to_process = user_input.strip()
elif hasattr(st.session_state, "_pending_query"):
    query_to_process = st.session_state._pending_query
    del st.session_state._pending_query

if query_to_process:
    # Agregar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": query_to_process})

    # Procesar con RAG
    t0 = time.time()
    result = rag.ask(
        query=query_to_process,
        hora=hora,
        presupuesto_bob=float(presupuesto) if presupuesto > 0 else None,
        tiempo_disponible_min=int(tiempo_min) if tiempo_min > 0 else None,
        extranjero=extranjero,
    )
    elapsed = round((time.time() - t0) * 1000, 1)

    # Actualizar métricas de sesión
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
            "sources": result["sources"],
        }
    })

    st.rerun()