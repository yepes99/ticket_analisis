import numpy as np
import pandas as pd


# =========================
# CONFIG SLA
# =========================

SLA_PRIORIDAD_HORAS = {
    "Highest": 4,
    "High": 8,
    "Medium": 24,
    "Low": 72,
    "Lowest": 120,
}

SLA_SIZE_DIAS = {
    "S": 7,
    "M": 14,
    "L": 21,
    "XL": 60,
}

DEFAULT_SLA_HORAS = 24


# =========================
# MÉTRICAS BASE
# =========================
def completar_metricas_resolucion(df):
    df = df.copy()

    df["horas_resolucion"] = (
        (df["fecha_resolucion"] - df["fecha_creacion"])
        .dt.total_seconds() / 3600
    ).round(2)

    df["dias_resolucion"] = np.where(
        df["fecha_resolucion"].notna(),
        (df["fecha_resolucion"] - df["fecha_creacion"]).dt.total_seconds() / 86400,
        np.nan,
    )

    df["resuelto"] = df["fecha_resolucion"].notna().astype(int)

    df["dias_abierto"] = np.where(
        df["fecha_resolucion"].isna(),
        (pd.Timestamp.now() - df["fecha_creacion"]).dt.days,
        (df["fecha_resolucion"] - df["fecha_creacion"]).dt.days,
    )

    return df


# =========================
# SLA PRIORIDAD
# =========================
def completar_sla_prioridad(df):
    df = df.copy()

    df["sla_horas_objetivo"] = (
        df["prioridad"]
        .map(SLA_PRIORIDAD_HORAS)
        .fillna(DEFAULT_SLA_HORAS)
    )

    df["sla_prioridad_cumple"] = np.where(
        df["horas_resolucion"] <= df["sla_horas_objetivo"],
        1,
        0
    )

    df["sla_prioridad_incumple"] = np.where(
        df["horas_resolucion"] > df["sla_horas_objetivo"],
        1,
        0
    )

    df["en_riesgo_sla"] = np.where(
        (df["resuelto"] == 0) &
        (df["dias_abierto"] * 24 > df["sla_horas_objetivo"]),
        1,
        0
    )

    return df


# =========================
# SLA SIZE
# =========================
def completar_sla_size(df):
    df = df.copy()

    df["sla_size_dias"] = (
        df["size"]
        .astype(str)
        .str.strip()
        .map(SLA_SIZE_DIAS)
    )

    df["desviacion_sla"] = df["dias_resolucion"] - df["sla_size_dias"]

    df["sla_size_cumple"] = np.where(
        df["dias_resolucion"] <= df["sla_size_dias"],
        1,
        0
    )

    df.loc[df["sla_size_dias"].isna(), "sla_size_cumple"] = np.nan

    return df


# =========================
# PIPELINE SLA COMPLETO
# =========================
def completar_sla(df):
    df = completar_metricas_resolucion(df)
    df = completar_sla_prioridad(df)
    df = completar_sla_size(df)

    # =========================
    # SLA GLOBAL (PRO)
    # =========================
    df["sla_global_cumple"] = np.where(
        (df["sla_prioridad_cumple"] == 1) &
        (df["sla_size_cumple"] == 1),
        1,
        0
    )

    return df