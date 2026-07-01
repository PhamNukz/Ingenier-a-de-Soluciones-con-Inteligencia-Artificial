"""
SEGURIDAD Y USO RESPONSABLE — EP3 Observabilidad (IE6)
======================================================

Implementa controles de seguridad y uso responsable que se aplican ANTES de que
una consulta llegue al agente, y utilidades de privacidad para el logging:

  1. Sanitización de inputs y detección de prompt injection.
  2. Anonimización de datos potencialmente sensibles en los logs (PII).
  3. Rate limiting simple (límite de consultas por ventana de tiempo) para
     proteger la cuota de la API de GitHub Models y mitigar abuso.

Estos controles están alineados con criterios éticos, normativos y de privacidad
(Ley N°19.628 sobre Protección de la Vida Privada en Chile y buenas prácticas
OWASP Top 10 para LLM — LLM01: Prompt Injection).
"""

import re
import time
from collections import deque

# ──────────────────────────────────────────────────────────────────────────────
# 1. DETECCIÓN DE PROMPT INJECTION (OWASP LLM01)
# ──────────────────────────────────────────────────────────────────────────────
# Patrones frecuentes de inyección de instrucciones. No pretende ser exhaustivo,
# sino una primera capa de defensa (defense-in-depth) sobre el input del usuario.
PATRONES_INYECCION = [
    r"ignora(r)?\s+(todas\s+)?(las\s+)?instrucciones",
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"olvida(r)?\s+(todo|tus\s+instrucciones|lo\s+anterior)",
    r"forget\s+(everything|all\s+previous)",
    r"act[uú]a\s+como\s+(si\s+fueras|un)",
    r"you\s+are\s+now\s+(a|an|in)",
    r"system\s*prompt",
    r"revela(r)?\s+(tu|el)\s+(prompt|system|configuraci[oó]n)",
    r"reveal\s+your\s+(prompt|instructions|system)",
    r"dispositivo\s+de\s+desarrollador|developer\s+mode|modo\s+desarrollador",
    r"jailbreak|DAN\b",
    r"imprime\s+(tu|las)\s+(api[\s_-]?key|token|credenciales)",
    r"print\s+(your\s+)?(api[\s_-]?key|token|secret)",
]

_REGEX_INYECCION = [re.compile(p, re.IGNORECASE) for p in PATRONES_INYECCION]

LONGITUD_MAXIMA_INPUT = 2000  # caracteres; evita payloads de inundación de contexto


class ResultadoSanitizacion:
    """Resultado del proceso de sanitización de una consulta."""

    def __init__(self, texto_limpio: str, bloqueado: bool, motivo: str | None):
        self.texto_limpio = texto_limpio
        self.bloqueado = bloqueado
        self.motivo = motivo  # None si no se bloqueó

    def __repr__(self) -> str:
        estado = f"BLOQUEADO ({self.motivo})" if self.bloqueado else "OK"
        return f"<Sanitizacion {estado}>"


def sanitizar_input(consulta: str) -> ResultadoSanitizacion:
    """
    Sanitiza y valida la consulta del usuario antes de enviarla al agente.

    Controles aplicados:
      - Recorta espacios y limita longitud máxima.
      - Neutraliza caracteres de control.
      - Detecta patrones de prompt injection conocidos.

    Args:
        consulta: texto crudo enviado por el usuario.

    Returns:
        ResultadoSanitizacion con el texto limpio y si debe bloquearse.
    """
    if consulta is None:
        return ResultadoSanitizacion("", bloqueado=True, motivo="input_vacio")

    texto = consulta.strip()

    if not texto:
        return ResultadoSanitizacion("", bloqueado=True, motivo="input_vacio")

    # Limitar longitud para evitar saturación de contexto / costos
    if len(texto) > LONGITUD_MAXIMA_INPUT:
        texto = texto[:LONGITUD_MAXIMA_INPUT]

    # Eliminar caracteres de control no imprimibles (excepto saltos de línea/tabs)
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texto)

    # Detección de prompt injection
    for regex in _REGEX_INYECCION:
        if regex.search(texto):
            return ResultadoSanitizacion(
                texto,
                bloqueado=True,
                motivo="prompt_injection_detectado",
            )

    return ResultadoSanitizacion(texto, bloqueado=False, motivo=None)


# ──────────────────────────────────────────────────────────────────────────────
# 2. ANONIMIZACIÓN DE PII PARA LOGS (Ley 19.628 / privacidad de datos portuarios)
# ──────────────────────────────────────────────────────────────────────────────
# Patrones de datos personales chilenos / sensibles que NO deben quedar en claro
# dentro de los registros de observabilidad.
_PATRONES_PII = [
    (re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b"), "[RUT]"),          # RUT chileno
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),            # email
    (re.compile(r"\b(\+?56)?\s?9\s?\d{4}\s?\d{4}\b"), "[TELEFONO]"),     # celular CL
    (re.compile(r"\b\d{16}\b"), "[TARJETA]"),                            # nº tarjeta
]


def anonimizar_pii(texto: str) -> str:
    """
    Reemplaza datos personales identificables por marcadores genéricos antes de
    escribirlos en los logs. Protege la privacidad en contextos de producción.

    Args:
        texto: texto a anonimizar (típicamente la consulta del usuario).

    Returns:
        Texto con la PII reemplazada por etiquetas.
    """
    if not texto:
        return texto
    for regex, reemplazo in _PATRONES_PII:
        texto = regex.sub(reemplazo, texto)
    return texto


# ──────────────────────────────────────────────────────────────────────────────
# 3. RATE LIMITING (protección de cuota y anti-abuso)
# ──────────────────────────────────────────────────────────────────────────────
class RateLimiter:
    """
    Limitador de tasa por ventana deslizante. Permite como máximo `max_consultas`
    en una ventana de `ventana_segundos`. Protege la cuota de la API de GitHub
    Models (que tiene límites estrictos en su nivel gratuito) y mitiga abuso.
    """

    def __init__(self, max_consultas: int = 20, ventana_segundos: float = 60.0):
        self.max_consultas = max_consultas
        self.ventana_segundos = ventana_segundos
        self._marcas: deque[float] = deque()

    def permitir(self) -> bool:
        """
        Devuelve True si la consulta está permitida en este momento, o False si se
        excedió el límite. Registra la marca de tiempo si se permite.
        """
        ahora = time.time()
        # Descartar marcas fuera de la ventana
        while self._marcas and (ahora - self._marcas[0]) > self.ventana_segundos:
            self._marcas.popleft()

        if len(self._marcas) >= self.max_consultas:
            return False

        self._marcas.append(ahora)
        return True

    def consultas_en_ventana(self) -> int:
        """Número de consultas registradas en la ventana actual."""
        ahora = time.time()
        while self._marcas and (ahora - self._marcas[0]) > self.ventana_segundos:
            self._marcas.popleft()
        return len(self._marcas)


# Instancia global reutilizable por la capa de instrumentación.
limitador_global = RateLimiter(max_consultas=20, ventana_segundos=60.0)
