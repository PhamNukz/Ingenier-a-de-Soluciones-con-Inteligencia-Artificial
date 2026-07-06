"""
Herramienta de RAZONAMIENTO — Agente Portuario EPV v2.0
Evalúa situaciones portuarias contra normativas, determina nivel de riesgo
y genera recomendaciones de cumplimiento estructuradas.
"""

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

PROMPT_EVALUACION = ChatPromptTemplate.from_template("""
Eres un experto en normativas de seguridad y operaciones del Puerto de Valparaíso (EPV).
Tu tarea es analizar la situación descrita y emitir un dictamen técnico estructurado.

SITUACIÓN A EVALUAR:
{situacion}

Proporciona un análisis con el siguiente formato EXACTO:

## DICTAMEN TÉCNICO EPV

**NIVEL DE RIESGO:** [BAJO / MEDIO / ALTO / CRÍTICO]

**ÁREAS NORMATIVAS INVOLUCRADAS:**
- [Lista las áreas de la normativa EPV que aplican: seguridad, operaciones, emergencias, laboral, ambiental, etc.]

**EVALUACIÓN DE CUMPLIMIENTO:**
[Indica si la situación cumple o incumple las normativas. Explica por qué con argumentos técnicos específicos.]

**HALLAZGOS PRINCIPALES:**
1. [Hallazgo 1]
2. [Hallazgo 2]
3. [Hallazgo 3 - si aplica]

**RECOMENDACIONES:**
1. [Acción específica a tomar]
2. [Acción específica a tomar]
3. [Acción específica a tomar]

**PRIORIDAD DE ACCIÓN:** [INMEDIATA (< 24h) / CORTO PLAZO (< 1 semana) / PLANIFICADA (> 1 semana)]

**SUSTENTO NORMATIVO:**
[Menciona qué tipo de reglamento o protocolo portuario respalda esta evaluación]
""")


@tool
def evaluar_cumplimiento(situacion: str) -> str:
    """
    Evalúa si una situación, procedimiento o condición del Puerto de Valparaíso
    cumple con las normativas vigentes, determina el nivel de riesgo y entrega recomendaciones.

    Úsala cuando necesites:
    - Analizar si una situación es conforme a las normas EPV
    - Determinar el nivel de riesgo de una condición operacional
    - Obtener recomendaciones ante un incumplimiento detectado
    - Evaluar procedimientos antes de ejecutarlos
    - Analizar reportes de condiciones inseguras

    El input debe ser la descripción detallada de la situación a evaluar.
    Sé específico: incluye lugar, condición observada, personas involucradas y contexto.

    Ejemplo: "Se observó que operadores del Muelle 2 no utilizan casco durante
    la descarga de contenedores en turno nocturno del 22/05/2026."
    """
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("GITHUB_TOKEN"),
            base_url=os.getenv("GITHUB_BASE_URL"),
            temperature=0.1,
            # Mejora EP3→EFT: backoff ante rate-limit (429) del free tier
            max_retries=5,
            timeout=45,
        )

        chain = PROMPT_EVALUACION | llm
        resultado = chain.invoke({"situacion": situacion})
        return resultado.content

    except Exception as e:
        return f"❌ Error en la evaluación de cumplimiento: {str(e)}"
