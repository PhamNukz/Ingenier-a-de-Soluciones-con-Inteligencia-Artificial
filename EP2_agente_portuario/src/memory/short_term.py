"""
Memoria de CORTO PLAZO — Agente Portuario EPV v2.0

Implementa una ventana deslizante (ConversationBufferWindowMemory) que mantiene
los últimos k intercambios completos (pregunta + respuesta) en memoria activa.

Rol en el sistema:
- Permite al agente recordar el hilo de la conversación actual
- Evita que el agente repita preguntas ya respondidas en la sesión
- Se reinicia cuando se inicia una nueva sesión de Streamlit
- Garantiza la continuidad de tareas en flujos prolongados (IE3)
"""

from langchain.memory import ConversationBufferWindowMemory


def crear_memoria_corto_plazo(k: int = 8) -> ConversationBufferWindowMemory:
    """
    Crea una instancia de memoria de corto plazo.

    Args:
        k (int): Número de intercambios recientes a mantener en memoria.
                 Valor por defecto: 8 (≈ últimas 8 preguntas y respuestas).

    Returns:
        ConversationBufferWindowMemory: Objeto de memoria listo para usar con AgentExecutor.

    Funcionamiento:
        - Almacena los últimos k pares (humano, IA) de la conversación
        - Cuando se supera el límite k, descarta el intercambio más antiguo
        - Retorna el historial como string para ser inyectado en el prompt ReAct
    """
    memory = ConversationBufferWindowMemory(
        k=k,
        memory_key="chat_history",   # clave en el prompt: {chat_history}
        return_messages=False,        # retorna string (compatible con PromptTemplate)
        input_key="input",            # clave de entrada del AgentExecutor
        output_key="output",          # clave de salida del AgentExecutor
        human_prefix="Trabajador",
        ai_prefix="Agente EPV",
    )
    return memory
