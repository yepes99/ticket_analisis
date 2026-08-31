"""
Métricas de backlog 
"""

import pandas as pd
import numpy as np


BACKLOG_ESTADOS = ["backlog"]


def _tramo_antiguedad(dias):
    if pd.isna(dias):
        return "Sin fecha"
    if dias <= 7:
        return "0-1 semana"
    if dias <= 14:
        return "1-2 semanas"
    if dias <= 30:
        return "2-4 semanas"
    return "Más de 1 mes"


ORDEN_ANTIGUEDAD = ["0-1 semana", "1-2 semanas", "2-4 semanas", "Más de 1 mes", "Sin fecha"]
ORDEN_PRIORIDAD = ["Supone un impedimento", "Highest", "High", "Medium", "Low", "Lowest"]


def get_backlog_df(df):
    """
    Filtra los tickets en estado Backlog y calcula días en backlog y tramo de antigüedad.
    """
    mask = df["estado"].str.lower().isin(BACKLOG_ESTADOS)
    backlog = df[mask].copy()

    now = pd.Timestamp.now()
    backlog["dias_en_backlog"] = (now - backlog["fecha_creacion"]).dt.days
    backlog["antigüedad"] = backlog["dias_en_backlog"].apply(_tramo_antiguedad)

    return backlog


def calculate_backlog_kpis(df):
    """
    KPIs principales del backlog.
    """
    backlog = get_backlog_df(df)
    total = len(backlog)
    tiempo_medio = round(backlog["dias_en_backlog"].mean(), 1) if total > 0 else 0.0
    sin_size = int(backlog["size"].isna().sum())
    sin_prioridad = int(backlog["prioridad"].isna().sum())

    return {
        "total": total,
        "tiempo_medio": tiempo_medio,
        "sin_size": sin_size,
        "sin_prioridad": sin_prioridad,
    }


def calculate_backlog_por_antiguedad(df):
    """
    Conteo de tickets por tramo de antigüedad.
    """
    backlog = get_backlog_df(df)
    if backlog.empty:
        return pd.DataFrame(columns=["antigüedad", "tickets"])

    resumen = (
        backlog["antigüedad"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "antigüedad", "count": "tickets"})
    )
    resumen.columns = ["antigüedad", "tickets"]
    resumen["_orden"] = resumen["antigüedad"].apply(
        lambda x: ORDEN_ANTIGUEDAD.index(x) if x in ORDEN_ANTIGUEDAD else 99
    )
    return resumen.sort_values("_orden").drop(columns=["_orden"]).reset_index(drop=True)


def calculate_backlog_por_prioridad(df):
    """
    Conteo de tickets por prioridad.
    """
    backlog = get_backlog_df(df)
    if backlog.empty:
        return pd.DataFrame(columns=["prioridad", "tickets"])

    resumen = (
        backlog["prioridad"].fillna("Sin prioridad")
        .value_counts()
        .reset_index()
    )
    resumen.columns = ["prioridad", "tickets"]
    resumen["_orden"] = resumen["prioridad"].apply(
        lambda x: ORDEN_PRIORIDAD.index(x) if x in ORDEN_PRIORIDAD else 99
    )
    return resumen.sort_values("_orden").drop(columns=["_orden"]).reset_index(drop=True)


def calculate_backlog_por_size(df):
    """
    Conteo de tickets por size.
    """
    backlog = get_backlog_df(df)
    if backlog.empty:
        return pd.DataFrame(columns=["size", "tickets"])

    resumen = (
        backlog["size"].fillna("Sin size")
        .value_counts()
        .reset_index()
    )
    resumen.columns = ["size", "tickets"]
    return resumen


def calculate_backlog_detalle(df):
    """
    Tabla detalle de todos los tickets en backlog.
    """
    backlog = get_backlog_df(df)
    if backlog.empty:
        return backlog

    cols_disponibles = [
        "ticket_id",
        "resumen",
        "prioridad",
        "size",
        "asignado_a",
        "fecha_creacion",
        "dias_en_backlog",
        "antigüedad",
    ]
    cols = [c for c in cols_disponibles if c in backlog.columns]
    return backlog[cols].sort_values("dias_en_backlog", ascending=False).reset_index(drop=True)