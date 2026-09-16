"""
Cálculo de métricas y KPIs.
"""

import re
import pandas as pd

import limites
from bono import calcular_bono_por_cliente
from config import TECNICOS_PERMITIDOS


def pct(series):
    if series is None or series.empty:
        return 0.0
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return 0.0
    value = numeric.mean(skipna=True)
    if pd.isna(value):
        return 0.0
    return float(round(value * 100, 1))


REOPENED_TERMS = [
    r"\breabiert",
    r"\breabrid",
    r"\breabrir",
    r"\breopen",
    r"\breopened",
    r"\breapertura",
    r"\breabro",
    r"\breabrimos",
    r"\bopen again\b",
    r"\bopened again\b",
    r"\breopening",
    r"\breopened again",
    r"\breopens",
    r"\breopen as",
    r"\bde nuevo\b",
    r"\bde nuevo\b",
]


def calculate_sla_kpis(df):
    total_tickets = len(df)
    tickets_resueltos = int(df["resuelto"].sum()) if "resuelto" in df else 0
    dias_promedio = 0.0
    if "dias_resolucion" in df and not df["dias_resolucion"].dropna().empty:
        dias_promedio = float(round(df["dias_resolucion"].mean(skipna=True), 1))

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
        "total_tecnicos": df.loc[df["asignado_a"].isin(TECNICOS_PERMITIDOS), "asignado_a"].nunique(),
    }


def calculate_ticket_trends(df):
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
    return (
        df["estado"].fillna("Sin estado")
        .value_counts()
        .reset_index(name="tickets")
        .rename(columns={"index": "estado"})
    )


def calculate_priority_summary(df):
    priority_order = ["Highest", "High", "Medium", "Low", "Lowest"]
    summary = (
        df["prioridad"].fillna("Sin prioridad")
        .value_counts()
        .reset_index(name="tickets")
        .rename(columns={"index": "prioridad"})
    )
    summary["orden"] = summary["prioridad"].apply(
        lambda x: priority_order.index(x) if x in priority_order else len(priority_order)
    )
    return summary.sort_values(["orden", "tickets"], ascending=[True, False]).drop(columns=["orden"])


def calculate_technician_sla_summary(df, top_n=15):
    ranking = calculate_technician_ranking(df)
    return ranking.head(top_n)


def calculate_reopened_tickets(df):
    """
    Identifica tickets reabiertos combinando dos señales:
    - Fiable: el ticket tuvo una fecha de resolucion pero su statusCategory
      de Jira ya no es "done" (ver sla.completar_metricas_resolucion).
    - Heuristica de texto: menciones de "reabierto"/"reopen" en el resumen
      o la descripcion, para los casos que la senal anterior no cubra.
    """
    if df.empty:
        return pd.DataFrame(columns=["ticket_id", "resumen", "estado", "cliente", "asignado_a", "fecha_creacion", "fecha_resolucion"])

    def is_reopened(row):
        text_parts = [
            row.get("resumen", ""),
            row.get("descripcion", ""),
            row.get("titulo_ticket", ""),
            row.get("estado", ""),
        ]
        text = " ".join(str(part or "") for part in text_parts).lower()
        return any(re.search(term, text) for term in REOPENED_TERMS)

    mask = df.apply(is_reopened, axis=1)
    if "reabierto_detectado" in df.columns:
        mask = mask | df["reabierto_detectado"].astype(bool)

    cols = [c for c in ["ticket_id", "resumen", "tipo", "estado", "cliente", "asignado_a", "fecha_creacion", "fecha_resolucion", "prioridad", "size", "descripcion"] if c in df.columns]
    return df.loc[mask, cols].copy()


def calculate_sla_size_comparison(df):
    sla_size_df = (
        df[df["sla_size_dias"].notna()]
        .groupby("size")
        .agg(
            tickets=("ticket_id", "nunique"),
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
    ranking = (
        df[df["asignado_a"].isin(TECNICOS_PERMITIDOS)]
        .groupby("asignado_a")
        .agg(
            tickets=("ticket_id", "nunique"),
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


def _ultimo_valor_no_nulo(serie):
    """Primer valor no nulo de la serie -- se llama sobre datos ya ordenados por fecha desc, asi que es "el mas reciente"."""
    no_nulos = serie.dropna()
    return no_nulos.iloc[0] if not no_nulos.empty else None


def calculate_top_clients(df):
    """
    Devuelve todos los clientes consultados en Jira ordenados por volumen de
    tareas, con su Plan/Tipo (valor mas reciente en Jira) y el saldo de su
    bono de horas (ver bono.py).
    """
    data = df.copy()
    data["cliente"] = data["cliente"].fillna("Sin cliente")
    for columna in ("cliente_domain", "sla_global_cumple", "dias_resolucion", "horas_resolucion", "plan_servicio", "tipo_producto"):
        if columna not in data.columns:
            data[columna] = pd.NA
    data["horas_resolucion"] = pd.to_numeric(data["horas_resolucion"], errors="coerce")

    clientes_df = (
        data.groupby("cliente", dropna=False)
        .agg(
            tickets=("ticket_id", "nunique"),
            dominios=("cliente_domain", lambda values: ", ".join(sorted(set(values.dropna())))),
            sla=("sla_global_cumple", "mean"),
            tiempo_horas=("horas_resolucion", "mean"),
            tickets_sin_tiempo=("horas_resolucion", lambda values: int(values.isna().sum())),
        )
        .reset_index()
        .sort_values("tickets", ascending=False)
    )

    if not clientes_df.empty:
        clientes_df["sla"] = (clientes_df["sla"] * 100).round(1)
        clientes_df["tiempo_horas"] = clientes_df["tiempo_horas"].round(1)

    # Plan/Tipo: el valor mas reciente visto en Jira para cada cliente.
    data_reciente = data.sort_values("fecha_creacion", ascending=False) if "fecha_creacion" in data.columns else data
    ultimos = (
        data_reciente.groupby("cliente", dropna=False)
        .agg(plan=("plan_servicio", _ultimo_valor_no_nulo), tipo=("tipo_producto", _ultimo_valor_no_nulo))
        .reset_index()
    )
    clientes_df = clientes_df.merge(ultimos, on="cliente", how="left")

    # Bono de horas: comprado, consumido y saldo disponible de cada cliente
    # (0 si nunca ha comprado un bono).
    bono_df = calcular_bono_por_cliente(data)
    if not bono_df.empty:
        clientes_df = clientes_df.merge(
            bono_df[["comprado", "consumido", "disponible"]].rename(
                columns={
                    "comprado": "bono_comprado",
                    "consumido": "horas_consumidas",
                    "disponible": "bono_disponible",
                }
            ),
            left_on="cliente",
            right_index=True,
            how="left",
        )
    else:
        clientes_df["bono_comprado"] = 0.0
        clientes_df["horas_consumidas"] = 0.0
        clientes_df["bono_disponible"] = 0.0
    for columna in ("bono_comprado", "horas_consumidas", "bono_disponible"):
        clientes_df[columna] = clientes_df[columna].fillna(0.0)

    # Limite contratado = suma de los bonos comprados, con el valor manual
    # como respaldo mientras el cliente no tenga ningun bono (ver
    # limites.limite_efectivo).
    manuales = limites.obtener_limites_manuales()
    limite_calculado = [
        limites.limite_efectivo(cliente_nombre, comprado, manuales=manuales)
        for cliente_nombre, comprado in zip(clientes_df["cliente"], clientes_df["bono_comprado"])
    ]
    clientes_df["limite"] = [valor for valor, _ in limite_calculado]
    clientes_df["limite_origen"] = [origen for _, origen in limite_calculado]

    # Horas que le quedan al cliente. Con bonos es exactamente el saldo del
    # bono; con un limite puesto a mano es ese limite menos lo consumido, de
    # modo que el semaforo funciona igual en los dos casos.
    clientes_df["disponible"] = clientes_df["limite"] - clientes_df["horas_consumidas"]

    return clientes_df


def apply_resolution_hour_overrides(df, overrides):
    """Aplica correcciones manuales de horas sin modificar la respuesta de Jira."""
    result = df.copy()
    if not overrides or "ticket_id" not in result.columns:
        return result

    if "horas_resolucion" not in result.columns:
        result["horas_resolucion"] = pd.NA
    result["horas_resolucion"] = pd.to_numeric(result["horas_resolucion"], errors="coerce")
    result["dias_resolucion"] = result["horas_resolucion"] / 24
    for ticket_id, hours in overrides.items():
        mask = result["ticket_id"].eq(ticket_id)
        result.loc[mask, "horas_resolucion"] = float(hours)
        result.loc[mask, "dias_resolucion"] = float(hours) / 24
        if "horas_transcurridas" in result.columns:
            result.loc[mask, "horas_transcurridas"] = float(hours)
        if "diferencia_horas" in result.columns and "presupuesto" in result.columns:
            result.loc[mask, "diferencia_horas"] = float(hours) - result.loc[mask, "presupuesto"]
    return result


def calculate_client_ticket_detail(df, cliente):
    """
    Devuelve todos los tickets de un cliente concreto con sus métricas de tiempo.
    """
    cols_disponibles = [
        "ticket_id",
        "cliente_nombre",
        "cliente_domain",
        "cliente_url",
        "resumen",
        "tipo",
        "plan_servicio",
        "tipo_producto",
        "estado",
        "resuelto",
        "prioridad",
        "size",
        "asignado_a",
        "fecha_creacion",
        "fecha_resolucion",
        "dias_resolucion",
        "horas_resolucion",
        "horas_pending_info",
        "horas_trabajo_real",
        "presupuesto",
        "diferencia_horas",
        "sla_prioridad_cumple",
        "sla_size_cumple",
        "desviacion_sla",
    ]

    detalle = df[df["cliente"] == cliente].copy()
    cols = [c for c in cols_disponibles if c in detalle.columns]
    return detalle[cols].sort_values("fecha_creacion", ascending=False)
