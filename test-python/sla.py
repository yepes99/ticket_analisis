import numpy as np
import pandas as pd


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
RISK_THRESHOLD = 0.8

# Estado desde el que se considera que "cogen" el ticket (el tiempo de
# trabajo real empieza al salir de aqui) y estado cuyo tiempo se descuenta
# del computo desde creacion (esperando informacion, no es tiempo de
# trabajo). Ver _analizar_historial_estados.
ESTADO_COGIDO_DESDE = "Backlog"
ESTADO_PENDING_INFO = "Pending Info"

ESTADOS_RESUELTOS = {
    "finalizada",
    "finalizado",
    "done",
    "closed",
    "cerrada",
    "cerrado",
    "resuelta",
    "resuelto",
    "resolved",
    "completada",
    "completado",
    "terminada",
    "terminado",
}


def normalizar_prioridad(series):
    return series.astype("string").str.strip()


def normalizar_size(series):
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA, "<NA>": pd.NA})
    )


def _analizar_historial_estados(historial, cutoff):
    """
    A partir del historial de cambios de estado de un ticket (lista de
    dicts con fecha/de/a, ya ordenada por fecha), calcula:
    - horas_pending: horas pasadas en Pending Info hasta `cutoff` (si
      sigue en Pending Info a esa fecha, cuenta hasta `cutoff`).
    - fecha_cogido: cuando salio de Backlog por primera vez (o None si
      nunca ha salido, p.ej. sigue en Backlog).

    Cambios posteriores a `cutoff` (ticket resuelto y luego reabierto, o
    todavia sin llegar) no se tienen en cuenta.
    """
    if not historial or pd.isna(cutoff):
        return 0.0, None

    fecha_cogido = None
    pending_inicio = None
    horas_pending = 0.0

    for cambio in historial:
        fecha = cambio.get("fecha")
        if fecha is None or pd.isna(fecha) or fecha > cutoff:
            break
        if fecha_cogido is None and cambio.get("de") == ESTADO_COGIDO_DESDE:
            fecha_cogido = fecha
        if cambio.get("a") == ESTADO_PENDING_INFO and pending_inicio is None:
            pending_inicio = fecha
        elif cambio.get("de") == ESTADO_PENDING_INFO and pending_inicio is not None:
            horas_pending += (fecha - pending_inicio).total_seconds() / 3600
            pending_inicio = None

    if pending_inicio is not None:
        horas_pending += (cutoff - pending_inicio).total_seconds() / 3600

    return horas_pending, fecha_cogido


def completar_metricas_resolucion(df):
    df = df.copy()

    fecha_creacion = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    fecha_resolucion_bruta = pd.to_datetime(df["fecha_resolucion"], errors="coerce")
    ahora = pd.Timestamp.now()

    estado_normalizado = df["estado"].astype("string").fillna("").str.strip().str.lower()
    resuelto_por_nombre = estado_normalizado.isin(ESTADOS_RESUELTOS)

    if "categoria_estado" in df.columns:
        categoria_estado = df["categoria_estado"]
        # La statusCategory de Jira es la fuente fiable: a diferencia de
        # resolutiondate, se actualiza al reabrir un ticket (resolutiondate
        # se queda con la fecha antigua en muchos workflows de Jira).
        resuelto_bool = pd.Series(
            np.where(
                categoria_estado.notna(),
                categoria_estado.eq("done"),
                fecha_resolucion_bruta.notna() | resuelto_por_nombre,
            ),
            index=df.index,
        ).astype(bool)
    else:
        resuelto_bool = fecha_resolucion_bruta.notna() | resuelto_por_nombre

    df["resuelto"] = resuelto_bool.astype(int)

    # Ticket con fecha de resolucion antigua pero que ya no esta resuelto:
    # senal fiable de que se reabrio (mas fiable que buscar "reabierto" en
    # el texto, que solo detecta reaperturas mencionadas a mano).
    df["reabierto_detectado"] = (fecha_resolucion_bruta.notna() & ~resuelto_bool).astype(int)

    # fecha_resolucion efectiva: solo cuenta si el ticket esta realmente
    # resuelto ahora mismo. Evita fechas de resolucion "fantasma" en
    # tickets reabiertos (Jira no siempre limpia resolutiondate al reabrir).
    fecha_resolucion = fecha_resolucion_bruta.where(resuelto_bool)
    df["fecha_resolucion"] = fecha_resolucion

    fecha_fin = fecha_resolucion.where(fecha_resolucion.notna(), ahora)

    # Horas en Pending Info (se descuentan del tiempo desde creacion) y
    # fecha en que se "cogio" el ticket (sale de Backlog; el tiempo de
    # trabajo real desde ahi NO descuenta Pending Info).
    if "historial_estados" in df.columns:
        analisis = [
            _analizar_historial_estados(historial, cutoff)
            for historial, cutoff in zip(df["historial_estados"], fecha_fin)
        ]
        horas_pending = pd.Series([a[0] for a in analisis], index=df.index)
        fecha_cogido = pd.to_datetime(
            pd.Series([a[1] for a in analisis], index=df.index),
            errors="coerce",
        )
    else:
        horas_pending = pd.Series(0.0, index=df.index)
        fecha_cogido = pd.Series(pd.NaT, index=df.index)

    df["horas_pending_info"] = horas_pending.round(2)
    df["fecha_cogido"] = fecha_cogido

    df["horas_resolucion"] = (
        (fecha_resolucion - fecha_creacion).dt.total_seconds() / 3600 - horas_pending
    )
    df.loc[fecha_resolucion.isna() | fecha_creacion.isna(), "horas_resolucion"] = np.nan
    df["horas_resolucion"] = df["horas_resolucion"].round(2)

    df["dias_resolucion"] = df["horas_resolucion"] / 24

    df["horas_transcurridas"] = (
        (fecha_fin - fecha_creacion).dt.total_seconds() / 3600 - horas_pending
    )
    df.loc[fecha_creacion.isna(), "horas_transcurridas"] = np.nan
    df["horas_transcurridas"] = df["horas_transcurridas"].round(2)
    df["dias_abierto"] = np.floor(df["horas_transcurridas"] / 24)

    # Tiempo de trabajo real: desde que se "cogio" el ticket (sale de
    # Backlog) hasta que se resuelve/ahora, descontando tambien el tiempo
    # en Pending Info (esperar info del cliente no cuenta como trabajo,
    # ni desde la creacion ni desde que se coge).
    horas_trabajo_real = pd.Series(np.nan, index=df.index, dtype="float64")
    tiene_fecha_cogido = fecha_cogido.notna()
    horas_trabajo_real.loc[tiene_fecha_cogido] = (
        (fecha_fin.loc[tiene_fecha_cogido] - fecha_cogido.loc[tiene_fecha_cogido]).dt.total_seconds() / 3600
        - horas_pending.loc[tiene_fecha_cogido]
    )
    df["horas_trabajo_real"] = horas_trabajo_real.round(2)

    return df


def evaluar_cumplimiento(tiempo_resolucion, tiempo_transcurrido, objetivo, resuelto):
    tiempo_resolucion = pd.to_numeric(tiempo_resolucion, errors="coerce")
    tiempo_transcurrido = pd.to_numeric(tiempo_transcurrido, errors="coerce")
    objetivo = pd.to_numeric(objetivo, errors="coerce")
    resuelto = pd.to_numeric(resuelto, errors="coerce").fillna(0).astype(int)

    cumple = pd.Series(np.nan, index=objetivo.index, dtype="float64")
    resuelto_evaluable = (resuelto == 1) & tiempo_resolucion.notna() & objetivo.notna()
    abierto_vencido = (
        (resuelto == 0)
        & tiempo_transcurrido.notna()
        & objetivo.notna()
        & (tiempo_transcurrido > objetivo)
    )

    cumple.loc[resuelto_evaluable] = (
        tiempo_resolucion.loc[resuelto_evaluable] <= objetivo.loc[resuelto_evaluable]
    ).astype(float)
    cumple.loc[abierto_vencido] = 0.0
    return cumple


def calcular_en_riesgo(tiempo_transcurrido, objetivo, resuelto):
    tiempo_transcurrido = pd.to_numeric(tiempo_transcurrido, errors="coerce")
    objetivo = pd.to_numeric(objetivo, errors="coerce")
    resuelto = pd.to_numeric(resuelto, errors="coerce").fillna(0).astype(int)

    return (
        (resuelto == 0)
        & tiempo_transcurrido.notna()
        & objetivo.notna()
        & (tiempo_transcurrido >= objetivo * RISK_THRESHOLD)
        & (tiempo_transcurrido <= objetivo)
    ).astype(int)


def calcular_sla_global(sla_prioridad, sla_size):
    componentes = pd.concat(
        [
            pd.to_numeric(sla_prioridad, errors="coerce"),
            pd.to_numeric(sla_size, errors="coerce"),
        ],
        axis=1,
    )
    global_cumple = pd.Series(np.nan, index=componentes.index, dtype="float64")

    global_cumple.loc[(componentes == 0).any(axis=1)] = 0.0
    global_cumple.loc[componentes.notna().all(axis=1) & (componentes == 1).all(axis=1)] = 1.0
    return global_cumple


def completar_sla_prioridad(df):
    df = df.copy()

    df["sla_horas_objetivo"] = (
        normalizar_prioridad(df["prioridad"])
        .map(SLA_PRIORIDAD_HORAS)
        .fillna(DEFAULT_SLA_HORAS)
    )

    df["sla_prioridad_cumple"] = evaluar_cumplimiento(
        df["horas_resolucion"],
        df["horas_transcurridas"],
        df["sla_horas_objetivo"],
        df["resuelto"],
    )
    df["sla_prioridad_incumple"] = (df["sla_prioridad_cumple"] == 0).astype(int)
    df["en_riesgo_sla"] = calcular_en_riesgo(
        df["horas_transcurridas"],
        df["sla_horas_objetivo"],
        df["resuelto"],
    )

    return df


def completar_sla_size(df):
    df = df.copy()

    df["size"] = normalizar_size(df["size"])
    df["sla_size_dias"] = df["size"].map(SLA_SIZE_DIAS)
    df["desviacion_sla"] = df["dias_resolucion"] - df["sla_size_dias"]
    df["sla_size_cumple"] = evaluar_cumplimiento(
        df["dias_resolucion"],
        df["horas_transcurridas"] / 24,
        df["sla_size_dias"],
        df["resuelto"],
    )

    return df


def completar_presupuesto(df):
    """
    Compara las horas presupuestadas (campo Budget de Jira) con las horas
    consumidas (tiempo transcurrido desde creacion, en curso o hasta resolucion).
    """
    df = df.copy()

    if "presupuesto" not in df.columns:
        df["presupuesto"] = np.nan
    df["presupuesto"] = pd.to_numeric(df["presupuesto"], errors="coerce")

    df["diferencia_horas"] = df["horas_transcurridas"] - df["presupuesto"]

    return df


def completar_sla(df):
    df = completar_metricas_resolucion(df)
    df = completar_sla_prioridad(df)
    df = completar_sla_size(df)
    df["sla_global_cumple"] = calcular_sla_global(df["sla_prioridad_cumple"], df["sla_size_cumple"])
    df = completar_presupuesto(df)
    return df
