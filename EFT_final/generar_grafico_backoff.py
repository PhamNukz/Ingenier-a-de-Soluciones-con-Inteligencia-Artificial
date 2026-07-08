"""Gráfico antes/después del backoff (IE12). Salida: antes_despues_backoff.png"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_EFT = os.path.dirname(os.path.abspath(__file__))
_LOGS = os.path.join(os.path.dirname(_EFT), "EP3_observabilidad", "logs")
ROJO, VERDE, AZUL, GRIS = "#c0392b", "#1e8449", "#1f4e79", "#566573"


def h(nombre):
    return json.load(open(os.path.join(_LOGS, nombre), encoding="utf-8"))


a, d = h("hallazgos_antes_backoff.json"), h("hallazgos.json")
plt.rcParams.update({"figure.dpi": 140, "font.size": 10, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))

# Izq: tasa de error de API
err = [a["errores"]["tasa_error_api_pct"], d["errores"]["tasa_error_api_pct"]]
b = ax1.bar(["Antes", "Después"], err, color=[ROJO, VERDE], width=0.55)
ax1.bar_label(b, fmt="%.1f%%", padding=3, fontweight="bold")
ax1.set_title("Tasa de error de API")
ax1.set_ylabel("%"); ax1.set_ylim(0, max(err) * 1.25)

# Der: latencias mediana / p95 / p99
et = ["Mediana", "p95", "p99"]
va = [a["latencia"]["mediana_total_s"], a["latencia"]["p95_total_s"], a["latencia"]["p99_total_s"]]
vd = [d["latencia"]["mediana_total_s"], d["latencia"]["p95_total_s"], d["latencia"]["p99_total_s"]]
x = range(len(et)); w = 0.38
ax2.bar([i - w / 2 for i in x], va, w, label="Antes", color=GRIS)
ax2.bar([i + w / 2 for i in x], vd, w, label="Después", color=AZUL)
ax2.set_xticks(list(x)); ax2.set_xticklabels(et)
ax2.set_title("Latencia (s)"); ax2.set_ylabel("segundos"); ax2.legend(fontsize=8)

fig.suptitle("Efecto del backoff (max_retries=5): mismo dataset, antes vs. después",
             fontsize=11, y=1.02)
fig.tight_layout()
salida = os.path.join(_EFT, "antes_despues_backoff.png")
fig.savefig(salida, bbox_inches="tight", facecolor="white")
print("OK:", salida)
