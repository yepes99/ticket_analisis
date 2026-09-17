"""
Pagina de Clientes: ranking, detalle individual y limite de horas contratadas.

Accesible por Web Admin, Soporte, CS y Lector.
- Web Admin: acceso completo, incluida la aprobacion de solicitudes (desde
  el Dashboard). Tambien puede ver el ranking y el detalle de clientes
  directamente en el Dashboard.
- Soporte y CS: pueden solicitar correcciones de horas de un ticket y cambios
  en el limite de horas contratadas de un cliente; ambas quedan pendientes
  hasta que un Web Admin las aprueba o rechaza.
- CS ademas tiene vista resumida (horas, presupuesto, limite, estado), sin el
  detalle tecnico de cada ticket.
- Lector: solo consulta, no puede solicitar nada.
"""

from datetime import datetime, timedelta

import streamlit as st

import busqueda
import config
import historial
import solicitudes
from auth import check_clientes_authentication, render_logout_button
from data import apply_filters, render_filters, validate_columns
from metrics import apply_resolution_hour_overrides
from periodos import PERIODOS, available_years, resolve_query_dates
from process import cargar_tickets_jira
from clientes_ui import (
    filtrar_tickets_clientes_wordpress,
    render_detalle_cliente,
    render_historico_cambios,
    render_ranking_clientes,
)
from ui_components import empty_state, render_hero_header, section_title


# =========================
# AUTENTICACIÓN (defensa en profundidad; el router ya filtro el acceso)
# =========================
check_clientes_authentication()
render_logout_button()

if st.session_state.get("role") == "admin":
    pendientes_count = solicitudes.contar_pendientes()
    if pendientes_count:
        st.sidebar.warning(f"🔔 {pendientes_count} solicitud(es) pendiente(s) — apruebalas en el Dashboard.")


# =========================
# SIDEBAR - CARGA DE DATOS
# =========================
st.sidebar.markdown("## Carga de datos")
st.sidebar.caption("Consulta Jira con el token configurado en secretos.")

if "clientes_df" not in st.session_state:
    st.session_state["clientes_df"] = None

periodo = st.sidebar.selectbox("Periodo", PERIODOS, key="clientes_periodo")
selected_year = datetime.now().year
if periodo == "Ano":
    selected_year = st.sidebar.selectbox("Ano", available_years(), key="clientes_year")
custom_range = None
if periodo == "Personalizado":
    today = datetime.now().date()
    custom_range = st.sidebar.date_input(
        "Desde / hasta",
        value=(today - timedelta(days=30), today),
        max_value=today,
        key="clientes_custom_range",
    )
    if len(custom_range) != 2:
        st.sidebar.warning("Selecciona una fecha inicial y una fecha final.")
        st.stop()
    if custom_range[0] > custom_range[1]:
        st.sidebar.error("La fecha inicial debe ser anterior o igual a la fecha final.")
        st.stop()

query_start_date, query_end_date = resolve_query_dates(periodo, selected_year, custom_range)

if st.sidebar.button("Consultar Jira", type="primary", width="stretch", key="clientes_consultar"):
    with st.spinner("Consultando Jira..."):
        datos = cargar_tickets_jira(start_date=query_start_date, end_date=query_end_date)
    is_valid, missing = validate_columns(datos)
    if not is_valid:
        st.sidebar.error(f"Faltan columnas: {missing}")
        st.stop()
    st.session_state["clientes_df"] = datos

st.sidebar.markdown("---")
st.sidebar.caption("Los datos se consultan directamente desde Jira.")


# =========================
# CARGA DE DATOS
# =========================
if st.session_state["clientes_df"] is None:
    st.info("Elige el periodo en la barra lateral y pulsa 'Consultar Jira' para cargar los clientes.")
    st.stop()

df = st.session_state["clientes_df"]
clientes_filter, asignadores_filter, sizes_filter, estados_filter = render_filters(df)

filtered = apply_filters(
    df,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
    estados=estados_filter,
)
filtered = apply_resolution_hour_overrides(filtered, solicitudes.obtener_overrides_horas_aprobados())

role = st.session_state.get("role")

if filtered.empty:
    st.warning("No se encontraron bugs en los datos de Jira para el periodo seleccionado.")
    st.stop()


# =========================
# CABECERA
# =========================
render_hero_header(
    title="Clientes — horas contratadas y consumo",
    description="Ranking de clientes, detalle ticket a ticket y control del presupuesto frente al tiempo de desarrollo.",
    timestamp=datetime.now().strftime(config.DATE_FORMAT),
)


# =========================
# BUSQUEDA DE TICKET
# =========================
# Filtra las dos pestañas a la vez. El ticket elegido enseña ademas su
# ficha; si es de una fecha fuera del periodo cargado, la ficha se trae de
# Jira y el resto de la pagina no se toca. Para buscar un cliente, usa el
# buscador de la tabla "Tickets por cliente" o el selector de "Detalle por
# cliente" (ver busqueda.py).
ticket_buscado = busqueda.render_panel_busqueda(filtered, key_prefix="clientes_")
busqueda.render_ficha_ticket(filtered, ticket_buscado)
filtered = busqueda.aplicar_busqueda(filtered, ticket_buscado)

if filtered.empty:
    st.warning("Ningun ticket cumple a la vez los filtros de la barra lateral y la busqueda.")
    st.stop()


# =========================
# PESTAÑAS PRINCIPALES
# =========================
tabs = st.tabs(["📊 Ranking de clientes", "🔍 Detalle por cliente", "🧩 Clientes WordPress", "📜 Historial de cambios"])

with tabs[0]:
    render_ranking_clientes(filtered, role=role)

with tabs[1]:
    render_detalle_cliente(filtered, role)

with tabs[2]:
    section_title(
        "🧩 Clientes WordPress",
        "Solo clientes en plan WP Smart, WP Custom o WP Advanced — los unicos con limite de horas contratado gestionable.",
    )
    filtered_wp = filtrar_tickets_clientes_wordpress(filtered)
    if filtered_wp.empty:
        empty_state("Ningun cliente del periodo/filtros actuales esta en plan WP Smart, WP Custom o WP Advanced.")
    else:
        render_ranking_clientes(filtered_wp, role=role, key_prefix="wp_")

with tabs[3]:
    section_title(
        "📜 Historial de cambios",
        "Cambios de horas y de limite pedidos sobre cualquier cliente, de lo mas reciente a lo mas antiguo.",
    )
    col_timeline, col_tabla = st.columns([1, 1.6])
    with col_timeline:
        historial.render_cambios_recientes(limite=8, titulo="Lo ultimo")
    with col_tabla:
        render_historico_cambios()
