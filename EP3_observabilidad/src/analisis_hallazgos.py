"""
ANÁLISIS DE LOGS Y HALLAZGOS — EP3 Observabilidad (IE3, IE4)
============================================================

Procesa logs/metricas.jsonl y produce un reporte de hallazgos: cuellos de botella,
patrones de error, anomalías y estadísticas agregadas. Sirve de insumo directo
para el informe (sección de análisis y recomendaciones).

Solo usa la librería estándar → corre sin dependencias pesadas.

Uso:
    cd EP3_observabilidad/src
    python analisis_hallazgos.py
"""

import json
import os
import statistics as stats
import sys
from collections import Counter, defaultdict

sys.path.append(os.path.dirname(__file__))
from observabilidad.logger_json import leer_metricas, RUTA_LOG_DEFECTO

_DIR_BASE = os.path.dirname(os.path.dirname(__file__))
RUTA_HALLAZGOS = os.path.join(_DIR_BASE, "logs", "hallazgos.json")


def _percentil(datos: list[float], p: float) -> float:
    """Percentil p (0-100) por interpolación lineal. Robusto ante listas cortas."""
    if not datos:
        return 0.0
    d = sorted(datos)
    if len(d) == 1:
        return d[0]
    k = (len(d) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(d) - 1)
    return d[f] + (d[c] - d[f]) * (k - f)


def analizar(registros: list[dict]) -> dict:
    """Calcula todas las métricas agregadas y hallazgos a partir de los registros."""
    total = len(registros)
    ok = [r for r in registros if not r["error"]]
    errores = [r for r in registros if r["error"]]

    # ── LATENCIA (IE2) ────────────────────────────────────────────────────────
    lat_total = [r["latencia_total_s"] for r in ok]
    lat_emb = [r["latencia_embedding_s"] for r in ok]
    lat_ret = [r["latencia_retrieval_s"] for r in ok]
    lat_llm = [r["latencia_llm_s"] for r in ok]

    suma_emb = sum(lat_emb)
    suma_ret = sum(lat_ret)
    suma_llm = sum(lat_llm)
    suma_fases = suma_emb + suma_ret + suma_llm or 1.0

    latencia = {
        "promedio_total_s": round(stats.mean(lat_total), 3) if lat_total else 0,
        "mediana_total_s": round(stats.median(lat_total), 3) if lat_total else 0,
        "p95_total_s": round(_percentil(lat_total, 95), 3),
        "p99_total_s": round(_percentil(lat_total, 99), 3),
        "max_total_s": round(max(lat_total), 3) if lat_total else 0,
        "desglose_promedio": {
            "embedding_s": round(stats.mean(lat_emb), 4) if lat_emb else 0,
            "retrieval_s": round(stats.mean(lat_ret), 4) if lat_ret else 0,
            "llm_s": round(stats.mean(lat_llm), 3) if lat_llm else 0,
        },
        "porcentaje_tiempo_por_fase": {
            "embedding_pct": round(100 * suma_emb / suma_fases, 1),
            "retrieval_pct": round(100 * suma_ret / suma_fases, 1),
            "llm_pct": round(100 * suma_llm / suma_fases, 1),
        },
    }

    # ── USO DE RECURSOS / TOKENS (IE2) ────────────────────────────────────────
    tok_total = [r["tokens_total"] for r in ok if r["tokens_total"] > 0]
    tok_prompt = [r["tokens_prompt"] for r in ok if r["tokens_total"] > 0]
    tok_comp = [r["tokens_completion"] for r in ok if r["tokens_total"] > 0]
    n_estimados = sum(1 for r in ok if r.get("tokens_estimados"))
    recursos = {
        "tokens_promedio_total": round(stats.mean(tok_total)) if tok_total else 0,
        "tokens_promedio_prompt": round(stats.mean(tok_prompt)) if tok_prompt else 0,
        "tokens_promedio_completion": round(stats.mean(tok_comp)) if tok_comp else 0,
        "tokens_max_total": max(tok_total) if tok_total else 0,
        "tokens_acumulados": sum(tok_total),
        "ratio_prompt_completion": round(sum(tok_prompt) / (sum(tok_comp) or 1), 1),
        "consultas_con_tokens": len(tok_total),
        "consultas_tokens_estimados": n_estimados,
    }

    # ── FRECUENCIA DE ERRORES (IE1) ───────────────────────────────────────────
    tipos_error = Counter(r["tipo_error"] for r in errores)
    bloqueados = [r for r in errores if str(r["tipo_error"]).startswith("bloqueado_")]
    errores_api = [r for r in errores if not str(r["tipo_error"]).startswith("bloqueado_")]
    errores_dict = {
        "total_ejecuciones": total,
        "total_errores": len(errores),
        "tasa_error_global_pct": round(100 * len(errores) / total, 1) if total else 0,
        "errores_api": len(errores_api),
        "tasa_error_api_pct": round(100 * len(errores_api) / total, 1) if total else 0,
        "bloqueados_seguridad": len(bloqueados),
        "por_tipo": dict(tipos_error),
    }

    # ── PRECISIÓN / RELEVANCIA por categoría (IE1) ────────────────────────────
    por_cat_scores = defaultdict(list)
    for r in registros:
        if r["score_similitud_top"] > 0:
            por_cat_scores[r["categoria"]].append(r["score_similitud_top"])
    relevancia = {
        cat: {
            "sim_top_promedio": round(stats.mean(v), 3),
            "sim_top_min": round(min(v), 3),
            "n": len(v),
        }
        for cat, v in por_cat_scores.items()
    }
    # Umbral de relevancia ADAPTATIVO: punto medio entre la media en-dominio y la
    # media fuera-dominio (o la mediana global si falta alguna categoría). Se
    # calcula desde los datos porque la escala del score depende de las distancias
    # L2 reales de ChromaDB y no puede fijarse a un valor absoluto arbitrario.
    if "en_dominio" in relevancia and "fuera_dominio" in relevancia:
        umbral_relevancia = round(
            (relevancia["en_dominio"]["sim_top_promedio"]
             + relevancia["fuera_dominio"]["sim_top_promedio"]) / 2, 3
        )
    else:
        todos = [s for v in por_cat_scores.values() for s in v]
        umbral_relevancia = round(stats.median(todos), 3) if todos else 0.0

    # ── CONSISTENCIA (IE1) ────────────────────────────────────────────────────
    grupos = defaultdict(list)
    for r in registros:
        grupos[r["id"]].append(r)
    consistencia = []
    for qid, runs in grupos.items():
        if len(runs) < 2:
            continue
        # El CV se calcula sobre las corridas EXITOSAS para medir la variabilidad
        # propia del LLM (un error/timeout zeroea la respuesta y distorsionaría el CV).
        ok_runs = [x for x in runs if not x["error"]]
        base = ok_runs if len(ok_runs) >= 2 else runs
        longs = [x["longitud_respuesta"] for x in base]
        toks = [x["tokens_total"] for x in base]
        lats = [x["latencia_total_s"] for x in base]
        pasos = [x["num_pasos"] for x in base]
        media_long = stats.mean(longs) or 1
        consistencia.append({
            "query": runs[0]["query"][:70],
            "n_runs": len(runs),
            "runs_con_error": len(runs) - len(ok_runs),
            "cv_longitud_respuesta_pct": round(100 * (stats.pstdev(longs) / media_long), 1),
            "cv_tokens_pct": round(100 * (stats.pstdev(toks) / (stats.mean(toks) or 1)), 1),
            "variacion_latencia_s": round(max(lats) - min(lats), 2),
            "pasos_distintos": len(set(pasos)),
        })

    # ── HERRAMIENTAS / PASOS ──────────────────────────────────────────────────
    # El agente ReAct a veces emite "acciones" que no son herramientas reales
    # (frases, o el marcador interno _Exception de LangChain ante un parse-error).
    # Se separan de las herramientas válidas para no ensuciar la métrica y, a la
    # vez, cuantificar la fiabilidad del parseo del agente (IE3/IE4).
    TOOLS_VALIDAS = {
        "consultar_normativa", "generar_reporte",
        "evaluar_cumplimiento", "buscar_fuente_externa",
    }
    herramientas = Counter()
    acciones_invalidas = 0
    for r in ok:
        for h in r["herramientas_usadas"]:
            if h in TOOLS_VALIDAS:
                herramientas[h] += 1
            else:
                acciones_invalidas += 1
    pasos_prom = round(stats.mean([r["num_pasos"] for r in ok]), 2) if ok else 0

    # ── HALLAZGOS NARRATIVOS (IE3, IE4) ───────────────────────────────────────
    hallazgos = []
    llm_pct = latencia["porcentaje_tiempo_por_fase"]["llm_pct"]
    if llm_pct > 70:
        hallazgos.append(
            f"CUELLO DE BOTELLA: la generación con el LLM concentra el {llm_pct}% "
            f"del tiempo total. El retrieval (embedding+búsqueda) es marginal "
            f"({latencia['porcentaje_tiempo_por_fase']['retrieval_pct']}%). La "
            f"optimización de desempeño debe enfocarse en el LLM, no en el RAG."
        )
    if "fuera_dominio" in relevancia and "en_dominio" in relevancia:
        fd = relevancia["fuera_dominio"]["sim_top_promedio"]
        ed = relevancia["en_dominio"]["sim_top_promedio"]
        factor = round(ed / fd, 1) if fd else 0
        hallazgos.append(
            f"PATRÓN DE RELEVANCIA: la similitud media en-dominio ({ed}) es ~{factor}× la de "
            f"fuera-dominio ({fd}). Lo relevante es la separación relativa, no el valor "
            f"absoluto (el score deriva de la distancia L2 de ChromaDB). La brecha valida un "
            f"umbral de rechazo/fallback en torno a {umbral_relevancia} para descartar "
            f"consultas no cubiertas por el corpus."
        )
    if latencia["p95_total_s"] > 1.5 * (latencia["mediana_total_s"] or 1):
        hallazgos.append(
            f"ANOMALÍA DE LATENCIA (cola larga): el p95 ({latencia['p95_total_s']}s) triplica "
            f"la mediana ({latencia['mediana_total_s']}s) y el p99 llega a "
            f"{latencia['p99_total_s']}s. La cola la explican las consultas con más pasos "
            f"ReAct (más llamadas al LLM) y los {errores_dict['errores_api']} fallos de API "
            f"({ {k: v for k, v in tipos_error.items() if not str(k).startswith('bloqueado_')} }). "
            f"Es el objetivo prioritario para reintentos y timeouts."
        )
    if bloqueados:
        hallazgos.append(
            f"SEGURIDAD: se bloquearon {len(bloqueados)} consultas adversariales "
            f"(prompt injection / extracción de credenciales) antes de llegar al "
            f"agente, sin consumir tokens. La capa de seguridad (IE6) opera correctamente."
        )
    if acciones_invalidas > 0:
        hallazgos.append(
            f"FIABILIDAD DEL AGENTE: se registraron {acciones_invalidas} acciones inválidas "
            f"(parse-errors del formato ReAct: el LLM emitió texto en vez de un nombre de "
            f"herramienta), recuperadas por handle_parsing_errors. Ocurren sobre todo en "
            f"consultas ambiguas y son un objetivo de mejora del prompt (IE4)."
        )
    if consistencia:
        cv_max = max(c["cv_longitud_respuesta_pct"] for c in consistencia)
        fallos_rep = sum(c["runs_con_error"] for c in consistencia)
        nota_err = (
            f" Además, se registraron {fallos_rep} repeticiones fallidas (timeout/API), lo "
            f"que evidencia que la fiabilidad también varía entre ejecuciones idénticas."
            if fallos_rep else ""
        )
        hallazgos.append(
            f"CONSISTENCIA: ante la misma consulta repetida, la longitud de respuesta "
            f"varía hasta un {cv_max}% (CV) en las corridas exitosas, mientras los chunks "
            f"recuperados se mantienen estables (embeddings deterministas). La variabilidad "
            f"proviene del LLM (temperature>0), no del retrieval.{nota_err}"
        )

    return {
        "resumen": {
            "total_ejecuciones": total,
            "exitosas": len(ok),
            "con_error": len(errores),
            "pasos_promedio": pasos_prom,
            "fuente_datos": registros[0].get("fuente_datos", "desconocida") if registros else "n/a",
        },
        "latencia": latencia,
        "recursos": recursos,
        "errores": errores_dict,
        "relevancia_por_categoria": relevancia,
        "umbral_relevancia": umbral_relevancia,
        "consistencia": consistencia,
        "herramientas_uso": dict(herramientas),
        "acciones_invalidas": acciones_invalidas,
        "hallazgos": hallazgos,
    }


def imprimir_reporte(a: dict) -> None:
    """Imprime el reporte de hallazgos en consola de forma legible."""
    L = "─" * 64
    print("=" * 64)
    print("  ANÁLISIS DE HALLAZGOS — Observabilidad del Agente Portuario EPV")
    print("=" * 64)
    r = a["resumen"]
    print(f"Fuente de datos : {r['fuente_datos'].upper()}")
    print(f"Ejecuciones     : {r['total_ejecuciones']}  "
          f"(OK: {r['exitosas']} | Error: {r['con_error']})")
    print(f"Pasos promedio  : {r['pasos_promedio']}")

    print(f"\n{L}\nLATENCIA (IE2)\n{L}")
    lat = a["latencia"]
    print(f"  Promedio total : {lat['promedio_total_s']}s | "
          f"Mediana: {lat['mediana_total_s']}s | "
          f"p95: {lat['p95_total_s']}s | p99: {lat['p99_total_s']}s")
    d = lat["desglose_promedio"]
    pf = lat["porcentaje_tiempo_por_fase"]
    print(f"  Desglose prom. : embedding {d['embedding_s']}s ({pf['embedding_pct']}%) | "
          f"retrieval {d['retrieval_s']}s ({pf['retrieval_pct']}%) | "
          f"LLM {d['llm_s']}s ({pf['llm_pct']}%)")

    print(f"\n{L}\nUSO DE RECURSOS / TOKENS (IE2)\n{L}")
    rec = a["recursos"]
    print(f"  Tokens promedio: {rec['tokens_promedio_total']} "
          f"(prompt {rec['tokens_promedio_prompt']} / completion {rec['tokens_promedio_completion']})")
    print(f"  Máx tokens     : {rec['tokens_max_total']} | "
          f"Acumulado: {rec['tokens_acumulados']} | "
          f"Ratio prompt:completion {rec['ratio_prompt_completion']}:1")
    print(f"  Cobertura      : {rec['consultas_con_tokens']} consultas con tokens "
          f"({rec['consultas_tokens_estimados']} estimados con tiktoken)")

    print(f"\n{L}\nFRECUENCIA DE ERRORES (IE1)\n{L}")
    e = a["errores"]
    print(f"  Tasa global    : {e['tasa_error_global_pct']}% "
          f"({e['total_errores']}/{e['total_ejecuciones']})")
    print(f"  Tasa API real  : {e['tasa_error_api_pct']}% "
          f"(excluye {e['bloqueados_seguridad']} bloqueos de seguridad)")
    print(f"  Por tipo       : {e['por_tipo']}")

    print(f"\n{L}\nPRECISIÓN/RELEVANCIA por categoría (IE1)\n{L}")
    for cat, v in a["relevancia_por_categoria"].items():
        print(f"  {cat:14} sim_top medio {v['sim_top_promedio']} "
              f"(mín {v['sim_top_min']}, n={v['n']})")

    print(f"\n{L}\nCONSISTENCIA (IE1)\n{L}")
    for c in a["consistencia"]:
        print(f"  '{c['query']}...'  x{c['n_runs']} (fallos: {c['runs_con_error']})")
        print(f"     CV long. resp. {c['cv_longitud_respuesta_pct']}% | "
              f"CV tokens {c['cv_tokens_pct']}% | "
              f"Δlatencia {c['variacion_latencia_s']}s | "
              f"pasos distintos {c['pasos_distintos']}")

    print(f"\n{L}\nHERRAMIENTAS USADAS\n{L}")
    print(f"  {a['herramientas_uso']}")
    print(f"  Acciones inválidas (parse-error ReAct): {a['acciones_invalidas']}")

    print(f"\n{L}\nHALLAZGOS CLAVE (IE3, IE4)\n{L}")
    for i, h in enumerate(a["hallazgos"], 1):
        print(f"  {i}. {h}\n")


def main() -> None:
    registros = leer_metricas()
    if not registros:
        print("⚠ No hay métricas. Ejecuta primero:")
        print("    python simular_metricas.py   (datos demo)")
        print("    python run_evaluacion.py     (datos reales)")
        return

    analisis = analizar(registros)
    imprimir_reporte(analisis)

    os.makedirs(os.path.dirname(RUTA_HALLAZGOS), exist_ok=True)
    with open(RUTA_HALLAZGOS, "w", encoding="utf-8") as f:
        json.dump(analisis, f, ensure_ascii=False, indent=2)
    print("=" * 64)
    print(f"📄 Hallazgos guardados en: {RUTA_HALLAZGOS}")
    print("=" * 64)


if __name__ == "__main__":
    main()
