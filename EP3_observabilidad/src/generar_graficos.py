"""
GENERADOR DE GRÁFICOS DE EVIDENCIA — EP3 Observabilidad (IE8)
============================================================

Lee logs/metricas.jsonl y produce imágenes PNG estáticas con las visualizaciones
clave para incluir como evidencia en el informe (capturas/gráficos). Son las
mismas vistas que ofrece el dashboard interactivo (dashboard.py), exportadas a
archivo para documentación.

Uso:
    cd EP3_observabilidad/src
    python generar_graficos.py
Salida:  EP3_observabilidad/docs/img/*.png
"""

import os
import sys
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")  # backend sin interfaz gráfica
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(__file__))
from observabilidad.logger_json import leer_metricas

_DIR_BASE = os.path.dirname(os.path.dirname(__file__))
DIR_IMG = os.path.join(_DIR_BASE, "docs", "img")

# Paleta coherente (tonos portuarios / sobrios)
AZUL = "#1f4e79"
CELESTE = "#2e86c1"
VERDE = "#1e8449"
NARANJA = "#d68910"
ROJO = "#c0392b"
GRIS = "#566573"

plt.rcParams.update({
    "figure.dpi": 130,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _percentil(datos, p):
    if not datos:
        return 0.0
    d = sorted(datos)
    if len(d) == 1:
        return d[0]
    k = (len(d) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(d) - 1)
    return d[f] + (d[c] - d[f]) * (k - f)


def fig_latencia_temporal(reg, path):
    """Línea temporal de latencia total con líneas de media y p95."""
    ok = [r for r in reg if not r["error"] and r["latencia_total_s"] > 0.1]
    ok = sorted(ok, key=lambda r: r["timestamp"])
    y = [r["latencia_total_s"] for r in ok]
    x = list(range(1, len(y) + 1))
    media = sum(y) / len(y)
    p95 = _percentil(y, 95)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(x, y, marker="o", color=CELESTE, lw=1.8, ms=4, label="Latencia por consulta")
    ax.axhline(media, color=VERDE, ls="--", lw=1.5, label=f"Media {media:.2f}s")
    ax.axhline(p95, color=ROJO, ls=":", lw=1.5, label=f"p95 {p95:.2f}s")
    ax.set_title("Latencia total por consulta (línea temporal)")
    ax.set_xlabel("Consulta (orden cronológico)")
    ax.set_ylabel("Segundos")
    ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_desglose_latencia(reg, path):
    """Barras del desglose promedio de latencia: embedding / retrieval / LLM."""
    ok = [r for r in reg if not r["error"] and r["latencia_total_s"] > 0.1]
    emb = sum(r["latencia_embedding_s"] for r in ok) / len(ok)
    ret = sum(r["latencia_retrieval_s"] for r in ok) / len(ok)
    llm = sum(r["latencia_llm_s"] for r in ok) / len(ok)
    total = emb + ret + llm

    fases = ["Embedding", "Retrieval", "LLM (generación)"]
    valores = [emb, ret, llm]
    colores = [GRIS, NARANJA, AZUL]

    fig, ax = plt.subplots(figsize=(8, 3.4))
    barras = ax.barh(fases, valores, color=colores)
    for b, v in zip(barras, valores):
        ax.text(v + total * 0.01, b.get_y() + b.get_height() / 2,
                f"{v:.3f}s ({100*v/total:.1f}%)", va="center", fontsize=9)
    ax.set_title("Desglose de latencia promedio por fase del pipeline RAG")
    ax.set_xlabel("Segundos (promedio)")
    ax.set_xlim(0, total * 1.18)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_tokens(reg, path):
    """Distribución de tokens totales + comparación prompt vs completion."""
    ok = [r for r in reg if not r["error"] and r["tokens_total"] > 0]
    tot = [r["tokens_total"] for r in ok]
    prompt = sum(r["tokens_prompt"] for r in ok) / len(ok)
    comp = sum(r["tokens_completion"] for r in ok) / len(ok)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.4))
    ax1.hist(tot, bins=10, color=CELESTE, edgecolor="white")
    ax1.set_title("Distribución de tokens por consulta")
    ax1.set_xlabel("Tokens totales")
    ax1.set_ylabel("Frecuencia")

    ax2.bar(["Prompt", "Completion"], [prompt, comp], color=[AZUL, VERDE])
    ax2.set_title("Promedio: prompt vs. completion")
    ax2.set_ylabel("Tokens (promedio)")
    for i, v in enumerate([prompt, comp]):
        ax2.text(i, v + max(prompt, comp) * 0.02, f"{v:.0f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_errores(reg, path):
    """Tasa de errores: dona OK/Error + barras por tipo de error."""
    total = len(reg)
    errores = [r for r in reg if r["error"]]
    cont = Counter(r["tipo_error"] for r in errores)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.6))
    ok = total - len(errores)
    ax1.pie([ok, len(errores)], labels=[f"OK ({ok})", f"Error ({len(errores)})"],
            colors=[VERDE, ROJO], autopct="%1.1f%%", startangle=90,
            wedgeprops={"width": 0.45})
    ax1.set_title("Tasa de error global")

    etiquetas = [k.replace("bloqueado_", "bloq:") for k in cont.keys()]
    valores = list(cont.values())
    colores = [ROJO if not k.startswith("bloqueado_") else NARANJA for k in cont.keys()]
    ax2.bar(range(len(valores)), valores, color=colores)
    ax2.set_xticks(range(len(valores)))
    ax2.set_xticklabels(etiquetas, rotation=20, ha="right", fontsize=7.5)
    ax2.set_title("Errores por tipo (API vs. seguridad)")
    ax2.set_ylabel("Cantidad")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_similitud_categoria(reg, path):
    """Boxplot de scores de similitud (top-1) por categoría de consulta."""
    por_cat = defaultdict(list)
    for r in reg:
        if r["score_similitud_top"] > 0:
            por_cat[r["categoria"]].append(r["score_similitud_top"])

    orden = [c for c in ["en_dominio", "ambigua", "fuera_dominio"] if c in por_cat]
    datos = [por_cat[c] for c in orden]

    # Umbral ADAPTATIVO: punto medio entre la media en-dominio y la media
    # fuera-dominio (la escala del score depende de las distancias L2 reales, por
    # eso no se fija un valor absoluto).
    def _media(cat):
        return sum(por_cat[cat]) / len(por_cat[cat]) if por_cat.get(cat) else None
    med_ed, med_fd = _media("en_dominio"), _media("fuera_dominio")
    if med_ed and med_fd:
        umbral = (med_ed + med_fd) / 2
    else:
        todos = [s for v in por_cat.values() for s in v]
        umbral = sorted(todos)[len(todos) // 2] if todos else 0.0

    fig, ax = plt.subplots(figsize=(8, 3.6))
    bp = ax.boxplot(datos, tick_labels=orden, patch_artist=True, widths=0.55)
    colores = [VERDE, NARANJA, ROJO]
    for parche, col in zip(bp["boxes"], colores):
        parche.set_facecolor(col)
        parche.set_alpha(0.65)
    for med in bp["medians"]:
        med.set_color("black")
    ax.axhline(umbral, color=GRIS, ls="--", lw=1.2,
               label=f"Umbral de relevancia sugerido ({umbral:.3f})")
    ax.set_title("Score de similitud (top-1) por categoría de consulta")
    ax.set_ylabel("Score de relevancia  (1/(1+dist))")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    reg = leer_metricas()
    if not reg:
        print("⚠ No hay métricas. Ejecuta simular_metricas.py o run_evaluacion.py primero.")
        return
    os.makedirs(DIR_IMG, exist_ok=True)

    figuras = [
        ("01_latencia_temporal.png", fig_latencia_temporal),
        ("02_desglose_latencia.png", fig_desglose_latencia),
        ("03_distribucion_tokens.png", fig_tokens),
        ("04_tasa_errores.png", fig_errores),
        ("05_similitud_categoria.png", fig_similitud_categoria),
    ]
    for nombre, func in figuras:
        ruta = os.path.join(DIR_IMG, nombre)
        func(reg, ruta)
        print(f"  ✓ {ruta}")

    print(f"\n{len(figuras)} gráficos generados en {DIR_IMG}")


if __name__ == "__main__":
    main()
