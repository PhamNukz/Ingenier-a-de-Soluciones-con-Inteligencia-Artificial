"""
CAPTURA DEL DASHBOARD — EP3 Observabilidad (evidencia IE8)
==========================================================

Genera imágenes PNG del dashboard Streamlit EN MARCHA, para usarlas como evidencia
visual en el informe/repositorio. Usa un navegador headless (Playwright/Chromium),
por lo que no depende de tomar capturas manuales.

Streamlit fija la altura del documento al viewport y desplaza su contenido en un
contenedor interno; por eso, en lugar de una sola captura de página completa, se
toman varias capturas por SECCIÓN haciendo scroll (encabezado+KPIs, tokens+errores,
similitud, trazabilidad).

Requisitos:
  1. El dashboard corriendo:   streamlit run dashboard.py   (deja localhost:8501)
  2. Playwright + Chromium:     pip install playwright && python -m playwright install chromium

Uso:
    cd EP3_observabilidad/src
    python capturar_dashboard.py

Salida:  docs/img/dashboard_1.png ... dashboard_N.png  (secciones del dashboard)
"""

import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("DASH_URL", "http://localhost:8501")
_BASE = os.path.dirname(os.path.dirname(__file__))
DIR_IMG = os.path.join(_BASE, "docs", "img")

PASO_SCROLL = 820   # px de avance por sección (algo menos que el alto útil → solapa)
MAX_SECCIONES = 5


def main() -> None:
    os.makedirs(DIR_IMG, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1600, "height": 1000})
        try:
            pagina.goto(URL, wait_until="networkidle", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print(f"⚠ No se pudo abrir {URL}. ¿Está corriendo 'streamlit run dashboard.py'?")
            print(f"  Detalle: {e}")
            navegador.close()
            sys.exit(1)

        # Tiempo para que Streamlit y los gráficos Plotly (iframes) rendericen.
        pagina.wait_for_timeout(6000)
        pagina.mouse.move(800, 500)  # posicionar el cursor sobre el área de contenido

        rutas = []
        pos_previa = -1
        for i in range(MAX_SECCIONES):
            ruta = os.path.join(DIR_IMG, f"dashboard_{i + 1}.png")
            pagina.screenshot(path=ruta)
            rutas.append(ruta)

            # Avanzar el scroll del contenedor interno con la rueda.
            pagina.mouse.wheel(0, PASO_SCROLL)
            pagina.wait_for_timeout(1400)

            # ¿Llegamos al fondo? (el scroll ya no avanza)
            pos = pagina.evaluate(
                "() => { const c = document.querySelector('[data-testid=\"stMain\"]')"
                " || document.scrollingElement || document.body;"
                " return c.scrollTop; }"
            )
            if pos == pos_previa:
                break
            pos_previa = pos

        navegador.close()

    print(f"✅ {len(rutas)} capturas del dashboard guardadas en:")
    for r in rutas:
        print(f"   {r}")


if __name__ == "__main__":
    main()
