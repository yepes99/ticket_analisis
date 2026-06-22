"""
Carga, validación y filtrado de datos.
"""

import streamlit as st
import pandas as pd
from process import cargar_tickets
from config import REQUIRED_COLUMNS, FILTER_COLUMNS
from ui_components import render_welcome_header, empty_state


@st.cache_data
def load_data(file):
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
    return cargar_tickets(file)


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
    st.info("Sube un CSV para comenzar.")
    return False


def load_and_validate_data(uploaded_file):
    """
    Carga y valida el archivo CSV. Detiene la app si hay errores.
    
    Args:
        uploaded_file: Archivo cargado por el usuario
        
    Returns:
        pd.DataFrame: DataFrame validado
    """
    try:
        df = load_data(uploaded_file)
    except Exception as exc:
        st.error(f"Error cargando CSV: {exc}")
        if hasattr(exc, "args") and exc.args:
            st.write("Revisa la cabecera del CSV y los nombres de columna esperados.")
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
        tuple: (clientes_filter, asignadores_filter, sizes_filter)
    """
    st.sidebar.markdown("## Filtros")

    clientes = st.sidebar.multiselect(
        "Cliente",
        sorted(df["cliente"].dropna().unique()),
    )

    asignadores = st.sidebar.multiselect(
        "Tecnico asignado",
        sorted(df["asignado_a"].dropna().unique()),
    )

    sizes = st.sidebar.multiselect(
        "Size",
        sorted(df["size"].dropna().unique()),
    )

    return clientes, asignadores, sizes


def apply_filters(df, clientes=None, asignadores=None, sizes=None):
    """
    Aplica filtros al DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame original
        clientes (list, optional): Lista de clientes a filtrar
        asignadores (list, optional): Lista de técnicos a filtrar
        sizes (list, optional): Lista de sizes a filtrar
        
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

    return filtered
