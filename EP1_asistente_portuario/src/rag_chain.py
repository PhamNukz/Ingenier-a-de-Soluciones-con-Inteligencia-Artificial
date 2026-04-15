# rag_chain.py - Pipeline RAG completo
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv(dotenv_path="../../.env")

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "../chroma_db")

SYSTEM_PROMPT = """Eres un asistente especializado en normativas y reglamentos del 
Puerto de Valparaiso (EPV). Tu funcion es responder preguntas de trabajadores 
portuarios de forma clara, precisa y siempre citando la fuente normativa.

REGLAS:
- Responde SOLO basandote en el contexto proporcionado.
- Si la informacion no esta en el contexto, indica claramente que no tienes 
  esa informacion en los documentos disponibles.
- Siempre cita el documento fuente al final de tu respuesta.
- Usa lenguaje claro y directo, adecuado para trabajadores portuarios.
- Si hay pasos o procedimientos, enumeralos claramente.

CONTEXTO DE DOCUMENTOS:
{context}

PREGUNTA DEL TRABAJADOR:
{question}

RESPUESTA (incluye la fuente al final):"""

def cargar_retriever():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    return retriever

def formatear_contexto(docs):
    resultado = []
    for doc in docs:
        fuente = doc.metadata.get("fuente", "Documento desconocido")
        resultado.append(f"[Fuente: {fuente}]\n{doc.page_content}")
    return "\n\n---\n\n".join(resultado)

def crear_cadena_rag():
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("GITHUB_TOKEN"),
        base_url=os.getenv("GITHUB_BASE_URL"),
        temperature=0.1
    )
    retriever = cargar_retriever()
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

    cadena = (
        {
            "context": retriever | formatear_contexto,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return cadena

def consultar(pregunta: str) -> str:
    cadena = crear_cadena_rag()
    respuesta = cadena.invoke(pregunta)
    return respuesta

if __name__ == "__main__":
    print("=== Asistente de Normativas Portuarias EPV ===")
    print("Escribe 'salir' para terminar\n")
    while True:
        pregunta = input("Tu pregunta: ").strip()
        if pregunta.lower() == "salir":
            break
        if pregunta:
            print("\nBuscando en normativas...\n")
            respuesta = consultar(pregunta)
            print(f"Respuesta:\n{respuesta}\n")
            print("-" * 60)