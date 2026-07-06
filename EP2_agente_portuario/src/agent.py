"""
AGENTE PRINCIPAL — Agente Portuario EPV v2.0
Implementa un agente ReAct (Reasoning + Acting) con LangChain que integra:
  - 4 herramientas: consultar_normativa, generar_reporte, evaluar_cumplimiento,
                    buscar_fuente_externa (Wikipedia ES — fuente externa en tiempo real)
  - Memoria de corto plazo: ConversationBufferWindowMemory (últimas 8 interacciones)
  - Memoria de largo plazo: ChromaDB semántico (recuperación entre sesiones)
  - Planificación autónoma con múltiples pasos y condiciones cambiantes
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from tools.consulta_tool import consultar_normativa
from tools.escritura_tool import generar_reporte
from tools.razonamiento_tool import evaluar_cumplimiento
from tools.busqueda_externa_tool import buscar_fuente_externa
from memory.short_term import crear_memoria_corto_plazo
from memory.long_term import guardar_en_memoria_larga, recuperar_memoria_larga

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

# ──────────────────────────────────────────────────────────────────────────────
# PROMPT REACT — Define el comportamiento del agente
# Variables requeridas: {tools}, {tool_names}, {input}, {agent_scratchpad}
# Variables de memoria: {chat_history}, {memoria_larga}
# ──────────────────────────────────────────────────────────────────────────────
REACT_PROMPT = PromptTemplate.from_template("""
Eres el Agente Portuario EPV, un asistente inteligente y autónomo especializado en normativas,
operaciones y seguridad del Puerto de Valparaíso (EPV). Resuelves tareas complejas de forma
independiente, usando tus herramientas de forma estratégica y secuenciada según cada situación.

════════════════════════════════════════════════════════════
CONTEXTO HISTÓRICO (sesiones anteriores):
{memoria_larga}

HISTORIAL DE CONVERSACIÓN ACTUAL:
{chat_history}
════════════════════════════════════════════════════════════

HERRAMIENTAS DISPONIBLES:
{tools}

NOMBRES DE HERRAMIENTAS DISPONIBLES: {tool_names}

════════════════════════════════════════════════════════════
INSTRUCCIONES DE PLANIFICACIÓN Y RAZONAMIENTO:

Debes razonar paso a paso antes de actuar. Sigue SIEMPRE este formato ReAct:

Thought: [Analiza la tarea. ¿Qué necesita el usuario? ¿Qué herramienta es más adecuada? ¿Necesito más de un paso?]
Action: [nombre_exacto_de_la_herramienta]
Action Input: [input preciso para la herramienta]
Observation: [resultado que recibirás de la herramienta]
... (repite Thought/Action/Observation hasta tener toda la información necesaria)
Thought: Tengo suficiente información para dar una respuesta completa y fundamentada.
Final Answer: [Respuesta final clara, en español, bien estructurada y citando fuentes si aplica]

REGLAS DE PLANIFICACIÓN:
- Si la tarea es simple → usa 1 herramienta directamente
- Si la tarea requiere consultar Y evaluar → usa consultar_normativa PRIMERO, luego evaluar_cumplimiento
- Si la tarea requiere consultar Y documentar → usa consultar_normativa PRIMERO, luego generar_reporte
- Si el usuario pide un reporte de un incidente → usa evaluar_cumplimiento PRIMERO para analizar, luego generar_reporte
- Si el usuario pregunta sobre normativas INTERNACIONALES (convenios OIT, SOLAS, MARPOL, ISO, etc.)
  o quiere contexto externo que complemente la normativa EPV → usa buscar_fuente_externa
- Si la tarea requiere normativa interna EPV + contexto internacional → usa consultar_normativa PRIMERO,
  luego buscar_fuente_externa para enriquecer la respuesta
- Máximo 6 pasos por tarea. Si no llegas a una respuesta en 6 pasos, sintetiza con lo que tienes.
- Siempre responde en español claro y técnico.
════════════════════════════════════════════════════════════

TAREA ACTUAL: {input}

{agent_scratchpad}
""")

# ──────────────────────────────────────────────────────────────────────────────
# INSTANCIAS GLOBALES (singleton para reutilizar entre llamadas)
# ──────────────────────────────────────────────────────────────────────────────
_executor: AgentExecutor | None = None
_memoria_corto_plazo = None


def obtener_agente() -> AgentExecutor:
    """
    Retorna la instancia del AgentExecutor (singleton).
    Crea el agente la primera vez que se llama.
    """
    global _executor, _memoria_corto_plazo

    if _executor is None:
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("GITHUB_TOKEN"),
            base_url=os.getenv("GITHUB_BASE_URL"),
            temperature=0.2,
            # Mejora EP3→EFT: reintentos con backoff exponencial (SDK OpenAI) ante
            # 429/503 del free tier, y timeout para cortar la cola de latencia p95.
            max_retries=5,
            timeout=45,
        )

        herramientas = [
            consultar_normativa,
            generar_reporte,
            evaluar_cumplimiento,
            buscar_fuente_externa,      # Fuente externa — Wikipedia ES en tiempo real
        ]

        _memoria_corto_plazo = crear_memoria_corto_plazo(k=8)

        agent = create_react_agent(
            llm=llm,
            tools=herramientas,
            prompt=REACT_PROMPT,
        )

        _executor = AgentExecutor(
            agent=agent,
            tools=herramientas,
            memory=_memoria_corto_plazo,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=6,
            return_intermediate_steps=True,
        )

    return _executor


def reiniciar_agente() -> None:
    """Reinicia el agente y limpia la memoria de corto plazo (nueva sesión)."""
    global _executor, _memoria_corto_plazo
    _executor = None
    _memoria_corto_plazo = None


def ejecutar_agente(pregunta: str) -> dict:
    """
    Ejecuta el agente con la pregunta del usuario.

    Flujo:
    1. Recupera contexto semántico relevante de la memoria de largo plazo
    2. Pasa la pregunta al AgentExecutor (que incluye memoria de corto plazo)
    3. El agente razona, selecciona herramientas y ejecuta su plan
    4. Si la respuesta es significativa, la persiste en memoria de largo plazo

    Args:
        pregunta (str): Consulta del usuario.

    Returns:
        dict con claves:
            - "output": respuesta final del agente
            - "intermediate_steps": lista de (accion, observacion) por cada paso
    """
    agente = obtener_agente()

    # 1. Recuperar contexto histórico semántico
    memoria_larga = recuperar_memoria_larga(pregunta, k=3)

    # 2. Ejecutar agente
    resultado = agente.invoke(
        {
            "input": pregunta,
            "memoria_larga": memoria_larga,
        }
    )

    # 3. Persistir respuesta relevante en memoria de largo plazo
    respuesta = resultado.get("output", "")
    if len(respuesta) > 80:
        resumen = f"Consulta: {pregunta[:200]}\nRespuesta: {respuesta[:400]}"
        guardar_en_memoria_larga(resumen, tipo="conversacion")

    return resultado


# ──────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN DIRECTA (modo consola para pruebas)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   AGENTE PORTUARIO EPV v2.0 — Modo Consola")
    print("=" * 60)
    print("Escribe 'salir' para terminar.\n")

    while True:
        try:
            pregunta = input("🧑 Tu consulta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSesión finalizada.")
            break

        if pregunta.lower() in ("salir", "exit", "quit"):
            print("Sesión finalizada. ¡Hasta pronto!")
            break

        if not pregunta:
            continue

        print("\n🤔 El agente está procesando tu consulta...\n")
        resultado = ejecutar_agente(pregunta)

        print(f"\n🚢 Respuesta del Agente:\n{resultado['output']}\n")

        pasos = resultado.get("intermediate_steps", [])
        if pasos:
            print(f"   [Se usaron {len(pasos)} herramienta(s) en {len(pasos)} paso(s)]")

        print("-" * 60)
