"""
Resolucion de rangos de fecha para los selectores de periodo.
"""

from datetime import datetime, timedelta


PERIODOS = [
    "Esta semana",
    "Semana pasada",
    "Este mes",
    "Mes pasado",
    "Ultima semana",
    "Ultimo mes",
    "Ultimos 2 meses",
    "Ano",
    "Todo el historico",
    "Personalizado",
]

# Texto que se ensena en el desplegable (las claves de arriba se mantienen
# sin tildes porque se usan en codigo).
ETIQUETAS_PERIODO = {
    "Esta semana": "Esta semana (lunes a hoy)",
    "Semana pasada": "Semana pasada (lunes a domingo)",
    "Este mes": "Este mes",
    "Mes pasado": "Mes pasado",
    "Ultima semana": "Últimos 7 días",
    "Ultimo mes": "Últimos 30 días",
    "Ultimos 2 meses": "Últimos 60 días",
    "Ano": "Año completo",
    "Todo el historico": "Todo el histórico",
    "Personalizado": "📅 Personalizado (elige fechas)",
}


def etiqueta_periodo(periodo):
    return ETIQUETAS_PERIODO.get(periodo, periodo)


def _lunes(dia):
    return dia - timedelta(days=dia.weekday())


def resolve_query_dates(periodo, year, custom_range=None, today=None):
    """
    Devuelve (start_date, end_date) para el periodo elegido. end_date es
    "hasta hoy" en los periodos en curso; en "Semana pasada", "Mes pasado",
    "Ano" y "Personalizado" es el ultimo dia de ese rango. start_date es
    None en "Todo el historico" (sin limite inferior: todos los tickets
    hasta hoy, se hayan creado cuando se hayan creado).
    """
    today = today or datetime.now().date()

    if periodo == "Esta semana":
        return _lunes(today), today
    if periodo == "Semana pasada":
        lunes_pasado = _lunes(today) - timedelta(days=7)
        return lunes_pasado, lunes_pasado + timedelta(days=6)
    if periodo == "Este mes":
        return today.replace(day=1), today
    if periodo == "Mes pasado":
        fin = today.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if periodo == "Ultima semana":
        return today - timedelta(days=6), today
    if periodo == "Ultimo mes":
        return today - timedelta(days=29), today
    if periodo == "Ultimos 2 meses":
        return today - timedelta(days=59), today
    if periodo == "Ano":
        return datetime(year, 1, 1).date(), datetime(year, 12, 31).date()
    if periodo == "Todo el historico":
        return None, today
    if periodo == "Personalizado" and custom_range and len(custom_range) == 2:
        start_date, end_date = custom_range
        if start_date > end_date:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
        return start_date, end_date

    raise ValueError(f"Periodo no soportado: {periodo}")


def describir_rango(start_date, end_date):
    """'Del 10/11/2026 al 13/11/2026 · 4 días' para ensenar que se va a consultar."""
    if start_date is None:
        return f"Todo hasta el {end_date.strftime('%d/%m/%Y')}"
    dias = (end_date - start_date).days + 1
    return (
        f"Del {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')} · "
        f"{dias} día{'s' if dias != 1 else ''}"
    )


def available_years(today=None):
    today = today or datetime.now().date()
    return list(range(today.year, today.year - 11, -1))
