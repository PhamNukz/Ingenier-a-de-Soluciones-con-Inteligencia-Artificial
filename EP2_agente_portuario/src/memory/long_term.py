"""
Memoria de LARGO PLAZO — Agente Portuario EPV v2.0

Implementa recuperación semántica de contexto mediante ChromaDB y embeddings
de HuggingFace. Persiste conversaciones importantes entre sesiones.

Rol en el sistema:
- Almacena hechos y conversaciones relevantes de forma permanente
- Recupera contexto semántico de interacciones pasadas (IE4)
- Complementa la memoria de corto plazo con información histórica
- Permite continuidad de tareas en flujos prolongados y multi-sesión
"""

import os
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Base de datos vectorial exclusiva para memoria de largo plazo del agente
LONG_TERM_PATH = os.path.join(
    os.path.dirname(__file__), "../../chroma_db_memoria_larga"
)

_vectorstore_cache = None


def _obtener_vectorstore() -> Chroma:
    """Retorna la instancia de ChromaDB para memoria de largo plazo (con caché)."""
    global _vectorstore_cache
    if _vectorstore_cache is None:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        _vectorstore_cache = Chroma(
            persist_directory=LONG_TERM_PATH,
            embedding_function=embeddings,
            collection_name="memoria_agente_epv",
        )
    return _vectorstore_cache


def guardar_en_memoria_larga(contenido: str, tipo: str = "conversacion") -> str:
    """
    Guarda un fragmento de conversación o dato relevante en la memoria de largo plazo.

    Args:
        contenido (str): Texto a almacenar (resumen de conversación, hecho importante, etc.)
        tipo (str): Categoría del contenido: 'conversacion', 'incidente', 'consulta', 'reporte'

    Returns:
        str: Confirmación del almacenamiento.
    """
    try:
        vectorstore = _obtener_vectorstore()
        doc = Document(
            page_content=contenido,
            metadata={
                "tipo": tipo,
                "timestamp": datetime.now().isoformat(),
                "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
        )
        vectorstore.add_documents([doc])
        return f"✅ Información persistida en memoria de largo plazo (tipo: {tipo})."
    except Exception as e:
        return f"⚠ Error al guardar en memoria de largo plazo: {str(e)}"


def recuperar_memoria_larga(consulta: str, k: int = 3) -> str:
    """
    Recupera contexto semántico relevante de conversaciones e interacciones pasadas.

    Usa similitud vectorial para encontrar los k fragmentos más relevantes
    para la consulta actual, permitiendo al agente recordar contexto histórico.

    Args:
        consulta (str): La pregunta o tarea actual del usuario.
        k (int): Número de fragmentos históricos a recuperar.

    Returns:
        str: Contexto histórico relevante formateado, o mensaje indicando
             que no hay historial previo disponible.
    """
    try:
        vectorstore = _obtener_vectorstore()

        # Verificar si hay documentos en la colección
        coleccion = vectorstore._collection
        if coleccion.count() == 0:
            return "Sin historial previo de interacciones en memoria de largo plazo."

        docs = vectorstore.similarity_search(consulta, k=k)

        if not docs:
            return "No se encontró contexto histórico relevante para esta consulta."

        fragmentos = []
        for doc in docs:
            fecha = doc.metadata.get("fecha_legible", "Fecha desconocida")
            tipo = doc.metadata.get("tipo", "general")
            fragmentos.append(f"[{fecha} | {tipo}] {doc.page_content}")

        return "CONTEXTO HISTÓRICO RECUPERADO:\n" + "\n\n".join(fragmentos)

    except Exception as e:
        return f"Sin historial previo disponible ({str(e)})."
