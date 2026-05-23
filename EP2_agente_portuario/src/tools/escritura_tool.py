"""
Herramienta de ESCRITURA — Agente Portuario EPV v2.0
Genera y persiste documentos formales: reportes de incidentes,
memos de cumplimiento, actas y resúmenes de consultas.
"""

import os
import json
from datetime import datetime
from langchain_core.tools import tool

REPORTES_PATH = os.path.join(os.path.dirname(__file__), "../../reportes")


@tool
def generar_reporte(datos_reporte: str) -> str:
    """
    Genera y guarda un documento formal relacionado con normativas o incidentes del Puerto de Valparaíso.

    Úsala cuando el usuario solicite:
    - Generar un reporte de incidente o hallazgo
    - Crear un memo de cumplimiento normativo
    - Redactar un acta o resumen formal
    - Documentar una consulta resuelta con su respuesta

    El input debe ser un JSON con la siguiente estructura:
    {
        "tipo": "incidente" | "memo" | "acta" | "consulta",
        "titulo": "Título descriptivo del documento",
        "contenido": "Cuerpo completo del documento con todos los detalles"
    }

    Si no puedes formatear como JSON, envía directamente el texto y se guardará como consulta genérica.

    Ejemplo de input JSON:
    {"tipo": "incidente", "titulo": "Caída de material en Muelle 3", "contenido": "El día 23/05/2026 a las 14:30h se registró una caída de contenedor en el Muelle 3..."}
    """
    try:
        os.makedirs(REPORTES_PATH, exist_ok=True)

        # Parsear JSON o usar texto plano
        try:
            datos = json.loads(datos_reporte)
            tipo = datos.get("tipo", "consulta").lower()
            titulo = datos.get("titulo", "Documento sin título")
            contenido = datos.get("contenido", datos_reporte)
        except (json.JSONDecodeError, AttributeError):
            tipo = "consulta"
            titulo = "Documento generado automáticamente"
            contenido = datos_reporte

        # Nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"EPV_{tipo}_{timestamp}.txt"
        ruta_archivo = os.path.join(REPORTES_PATH, nombre_archivo)

        # Encabezado formal del documento
        encabezado = {
            "incidente": "REPORTE DE INCIDENTE",
            "memo":      "MEMO DE CUMPLIMIENTO NORMATIVO",
            "acta":      "ACTA OFICIAL",
            "consulta":  "REGISTRO DE CONSULTA NORMATIVA",
        }.get(tipo, "DOCUMENTO PORTUARIO")

        contenido_final = f"""
╔══════════════════════════════════════════════════════════╗
║         EMPRESA PORTUARIA VALPARAÍSO (EPV)              ║
║         {encabezado:<48}║
╚══════════════════════════════════════════════════════════╝

Fecha y hora  : {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Tipo          : {tipo.upper()}
Título        : {titulo}
Generado por  : Agente Portuario EPV v2.0

──────────────────────────────────────────────────────────
CONTENIDO
──────────────────────────────────────────────────────────

{contenido}

──────────────────────────────────────────────────────────
Documento generado automáticamente por el Agente Inteligente EPV.
Para consultas, contactar al área de Operaciones y Normativa.
══════════════════════════════════════════════════════════
"""

        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(contenido_final)

        return (
            f"✅ Documento generado exitosamente.\n"
            f"Tipo     : {encabezado}\n"
            f"Archivo  : {nombre_archivo}\n"
            f"Ruta     : {ruta_archivo}\n\n"
            f"Vista previa:\n{contenido_final[:600]}..."
        )

    except Exception as e:
        return f"❌ Error al generar el documento: {str(e)}"
