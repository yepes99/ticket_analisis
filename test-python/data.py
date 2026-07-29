"""
Carga, validación y filtrado de datos.
"""

import streamlit as st
import pandas as pd
from process import (
    SNAPSHOT_FILE,
    cargar_snapshot_jira,
    cargar_tickets,
    cargar_tickets_jira,
    guardar_snapshot_jira,
)
from config import REQUIRED_COLUMNS, FILTER_COLUMNS, TECNICOS_PERMITIDOS
from ui_components import render_welcome_header, empty_state


def load_data(file, max_results=10):
    """
    Carga datos desde un archivo CSV.
    
    Args:
        file: Archivo CSV cargado
        
    Returns:
        pd.DataFrame: DataFrame con los tickets cargados
        
    Raises:
        Exception: Si hay error en el formato del CSV
    """
    if hasattr(file, "seek"):
        file.seek(0)
    if file is None:
        return cargar_tickets_jira(max_results=max_results)
    return cargar_tickets(file)


def load_snapshot_data():
    df = cargar_snapshot_jira()
    is_valid, missing = validate_columns(df)
    if not is_valid:
        raise ValueError(f"Snapshot incompleto. Faltan columnas: {missing}")
    return df


def snapshot_exists():
    return SNAPSHOT_FILE.exists()


def refresh_jira_snapshot():
    df = cargar_tickets_jira(max_results=None, page_size=100, pause_seconds=0.2)
    is_valid, missing = validate_columns(df)
    if not is_valid:
        raise ValueError(f"Datos de Jira incompletos. Faltan columnas: {missing}")
    guardar_snapshot_jira(df)
    return df


def validate_columns(df):
    """
    Valida que el DataFrame contenga las columnas requeridas.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        
    Returns:
        tuple: (is_valid, missing_columns)
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return len(missing) == 0, missing


def show_welcome_if_no_file():
    """
    Muestra pantalla de bienvenida si no hay archivo cargado.
    
    Returns:
        bool: True si debe continuar, False si debe detener
    """
    render_welcome_header()
    st.info("Cargando datos directamente desde Jira.")
    return False


def load_and_validate_data(uploaded_file, max_results=10):
    """
    Carga y valida los datos. Por defecto usa Jira si no se recibe un archivo CSV.
    
    Args:
        uploaded_file: Archivo cargado por el usuario
        
    Returns:
        pd.DataFrame: DataFrame validado
    """
    try:
        df = load_data(uploaded_file, max_results=max_results)
    except Exception as exc:
        st.error(f"Error cargando datos desde Jira: {exc}")
        if hasattr(exc, "args") and exc.args:
            st.write("Revisa la configuración de Jira y el token de acceso.")
        df = pd.DataFrame()
        st.stop()

    # Validar columnas requeridas
    is_valid, missing = validate_columns(df)
    if not is_valid:
        st.error(f"Faltan columnas: {missing}")
        st.write("Columnas detectadas:", df.columns.tolist())
        st.stop()

    return df


def render_filters(df):
    """
    Renderiza controles de filtro en la sidebar.
    
    Args:
        df (pd.DataFrame): DataFrame para obtener valores únicos
        
    Returns:
        tuple: (clientes_filter, asignadores_filter, sizes_filter, tipos_filter, date_range)
    """
    st.sidebar.markdown("## Filtros")

    clientes = []
    if "cliente" in df.columns:
        clientes = st.sidebar.multiselect(
            "Cliente",
            sorted(df["cliente"].dropna().unique()),
        )

    # Mostrar sólo los técnicos permitidos (si existen en el CSV)
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

    # No activity-type filter: keep filters to cliente, asignador y size

    # Manejo seguro de fechas: si no existe la columna o está vacía, usar hoy
    if "fecha_creacion" in df.columns and not df["fecha_creacion"].dropna().empty:
        min_date = df["fecha_creacion"].min().date()
        max_date = df["fecha_creacion"].max().date()
    else:
        today = pd.Timestamp.now().date()
        min_date = today
        max_date = today

    date_range = st.sidebar.date_input(
        "Rango de fecha de creación",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    return clientes, asignadores, sizes, date_range


def apply_filters(df, clientes=None, asignadores=None, sizes=None, date_range=None):
    """
    Aplica filtros al DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame original
        clientes (list, optional): Lista de clientes a filtrar
        asignadores (list, optional): Lista de técnicos a filtrar
        sizes (list, optional): Lista de sizes a filtrar
        tipos (list, optional): Lista de tipos de actividad a filtrar
        date_range (tuple, optional): Rango de fechas para fecha_creacion
        
    Returns:
        pd.DataFrame: DataFrame filtrado
    """
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
