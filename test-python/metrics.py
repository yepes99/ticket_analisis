"""
Cálculo de métricas y KPIs.
"""

import pandas as pd


def pct(series):
    """
    Calcula el porcentaje promedio de una serie.
    
    Args:
        series (pd.Series): Serie a calcular
        
    Returns:
        float: Valor porcentual redondeado a 1 decimal
    """
    if series.empty:
        return 0.0
    value = series.mean()
    if pd.isna(value):
        return 0.0
    return round(value * 100, 1)


def calculate_sla_kpis(df):
    """
    Calcula los KPIs principales de SLA.
    
    - tickets_resueltos: Conteo de tickets donde estado = "Finalizada"
    - tickets_abiertos: Tickets que no están finalizados
    - tickets_incumplidos: Tickets que no cumplen SLA global
    - tickets_en_riesgo: Tickets en riesgo de incumplir SLA por prioridad
    - dias_resolucion_promedio: Promedio de días de resolución
    """
    total_tickets = len(df)
    tickets_resueltos = int(df["resuelto"].sum()) if "resuelto" in df else 0
    dias_promedio = 0.0
    if "dias_resolucion" in df and not df["dias_resolucion"].dropna().empty:
        dias_promedio = round(df["dias_resolucion"].mean(skipna=True), 1)

    return {
        "sla_prioridad": pct(df["sla_prioridad_cumple"]),
        "sla_size": pct(df["sla_size_cumple"]),
        "sla_global": pct(df["sla_global_cumple"]),
        "tickets_resueltos": tickets_resueltos,
        "tickets_abiertos": total_tickets - tickets_resueltos,
        "tickets_incumplidos": int((df["sla_global_cumple"] == 0).sum()),
        "tickets_en_riesgo": int(df["en_riesgo_sla"].sum()) if "en_riesgo_sla" in df else 0,
        "dias_resolucion_promedio": dias_promedio,
        "total_tickets": total_tickets,
        "total_clientes": df["cliente"].nunique(),
        "total_tecnicos": df["asignado_a"].nunique(),
    }


def calculate_ticket_trends(df):
    """
    Genera una serie temporal de tickets creados y resueltos.
    """
    created = df.groupby(df["fecha_creacion"].dt.to_period("D")).size().rename("creados")
    resolved = (
        df[df["fecha_resolucion"].notna()]
        .groupby(df["fecha_resolucion"].dt.to_period("D"))
        .size()
        .rename("resueltos")
    )

    trend = pd.concat([created, resolved], axis=1).fillna(0)
    trend.index = trend.index.to_timestamp()
    trend.index.name = "fecha"
    trend = trend.reset_index()
    trend["creados"] = trend["creados"].astype(int)
    trend["resueltos"] = trend["resueltos"].astype(int)

    return trend


def calculate_status_summary(df):
    """
    Calcula el resumen de tickets por estado.
    """
    return (
        df["estado"].fillna("Sin estado")
        .value_counts()
        .reset_index(name="tickets")
        .rename(columns={"index": "estado"})
    )


def calculate_priority_summary(df):
    """
    Calcula el resumen de tickets por prioridad.
    """
    priority_order = ["Highest", "High", "Medium", "Low", "Lowest"]
    summary = (
        df["prioridad"].fillna("Sin prioridad")
        .value_counts()
        .reset_index(name="tickets")
        .rename(columns={"index": "prioridad"})
    )
    summary["orden"] = summary["prioridad"].apply(lambda x: priority_order.index(x) if x in priority_order else len(priority_order))
    return summary.sort_values(["orden", "tickets"], ascending=[True, False]).drop(columns=["orden"])


def calculate_technician_sla_summary(df, top_n=15):
    """
    Calcula el resumen de SLA por técnico para display en gráfico.
    """
    ranking = calculate_technician_ranking(df)
    return ranking.head(top_n)


def calculate_sla_size_comparison(df):
    """
    Calcula la comparación entre SLA objetivo y tiempo real por size.
    
    Args:
        df (pd.DataFrame): DataFrame filtrado
        
    Returns:
        pd.DataFrame: DataFrame con comparación, vacío si no hay datos
    """
    sla_size_df = (
        df[df["sla_size_dias"].notna()]
        .groupby("size")
        .agg(
            tickets=("ticket_id", "count"),
            objetivo=("sla_size_dias", "mean"),
            real=("dias_resolucion", "mean"),
            cumplimiento=("sla_size_cumple", "mean"),
        )
        .reset_index()
    )

    if not sla_size_df.empty:
        sla_size_df["objetivo"] = sla_size_df["objetivo"].round(1)
        sla_size_df["real"] = sla_size_df["real"].round(1)
        sla_size_df["cumplimiento"] = (sla_size_df["cumplimiento"] * 100).round(1)

    return sla_size_df


def calculate_technician_ranking(df):
    """
    Calcula el ranking de técnicos por rendimiento.
    
    Args:
        df (pd.DataFrame): DataFrame filtrado
        
    Returns:
        pd.DataFrame: DataFrame con ranking, vacío si no hay datos
    """
    ranking = (
        df.groupby("asignado_a")
        .agg(
            tickets=("ticket_id", "count"),
            resueltos=("resuelto", "sum"),
            sla_size=("sla_size_cumple", "mean"),
            sla_prioridad=("sla_prioridad_cumple", "mean"),
            sla_global=("sla_global_cumple", "mean"),
            tiempo=("dias_resolucion", "mean"),
        )
        .reset_index()
    )

    if not ranking.empty:
        ranking["sla_size"] = (ranking["sla_size"] * 100).round(1)
        ranking["sla_prioridad"] = (ranking["sla_prioridad"] * 100).round(1)
        ranking["sla_global"] = (ranking["sla_global"] * 100).round(1)
        ranking["tiempo"] = ranking["tiempo"].round(1)

    return ranking.sort_values("tickets", ascending=False)


def calculate_top_clients(df, top_n=20):
    """
    Calcula los clientes con más tickets.
    
    Args:
        df (pd.DataFrame): DataFrame filtrado
        top_n (int): Número de clientes top a retornar
        
    Returns:
        pd.DataFrame: DataFrame con top clientes, vacío si no hay datos
    """
    clientes_df = (
        df.groupby("cliente")
        .agg(
            tickets=("ticket_id", "count"),
            sla=("sla_global_cumple", "mean"),
            tiempo=("dias_resolucion", "mean"),
        )
        .reset_index()
        .sort_values("tickets", ascending=False)
        .head(top_n)
    )

    if not clientes_df.empty:
        clientes_df["sla"] = (clientes_df["sla"] * 100).round(1)
        clientes_df["tiempo"] = clientes_df["tiempo"].round(1)

    return clientes_df
