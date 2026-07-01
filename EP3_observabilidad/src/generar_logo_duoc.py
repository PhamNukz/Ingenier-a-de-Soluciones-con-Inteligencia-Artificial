"""
Genera un logo "Duoc UC" aproximado (docs/img/logo_duoc.png) para la portada,
con los colores oficiales (Duoc en naranja, UC en gris oscuro).

⚠ Es una recreación tipográfica SIN el escudo PUC. Para el logo oficial exacto,
reemplaza docs/img/logo_duoc.png por la imagen oficial de DuocUC y vuelve a
ejecutar generar_informe.py.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_BASE = os.path.dirname(os.path.dirname(__file__))
DIR_IMG = os.path.join(_BASE, "docs", "img")
SALIDA = os.path.join(DIR_IMG, "logo_duoc.png")

NARANJA = "#EE7D00"   # naranja DuocUC
CARBON = "#3a3a3a"    # gris oscuro de "UC"
GRIS = "#5a5a5a"      # texto de la escuela

ESCUELA = "ESCUELA DE\nINFORMÁTICA Y\nTELECOMUNICACIONES"


def main():
    os.makedirs(DIR_IMG, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.8, 1.8), dpi=200)
    ax.set_xlim(0, 15.6)
    ax.set_ylim(0, 3)
    ax.axis("off")

    # "Duoc" (naranja) + "UC" (gris oscuro) como una sola palabra
    ax.text(0.15, 1.5, "Duoc", fontsize=50, fontweight="bold",
            color=NARANJA, ha="left", va="center", family="DejaVu Sans")
    ax.text(5.55, 1.5, "UC", fontsize=50, fontweight="bold",
            color=CARBON, ha="left", va="center", family="DejaVu Sans")
    ax.text(8.35, 2.15, "®", fontsize=13, color=CARBON,
            ha="left", va="center", family="DejaVu Sans")

    # Divisor vertical + nombre de la escuela (3 líneas, gris)
    ax.plot([9.15, 9.15], [0.55, 2.55], color=GRIS, linewidth=1.3)
    ax.text(9.5, 1.5, ESCUELA, fontsize=11, color=GRIS,
            ha="left", va="center", family="DejaVu Sans", linespacing=1.35)

    fig.savefig(SALIDA, transparent=True, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print("logo:", SALIDA)


if __name__ == "__main__":
    main()
