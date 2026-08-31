"""
Resolucion de rangos de fecha para los selectores de periodo.
"""

from datetime import datetime, timedelta


PERIODOS = [
    "Ultima semana",
    "Ultimo mes",
    "Ultimos 2 meses",
    "Ano",
    "Todo el historico",
    "Personalizado",
]


def resolve_query_dates(periodo, year, custom_range=None, today=None):
    """
    Devuelve (start_date, end_date) para el periodo elegido. end_date es
    siempre "hasta hoy" salvo en "Ano" y "Personalizado". start_date es
    None en "Todo el historico" (sin limite inferior: todos los tickets
    hasta hoy, se hayan creado cuando se hayan creado).
    """
    today = today or datetime.now().date()

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


def available_years(today=None):
    today = today or datetime.now().date()
    return list(range(today.year, today.year - 11, -1))
