import streamlit as st

from config import REQUIRED_COLUMNS, TECNICOS_PERMITIDOS
from process import cargar_tickets_jira


def load_jira_data(max_results=None, start_date=None, end_date=None, jql=None):
    return cargar_tickets_jira(
        max_results=max_results,
        start_date=start_date,
        end_date=end_date,
        jql=jql,
    )


def validate_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return len(missing) == 0, missing


def load_and_validate_jira_data(max_results=None, start_date=None, end_date=None, jql=None):
    try:
        df = load_jira_data(
            max_results=max_results,
            start_date=start_date,
            end_date=end_date,
            jql=jql,
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

    return clientes, asignadores, sizes


def apply_filters(df, clientes=None, asignadores=None, sizes=None):
    filtered = df.copy()

    if clientes:
        filtered = filtered[filtered["cliente"].isin(clientes)]

    if asignadores:
        filtered = filtered[filtered["asignado_a"].isin(asignadores)]

    if sizes:
        filtered = filtered[filtered["size"].isin(sizes)]

    return filtered
