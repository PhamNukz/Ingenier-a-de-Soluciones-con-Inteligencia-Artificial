# indexer.py - Carga y vectoriza los PDFs de normativa portuaria
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

load_dotenv(dotenv_path="../../.env")

DOCS_PATH = os.path.join(os.path.dirname(__file__), "../documentos")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../chroma_db")

def cargar_documentos():
    documentos = []
    for archivo in os.listdir(DOCS_PATH):
        if archivo.endswith(".pdf"):
            ruta = os.path.join(DOCS_PATH, archivo)
            loader = PyPDFLoader(ruta)
            docs = loader.load()
            # Agregar metadata con nombre del documento fuente
            for doc in docs:
                doc.metadata["fuente"] = archivo
            documentos.extend(docs)
            print(f"  Cargado: {archivo} ({len(docs)} paginas)")
    return documentos

def dividir_chunks(documentos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(documentos)
    print(f"  Total chunks generados: {len(chunks)}")
    return chunks

def crear_vectorstore(chunks):
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    print(f"  VectorStore creado en: {CHROMA_PATH}")
    return vectorstore

if __name__ == "__main__":
    print("=== Indexando documentos portuarios ===")
    print("\n1. Cargando PDFs...")
    docs = cargar_documentos()
    print(f"\n2. Dividiendo en chunks...")
    chunks = dividir_chunks(docs)
    print(f"\n3. Creando vectorstore...")
    vs = crear_vectorstore(chunks)
    print("\n=== Indexacion completada exitosamente ===")