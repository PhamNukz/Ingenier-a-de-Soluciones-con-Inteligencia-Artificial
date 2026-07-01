"""
DASHBOARD DE OBSERVABILIDAD — EP3 (IE5)
=======================================

Dashboard visual en Streamlit que lee logs/metricas.jsonl y muestra el
comportamiento del Agente Portuario EPV según las métricas instrumentadas:

  - KPIs: nº de consultas, tasa de error, latencia media/p95, tokens medios.
  - Latencia promedio/p95 en línea temporal.
  - Desglose de latencia por fase (embedding → retrieval → LLM).
  - Distribución de tokens (prompt vs. completion).
  - Tasa de errores por tipo.
  - Scores de similitud por consulta y por categoría.

Uso:
    cd EP3_observabilidad/src
    streamlit run dashboard.py
"""

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.dirname(__file__))
from observabilidad.logger_json import leer_metricas, RUTA_LOG_DEFECTO

st.set_page_config(
    page_title="Observabilidad — Agente Portuario EPV",
    page_icon="📊",
    layout="wide",
)

AZUL = "#1f4e79"
VERDE = "#1e8449"
ROJO = "#c0392b"
NARANJA = "#d68910"


@st.cache_data(ttl=10)
def cargar_datos(ruta: str) -> pd.DataFrame:
    registros = leer_metricas(ruta)
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["orden"] = range(1, len(df) + 1)
    return df


def percentil(serie, p):
    return float(serie.quantile(p / 100)) if len(serie) else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# CARGA Y SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
st.title("📊 Dashboard de Observabilidad — Agente Portuario EPV")
st.caption("ISY0101 · EP3 · Métricas de precisión, latencia, consistencia, errores y recursos")

df = cargar_datos(RUTA_LOG_DEFECTO)

if df.empty:
    st.warning(
        "No hay métricas en `logs/metricas.jsonl`. Genera datos con:\n\n"
        "```\npython simular_metricas.py   # datos demo\n"
        "python run_evaluacion.py     # datos reales (requiere token)\n```"
    )
    st.stop()

with st.sidebar:
    st.header("⚙ Filtros")
    categorias = sorted(df["categoria"].unique())
    sel_cat = st.multiselect("Categoría de consulta", categorias, default=categorias)
    solo_errores = st.checkbox("Mostrar solo errores", value=False)

    fuente = df["fuente_datos"].iloc[0] if "fuente_datos" in df else "desconocida"
    color_badge = NARANJA if fuente == "simulado" else VERDE
    st.markdown(
        f"<div style='padding:8px;border-radius:8px;background:{color_badge}22;"
        f"border:1px solid {color_badge}'>Fuente de datos: "
        f"<b style='color:{color_badge}'>{str(fuente).upper()}</b></div>",
        unsafe_allow_html=True,
    )
    if fuente == "simulado":
        st.caption("⚠ Datos simulados para demo. Regenera con `run_evaluacion.py` "
                   "y tu token para evidencia real.")
    st.divider()
    st.metric("Registros totales", len(df))
    st.caption(f"Archivo: `{os.path.basename(RUTA_LOG_DEFECTO)}`")

df_f = df[df["categoria"].isin(sel_cat)]
if solo_errores:
    df_f = df_f[df_f["error"]]

df_ok = df_f[~df_f["error"]]

# ──────────────────────────────────────────────────────────────────────────────
# KPIs
# ──────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Consultas", len(df_f))
tasa_err = 100 * df_f["error"].sum() / len(df_f) if len(df_f) else 0
c2.metric("Tasa de error", f"{tasa_err:.1f}%")
lat_media = df_ok["latencia_total_s"].mean() if len(df_ok) else 0
c3.metric("Latencia media", f"{lat_media:.2f}s")
p95 = percentil(df_ok["latencia_total_s"], 95) if len(df_ok) else 0
c4.metric("Latencia p95", f"{p95:.2f}s")
tok_medio = df_ok[df_ok["tokens_total"] > 0]["tokens_total"].mean() if len(df_ok) else 0
c5.metric("Tokens medios", f"{tok_medio:.0f}" if tok_medio == tok_medio else "0")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# FILA 1: Latencia temporal + desglose por fase
# ──────────────────────────────────────────────────────────────────────────────
col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("⏱ Latencia total por consulta (línea temporal)")
    dft = df_ok[df_ok["latencia_total_s"] > 0.1]
    if len(dft):
        fig = px.line(dft, x="orden", y="latencia_total_s", markers=True,
                      color_discrete_sequence=[AZUL],
                      labels={"orden": "Consulta (orden cronológico)",
                              "latencia_total_s": "Segundos"})
        fig.add_hline(y=dft["latencia_total_s"].mean(), line_dash="dash", line_color=VERDE,
                      annotation_text=f"Media {dft['latencia_total_s'].mean():.2f}s")
        fig.add_hline(y=percentil(dft["latencia_total_s"], 95), line_dash="dot", line_color=ROJO,
                      annotation_text=f"p95 {percentil(dft['latencia_total_s'],95):.2f}s")
        fig.update_layout(height=340, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("🔬 Desglose de latencia por fase")
    if len(df_ok):
        desglose = pd.DataFrame({
            "Fase": ["Embedding", "Retrieval", "LLM (generación)"],
            "Segundos": [
                df_ok["latencia_embedding_s"].mean(),
                df_ok["latencia_retrieval_s"].mean(),
                df_ok["latencia_llm_s"].mean(),
            ],
        })
        fig = px.bar(desglose, x="Segundos", y="Fase", orientation="h", text_auto=".3f",
                     color="Fase", color_discrete_sequence=["#566573", NARANJA, AZUL])
        fig.update_layout(height=340, showlegend=False, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("El LLM domina el tiempo total: el cuello de botella es la generación, no el RAG.")

# ──────────────────────────────────────────────────────────────────────────────
# FILA 2: Tokens + errores
# ──────────────────────────────────────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("🔢 Distribución de tokens")
    dtok = df_ok[df_ok["tokens_total"] > 0]
    if len(dtok):
        fig = px.histogram(dtok, x="tokens_total", nbins=12,
                           color_discrete_sequence=[AZUL],
                           labels={"tokens_total": "Tokens totales por consulta"})
        fig.update_layout(height=320, margin=dict(t=30, b=10), yaxis_title="Frecuencia")
        st.plotly_chart(fig, use_container_width=True)
        cc1, cc2 = st.columns(2)
        cc1.metric("Prompt medio", f"{dtok['tokens_prompt'].mean():.0f} tok")
        cc2.metric("Completion medio", f"{dtok['tokens_completion'].mean():.0f} tok")

with col_d:
    st.subheader("⚠ Tasa de errores por tipo")
    df_err = df_f[df_f["error"]]
    if len(df_err):
        cont = df_err["tipo_error"].value_counts().reset_index()
        cont.columns = ["tipo_error", "cantidad"]
        cont["clase"] = cont["tipo_error"].apply(
            lambda t: "Seguridad (bloqueo)" if str(t).startswith("bloqueado_") else "Error API/sistema"
        )
        fig = px.bar(cont, x="cantidad", y="tipo_error", orientation="h", color="clase",
                     color_discrete_map={"Seguridad (bloqueo)": NARANJA, "Error API/sistema": ROJO})
        fig.update_layout(height=320, margin=dict(t=30, b=10), legend_title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("Sin errores en la selección actual. ✅")

# ──────────────────────────────────────────────────────────────────────────────
# FILA 3: Similitud por categoría + por consulta
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🎯 Precisión / Relevancia — Score de similitud de chunks recuperados")
col_e, col_f = st.columns([2, 3])

df_sim = df_f[df_f["score_similitud_top"] > 0]

with col_e:
    if len(df_sim):
        # Umbral adaptativo: punto medio entre las medias en-dominio y fuera-dominio.
        medias = df_sim.groupby("categoria")["score_similitud_top"].mean()
        if "en_dominio" in medias and "fuera_dominio" in medias:
            umbral = (medias["en_dominio"] + medias["fuera_dominio"]) / 2
        else:
            umbral = df_sim["score_similitud_top"].median()
        fig = px.box(df_sim, x="categoria", y="score_similitud_top", color="categoria",
                     points="all",
                     color_discrete_map={"en_dominio": VERDE, "ambigua": NARANJA,
                                         "fuera_dominio": ROJO},
                     labels={"score_similitud_top": "Score top-1", "categoria": "Categoría"})
        fig.add_hline(y=umbral, line_dash="dash", line_color="#566573",
                      annotation_text=f"Umbral sugerido {umbral:.3f}")
        fig.update_layout(height=360, showlegend=False, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with col_f:
    if len(df_sim):
        dfq = df_sim.drop_duplicates("id").sort_values("score_similitud_top")
        dfq["q_corta"] = dfq["query"].str.slice(0, 45) + "…"
        fig = px.bar(dfq, x="score_similitud_top", y="q_corta", orientation="h",
                     color="categoria",
                     color_discrete_map={"en_dominio": VERDE, "ambigua": NARANJA,
                                         "fuera_dominio": ROJO},
                     labels={"score_similitud_top": "Score similitud top-1", "q_corta": ""})
        fig.update_layout(height=360, margin=dict(t=30, b=10), legend_title="",
                          yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# DETALLE / TRAZABILIDAD
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🔎 Trazabilidad — registros crudos (logs JSON)"):
    cols = ["timestamp", "categoria", "query", "latencia_total_s", "latencia_llm_s",
            "tokens_total", "score_similitud_top", "num_pasos", "herramientas_usadas",
            "error", "tipo_error"]
    cols = [c for c in cols if c in df_f.columns]
    st.dataframe(df_f[cols], use_container_width=True, height=300)

st.caption("EP3 · Observabilidad, Seguridad y Ética en Agentes de IA · Agente Portuario EPV")
