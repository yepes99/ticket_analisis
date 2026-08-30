"""
Resolucion de rangos de fecha para los selectores de periodo.
"""

from datetime import datetime, timedelta


PERIODOS = ["Ultima semana", "Ultimo mes", "Ano", "Personalizado"]


def resolve_query_dates(periodo, year, custom_range=None, today=None):
    today = today or datetime.now().date()

    if periodo == "Ultima semana":
        return today - timedelta(days=6), today
    if periodo == "Ultimo mes":
        return today - timedelta(days=29), today
    if periodo == "Ano":
        return datetime(year, 1, 1).date(), datetime(year, 12, 31).date()
    if periodo == "Personalizado" and custom_range and len(custom_range) == 2:
        start_date, end_date = custom_range
        if start_date > end_date:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
        return start_date, end_date

    raise ValueError(f"Periodo no soportado: {periodo}")


def available_years(today=None):
    today = today or datetime.now().date()
    return list(range(today.year, today.year - 11, -1))
