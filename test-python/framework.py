"""
Tareas del proyecto Framework Webplus (FW).

Los tecnicos de soporte no solo cierran bugs de WP: tambien hacen tareas
del framework. Esa carga no aparecia en ninguna parte del dashboard, asi
que al comparar el rendimiento del equipo faltaba la mitad de la foto:
alguien con pocos tickets WP podia estar cargado de tareas de FW.

Se traen con su propia consulta (FW_JQL en los secretos, o el JQL de mas
abajo por defecto) y se quedan solo las asignadas al equipo de soporte.

FW no es comparable con WP y por eso va en su propio bloque:
- no tiene el campo Size, asi que no hay SLA por tamaño;
- no tiene presupuesto de cliente ni bono de horas;
- su flujo no pasa por Backlog ("Tareas por hacer"), asi que no hay
  'horas_trabajo_real' y el unico tiempo fiable es 'dias_resolucion'.
"""

import pandas as pd

from config import TECNICOS_PERMITIDOS

# JQL por defecto. Se puede sobrescribir poniendo FW_JQL en la seccion
# [JIRA] de .streamlit/secrets.toml.
FW_JQL = 'project = "Framework Webplus"'

# El tecnico va primero: la tabla responde a "quien esta con que tarea de
# framework", no a "que tareas hay".
COLUMNAS_TABLA = [
    "asignado_a",
    "ticket_id",
    "resumen",
    "tipo",
    "estado",
    "prioridad",
    "fecha_creacion",
    "fecha_resolucion",
    "dias_resolucion",
]

# Un ticket sin tecnico del equipo no es carga nuestra; y los Epic son
# contenedores de otras tareas, contarlos inflaria el volumen.
TIPOS_EXCLUIDOS = {"epic"}


def leer_fw_jql(jira_config):
    """JQL de Framework Webplus: el de los secretos si esta, si no el de aqui."""
    return (jira_config or {}).get("FW_JQL") or FW_JQL


def filtrar_equipo(df):
    """
    Deja solo las tareas de FW asignadas al equipo de soporte, sin Epics.

    El proyecto Framework Webplus lo comparten varios equipos; aqui solo
    interesa lo que consume tiempo de Carmen y Alejandro.
    """
    if df is None or df.empty or "asignado_a" not in df.columns:
        return df.iloc[0:0] if df is not None else pd.DataFrame()

    tareas = df[df["asignado_a"].isin(TECNICOS_PERMITIDOS)]
    if "tipo" in tareas.columns:
        tareas = tareas[~tareas["tipo"].astype(str).str.strip().str.lower().isin(TIPOS_EXCLUIDOS)]
    return tareas


def resumen_fw(df):
    """Cifras de cabecera de las tareas de FW del equipo."""
    if df is None or df.empty:
        return {"total": 0, "resueltas": 0, "abiertas": 0, "dias_medios": None, "tecnicos": 0}

    if "resuelto" in df.columns:
        resueltas = int(pd.to_numeric(df["resuelto"], errors="coerce").fillna(0).sum())
    else:
        resueltas = int(df["fecha_resolucion"].notna().sum()) if "fecha_resolucion" in df.columns else 0

    dias = pd.to_numeric(df.get("dias_resolucion"), errors="coerce")
    return {
        "total": len(df),
        "resueltas": resueltas,
        "abiertas": len(df) - resueltas,
        "dias_medios": None if dias.dropna().empty else round(float(dias.mean()), 1),
        "tecnicos": int(df["asignado_a"].nunique()) if "asignado_a" in df.columns else 0,
    }


def tareas_por_tecnico(df):
    """
    {tecnico: nº de tareas de FW}, con un 0 para los tecnicos del equipo
    que no tienen ninguna (si no, en la comparativa pareceria que les
    falta el dato en vez de que no han tocado el framework).
    """
    conteo = {tecnico: 0 for tecnico in TECNICOS_PERMITIDOS}
    if df is None or df.empty or "asignado_a" not in df.columns:
        return conteo

    for tecnico, tareas in df["asignado_a"].value_counts().items():
        conteo[tecnico] = int(tareas)
    return conteo


def carga_por_tecnico(df):
    """
    {tecnico: {"total": n, "abiertas": m}} para la fila de tarjetas por
    persona. Incluye a los tecnicos sin ninguna tarea (con 0) para que se
    vea que no han tocado el framework, en vez de desaparecer de la fila.
    """
    carga = {tecnico: {"total": 0, "abiertas": 0} for tecnico in TECNICOS_PERMITIDOS}
    if df is None or df.empty or "asignado_a" not in df.columns:
        return carga

    resueltas = (
        pd.to_numeric(df["resuelto"], errors="coerce").fillna(0).astype(bool)
        if "resuelto" in df.columns
        else pd.Series(False, index=df.index)
    )
    for tecnico, tareas in df.groupby("asignado_a"):
        if tecnico not in carga:
            continue
        carga[tecnico] = {
            "total": len(tareas),
            "abiertas": int((~resueltas.loc[tareas.index]).sum()),
        }
    return carga


def detalle_fw(df):
    """
    Tabla de tareas de FW, de la mas reciente a la mas antigua.

    La fecha de resolucion y los dias van como texto porque la mayoria de
    tareas estan sin cerrar: en una columna de fecha o numerica cada hueco
    se pinta con un "None" gris, y aqui serian casi todas las filas.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA)

    columnas = [c for c in COLUMNAS_TABLA if c in df.columns]
    tabla = df[columnas].copy()

    # Primero lo que esta en curso (que es lo que se quiere saber: en que
    # anda cada uno ahora mismo), agrupado por tecnico y de lo mas reciente
    # a lo mas antiguo.
    if "resuelto" in df.columns:
        tabla["_abierta"] = ~pd.to_numeric(df["resuelto"], errors="coerce").fillna(0).astype(bool)
    else:
        tabla["_abierta"] = True

    criterios = [("_abierta", False)]
    if "asignado_a" in tabla.columns:
        criterios.append(("asignado_a", True))
    if "fecha_creacion" in tabla.columns:
        criterios.append(("fecha_creacion", False))

    tabla = tabla.sort_values(
        [columna for columna, _ in criterios],
        ascending=[ascendente for _, ascendente in criterios],
    ).drop(columns="_abierta")

    if "fecha_resolucion" in tabla.columns:
        fechas = pd.to_datetime(tabla["fecha_resolucion"], errors="coerce")
        tabla["fecha_resolucion"] = fechas.map(
            lambda v: "Sin cerrar" if pd.isna(v) else v.strftime("%d/%m/%Y")
        )

    if "dias_resolucion" in tabla.columns:
        dias = pd.to_numeric(tabla["dias_resolucion"], errors="coerce")
        tabla["dias_resolucion"] = dias.map(lambda v: "—" if pd.isna(v) else f"{v:.1f} días")

    return tabla
