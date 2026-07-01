"""
LOGGING ESTRUCTURADO EN JSON — EP3 Observabilidad (IE3)
========================================================

Cada consulta al agente produce UN registro JSON (formato JSON Lines, .jsonl):
un objeto por línea. Este formato es ideal para observabilidad porque:

  - Es append-only: no hay que reescribir el archivo completo por cada query.
  - Se procesa en streaming (línea por línea) sin cargar todo en memoria.
  - Lo consumen directamente pandas, jq, Grafana/Loki, Elastic, etc.

Política de privacidad (IE6):
  - El logger NO almacena la API key ni variables de entorno sensibles.
  - El texto de la consulta se trunca y puede anonimizarse (ver seguridad.py).
"""

import json
import os
import threading
from datetime import datetime

# Ruta por defecto del archivo de métricas (carpeta logs/ del proyecto EP3)
_DIR_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # EP3_observabilidad/
RUTA_LOG_DEFECTO = os.path.join(_DIR_BASE, "logs", "metricas.jsonl")

# Lock para escrituras seguras si se ejecuta el dataset en paralelo
_lock = threading.Lock()


def _serializar(valor):
    """Convierte tipos no serializables (datetime, set) a algo que JSON acepte."""
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, set):
        return sorted(valor)
    return str(valor)


def registrar_metricas(registro: dict, ruta_log: str = RUTA_LOG_DEFECTO) -> None:
    """
    Persiste un registro de métricas como una línea JSON en el archivo .jsonl.

    Args:
        registro: diccionario con las métricas de UNA ejecución de consulta.
        ruta_log: archivo destino (por defecto logs/metricas.jsonl).
    """
    os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
    linea = json.dumps(registro, ensure_ascii=False, default=_serializar)
    with _lock:
        with open(ruta_log, "a", encoding="utf-8") as f:
            f.write(linea + "\n")


def leer_metricas(ruta_log: str = RUTA_LOG_DEFECTO) -> list[dict]:
    """
    Lee todos los registros del archivo .jsonl y los devuelve como lista de dicts.
    Ignora líneas vacías o corruptas (robustez ante logs incompletos).

    Args:
        ruta_log: archivo de métricas a leer.

    Returns:
        Lista de registros (dicts). Lista vacía si el archivo no existe.
    """
    if not os.path.exists(ruta_log):
        return []

    registros = []
    with open(ruta_log, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                registros.append(json.loads(linea))
            except json.JSONDecodeError:
                # Línea corrupta: se omite para no romper el análisis/dashboard.
                continue
    return registros


def limpiar_log(ruta_log: str = RUTA_LOG_DEFECTO) -> None:
    """Elimina el archivo de métricas (útil antes de una corrida limpia)."""
    if os.path.exists(ruta_log):
        os.remove(ruta_log)
