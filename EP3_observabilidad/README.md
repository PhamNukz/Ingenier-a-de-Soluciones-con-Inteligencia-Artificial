# EP3 — Observabilidad del Agente Portuario EPV

**Asignatura:** ISY0101 · Ingeniería de Soluciones con IA · **Evaluación Parcial N°3**
**RA3 — Observabilidad, Seguridad y Ética en Agentes de IA**

Instrumentación de observabilidad sobre el **Agente Portuario EPV v2.0** (EP2): un
agente ReAct (LangChain) con RAG sobre ChromaDB, `gpt-4o-mini` vía GitHub Models y
4 herramientas (consulta de normativas, evaluación de cumplimiento, generación de
reportes y búsqueda externa en Wikipedia).

Este módulo **no modifica** el agente EP2: lo envuelve con una capa de medición,
logging estructurado, análisis de trazas, un dashboard visual y controles de
seguridad.

---

## 🎯 Qué mide (las 5 familias de métricas)

| Métrica | Descripción | Indicador |
|---|---|---|
| **Precisión / Relevancia** | Score de similitud de los chunks recuperados de ChromaDB (`1/(1+distancia)`). | IE1 |
| **Latencia** | Tiempo total por consulta, desglosado en *embedding → retrieval → LLM*. | IE2 |
| **Consistencia** | Variación de respuesta/tokens/chunks al repetir la misma consulta N veces. | IE1 |
| **Frecuencia de errores** | Fallos de la API (timeouts, 429/503), respuestas vacías y bloqueos de seguridad. | IE1 |
| **Uso de recursos** | Tokens consumidos (prompt + completion) y nº de chunks recuperados. | IE2 |

---

## 📁 Estructura

```
EP3_observabilidad/
├── src/
│   ├── observabilidad/
│   │   ├── instrumentacion.py     # Wrapper medir_consulta() + callback de métricas
│   │   ├── retrieval_metrics.py   # Scores de similitud de ChromaDB (precisión)
│   │   ├── logger_json.py         # Logging estructurado en JSON Lines
│   │   └── seguridad.py           # Sanitización, anti prompt-injection, PII, rate limit
│   ├── dataset_queries.py         # 28 consultas (en-dominio, ambiguas, fuera-dominio, adversariales)
│   ├── run_evaluacion.py          # Corre el dataset contra el agente REAL (requiere token)
│   ├── simular_metricas.py        # Genera datos demo realistas (sin token)
│   ├── analisis_hallazgos.py      # Análisis de logs: cuellos de botella, patrones, anomalías
│   ├── generar_graficos.py        # Exporta los gráficos PNG de evidencia
│   ├── generar_informe.py         # Regenera el informe Word desde los datos
│   └── dashboard.py               # Dashboard Streamlit (IE5)
├── logs/
│   ├── metricas.jsonl             # Un registro JSON por consulta (trazabilidad)
│   └── hallazgos.json             # Resumen del análisis
├── docs/img/                      # Gráficos de evidencia (PNG)
├── Informe_EP3_ISY0101.docx       # Informe final
├── requirements.txt
└── .env.example
```

---

## 🚀 Ejecución

### 1. Instalar dependencias

```bash
cd EP3_observabilidad
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
```

### 2A. Camino RÁPIDO — datos de demostración (sin token)

Para ver el dashboard y el análisis funcionando de inmediato:

```bash
cd src
python simular_metricas.py        # genera logs/metricas.jsonl (datos simulados)
python analisis_hallazgos.py      # imprime hallazgos y crea logs/hallazgos.json
python generar_graficos.py        # genera docs/img/*.png
streamlit run dashboard.py        # abre el dashboard en http://localhost:8501
```

> Los datos demo están marcados con `"fuente_datos": "simulado"`. El dashboard lo
> indica con un badge naranja.

### 2B. Camino REAL — instrumentación con el agente EP2

Requiere la base vectorial de EP2 y un token de GitHub Models:

```bash
# 1. Configurar credenciales
cp .env.example .env        # y editar GITHUB_TOKEN

# 2. Asegurar la base vectorial de EP2 (si no existe):
cd ../EP2_agente_portuario/src && python indexer.py && cd ../../EP3_observabilidad/src

# 3. Correr la evaluación real (instrumenta el agente con las 28 consultas)
python run_evaluacion.py --limpiar

# 4. Analizar y visualizar
python analisis_hallazgos.py
python generar_graficos.py
streamlit run dashboard.py
```

El dashboard funciona igual con datos reales o simulados (lee el mismo `metricas.jsonl`).

---

## 🔒 Seguridad y uso responsable (IE6)

Implementado en [`src/observabilidad/seguridad.py`](src/observabilidad/seguridad.py):

- **Sanitización de inputs** y detección de **prompt injection** (alineado a OWASP LLM01).
- **Anonimización de PII** en los logs (RUT, email, teléfono) — Ley N° 19.628 (Chile).
- **Gestión de la API key por variable de entorno** (`.env`, nunca versionada).
- **Rate limiting** (ventana deslizante) para proteger la cuota de la API.
- **No se loguean datos sensibles**: la consulta se trunca y se anonimiza antes de persistir.

Las 4 consultas adversariales del dataset se **bloquean antes** de llegar al agente
(no consumen tokens), lo que queda registrado en las métricas como
`bloqueado_prompt_injection_detectado`.

---

## 🧪 Evidencia de pruebas

- `logs/metricas.jsonl` — registros de trazabilidad de cada consulta.
- `logs/hallazgos.json` — resultado del análisis automatizado.
- `docs/img/*.png` — visualizaciones generadas a partir de los datos.

---

## 🔁 Reproducibilidad

El simulador usa semilla fija (`SEED = 42`): la corrida demo es reproducible.
El análisis y los gráficos se regeneran de forma determinista desde `metricas.jsonl`.
