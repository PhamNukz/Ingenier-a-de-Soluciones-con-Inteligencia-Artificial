"""Diagrama de arquitectura del sistema completo (EFT). Salida: diagrama_arquitectura.png"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AZUL = "#1f4e79"; CELESTE = "#2e86c1"; VERDE = "#1e8449"
NARANJA = "#d68910"; ROJO = "#c0392b"; GRIS = "#566573"; MORADO = "#6c3483"
SALIDA = os.path.join(os.path.dirname(__file__), "diagrama_arquitectura.png")


def caja(ax, x, y, w, h, titulo, sub, color, fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                facecolor=color + "18", edgecolor=color, linewidth=1.6))
    ax.text(x + w / 2, y + h - 0.32, titulo, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=color)
    if sub:
        ax.text(x + w / 2, y + (h - 0.32) / 2 - 0.05, sub, ha="center", va="center",
                fontsize=fs - 2.2, color="#333333", linespacing=1.35)


def flecha(ax, x1, y1, x2, y2, color=GRIS, estilo="-", lw=1.6):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                                 color=color, linewidth=lw, linestyle=estilo))


fig, ax = plt.subplots(figsize=(13, 8.2), dpi=170)
ax.set_xlim(0, 13); ax.set_ylim(0, 10.2); ax.axis("off")
ax.text(6.5, 9.9, "Arquitectura — Agente Portuario EPV (RAG + Agente ReAct + Observabilidad)",
        ha="center", fontsize=13.5, fontweight="bold", color=AZUL)

# Fila superior: usuario → seguridad → agente
caja(ax, 0.2, 7.6, 2.4, 1.5, "Usuario", "Interfaz Streamlit\n(chat + razonamiento)", CELESTE)
caja(ax, 3.3, 7.6, 2.9, 1.5, "Capa de Seguridad", "Sanitización · anti prompt-injection\nRate limit · PII (Ley 19.628)", ROJO)
caja(ax, 7.0, 7.2, 5.6, 2.3, "AGENTE ReAct — gpt-4o-mini (GitHub Models)",
     "AgentExecutor LangChain · máx. 6 pasos\nThought → Action → Observation → Final Answer\nbackoff: max_retries=5 · timeout 45 s", AZUL, fs=11)

flecha(ax, 2.6, 8.35, 3.3, 8.35)
flecha(ax, 6.2, 8.35, 7.0, 8.35)

# Herramientas (fila media)
caja(ax, 0.6, 4.6, 3.0, 1.7, "consultar_normativa", "RAG interno · ChromaDB\n4 PDF EPV · MiniLM k=4", VERDE)
caja(ax, 3.9, 4.6, 2.7, 1.7, "evaluar_cumplimiento", "Dictamen técnico\nriesgo + recomendaciones", MORADO)
caja(ax, 6.9, 4.6, 2.5, 1.7, "generar_reporte", "Escritura de documentos\nformales (memos, actas)", NARANJA)
caja(ax, 9.7, 4.6, 3.0, 1.7, "buscar_fuente_externa", "Wikipedia ES (API REST)\nSOLAS · MARPOL · OIT", CELESTE)
ax.text(6.65, 6.55, "4 herramientas (consulta · razonamiento · escritura · fuente externa)",
        ha="center", fontsize=9, color=GRIS, style="italic")
for x in (2.1, 5.25, 8.15, 11.2):
    flecha(ax, min(max(x, 7.4), 12.2), 7.2, x, 6.3, color=GRIS)

# Memorias (izquierda inferior)
caja(ax, 0.6, 2.2, 3.0, 1.6, "Memoria corto plazo", "Buffer ventana k=8 turnos\n(continuidad de sesión)", GRIS)
caja(ax, 3.9, 2.2, 3.0, 1.6, "Memoria largo plazo", "ChromaDB semántico\n(continuidad entre sesiones)", GRIS)
flecha(ax, 2.1, 3.8, 8.5, 7.2, color=GRIS, estilo="--", lw=1.1)
flecha(ax, 5.4, 3.8, 9.0, 7.2, color=GRIS, estilo="--", lw=1.1)

# Observabilidad (derecha inferior)
caja(ax, 7.4, 2.2, 5.3, 1.6, "OBSERVABILIDAD (no invasiva)",
     "wrapper medir_consulta + callback LangChain\nlatencia por fase · tokens (tiktoken) · errores · scores", VERDE, fs=10)
caja(ax, 7.4, 0.2, 2.5, 1.5, "Logs JSONL", "1 registro JSON\npor consulta (trazabilidad)", GRIS)
caja(ax, 10.2, 0.2, 2.5, 1.5, "Dashboard", "Streamlit + Plotly\nKPIs · p95 · errores · relevancia", NARANJA)
flecha(ax, 10.0, 7.2, 10.0, 3.8, color=VERDE)
flecha(ax, 8.6, 2.2, 8.6, 1.7, color=GRIS)
flecha(ax, 9.9, 0.95, 10.2, 0.95, color=GRIS)

fig.tight_layout()
fig.savefig(SALIDA, bbox_inches="tight", facecolor="white")
print("OK:", SALIDA)
