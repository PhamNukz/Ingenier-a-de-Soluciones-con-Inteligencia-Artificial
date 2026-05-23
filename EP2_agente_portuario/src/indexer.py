"""
INDEXADOR DE DOCUMENTOS — Agente Portuario EPV v2.0
Script para vectorizar los documentos PDF de normativas portuarias
y almacenarlos en ChromaDB para ser consultados por el agente.

IMPORTANTE: Ejecutar este script UNA VEZ antes de usar el agente,
o cada vez que se agreguen nuevos documentos a la carpeta /documentos.

Uso:
    cd EP2_agente_portuario/src
    python indexer.py
"""

import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

DOCUMENTOS_PATH = os.path.join(os.path.dirname(__file__), "../documentos")
CHROMA_PATH     = os.path.join(os.path.dirname(__file__), "../chroma_db")


def indexar_documentos() -> None:
    """
    Carga todos los PDF de /documentos, los divide en fragmentos
    y los vectoriza en ChromaDB con embeddings multilingües.
    """
    print("=" * 55)
    print("  INDEXADOR — Agente Portuario EPV v2.0")
    print("=" * 55)

    # Verificar que la carpeta de documentos existe
    if not os.path.exists(DOCUMENTOS_PATH):
        os.makedirs(DOCUMENTOS_PATH, exist_ok=True)
        print(f"\n⚠ Carpeta creada: {DOCUMENTOS_PATH}")
        print("  Agrega los PDF de normativas y vuelve a ejecutar.")
        sys.exit(0)

    # Cargar todos los PDF
    pdfs = [f for f in os.listdir(DOCUMENTOS_PATH) if f.endswith(".pdf")]
    if not pdfs:
        print(f"\n⚠ No se encontraron archivos PDF en: {DOCUMENTOS_PATH}")
        print("  Copia los documentos de normativas y vuelve a ejecutar.")
        sys.exit(0)

    print(f"\n📄 Documentos encontrados: {len(pdfs)}")
    todos_los_docs = []

    for nombre_pdf in pdfs:
        ruta = os.path.join(DOCUMENTOS_PATH, nombre_pdf)
        print(f"   Cargando: {nombre_pdf}")
        loader = PyPDFLoader(ruta)
        paginas = loader.load()

        # Agregar metadato de fuente para las citas
        for pagina in paginas:
            pagina.metadata["fuente"] = nombre_pdf.replace(".pdf", "")

        todos_los_docs.extend(paginas)

    print(f"\n✂ Dividiendo en fragmentos...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "],
    )
    fragmentos = splitter.split_documents(todos_los_docs)
    print(f"   Total de fragmentos: {len(fragmentos)}")

    print(f"\n🔢 Generando embeddings (HuggingFace multilingüe)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    print(f"\n💾 Almacenando en ChromaDB: {CHROMA_PATH}")
    vectorstore = Chroma.from_documents(
        documents=fragmentos,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
    )

    print(f"\n✅ Indexación completa.")
    print(f"   Fragmentos indexados: {len(fragmentos)}")
    print(f"   Base de datos: {CHROMA_PATH}")
    print("=" * 55)


if __name__ == "__main__":
    indexar_documentos()
