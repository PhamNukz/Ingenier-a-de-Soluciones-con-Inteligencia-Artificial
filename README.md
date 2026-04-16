# 🚢 Asistente de Normativas Portuarias EPV
## ISY0101 – Ingeniería de Soluciones con IA | DuocUC 2026

Chatbot basado en LLM y RAG que permite a trabajadores del Puerto de Valparaíso consultar normativas operacionales y de seguridad en lenguaje natural, con respuestas citadas por fuente documental.

---

## Requisitos previos
- Python 3.11+
- Cuenta GitHub con token Models habilitado → [github.com/marketplace/models](https://github.com/marketplace/models)

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/PhamNukz/Ingenier-a-de-Soluciones-con-Inteligencia-Artificial
cd Ingenier-a-de-Soluciones-con-Inteligencia-Artificial

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r EP1_asistente_portuario/requirements.txt
```

---

## Configuración

Crear archivo `.env` en la **raíz del repositorio** (mismo nivel que este README):

```
GITHUB_TOKEN=tu_token_aqui
GITHUB_BASE_URL=https://models.inference.ai.azure.com
OPENAI_API_KEY=tu_token_aqui
```

> ⚠️ El `.env` nunca se sube al repositorio. Cada usuario debe crear el suyo con su propio token.

---

## Ejecución

```bash
cd EP1_asistente_portuario/src

# 1. Indexar documentos (solo la primera vez)
python indexer.py

# 2. Lanzar interfaz web
streamlit run app.py
```

La interfaz se abre automáticamente en `http://localhost:8501`

También se puede usar en modo terminal:
```bash
python rag_chain.py
```

---

## Ejemplos de consultas

- `¿Cuántas horas de descanso hay entre turnos?`
- `¿Qué EPP necesito para trabajar en la zona de grúas?`
- `¿Cuál es el protocolo si cae una persona al mar?`
- `¿Cuántas horas extra puedo trabajar por semana?`
- `¿Qué hago si hay un derrame de mercancía peligrosa?`

---

## Estructura del proyecto

```
EP1_asistente_portuario/
├── documentos/                          ← PDFs de normativa EPV
│   ├── reglamento_operaciones_portuarias.pdf
│   ├── manual_seguridad_epp.pdf
│   ├── protocolo_emergencias_maritimas.pdf
│   └── convenio_colectivo_trabajadores.pdf
├── src/
│   ├── indexer.py                       ← Carga y vectorización de PDFs
│   ├── rag_chain.py                     ← Pipeline RAG completo
│   └── app.py                           ← Interfaz Streamlit
├── chroma_db/                           ← Generado automáticamente al indexar
└── requirements.txt
```

---

## Stack tecnológico

| Componente     | Tecnología                                        |
|----------------|---------------------------------------------------|
| LLM            | GPT-4o-mini vía GitHub Models                     |
| RAG Framework  | LangChain                                         |
| Vector Store   | ChromaDB (local)                                  |
| Embeddings     | HuggingFace paraphrase-multilingual-MiniLM-L12-v2 |
| Frontend       | Streamlit                                         |

---

## Integrantes
- Benjamin Aravena R.
- Francisco Gómez R.

**DuocUC – Escuela de Informática y Telecomunicaciones | 2026**
