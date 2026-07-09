"""
CAPA DE INSTRUMENTACIÓN — EP3 Observabilidad (IE1, IE2, IE3)
============================================================

Envuelve el agente RAG existente (EP2) con un wrapper que mide, por cada consulta,
las 5 familias de métricas exigidas y registra todo en logs JSON estructurados:

  1. PRECISIÓN / RELEVANCIA  → scores de similitud de los chunks (ChromaDB).
  2. LATENCIA                → total y desglosada: embedding → retrieval → LLM.
  3. CONSISTENCIA            → helper para correr N veces la misma query y medir
                               la variación de respuesta/tokens/chunks.
  4. FRECUENCIA DE ERRORES   → fallos de la API, timeouts, respuestas vacías,
                               consultas bloqueadas por seguridad.
  5. USO DE RECURSOS         → tokens (prompt + completion) y nº de chunks.

Diseño: un CALLBACK HANDLER de LangChain captura automáticamente el uso de tokens
y la latencia de cada llamada al LLM dentro del bucle ReAct, sin tocar el código de
EP2. El wrapper `medir_consulta` orquesta seguridad + retrieval instrumentado +
ejecución del agente + ensamblado del registro.
"""

import hashlib
import os
import sys
from datetime import datetime
from time import perf_counter

from langchain_core.callbacks.base import BaseCallbackHandler

# Importes locales del paquete de observabilidad
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from observabilidad.logger_json import registrar_metricas
from observabilidad.seguridad import (
    sanitizar_input,
    anonimizar_pii,
    limitador_global,
)

# Ruta al código del agente EP2 (se importa de forma perezosa para no exigir el
# stack pesado de LangChain cuando solo se usa el dashboard o el simulador).
_EP2_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "EP2_agente_portuario",
    "src",
)

# Carga del token (.env con GITHUB_TOKEN) buscando en ubicaciones sensatas: la
# carpeta de EP3 y la raíz del repo (donde el agente EP2 también lo espera). Así
# la corrida real funciona sin importar en cuál de las dos se coloque el .env.
from dotenv import load_dotenv

_EP3_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_REPO_ROOT = os.path.dirname(_EP3_ROOT)
for _ruta_env in (os.path.join(_EP3_ROOT, ".env"), os.path.join(_REPO_ROOT, ".env")):
    if os.path.exists(_ruta_env):
        load_dotenv(dotenv_path=_ruta_env)  # override=False: gana el primero encontrado


# ──────────────────────────────────────────────────────────────────────────────
# CONTADOR DE TOKENS DE RESPALDO (cuando la API no devuelve token_usage)
# ──────────────────────────────────────────────────────────────────────────────
# GitHub Models no siempre incluye token_usage en la respuesta; en ese caso
# contamos los tokens localmente con tiktoken (codificación de gpt-4o) para no
# perder la métrica de uso de recursos (IE2). Si tiktoken no está instalado, se
# usa la aproximación estándar de ~4 caracteres por token.
_encoder = None


def _contar_tokens(texto: str) -> int:
    global _encoder
    if not texto:
        return 0
    if _encoder is None:
        try:
            import tiktoken

            try:
                _encoder = tiktoken.encoding_for_model("gpt-4o-mini")
            except Exception:  # noqa: BLE001
                _encoder = tiktoken.get_encoding("o200k_base")
        except Exception:  # noqa: BLE001 — tiktoken ausente
            _encoder = False
    if _encoder is False:
        return max(1, len(texto) // 4)
    return len(_encoder.encode(texto))


# ──────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER — captura tokens y latencia del LLM (IE2, uso de recursos)
# ──────────────────────────────────────────────────────────────────────────────
class MetricasCallbackHandler(BaseCallbackHandler):
    """
    Handler de LangChain que acumula métricas de TODAS las llamadas al LLM que el
    agente ReAct realiza durante una única consulta (suele hacer varias: una por
    paso Thought/Action). Es reutilizable creando una instancia por consulta.
    """

    def __init__(self):
        self.tokens_prompt = 0
        self.tokens_completion = 0
        self.tokens_total = 0
        self.tokens_estimados = False  # True si se usó el respaldo tiktoken
        self.llamadas_llm = 0
        self.latencia_llm_s = 0.0
        self.errores_llm = 0
        self._t_inicio_llm = None
        self._prompts_actuales = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._t_inicio_llm = perf_counter()
        self._prompts_actuales = list(prompts or [])

    def on_llm_end(self, response, **kwargs):
        # Latencia de esta llamada al LLM
        if self._t_inicio_llm is not None:
            self.latencia_llm_s += perf_counter() - self._t_inicio_llm
            self._t_inicio_llm = None
        self.llamadas_llm += 1

        # Uso de tokens. GitHub Models / OpenAI devuelven el desglose en
        # llm_output["token_usage"]. Se contemplan claves alternativas por robustez.
        llm_output = getattr(response, "llm_output", None) or {}
        uso = llm_output.get("token_usage") or llm_output.get("usage") or {}
        if not uso:
            # Algunos backends ponen el usage en generation_info
            try:
                gen = response.generations[0][0]
                info = getattr(gen, "generation_info", None) or {}
                uso = info.get("token_usage") or info.get("usage") or {}
            except (AttributeError, IndexError):
                uso = {}

        p = uso.get("prompt_tokens", 0) or 0
        c = uso.get("completion_tokens", 0) or 0

        if not p and not c:
            # Respaldo con tiktoken: la API no reportó uso → se cuenta localmente.
            p = sum(_contar_tokens(pr) for pr in self._prompts_actuales)
            try:
                textos = [g.text for lista in response.generations for g in lista]
            except (AttributeError, TypeError):
                textos = []
            c = sum(_contar_tokens(t) for t in textos)
            self.tokens_estimados = True

        self.tokens_prompt += p
        self.tokens_completion += c
        total = uso.get("total_tokens", 0) or 0
        self.tokens_total += total if total else (p + c)
        self._prompts_actuales = []

    def on_llm_error(self, error, **kwargs):
        self.errores_llm += 1
        self._t_inicio_llm = None


# ──────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────────────────────────────────────────
def _hash_consulta(texto: str) -> str:
    """ID corto y estable para agrupar la misma consulta entre corridas."""
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]


def _clasificar_error(salida: str) -> str | None:
    """Detecta respuestas-error devueltas como texto por las herramientas EP2."""
    if not salida:
        return "respuesta_vacia"
    bajo = salida.lower()
    if "tiempo de espera" in bajo or "timeout" in bajo:
        return "timeout"
    if "error al consultar" in bajo or "error en la evaluaci" in bajo:
        return "error_herramienta"
    if "no se pudo conectar" in bajo or "connection" in bajo:
        return "error_conexion"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# WRAPPER PRINCIPAL — instrumenta una consulta de punta a punta
# ──────────────────────────────────────────────────────────────────────────────
def medir_consulta(
    pregunta: str,
    *,
    categoria: str = "en_dominio",
    es_caso_limite: bool = False,
    run_idx: int = 0,
    medir_rag: bool = True,
    persistir: bool = True,
) -> dict:
    """
    Ejecuta UNA consulta contra el agente EP2 midiendo todas las métricas y
    registrando el resultado en el log JSON estructurado.

    Args:
        pregunta: consulta del usuario.
        categoria: 'en_dominio' | 'fuera_dominio' | 'ambigua' | 'adversarial'.
        es_caso_limite: marca casos límite del dataset.
        run_idx: índice de repetición (para análisis de consistencia).
        medir_rag: si True, mide el retrieval instrumentado (scores de similitud).
        persistir: si True, escribe el registro en logs/metricas.jsonl.

    Returns:
        El registro de métricas (dict) de esta ejecución.
    """
    timestamp = datetime.now().isoformat()
    consulta_hash = _hash_consulta(pregunta.strip().lower())

    registro = {
        "id": consulta_hash,
        "timestamp": timestamp,
        "query": anonimizar_pii(pregunta.strip())[:300],  # privacidad: trunc + PII
        "categoria": categoria,
        "es_caso_limite": es_caso_limite,
        "run_idx": run_idx,
        "modelo": "gpt-4o-mini",
        "fuente_datos": "real",
        "latencia_total_s": 0.0,
        "latencia_embedding_s": 0.0,
        "latencia_retrieval_s": 0.0,
        "latencia_llm_s": 0.0,
        "tokens_prompt": 0,
        "tokens_completion": 0,
        "tokens_total": 0,
        "tokens_estimados": False,
        "num_chunks": 0,
        "scores_similitud": [],
        "score_similitud_top": 0.0,
        "score_similitud_promedio": 0.0,
        "fuentes": [],
        "herramientas_usadas": [],
        "num_pasos": 0,
        "longitud_respuesta": 0,
        "respuesta_vacia": False,
        "error": False,
        "tipo_error": None,
    }

    t_total_inicio = perf_counter()

    # 1. SEGURIDAD: rate limiting (IE6)
    if not limitador_global.permitir():
        registro["error"] = True
        registro["tipo_error"] = "rate_limit_local"
        registro["latencia_total_s"] = round(perf_counter() - t_total_inicio, 4)
        if persistir:
            registrar_metricas(registro)
        return registro

    # 2. SEGURIDAD: sanitización + prompt injection (IE6)
    saneado = sanitizar_input(pregunta)
    if saneado.bloqueado:
        registro["error"] = True
        registro["tipo_error"] = f"bloqueado_{saneado.motivo}"
        registro["latencia_total_s"] = round(perf_counter() - t_total_inicio, 4)
        if persistir:
            registrar_metricas(registro)
        return registro

    pregunta_limpia = saneado.texto_limpio

    # 3. PRECISIÓN/RELEVANCIA + latencia de embedding/retrieval (IE1)
    if medir_rag:
        try:
            from observabilidad.retrieval_metrics import medir_retrieval

            rag = medir_retrieval(pregunta_limpia, k=4)
            registro.update(
                {
                    "latencia_embedding_s": rag["latencia_embedding_s"],
                    "latencia_retrieval_s": rag["latencia_retrieval_s"],
                    "num_chunks": rag["num_chunks"],
                    "scores_similitud": rag["scores_similitud"],
                    "score_similitud_top": rag["score_similitud_top"],
                    "score_similitud_promedio": rag["score_similitud_promedio"],
                    "fuentes": rag["fuentes"],
                }
            )
        except Exception as e:  # noqa: BLE001 — el retrieval no debe tumbar la medición
            registro["tipo_error"] = f"retrieval_metrica_fallida:{type(e).__name__}"

    # 4. EJECUCIÓN DEL AGENTE con callback de tokens/latencia LLM (IE2)
    handler = MetricasCallbackHandler()
    respuesta = ""
    pasos = []
    try:
        sys.path.append(_EP2_SRC)
        from agent import obtener_agente  # type: ignore
        from memory.long_term import recuperar_memoria_larga, guardar_en_memoria_larga  # type: ignore

        agente = obtener_agente()
        memoria_larga = recuperar_memoria_larga(pregunta_limpia, k=3)

        resultado = agente.invoke(
            {"input": pregunta_limpia, "memoria_larga": memoria_larga},
            config={"callbacks": [handler]},
        )

        respuesta = resultado.get("output", "") or ""
        pasos = resultado.get("intermediate_steps", []) or []

        # Persistencia en memoria de largo plazo (igual que EP2)
        if len(respuesta) > 80:
            resumen = f"Consulta: {pregunta_limpia[:200]}\nRespuesta: {respuesta[:400]}"
            guardar_en_memoria_larga(resumen, tipo="conversacion")

        # Métricas derivadas de la ejecución
        registro["herramientas_usadas"] = [a.tool for a, _ in pasos]
        registro["num_pasos"] = len(pasos)
        registro["longitud_respuesta"] = len(respuesta)
        registro["respuesta_vacia"] = len(respuesta.strip()) == 0
        registro["tokens_prompt"] = handler.tokens_prompt
        registro["tokens_completion"] = handler.tokens_completion
        registro["tokens_total"] = handler.tokens_total
        registro["tokens_estimados"] = handler.tokens_estimados
        registro["latencia_llm_s"] = round(handler.latencia_llm_s, 4)

        # Frecuencia de errores (IE1): clasifica fallos blandos
        tipo_err = _clasificar_error(respuesta)
        if registro["respuesta_vacia"]:
            registro["error"] = True
            registro["tipo_error"] = "respuesta_vacia"
        elif handler.errores_llm > 0:
            registro["error"] = True
            registro["tipo_error"] = "api_error"
        elif tipo_err:
            registro["error"] = True
            registro["tipo_error"] = tipo_err

    except Exception as e:  # noqa: BLE001 — cualquier fallo se registra como error duro
        registro["error"] = True
        nombre = type(e).__name__
        if "timeout" in nombre.lower() or "timeout" in str(e).lower():
            registro["tipo_error"] = "timeout"
        elif "rate" in str(e).lower() or "429" in str(e):
            registro["tipo_error"] = "rate_limit_api"
        else:
            registro["tipo_error"] = f"excepcion:{nombre}"

    # 5. Latencia total y persistencia
    registro["latencia_total_s"] = round(perf_counter() - t_total_inicio, 4)

    if persistir:
        registrar_metricas(registro)

    # Campos ephemeros para el llamador (UI del chat) — no se persisten en el
    # log para no romper el esquema plano que lee el dashboard.
    registro["respuesta"] = respuesta
    registro["pasos"] = pasos

    return registro


def medir_consistencia(
    pregunta: str,
    n: int = 5,
    *,
    categoria: str = "en_dominio",
    es_caso_limite: bool = False,
) -> list[dict]:
    """
    Mide la CONSISTENCIA ejecutando la misma consulta `n` veces. Cada corrida se
    registra con su `run_idx`; el análisis posterior (analisis_hallazgos.py)
    calcula la variación de longitud de respuesta, tokens y conjunto de chunks.

    Returns:
        Lista de los `n` registros de métricas.
    """
    return [
        medir_consulta(
            pregunta,
            categoria=categoria,
            es_caso_limite=es_caso_limite,
            run_idx=i,
        )
        for i in range(n)
    ]
