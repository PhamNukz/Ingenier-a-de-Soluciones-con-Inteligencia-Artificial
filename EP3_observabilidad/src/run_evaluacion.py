"""
RUNNER DE EVALUACIÓN REAL — EP3 Observabilidad
==============================================

Ejecuta TODO el dataset contra el agente RAG real (EP2), instrumentándolo con la
capa de observabilidad. Cada consulta genera un registro JSON en logs/metricas.jsonl.

Requisitos para la corrida REAL:
  1. Dependencias instaladas:  pip install -r requirements.txt
  2. Base vectorial de EP2 construida (EP2_agente_portuario/chroma_db).
  3. Variables de entorno en .env:  GITHUB_TOKEN y GITHUB_BASE_URL.

Uso:
    cd EP3_observabilidad/src
    python run_evaluacion.py                 # corre todo el dataset
    python run_evaluacion.py --limpiar       # borra el log previo antes de correr

Si NO tienes token/dependencias, usa el simulador para poblar el dashboard:
    python simular_metricas.py
"""

import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from dataset_queries import queries_planas, N_CONSISTENCIA
from observabilidad.instrumentacion import medir_consulta, medir_consistencia
from observabilidad.logger_json import limpiar_log, RUTA_LOG_DEFECTO


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluación de observabilidad EP3")
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Borra logs/metricas.jsonl antes de la corrida.",
    )
    args = parser.parse_args()

    if args.limpiar:
        limpiar_log()
        print(f"🧹 Log previo eliminado: {RUTA_LOG_DEFECTO}")

    dataset = queries_planas()
    print("=" * 60)
    print(f"  EVALUACIÓN DE OBSERVABILIDAD — {len(dataset)} consultas")
    print("=" * 60)

    t0 = time.time()
    total_ejecuciones = 0

    for i, item in enumerate(dataset, 1):
        q = item["query"]
        cat = item["categoria"]
        print(f"\n[{i}/{len(dataset)}] ({cat}) {q[:60]}...")

        if item["consistencia"]:
            registros = medir_consistencia(
                q,
                n=N_CONSISTENCIA,
                categoria=cat,
                es_caso_limite=item["es_caso_limite"],
            )
            total_ejecuciones += len(registros)
            lat = sum(r["latencia_total_s"] for r in registros) / len(registros)
            print(f"    Consistencia x{N_CONSISTENCIA} | latencia media {lat:.2f}s")
        else:
            r = medir_consulta(
                q,
                categoria=cat,
                es_caso_limite=item["es_caso_limite"],
            )
            total_ejecuciones += 1
            estado = "ERROR" if r["error"] else "OK"
            print(
                f"    {estado} | total {r['latencia_total_s']:.2f}s | "
                f"LLM {r['latencia_llm_s']:.2f}s | tokens {r['tokens_total']} | "
                f"sim_top {r['score_similitud_top']:.2f} | "
                f"tools {r['herramientas_usadas']}"
            )

    dur = time.time() - t0
    print("\n" + "=" * 60)
    print(f"✅ Evaluación completa: {total_ejecuciones} ejecuciones en {dur:.1f}s")
    print(f"   Log generado: {RUTA_LOG_DEFECTO}")
    print(f"   Analiza con:  python analisis_hallazgos.py")
    print(f"   Dashboard:    streamlit run dashboard.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
