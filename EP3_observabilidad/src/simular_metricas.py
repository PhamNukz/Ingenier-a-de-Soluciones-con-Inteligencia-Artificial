"""
SIMULADOR DE MÉTRICAS — EP3 Observabilidad (datos de demostración)
==================================================================

Genera un archivo logs/metricas.jsonl con datos SINTÉTICOS pero REALISTAS e
internamente consistentes, calibrados al sistema real (agente ReAct gpt-4o-mini
vía GitHub Models, embeddings MiniLM multilingüe, k=4 chunks, 4 documentos EPV).

⚠ IMPORTANTE — HONESTIDAD ACADÉMICA:
    Cada registro lleva  "fuente_datos": "simulado".
    Este script existe para poder probar el dashboard y el flujo de análisis SIN
    consumir la cuota de la API. Para la evidencia FINAL del informe, regenera los
    datos con la corrida real:   python run_evaluacion.py --limpiar
    El dashboard y el análisis funcionan igual con datos reales o simulados.

Modelo de simulación (basado en el comportamiento observado de la arquitectura):
  - La latencia del LLM domina el tiempo total (~85-92%): cuello de botella.
  - El retrieval (embedding + búsqueda vectorial) es local y muy rápido (<0.2s).
  - Consultas fuera de dominio → baja similitud de chunks (corpus no las cubre).
  - Consultas adversariales → BLOQUEADAS por la capa de seguridad (IE6).
  - Tasa de error realista del nivel gratuito de GitHub Models (~8%).
"""

import os
import random
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(__file__))
from dataset_queries import DATASET, N_CONSISTENCIA
from observabilidad.logger_json import limpiar_log, RUTA_LOG_DEFECTO, registrar_metricas
from observabilidad.seguridad import sanitizar_input

SEED = 42
random.seed(SEED)

# Perfiles por categoría: (sim_top medio, sim_top sd, pasos probables, prob_error)
PERFILES = {
    "en_dominio":    {"sim_mu": 0.78, "sim_sd": 0.05, "pasos": [1, 1, 1, 2, 2], "p_err": 0.05},
    "ambigua":       {"sim_mu": 0.54, "sim_sd": 0.08, "pasos": [1, 2, 2, 3],    "p_err": 0.12},
    "fuera_dominio": {"sim_mu": 0.32, "sim_sd": 0.06, "pasos": [0, 1, 1, 2],    "p_err": 0.14},
    # adversarial se maneja aparte (bloqueo por seguridad)
}

TIPOS_ERROR_API = ["timeout", "api_error", "rate_limit_api"]
FUENTES_DOCS = [
    "manual_seguridad_epp",
    "reglamento_operaciones_portuarias",
    "protocolo_emergencias_maritimas",
    "convenio_colectivo_trabajadores",
]


def _hash(texto: str) -> str:
    import hashlib
    return hashlib.sha1(texto.strip().lower().encode("utf-8")).hexdigest()[:10]


def _scores_similitud(sim_top: float) -> list[float]:
    """Genera 4 scores decrecientes y plausibles a partir del score top."""
    scores = [round(max(0.05, min(0.99, sim_top)), 4)]
    actual = sim_top
    for _ in range(3):
        actual -= random.uniform(0.03, 0.10)
        scores.append(round(max(0.05, actual), 4))
    return scores


def _herramientas(categoria: str, query: str, pasos: int) -> list[str]:
    """Decide qué herramientas usó el agente según categoría y consulta."""
    if pasos == 0:
        return []  # respondió directo sin herramientas (p.ej. cálculo aritmético)
    q = query.lower()
    if categoria == "fuera_dominio":
        # El agente intenta la fuente externa (Wikipedia) al no hallar en el corpus
        return ["buscar_fuente_externa"] if "multiplicado" not in q else []
    if "evalúa" in q or "riesgo" in q:
        return ["consultar_normativa", "evaluar_cumplimiento"][:max(1, pasos)]
    if pasos >= 2:
        return ["consultar_normativa", "evaluar_cumplimiento"]
    return ["consultar_normativa"]


def _registro_normal(query, categoria, es_limite, run_idx, ts) -> dict:
    perfil = PERFILES[categoria]
    sim_top = random.gauss(perfil["sim_mu"], perfil["sim_sd"])
    sim_top = max(0.08, min(0.97, sim_top))
    scores = _scores_similitud(sim_top)
    pasos = random.choice(perfil["pasos"])
    herramientas = _herramientas(categoria, query, pasos)

    # ── Latencias ────────────────────────────────────────────────────────────
    lat_emb = round(random.uniform(0.020, 0.055), 4)
    lat_ret = round(random.uniform(0.050, 0.150), 4)
    # Cada paso ReAct implica una llamada al LLM (pasos+1 llamadas: razonar + responder)
    n_llm_calls = max(1, pasos + 1)
    lat_llm = round(sum(random.gauss(1.8, 0.45) for _ in range(n_llm_calls)), 4)
    lat_llm = max(0.6, lat_llm)

    # ── Tokens (crecen con los pasos por el scratchpad ReAct) ─────────────────
    tokens_prompt = int(random.gauss(950 + 620 * pasos, 130))
    tokens_completion = int(random.gauss(190 + 70 * pasos, 55))
    tokens_prompt = max(300, tokens_prompt)
    tokens_completion = max(40, tokens_completion)

    # ── Errores (inyección realista) ──────────────────────────────────────────
    error = False
    tipo_error = None
    respuesta_vacia = False
    long_resp = int(random.gauss(620 + 90 * pasos, 160))
    long_resp = max(60, long_resp)

    if random.random() < perfil["p_err"]:
        error = True
        tipo_error = random.choice(TIPOS_ERROR_API)
        if tipo_error == "timeout":
            lat_llm = round(lat_llm + random.uniform(8, 12), 4)  # timeout largo
        tokens_completion = 0
        long_resp = 0
        respuesta_vacia = tipo_error in ("api_error",)

    # Fuera de dominio: a veces respuesta vacía o "no encontrado" aunque no haya error de API
    if categoria == "fuera_dominio" and not error and random.random() < 0.4:
        long_resp = random.randint(80, 180)

    lat_total = round(lat_emb + lat_ret + lat_llm + random.uniform(0.05, 0.2), 4)

    return {
        "id": _hash(query),
        "timestamp": ts.isoformat(),
        "query": query[:300],
        "categoria": categoria,
        "es_caso_limite": es_limite,
        "run_idx": run_idx,
        "modelo": "gpt-4o-mini",
        "fuente_datos": "simulado",
        "latencia_total_s": lat_total,
        "latencia_embedding_s": lat_emb,
        "latencia_retrieval_s": lat_ret,
        "latencia_llm_s": lat_llm,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "tokens_total": tokens_prompt + tokens_completion,
        "num_chunks": 4,
        "scores_similitud": scores,
        "score_similitud_top": scores[0],
        "score_similitud_promedio": round(sum(scores) / len(scores), 4),
        "fuentes": random.sample(FUENTES_DOCS, k=min(4, len(FUENTES_DOCS))),
        "herramientas_usadas": herramientas,
        "num_pasos": pasos,
        "longitud_respuesta": long_resp,
        "respuesta_vacia": respuesta_vacia,
        "error": error,
        "tipo_error": tipo_error,
    }


def _registro_adversarial(query, es_limite, ts) -> dict:
    """Consulta adversarial: bloqueada por la capa de seguridad antes del agente."""
    saneado = sanitizar_input(query)
    motivo = saneado.motivo or "prompt_injection_detectado"
    return {
        "id": _hash(query),
        "timestamp": ts.isoformat(),
        "query": query[:300],
        "categoria": "adversarial",
        "es_caso_limite": es_limite,
        "run_idx": 0,
        "modelo": "gpt-4o-mini",
        "fuente_datos": "simulado",
        "latencia_total_s": round(random.uniform(0.0008, 0.004), 4),
        "latencia_embedding_s": 0.0,
        "latencia_retrieval_s": 0.0,
        "latencia_llm_s": 0.0,
        "tokens_prompt": 0,
        "tokens_completion": 0,
        "tokens_total": 0,
        "num_chunks": 0,
        "scores_similitud": [],
        "score_similitud_top": 0.0,
        "score_similitud_promedio": 0.0,
        "fuentes": [],
        "herramientas_usadas": [],
        "num_pasos": 0,
        "longitud_respuesta": 0,
        "respuesta_vacia": False,
        "error": True,
        "tipo_error": f"bloqueado_{motivo}",
    }


def main() -> None:
    limpiar_log()
    ts = datetime(2026, 6, 30, 9, 0, 0)
    total = 0

    for (query, categoria, es_limite, consistencia) in DATASET:
        repeticiones = N_CONSISTENCIA if consistencia else 1
        for run_idx in range(repeticiones):
            if categoria == "adversarial":
                reg = _registro_adversarial(query, es_limite, ts)
            else:
                reg = _registro_normal(query, categoria, es_limite, run_idx, ts)
            registrar_metricas(reg)
            total += 1
            # Avanzar el reloj según la latencia + un pequeño intervalo entre queries
            ts += timedelta(seconds=reg["latencia_total_s"] + random.uniform(0.5, 2.5))

    print("=" * 60)
    print("  SIMULADOR DE MÉTRICAS — datos de demostración generados")
    print("=" * 60)
    print(f"  Registros generados : {total}")
    print(f"  Archivo             : {RUTA_LOG_DEFECTO}")
    print(f"  Semilla (reproducible): {SEED}")
    print('  Marca               : "fuente_datos": "simulado"')
    print("=" * 60)
    print("  Siguiente paso:")
    print("    python analisis_hallazgos.py     # análisis de hallazgos")
    print("    streamlit run dashboard.py       # dashboard visual")
    print("=" * 60)


if __name__ == "__main__":
    main()
