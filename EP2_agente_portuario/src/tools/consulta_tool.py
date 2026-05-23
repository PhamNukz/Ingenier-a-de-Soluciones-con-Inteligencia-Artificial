"""
Herramienta de CONSULTA — Agente Portuario EPV v2.0
Recupera información de normativas usando RAG (Retrieval-Augmented Generation)
sobre la base vectorial ChromaDB construida en EP1.
"""

import os
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Ruta a la base vectorial de normativas (compatible con EP1)
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../../chroma_db")

_retriever_cache = None


def _cargar_retriever():
    """Carga el retriever RAG desde ChromaDB (con caché para evitar recargas)."""
    global _retriever_cache
    if _retriever_cache is None:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
        )
        _retriever_cache = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )
    return _retriever_cache


@tool
def consultar_normativa(consulta: str) -> str:
    """
    Consulta la base de datos de normativas y reglamentos del Puerto de Valparaíso (EPV).

    Úsala cuando necesites información sobre:
    - Procedimientos operacionales portuarios
    - Normas de seguridad e higiene
    - Reglamentos de operación de maquinaria
    - Protocolos de emergencia
    - Convenios colectivos o disposiciones laborales
    - Cualquier regulación vigente en EPV

    El input debe ser la pregunta o tema que deseas buscar en las normativas.
    Ejemplo: "¿Cuáles son los EPP obligatorios para trabajar en el muelle?"
    """
    try:
        retriever = _cargar_retriever()
        docs = retriever.invoke(consulta)

        if not docs:
            return (
                "No se encontró información relevante en las normativas EPV "
                "para esta consulta. Intenta reformular la pregunta o consulta "
                "directamente con el área de Operaciones."
            )

        fragmentos = []
        for i, doc in enumerate(docs, 1):
            fuente = doc.metadata.get("fuente", "Documento desconocido")
            fragmentos.append(
                f"[Fragmento {i} | Fuente: {fuente}]\n{doc.page_content}"
            )

        return "\n\n---\n\n".join(fragmentos)

    except Exception as e:
        return f"Error al consultar normativas: {str(e)}"
