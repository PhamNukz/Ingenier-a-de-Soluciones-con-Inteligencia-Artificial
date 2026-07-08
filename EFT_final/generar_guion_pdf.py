"""Convierte GUION_DEFENSA.md a PDF legible (GUION_DEFENSA.pdf) con fpdf2."""
import os
import re
from fpdf import FPDF

_DIR = os.path.dirname(os.path.abspath(__file__))
FUENTES = "C:/Windows/Fonts"
AZUL = (31, 78, 121)
GRIS = (86, 101, 115)
NEGRO = (30, 30, 30)


class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("calibri", "", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 8, f"Guion de defensa EFT ISY0101 — pág. {self.page_no()}", align="C")


def escribir_con_negritas(pdf, texto, size=10.5, color=NEGRO, indent=0):
    """Renderiza una línea respetando **negritas** inline."""
    pdf.set_text_color(*color)
    pdf.set_x(pdf.l_margin + indent)
    partes = re.split(r"(\*\*.+?\*\*)", texto)
    for parte in partes:
        if parte.startswith("**") and parte.endswith("**"):
            pdf.set_font("calibri", "B", size)
            pdf.write(5.2, parte[2:-2])
        else:
            pdf.set_font("calibri", "", size)
            pdf.write(5.2, parte)
    pdf.ln(6.5)


def main():
    pdf = PDF(format="A4")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("calibri", "", os.path.join(FUENTES, "calibri.ttf"))
    pdf.add_font("calibri", "B", os.path.join(FUENTES, "calibrib.ttf"))
    pdf.add_font("calibri", "I", os.path.join(FUENTES, "calibrii.ttf"))
    pdf.add_page()

    with open(os.path.join(_DIR, "GUION_DEFENSA.md"), encoding="utf-8") as f:
        lineas = f.read().splitlines()

    for linea in lineas:
        t = linea.rstrip()
        if t == "---":
            pdf.ln(2)
            pdf.set_draw_color(*GRIS)
            pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
            pdf.ln(4)
        elif t.startswith("# "):
            pdf.set_font("calibri", "B", 16)
            pdf.set_text_color(*AZUL)
            pdf.multi_cell(0, 8, t[2:].replace("**", ""))
            pdf.ln(1)
        elif t.startswith("## "):
            pdf.ln(2)
            pdf.set_font("calibri", "B", 13)
            pdf.set_text_color(*AZUL)
            pdf.multi_cell(0, 7, t[3:].replace("**", ""))
            pdf.ln(1)
        elif t.startswith("### "):
            pdf.ln(1.5)
            pdf.set_font("calibri", "B", 11.5)
            pdf.set_text_color(*AZUL)
            pdf.multi_cell(0, 6, t[4:].replace("**", ""))
        elif t.startswith("> "):
            escribir_con_negritas(pdf, t[2:].strip('"“”').strip(), size=10.5,
                                  color=GRIS, indent=5)
        elif t.startswith("- [ ] "):
            escribir_con_negritas(pdf, "[  ]  " + t[6:], indent=3)
        elif t.startswith("- "):
            escribir_con_negritas(pdf, "•  " + t[2:], indent=3)
        elif re.match(r"^\d+\.\s", t):
            escribir_con_negritas(pdf, t, indent=3)
        elif t.startswith("**") and t.endswith("**") and t.count("**") == 2:
            pdf.ln(1)
            pdf.set_font("calibri", "B", 11)
            pdf.set_text_color(*NEGRO)
            pdf.multi_cell(0, 6, t.strip("*"))
        elif t:
            escribir_con_negritas(pdf, t)
        else:
            pdf.ln(2.5)

    salida = os.path.join(_DIR, "GUION_DEFENSA.pdf")
    pdf.output(salida)
    print("OK:", salida)


if __name__ == "__main__":
    main()
