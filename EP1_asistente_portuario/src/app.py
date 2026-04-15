# app.py - Interfaz Streamlit del asistente
import streamlit as st
import sys, os
sys.path.append(os.path.dirname(__file__))
from rag_chain import consultar

st.set_page_config(
    page_title="Asistente Normativo EPV",
    page_icon="🚢",
    layout="centered"
)

st.title("🚢 Asistente de Normativas Portuarias")
st.caption("Puerto de Valparaíso (EPV) — Consulta reglamentos y protocolos")

with st.sidebar:
    st.header("📋 Documentos disponibles")
    st.markdown("""
    - Reglamento de Operaciones Portuarias
    - Manual de Seguridad y EPP
    - Protocolo de Emergencias Marítimas
    - Convenio Colectivo de Trabajadores
    """)
    st.info("Las respuestas citan siempre la fuente normativa.")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
    st.session_state.mensajes.append({
        "role": "assistant",
        "content": "Hola, soy el asistente normativo del Puerto de Valparaíso. ¿En qué te puedo ayudar?"
    })

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if pregunta := st.chat_input("Escribe tu consulta..."):
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando normativas..."):
            respuesta = consultar(pregunta)
        st.write(respuesta)
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})