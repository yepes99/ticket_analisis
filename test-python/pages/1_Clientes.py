"""
Pagina de Clientes: ranking, detalle individual y limite de horas contratadas.

Accesible por administradores y por usuarios de clientes (contrasena propia,
ver auth.check_clientes_authentication). Solo los administradores pueden
corregir horas de resolucion o modificar el limite de horas de un cliente.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.column_config as stcc

import config
import limites
from styles import apply_styles
from auth import check_clientes_authentication
from data import apply_filters, render_filters, validate_columns
from metrics import (
    apply_resolution_hour_overrides,
    calculate_client_ticket_detail,
    calculate_top_clients,
)
from charts import create_top_clients_chart
from periodos import PERIODOS, available_years, resolve_query_dates
from process import cargar_tickets_jira
from ui_components import empty_state, kpi_grid, render_chart_wrapper, section_title


st.set_page_config(**config.PAGE_CONFIG)
apply_styles()

check_clientes_authentication()


@st.cache_data(ttl=300, show_spinner="Consultando Jira...")
def _cargar_datos_clientes(start_date, end_date):
    return cargar_tickets_jira(start_date=start_date, end_date=end_date)


# =========================
# SIDEBAR - CARGA DE DATOS
# =========================
st.sidebar.markdown("## Carga de datos")
st.sidebar.caption("Consulta Jira con el token configurado en secretos.")

if "clientes_df" not in st.session_state:
    st.session_state["clientes_df"] = None
if "resolution_hour_overrides" not in st.session_state:
    st.session_state["resolution_hour_overrides"] = {}

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
    datos = _cargar_datos_clientes(query_start_date, query_end_date)
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
clientes_filter, asignadores_filter, sizes_filter = render_filters(df)

filtered = apply_filters(
    df,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
)
filtered = apply_resolution_hour_overrides(filtered, st.session_state["resolution_hour_overrides"])

if filtered.empty:
    st.warning("No se encontraron bugs en los datos de Jira para el periodo seleccionado.")
    st.stop()


# =========================
# CLIENTES — RESUMEN
# =========================
section_title(
    "Tickets por cliente",
    "Conteo exacto de bugs Jira unicos, con el nombre comercial separado del dominio.",
)
clientes_resumen = calculate_top_clients(filtered)
if not clientes_resumen.empty:
    chart_col, table_col = st.columns([1, 1.35], gap="large")
    with chart_col:
        render_chart_wrapper(create_top_clients_chart(clientes_resumen.head(20)))
    with table_col:
        st.dataframe(
            clientes_resumen,
            width="stretch",
            hide_index=True,
            column_config={
                "cliente": stcc.TextColumn("Cliente", width="medium"),
                "dominios": stcc.TextColumn("Domain / URL", width="large"),
                "tickets": stcc.NumberColumn("Tickets Bug", format="%d"),
                "tickets_sin_tiempo": stcc.NumberColumn("Sin tiempo", format="%d"),
                "sla": stcc.NumberColumn("SLA global", format="%.1f%%"),
                "tiempo_horas": stcc.NumberColumn("Tiempo medio", format="%.1f h"),
            },
        )
else:
    empty_state("No hay clientes para los filtros actuales.")


# =========================
# CLIENTES — DETALLE POR CLIENTE
# =========================
section_title(
    "🔍 Detalle de tareas por cliente",
    "Selecciona un cliente para ver sus tareas, su tiempo de resolucion y el consumo frente al limite de horas contratado.",
)

clientes_disponibles = sorted(filtered["cliente"].dropna().unique().tolist())

cliente_seleccionado = st.selectbox(
    "Selecciona un cliente para ver su detalle",
    options=[""] + clientes_disponibles,
    index=0,
    format_func=lambda x: "— Elige un cliente —" if x == "" else x,
)

if cliente_seleccionado:
    detalle_df = calculate_client_ticket_detail(filtered, cliente_seleccionado)
    is_admin = st.session_state.get("role") == "admin"

    if is_admin:
        with st.expander("Corregir horas de resolucion", expanded=False):
            st.caption("Los tickets abiertos o sin resolutiondate aparecen sin tiempo. La correccion se guarda solo en esta sesion.")
            ticket_options = detalle_df["ticket_id"].dropna().astype(str).tolist()
            if ticket_options:
                ticket_to_edit = st.selectbox("Ticket", ticket_options, key="ticket_to_edit")
                current_hours = detalle_df.loc[
                    detalle_df["ticket_id"].astype(str).eq(ticket_to_edit), "horas_resolucion"
                ].iloc[0]
                corrected_hours = st.number_input(
                    "Horas correctas",
                    min_value=0.0,
                    value=float(current_hours) if pd.notna(current_hours) else 0.0,
                    step=0.25,
                    key="corrected_hours",
                )
                if st.button("Guardar correccion", key="save_hours_correction", width="stretch"):
                    st.session_state["resolution_hour_overrides"][ticket_to_edit] = corrected_hours
                    st.rerun()

    total = len(detalle_df)
    if "resuelto" in detalle_df.columns:
        resueltos = int(detalle_df["resuelto"].sum())
    elif "estado" in detalle_df.columns:
        resueltos = int(detalle_df["estado"].astype(str).str.lower().eq("finalizada").sum())
    else:
        resueltos = 0

    horas_totales = pd.to_numeric(detalle_df.get("horas_resolucion"), errors="coerce").sum()
    limite_actual = limites.obtener_limite(cliente_seleccionado)

    kpi_items = [
        ("Tareas", str(total), f"Total de {cliente_seleccionado}", ""),
        ("Resueltas", str(resueltos), "En estado Finalizada", "success"),
        ("Horas consumidas", f"{horas_totales:.1f} h", "Suma de horas de resolucion de todos sus tickets", ""),
    ]
    if limite_actual is not None:
        sobre_limite = horas_totales > limite_actual
        kpi_items.append(
            (
                "Limite contratado",
                f"{limite_actual:.1f} h",
                "Por encima del limite contratado" if sobre_limite else "Dentro del limite contratado",
                "danger" if sobre_limite else "success",
            )
        )
    else:
        kpi_items.append(("Limite contratado", "Sin definir", "Un administrador puede configurarlo abajo", ""))

    kpi_grid(kpi_items)

    if is_admin:
        with st.expander("Configurar limite de horas del cliente", expanded=False):
            nuevo_limite = st.number_input(
                "Limite de horas contratadas",
                min_value=0.0,
                value=float(limite_actual) if limite_actual is not None else 0.0,
                step=1.0,
                key="nuevo_limite_horas",
            )
            if st.button("Guardar limite", key="guardar_limite_horas", width="stretch"):
                limites.actualizar_limite(
                    cliente_seleccionado,
                    nuevo_limite,
                    usuario=st.session_state.get("username") or "admin",
                )
                st.rerun()

            historial = limites.obtener_historial(cliente_seleccionado)
            if historial:
                st.caption("Historico de cambios del limite")
                st.dataframe(
                    pd.DataFrame(historial),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "timestamp": "Fecha",
                        "usuario": "Usuario",
                        "valor_anterior": stcc.NumberColumn("Antes", format="%.1f h"),
                        "valor_nuevo": stcc.NumberColumn("Despues", format="%.1f h"),
                    },
                )

    if not detalle_df.empty:
        st.caption("Tareas ordenadas de mas reciente a mas antigua.")
        st.dataframe(
            detalle_df,
            width="stretch",
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "cliente_nombre": "Cliente",
                "cliente_domain": "Domain",
                "cliente_url": stcc.LinkColumn("URL", display_text="Abrir URL"),
                "resumen": stcc.TextColumn("Descripcion", width="large"),
                "tipo": "Tipo",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "asignado_a": "Tecnico",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "horas_resolucion": stcc.NumberColumn("Horas resolucion", format="%.1f h"),
            },
        )
    else:
        empty_state(f"No hay tareas para {cliente_seleccionado}.")
