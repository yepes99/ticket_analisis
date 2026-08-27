import pandas as pd
import streamlit as st

from config import REQUIRED_COLUMNS, TECNICOS_PERMITIDOS
from process import cargar_tickets_jira


def load_jira_data(max_results=100, start_date=None, end_date=None):
    return cargar_tickets_jira(
        max_results=max_results,
        start_date=start_date,
        end_date=end_date,
    )


def validate_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return len(missing) == 0, missing


def load_and_validate_jira_data(max_results=100, start_date=None, end_date=None):
    try:
        df = load_jira_data(
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        st.error(f"Error cargando datos desde Jira: {exc}")
        st.write("Revisa la configuracion de Jira, el token de acceso y los filtros de fecha.")
        st.stop()

    is_valid, missing = validate_columns(df)
    if not is_valid:
        st.error(f"Faltan columnas: {missing}")
        st.write("Columnas detectadas:", df.columns.tolist())
        st.stop()

    return df


def render_filters(df):
    st.sidebar.markdown("## Filtros")

    clientes = []
    if "cliente" in df.columns:
        clientes = st.sidebar.multiselect(
            "Cliente",
            sorted(df["cliente"].dropna().unique()),
        )

    asignadores_disponibles = []
    if "asignado_a" in df.columns:
        asignadores_disponibles = sorted(df["asignado_a"].dropna().unique())
    asignadores_permitidos = [t for t in asignadores_disponibles if t in TECNICOS_PERMITIDOS]
    asignadores_options = asignadores_permitidos if asignadores_permitidos else asignadores_disponibles

    asignadores = st.sidebar.multiselect(
        "Tecnico asignado",
        sorted(asignadores_options),
    )

    sizes = []
    if "size" in df.columns:
        sizes = st.sidebar.multiselect(
            "Size",
            sorted(df["size"].dropna().unique()),
        )

    if "fecha_creacion" in df.columns and not df["fecha_creacion"].dropna().empty:
        min_date = df["fecha_creacion"].min().date()
        max_date = df["fecha_creacion"].max().date()
    else:
        today = pd.Timestamp.now().date()
        min_date = today
        max_date = today

    date_range = st.sidebar.date_input(
        "Refinar fecha de creacion",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    return clientes, asignadores, sizes, date_range


def apply_filters(df, clientes=None, asignadores=None, sizes=None, date_range=None):
    filtered = df.copy()

    if clientes:
        filtered = filtered[filtered["cliente"].isin(clientes)]

    if asignadores:
        filtered = filtered[filtered["asignado_a"].isin(asignadores)]

    if sizes:
        filtered = filtered[filtered["size"].isin(sizes)]

    if date_range and len(date_range) == 2 and "fecha_creacion" in filtered.columns:
        start_date, end_date = date_range
        fecha_creacion = pd.to_datetime(filtered["fecha_creacion"], errors="coerce")
        start_dt = pd.Timestamp(start_date).normalize()
        end_dt = pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1)

        mask = fecha_creacion.notna() & (fecha_creacion >= start_dt) & (fecha_creacion < end_dt)
        filtered = filtered.loc[mask]

    return filtered
