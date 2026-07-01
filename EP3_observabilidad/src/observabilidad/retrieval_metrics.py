"""
INSTRUMENTACIÓN DEL RETRIEVAL — EP3 Observabilidad (IE1 — precisión/relevancia)
================================================================================

El agente EP2 recupera contexto con `consultar_normativa`, que internamente hace
similarity search sobre ChromaDB pero NO expone las distancias/scores. Para poder
medir la PRECISIÓN/RELEVANCIA del retrieval, aquí replicamos exactamente la misma
configuración (mismos embeddings, misma base, mismo k=4) pero capturando:

  - distancia de cada chunk recuperado (ChromaDB devuelve distancias),
  - score de similitud derivado de la distancia,
  - latencia desglosada: embedding de la query vs. búsqueda vectorial,
  - número de chunks recuperados y sus fuentes.

Nota sobre la métrica de similitud:
  ChromaDB, con estos embeddings, usa distancia L2 por defecto. Convertimos la
  distancia a un score de relevancia acotado en (0, 1] con  score = 1 / (1 + dist).
  Un score más alto = chunk más relevante. Es una métrica monótona y comparable
  entre queries, suficiente para detectar consultas mal cubiertas por el corpus.
"""

import os
from time import perf_counter

# Misma configuración que EP2 (consulta_tool.py / indexer.py)
_MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "EP2_agente_portuario",
    "chroma_db",
)

_embeddings_cache = None
_collection_cache = None


def _cargar_recursos():
    """Carga (con caché) el modelo de embeddings y la colección ChromaDB de EP2."""
    global _embeddings_cache, _collection_cache
    if _embeddings_cache is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings_cache = HuggingFaceEmbeddings(model_name=_MODELO_EMBEDDINGS)

    if _collection_cache is None:
        import chromadb

        cliente = chromadb.PersistentClient(path=_CHROMA_PATH)
        # EP2 usa la colección por defecto de langchain_chroma ("langchain")
        colecciones = cliente.list_collections()
        nombre = "langchain"
        if colecciones:
            nombres = [c.name for c in colecciones]
            nombre = "langchain" if "langchain" in nombres else nombres[0]
        _collection_cache = cliente.get_collection(nombre)

    return _embeddings_cache, _collection_cache


def medir_retrieval(consulta: str, k: int = 4) -> dict:
    """
    Ejecuta el retrieval instrumentado para una consulta y devuelve sus métricas.

    Args:
        consulta: pregunta del usuario.
        k: número de chunks a recuperar (igual que EP2: k=4).

    Returns:
        dict con:
          - latencia_embedding_s, latencia_retrieval_s
          - num_chunks
          - distancias            (lista de float)
          - scores_similitud      (lista de float en (0,1])
          - score_similitud_top   (float)
          - score_similitud_promedio (float)
          - fuentes               (lista de str)
    """
    embeddings, coleccion = _cargar_recursos()

    # 1. Embedding de la query (latencia de embedding)
    t0 = perf_counter()
    vector = embeddings.embed_query(consulta)
    latencia_embedding = perf_counter() - t0

    # 2. Búsqueda vectorial en ChromaDB (latencia de retrieval)
    t0 = perf_counter()
    resultado = coleccion.query(
        query_embeddings=[vector],
        n_results=k,
        include=["distances", "metadatas"],
    )
    latencia_retrieval = perf_counter() - t0

    distancias = (resultado.get("distances") or [[]])[0]
    metadatas = (resultado.get("metadatas") or [[]])[0]

    scores = [round(1.0 / (1.0 + float(d)), 4) for d in distancias]
    fuentes = [m.get("fuente", "desconocido") for m in metadatas]

    return {
        "latencia_embedding_s": round(latencia_embedding, 4),
        "latencia_retrieval_s": round(latencia_retrieval, 4),
        "num_chunks": len(distancias),
        "distancias": [round(float(d), 4) for d in distancias],
        "scores_similitud": scores,
        "score_similitud_top": scores[0] if scores else 0.0,
        "score_similitud_promedio": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "fuentes": fuentes,
    }
