"""
INTERFAZ STREAMLIT — Agente Portuario EPV v2.0
Interfaz web que muestra el chat con el agente y el proceso de razonamiento
interno (cadena Thought → Action → Observation) en tiempo real.
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

import streamlit as st
from agent import ejecutar_agente, reiniciar_agente

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE LA PÁGINA
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente Portuario EPV v2.0",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# ESTILOS CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .tool-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 4px;
    }
    .badge-consulta   { background: #1e3a5f; color: #60a5fa; }
    .badge-escritura  { background: #1e3b2e; color: #34d399; }
    .badge-razon      { background: #3b1e2e; color: #f472b6; }
    .badge-externa    { background: #2d2a1e; color: #fbbf24; }
    .step-box {
        border-left: 3px solid #6366f1;
        padding-left: 12px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Valpo_EPV_logo.png/200px-Valpo_EPV_logo.png",
             use_container_width=True, caption="Puerto de Valparaíso")

    st.markdown("## 🛠 Herramientas del Agente")
    st.markdown("""
<div class="tool-badge badge-consulta">📋 consultar_normativa</div><br>
Busca en la base vectorial de normativas EPV usando RAG + ChromaDB<br><br>
<div class="tool-badge badge-escritura">📝 generar_reporte</div><br>
Crea y guarda documentos formales (reportes, memos, actas)<br><br>
<div class="tool-badge badge-razon">🔍 evaluar_cumplimiento</div><br>
Analiza situaciones y determina nivel de riesgo normativo<br><br>
<div class="tool-badge badge-externa">🌐 buscar_fuente_externa</div><br>
Consulta Wikipedia ES en tiempo real (fuente externa — sin API key)
""", unsafe_allow_html=True)

    st.divider()

    st.markdown("## 💾 Arquitectura de Memoria")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Corto plazo", "8 turnos", "Sesión activa")
    with col2:
        st.metric("Largo plazo", "ChromaDB", "Persistente")

    st.divider()

    st.markdown("## 💡 Ejemplos de consultas")
    ejemplos = [
        "¿Cuáles son los EPP obligatorios en el muelle?",
        "Evalúa: operadores sin casco en zona de descarga nocturna",
        "Genera un reporte del incidente del grúa en muelle 3",
        "¿Cuál es el protocolo de emergencia ante derrame de combustible?",
        "Consulta las normas de seguridad y luego genera un memo de cumplimiento",
        "¿Qué dice Wikipedia sobre el convenio SOLAS?",
    ]
    for ejemplo in ejemplos:
        if st.button(f"💬 {ejemplo[:45]}...", use_container_width=True, key=ejemplo):
            st.session_state.consulta_rapida = ejemplo

    st.divider()

    if st.button("🗑️ Nueva sesión (limpiar memoria)", use_container_width=True, type="secondary"):
        st.session_state.mensajes = []
        st.session_state.pasos_intermedios = []
        reiniciar_agente()
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# ──────────────────────────────────────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "rol": "agente",
            "contenido": (
                "👋 **Bienvenido al Agente Portuario EPV v2.0**\n\n"
                "Soy un agente inteligente especializado en las normativas y operaciones "
                "del Puerto de Valparaíso. Puedo:\n"
                "- 📋 **Consultar** normativas y reglamentos EPV (base vectorial interna)\n"
                "- 🔍 **Evaluar** situaciones de cumplimiento y riesgo normativo\n"
                "- 📝 **Generar** reportes formales y documentos oficiales\n"
                "- 🌐 **Buscar** en fuentes externas (Wikipedia ES) para contexto internacional\n\n"
                "¿En qué puedo ayudarte hoy?"
            ),
        }
    ]

if "pasos_intermedios" not in st.session_state:
    st.session_state.pasos_intermedios = []

if "consulta_rapida" not in st.session_state:
    st.session_state.consulta_rapida = None

# ──────────────────────────────────────────────────────────────────────────────
# LAYOUT PRINCIPAL: Chat (izquierda) + Razonamiento (derecha)
# ──────────────────────────────────────────────────────────────────────────────
st.title("🚢 Agente Portuario EPV v2.0")
st.caption("Agente ReAct con herramientas de consulta, escritura y razonamiento | ISY0101 EP2")

col_chat, col_razon = st.columns([3, 2], gap="medium")

# ── COLUMNA CHAT ──────────────────────────────────────────────────────────────
with col_chat:
    st.subheader("💬 Conversación")

    chat_container = st.container(height=480)
    with chat_container:
        for msg in st.session_state.mensajes:
            if msg["rol"] == "usuario":
                with st.chat_message("user"):
                    st.markdown(msg["contenido"])
            else:
                with st.chat_message("assistant", avatar="🚢"):
                    st.markdown(msg["contenido"])

    # Input de consulta
    consulta_input = st.chat_input("Escribe tu consulta al agente...")

    # Manejar consulta rápida desde sidebar
    if st.session_state.consulta_rapida:
        consulta_input = st.session_state.consulta_rapida
        st.session_state.consulta_rapida = None

    if consulta_input:
        # Agregar mensaje del usuario
        st.session_state.mensajes.append({"rol": "usuario", "contenido": consulta_input})

        # Ejecutar agente
        with st.spinner("🤔 El agente está razonando y seleccionando herramientas..."):
            try:
                resultado = ejecutar_agente(consulta_input)
                respuesta = resultado.get("output", "No se pudo obtener una respuesta.")
                pasos = resultado.get("intermediate_steps", [])
            except Exception as e:
                respuesta = f"⚠ Error al ejecutar el agente: {str(e)}"
                pasos = []

        st.session_state.mensajes.append({"rol": "agente", "contenido": respuesta})
        st.session_state.pasos_intermedios = pasos
        st.rerun()

# ── COLUMNA RAZONAMIENTO ──────────────────────────────────────────────────────
with col_razon:
    st.subheader("🧠 Proceso de Razonamiento")

    COLORES_TOOL = {
        "consultar_normativa":  ("badge-consulta",  "📋"),
        "generar_reporte":      ("badge-escritura",  "📝"),
        "evaluar_cumplimiento": ("badge-razon",      "🔍"),
        "buscar_fuente_externa":("badge-externa",    "🌐"),
    }

    if st.session_state.pasos_intermedios:
        total_pasos = len(st.session_state.pasos_intermedios)
        st.success(f"✅ El agente completó {total_pasos} paso(s) de razonamiento")

        for i, (accion, observacion) in enumerate(st.session_state.pasos_intermedios, 1):
            badge_class, icono = COLORES_TOOL.get(
                accion.tool, ("badge-consulta", "🔧")
            )
            with st.expander(
                f"Paso {i}/{total_pasos} — {icono} {accion.tool}",
                expanded=(i == total_pasos),
            ):
                st.markdown(
                    f'<span class="tool-badge {badge_class}">{icono} {accion.tool}</span>',
                    unsafe_allow_html=True,
                )

                st.markdown("**📥 Input enviado a la herramienta:**")
                st.code(str(accion.tool_input), language="text")

                st.markdown("**📤 Resultado obtenido:**")
                obs_str = str(observacion)
                if len(obs_str) > 800:
                    st.text(obs_str[:800] + f"\n... [{len(obs_str) - 800} caracteres más]")
                else:
                    st.text(obs_str)

                # Mostrar log de razonamiento si está disponible
                if hasattr(accion, "log") and accion.log:
                    thought = accion.log.split("Action:")[0].replace("Thought:", "").strip()
                    if thought:
                        st.markdown("**🤔 Pensamiento del agente (Thought):**")
                        st.markdown(
                            f'<div style="background:#1a1a2e;border-left:3px solid #6366f1;'
                            f'padding:8px 12px;border-radius:4px;font-style:italic;'
                            f'color:#a5b4fc;margin-top:4px">{thought}</div>',
                            unsafe_allow_html=True,
                        )
    else:
        st.info(
            "👆 Envía una consulta y aquí verás el proceso de razonamiento interno "
            "del agente: qué herramientas eligió, con qué inputs y qué obtuvo."
        )

        st.markdown("---")
        st.markdown("**¿Cómo razona el agente?**")
        st.markdown("""
```
Thought: Analiza la tarea
    ↓
Action: Elige herramienta
    ↓
Action Input: Prepara el input
    ↓
Observation: Recibe resultado
    ↓
Thought: ¿Necesito más info?
    ↓ (si no)
Final Answer: Responde
```
""")
