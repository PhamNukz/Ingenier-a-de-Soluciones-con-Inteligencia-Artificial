"""
Herramienta de BÚSQUEDA EXTERNA — Agente Portuario EPV v2.0

Consulta Wikipedia en español como fuente de datos externa en tiempo real.
Permite al agente obtener información de contexto sobre regulaciones marítimas
internacionales, estándares de seguridad, terminología técnica portuaria y
marcos normativos que complementan las normativas internas de EPV.

Fuente: API REST pública de Wikipedia en español (https://es.wikipedia.org)
Acceso: Sin API key — acceso libre y gratuito.
"""

import requests
from langchain_core.tools import tool

WIKIPEDIA_SEARCH_URL = "https://es.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://es.wikipedia.org/api/rest_v1/page/summary/{}"
TIMEOUT_SEGUNDOS = 8


def _buscar_titulo_wikipedia(consulta: str) -> str | None:
    """
    Busca el título de artículo más relevante en Wikipedia ES para la consulta.

    Args:
        consulta: Término o frase de búsqueda.

    Returns:
        Título del artículo más relevante, o None si no se encontró.
    """
    params = {
        "action": "opensearch",
        "search": consulta,
        "limit": 3,
        "namespace": 0,
        "format": "json",
    }
    respuesta = requests.get(
        WIKIPEDIA_SEARCH_URL,
        params=params,
        timeout=TIMEOUT_SEGUNDOS,
        headers={"User-Agent": "AgentePortuarioEPV/2.0 (ISY0101-DuocUC)"},
    )
    respuesta.raise_for_status()
    datos = respuesta.json()

    # opensearch retorna [consulta, [títulos], [descripciones], [urls]]
    titulos = datos[1]
    if not titulos:
        return None
    return titulos[0]


def _obtener_resumen_wikipedia(titulo: str) -> dict:
    """
    Obtiene el resumen del artículo de Wikipedia con el título dado.

    Args:
        titulo: Título exacto del artículo Wikipedia.

    Returns:
        Dict con 'extracto', 'url' y 'titulo'.
    """
    titulo_encoded = titulo.replace(" ", "_")
    url = WIKIPEDIA_SUMMARY_URL.format(titulo_encoded)
    respuesta = requests.get(
        url,
        timeout=TIMEOUT_SEGUNDOS,
        headers={"User-Agent": "AgentePortuarioEPV/2.0 (ISY0101-DuocUC)"},
    )
    respuesta.raise_for_status()
    datos = respuesta.json()

    extracto = datos.get("extract", "Sin extracto disponible.")
    # Limitar a 1200 caracteres para no saturar el contexto del agente
    if len(extracto) > 1200:
        extracto = extracto[:1200] + "…"

    return {
        "titulo": datos.get("title", titulo),
        "extracto": extracto,
        "url": datos.get("content_urls", {})
                      .get("desktop", {})
                      .get("page", f"https://es.wikipedia.org/wiki/{titulo_encoded}"),
    }


@tool
def buscar_fuente_externa(consulta: str) -> str:
    """
    Busca información en Wikipedia (fuente externa en tiempo real) sobre temas
    relacionados con seguridad portuaria, normativas marítimas internacionales,
    convenios de la OIT, estándares ISO, reglamentación aduanera u otros conceptos
    técnicos que complementen las normativas internas del Puerto de Valparaíso.

    Úsala cuando necesites:
    - Contexto internacional sobre un reglamento o estándar mencionado en las normativas EPV
    - Definición técnica de terminología marítima o portuaria
    - Información sobre convenios internacionales (SOLAS, MARPOL, OIT, etc.)
    - Marco regulatorio general que no esté en los documentos internos de EPV
    - Complementar una respuesta con información verificable de fuente pública

    El input debe ser el término o concepto que deseas buscar.
    Ejemplo: "Convenio SOLAS seguridad marítima"
    Ejemplo: "equipos de protección personal normativa ISO"
    Ejemplo: "reglamento IMDG mercancías peligrosas"
    """
    try:
        # 1. Buscar el título más relevante
        titulo = _buscar_titulo_wikipedia(consulta)
        if not titulo:
            return (
                f"[Fuente externa — Wikipedia ES] "
                f"No se encontraron resultados para '{consulta}'. "
                f"Intenta con términos más específicos o en inglés técnico."
            )

        # 2. Obtener el resumen del artículo
        articulo = _obtener_resumen_wikipedia(titulo)

        return (
            f"[Fuente externa — Wikipedia ES]\n"
            f"Artículo: {articulo['titulo']}\n"
            f"URL: {articulo['url']}\n\n"
            f"{articulo['extracto']}"
        )

    except requests.exceptions.Timeout:
        return (
            "[Fuente externa — Wikipedia ES] "
            "La consulta superó el tiempo de espera. "
            "Verifica tu conexión a internet e intenta nuevamente."
        )
    except requests.exceptions.ConnectionError:
        return (
            "[Fuente externa — Wikipedia ES] "
            "No se pudo conectar con Wikipedia. "
            "Verifica tu conexión a internet."
        )
    except Exception as e:
        return f"[Fuente externa — Wikipedia ES] Error al consultar: {str(e)}"
