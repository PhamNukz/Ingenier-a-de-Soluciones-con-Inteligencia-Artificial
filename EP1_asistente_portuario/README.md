# Asistente de Normativas Portuarias EPV
## ISY0101 – Ingeniería de Soluciones con IA | DuocUC 2025

Chatbot basado en LLM y RAG que permite a trabajadores del Puerto de Valparaíso 
consultar normativas operacionales y de seguridad en lenguaje natural.

## Requisitos
- Python 3.11+
- Token GitHub con permiso Models habilitado (github.com/marketplace/models)

## Instalación
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install langchain langchain-openai langchain-community langchain-core
pip install langchain-text-splitters langchain-huggingface langchain-chroma
pip install chromadb openai pypdf python-dotenv streamlit sentence-transformers
```

## Configuración
Crear archivo `.env` en la raíz del repo:
GITHUB_TOKEN=tu_token_aqui
GITHUB_BASE_URL=https://models.inference.ai.azure.com
OPENAI_API_KEY=tu_token_aqui

## Ejecución
```bash
cd EP1_asistente_portuario/src

# 1. Indexar documentos (solo primera vez)
python indexer.py

# 2. Lanzar interfaz web
streamlit run app.py

# O usar modo terminal
python rag_chain.py
```

## Estructura
EP1_asistente_portuario/
├── documentos/        ← PDFs de normativa EPV
├── src/
│   ├── indexer.py     ← Carga y vectorización de PDFs
│   ├── rag_chain.py   ← Pipeline RAG (recuperación + generación)
│   └── app.py         ← Interfaz Streamlit
└── chroma_db/         ← Generado automáticamente al indexar

## Stack tecnológico
| Componente | Tecnología |
|-----------|------------|
| LLM | GPT-4o-mini vía GitHub Models |
| RAG Framework | LangChain |
| Vector Store | ChromaDB |
| Embeddings | HuggingFace paraphrase-multilingual-MiniLM-L12-v2 |
| Frontend | Streamlit |