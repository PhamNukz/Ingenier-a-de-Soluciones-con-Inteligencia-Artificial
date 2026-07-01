"""
Paquete de OBSERVABILIDAD — EP3 (ISY0101)
=========================================

Instrumenta el agente RAG portuario (EP2) con métricas, logging estructurado,
trazabilidad y controles de seguridad.

Módulos:
    instrumentacion   → wrapper `medir_consulta` + callback handler de métricas.
    retrieval_metrics → medición del retrieval (scores de similitud ChromaDB).
    logger_json       → logging estructurado en JSON Lines.
    seguridad         → sanitización, anti prompt-injection, PII y rate limiting.
"""

from observabilidad.logger_json import registrar_metricas, leer_metricas

__all__ = ["registrar_metricas", "leer_metricas"]
