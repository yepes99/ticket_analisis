"""
Estimacion del desarrollador frente al tiempo de desarrollo real.

El campo de Jira "Presupuesto cliente (en horas)" lo rellena el propio
desarrollador con las horas que cree que le va a costar el ticket. Aqui se
contrasta esa estimacion con 'horas_trabajo_real' (desde que coge el ticket
hasta que lo termina, descontando el tiempo en Pending Info), que es lo que
de verdad ha costado: sirve para ver como de bien se estima.

No se compara con 'horas_resolucion' ni con 'horas_transcurridas' porque
esas cuentan desde que se creo el ticket, e incluyen todo el rato que
estuvo en Backlog sin que nadie trabajase en el: no es tiempo de
desarrollo y ensuciaria la comparacion.
"""

import pandas as pd

from sla import PRESUPUESTO_AVISO_RATIO, PRESUPUESTO_GRAVE_RATIO

COLUMNAS = [
    "ticket_id",
    "cliente",
    "resumen",
    "estado",
    "asignado_a",
    "presupuesto_cliente",
    "horas_trabajo_real",
    "desviacion_presupuesto",
    "consumo_presupuesto",
]


def presupuesto_tono(presupuesto, trabajo_real):
    """
    Tono, icono y mensaje de un ticket frente a su estimacion.

    Verde mientras el desarrollo cabe en las horas estimadas, naranja hasta
    un 25% por encima y rojo a partir de ahi (ver PRESUPUESTO_*_RATIO).
    """
    presupuesto = pd.to_numeric(presupuesto, errors="coerce")
    trabajo_real = pd.to_numeric(trabajo_real, errors="coerce")

    if pd.isna(presupuesto) or presupuesto <= 0:
        return "neutral", "⚪", "Sin estimacion en Jira"
    if pd.isna(trabajo_real):
        return "neutral", "⚪", "Todavia sin tiempo de desarrollo registrado"

    ratio = trabajo_real / presupuesto
    desviacion = trabajo_real - presupuesto

    if ratio <= PRESUPUESTO_AVISO_RATIO:
        return "success", "🟢", f"Dentro de lo estimado ({abs(desviacion):.1f} h de margen)"
    if ratio <= PRESUPUESTO_GRAVE_RATIO:
        return "warning", "🟠", f"{desviacion:.1f} h de mas ({(ratio - 1) * 100:.0f}% sobre lo estimado)"
    return "danger", "🔴", f"{desviacion:.1f} h de mas ({(ratio - 1) * 100:.0f}% sobre lo estimado)"


def tickets_con_presupuesto(df):
    """
    Tickets que llevan relleno "Presupuesto cliente (en horas)", ordenados
    por desviacion (los que mas se han pasado de la estimacion, primero).
    """
    if df is None or df.empty or "presupuesto_cliente" not in df.columns:
        return pd.DataFrame(columns=COLUMNAS)

    con_presupuesto = df[pd.to_numeric(df["presupuesto_cliente"], errors="coerce").notna()]
    if con_presupuesto.empty:
        return pd.DataFrame(columns=COLUMNAS)

    columnas = [c for c in COLUMNAS if c in con_presupuesto.columns]
    tabla = con_presupuesto[columnas].copy()
    if "desviacion_presupuesto" in tabla.columns:
        tabla = tabla.sort_values("desviacion_presupuesto", ascending=False)
    return tabla


def resumen_presupuesto(df):
    """
    Cifras globales de acierto en la estimacion para un conjunto de
    tickets: cuantos llevan estimacion, cuantos se han pasado y cuantas
    horas se han ido de mas en total.
    """
    tabla = tickets_con_presupuesto(df)
    if tabla.empty:
        return {
            "con_presupuesto": 0,
            "dentro": 0,
            "pasados": 0,
            "horas_estimadas": 0.0,
            "horas_desarrollo": 0.0,
            "horas_exceso": 0.0,
            "pct_dentro": None,
        }

    estimadas = pd.to_numeric(tabla["presupuesto_cliente"], errors="coerce")
    desarrollo = pd.to_numeric(tabla.get("horas_trabajo_real"), errors="coerce")
    desviacion = desarrollo - estimadas

    # Solo cuentan como "dentro"/"pasados" los tickets que ya tienen tiempo
    # de desarrollo registrado; el resto todavia no se puede evaluar.
    evaluables = desviacion.notna()
    pasados = int((desviacion > 0).sum())

    return {
        "con_presupuesto": len(tabla),
        "dentro": int(evaluables.sum()) - pasados,
        "pasados": pasados,
        "horas_estimadas": float(estimadas.sum(skipna=True)),
        "horas_desarrollo": float(desarrollo.sum(skipna=True)),
        "horas_exceso": float(desviacion[desviacion > 0].sum(skipna=True)),
        "pct_dentro": None if not evaluables.any() else round((int(evaluables.sum()) - pasados) / int(evaluables.sum()) * 100, 1),
    }
