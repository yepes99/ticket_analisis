"""
Dashboard Jira Pro - pagina interna (Web Admin y Soporte).
"""

from datetime import datetime, timedelta
from io import BytesIO
import math
import streamlit as st

import busqueda
import config
import historial
from auth import check_authentication, render_logout_button
from bono import detectar_bonos_sin_cliente
from process import leer_config_jira
from data import (
    apply_filters,
    load_and_validate_jira_data,
    render_filters,
)
from report import generate_excel_report, generate_pdf_report
from ui_components import (
    render_hero_header,
    section_title,
    empty_state,
    kpi_grid,
    render_chart_wrapper,
)
from metrics import (
    apply_resolution_hour_overrides,
    calculate_sla_kpis,
    calculate_sla_size_comparison,
    calculate_technician_ranking,
    calculate_technician_sla_summary,
    calculate_top_clients,
    calculate_ticket_trends,
    calculate_status_summary,
    calculate_priority_summary,
    calculate_reopened_tickets,
)
import solicitudes
from clientes_ui import (
    render_detalle_cliente,
    render_historico_cambios,
    render_presupuesto_global,
    render_ranking_clientes,
    render_solicitudes_pendientes,
)
from charts import (
    create_sla_comparison_chart,
    create_status_bar_chart,
    create_priority_bar_chart,
    create_avg_resolution_chart,
)
from periodos import resolve_query_dates, available_years, PERIODOS
from backlog_metrics import calculate_backlog_detalle
import streamlit.column_config as stcc


def format_percent(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    try:
        return f"{int(round(float(value)))}%"
    except (TypeError, ValueError):
        return "-"


def sla_tone(value, objetivo=80, aviso=50):
    """
    Semaforo de 3 niveles para un % de cumplimiento SLA: verde >= objetivo,
    naranja entre aviso y objetivo, rojo por debajo de aviso. Con solo dos
    colores (verde/rojo) un 60% se veia en rojo igual que un 10%, sin
    distinguir "cerca del objetivo" de "muy lejos".
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(value):
        return ""
    if value >= objetivo:
        return "success"
    if value >= aviso:
        return "warning"
    return "danger"


# =========================
# AUTENTICACIÓN (defensa en profundidad; el router ya filtro el acceso)
# =========================
check_authentication()
render_logout_button()

role = st.session_state.get("role")
pendientes_count = solicitudes.contar_pendientes() if role == "admin" else 0
if pendientes_count:
    st.sidebar.warning(f"🔔 {pendientes_count} solicitud(es) pendiente(s) de aprobar, mas abajo.")


# =========================
# SOLICITUDES PENDIENTES (solo Web Admin)
# =========================
if pendientes_count:
    render_solicitudes_pendientes()


# =========================
# HISTÓRICO DE CAMBIOS DE HORAS Y LÍMITES (solo Web Admin)
# =========================
# Plegado por defecto: es un registro para consultar de vez en cuando, y
# abierto se comia la primera pantalla del dashboard.
if role == "admin":
    resueltas_count = solicitudes.contar_resueltas()
    with st.expander(f"📜 Histórico de cambios de horas y límites ({resueltas_count})", expanded=False):
        st.caption(
            "Todas las solicitudes ya resueltas (aprobadas o rechazadas), de cualquier cliente, "
            "con quién las pidió y quién las revisó."
        )
        col_timeline, col_tabla = st.columns([1, 1.6])
        with col_timeline:
            historial.render_cambios_recientes(limite=8, titulo="Lo ultimo")
        with col_tabla:
            render_historico_cambios()


# =========================
# SIDEBAR - CARGA DE DATOS
# =========================
st.sidebar.markdown("## Carga de datos")
st.sidebar.caption("Consulta Jira con el token configurado en secretos.")

if "jira_df" not in st.session_state:
    st.session_state["jira_df"] = None
if "jira_source" not in st.session_state:
    st.session_state["jira_source"] = None
if "jira_backlog_df" not in st.session_state:
    st.session_state["jira_backlog_df"] = None

periodo = st.sidebar.selectbox(
    "Periodo",
    PERIODOS,
)
selected_year = datetime.now().year
if periodo == "Ano":
    selected_year = st.sidebar.selectbox("Ano", available_years())
custom_range = None
if periodo == "Personalizado":
    today = datetime.now().date()
    custom_range = st.sidebar.date_input(
        "Desde / hasta",
        value=(today - timedelta(days=30), today),
        max_value=today,
    )
    if len(custom_range) != 2:
        st.sidebar.warning("Selecciona una fecha inicial y una fecha final.")
        st.stop()
    if custom_range[0] > custom_range[1]:
        st.sidebar.error("La fecha inicial debe ser anterior o igual a la fecha final.")
        st.stop()

query_start_date, query_end_date = resolve_query_dates(periodo, selected_year, custom_range)

if st.sidebar.button("Consultar Jira", type="primary", width="stretch"):
    with st.spinner("Consultando Jira..."):
        st.session_state["jira_df"] = load_and_validate_jira_data(
            max_results=None,
            start_date=query_start_date,
            end_date=query_end_date,
        )
        jira_config = leer_config_jira()
        st.session_state["jira_backlog_df"] = load_and_validate_jira_data(
            max_results=None,
            jql=jira_config["BACKLOG_JQL"],
        )
        inicio_label = query_start_date.strftime("%d/%m/%Y") if query_start_date else "el origen"
        periodo_label = f"{inicio_label} - {query_end_date.strftime('%d/%m/%Y')}"
        st.session_state["jira_source"] = f"Jira ({periodo_label})"

st.sidebar.markdown("---")
st.sidebar.caption("Los datos se consultan directamente desde Jira.")


# =========================
# CARGA DE DATOS
# =========================
if st.session_state["jira_df"] is None:
    render_hero_header(
        title="Dashboard Web” Equipo de Soporte",
        description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Leslie Jara · Carmen Yepes · Jorge Gallego.",
        timestamp=datetime.now().strftime(config.DATE_FORMAT),
    )
    st.info("Elige el periodo en la barra lateral para consultar Jira.")
    st.stop()

df = st.session_state["jira_df"]
source = st.session_state.get("jira_source") or "Jira"
st.sidebar.success(f"{len(df)} tickets cargados desde {source}.")


# =========================
# HEADER
# =========================
fecha_dashboard = datetime.now().strftime(config.DATE_FORMAT)
render_hero_header(
    title="Dashboard Web — Equipo de Soporte",
    description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Leslie Jara · Carmen Yepes · Jorge Gallego.",
    timestamp=fecha_dashboard,
)

# El buscador y la ficha del ticket se enseñan aqui, debajo de la cabecera,
# pero se rellenan mas abajo: necesitan 'filtered', que depende de los
# filtros de la barra lateral.
panel_busqueda = st.container()
ficha_ticket = st.container()

clientes_filter, asignadores_filter, sizes_filter, estados_filter = render_filters(df)

filtered = apply_filters(
    df,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
    estados=estados_filter,
)
filtered = apply_resolution_hour_overrides(filtered, solicitudes.obtener_overrides_horas_aprobados())

backlog_df = apply_filters(
    st.session_state["jira_backlog_df"] if st.session_state["jira_backlog_df"] is not None else df.iloc[0:0].copy(),
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
)

if filtered.empty:
    st.warning("No se encontraron bugs en los datos de Jira para el periodo seleccionado.")
    st.stop()


# =========================
# BUSQUEDA DE TICKET Y DE CLIENTE
# =========================
# Filtra todo el dashboard (KPIs, tablas y exportes). El ticket elegido
# enseña ademas su ficha; si es de una fecha fuera del periodo cargado, la
# ficha se trae de Jira y el resto de la pagina no se toca.
with panel_busqueda:
    ticket_buscado = busqueda.render_panel_busqueda(filtered, key_prefix="dash_")

with ficha_ticket:
    busqueda.render_ficha_ticket(filtered, ticket_buscado)

filtered = busqueda.aplicar_busqueda(filtered, ticket_buscado)
backlog_df = busqueda.aplicar_busqueda(backlog_df, ticket_buscado)

if filtered.empty:
    st.warning("Ningun ticket cumple a la vez los filtros de la barra lateral y la busqueda.")
    st.stop()


# =========================
# BONOS DE HORAS SIN CLIENTE ASIGNADO (solo Web Admin)
# =========================
if role == "admin":
    bonos_sin_cliente = detectar_bonos_sin_cliente(df)
    if not bonos_sin_cliente.empty:
        st.warning(
            f"⚠️ {len(bonos_sin_cliente)} compra(s) de bono de horas no se han podido asociar a ningun cliente "
            "(el ticket no lleva el prefijo \"Cliente | ...\" en el resumen ni el campo Domain relleno). "
            "Esas horas no se estan sumando al bono de nadie hasta que se corrija en Jira."
        )
        with st.expander("Ver tickets afectados", expanded=False):
            st.dataframe(
                bonos_sin_cliente,
                width="stretch",
                hide_index=True,
                column_config={
                    "ticket_id": "Ticket",
                    "resumen": stcc.TextColumn("Resumen", width="large"),
                    "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                    "bono_horas_compradas": stcc.NumberColumn("Horas compradas", format="%.1f h"),
                },
            )


# =========================
# EXPORTAR
# =========================
st.sidebar.markdown("## Exportar")
st.sidebar.caption("Descarga el resumen del periodo y los filtros seleccionados.")
st.sidebar.caption(f"Incluye {filtered['ticket_id'].nunique()} bugs Jira únicos.")

try:
    kpis_export = calculate_sla_kpis(filtered)
    trend_export = calculate_ticket_trends(filtered)
    sla_size_export = calculate_sla_size_comparison(filtered)
    ranking_export = calculate_technician_ranking(filtered)
    clientes_export = calculate_top_clients(filtered)
    tech_sla_export = calculate_technician_sla_summary(filtered)

    excel_bytes = generate_excel_report(
        kpis_export,
        trend_export,
        sla_size_export,
        ranking_export,
        clientes_export,
        tech_sla_export,
    )
    st.sidebar.download_button(
        "Descargar Excel del periodo",
        data=excel_bytes,
        file_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    pdf_bytes = generate_pdf_report(kpis_export, clientes_export, tech_sla_export)
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    pdf_buffer = BytesIO(pdf_bytes) if isinstance(pdf_bytes, (bytes, bytearray)) else pdf_bytes
    st.sidebar.download_button(
        "Descargar PDF del periodo",
        data=pdf_buffer,
        file_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
    )
except Exception as exc:
    st.sidebar.info("No hay datos suficientes para generar exportes.")


# =========================
# RESUMEN GLOBAL — KPIs
# =========================
section_title("Resumen global", "Visión general de todas las tareas del equipo en el período cargado")

try:
    kpis = calculate_sla_kpis(filtered)
except Exception:
    # En un DataFrame vacío o con columnas incompletas,
    # devolvemos valores por defecto para que la UI no falle.
    kpis = {
        "total_tickets": 0,
        "sla_prioridad": 0,
        "sla_size": 0,
        "sla_global": 0,
        "tickets_resueltos": 0,
        "tickets_abiertos": 0,
        "tickets_incumplidos": 0,
        "tickets_en_riesgo": 0,
        "dias_resolucion_promedio": 0,
        "total_clientes": 0,
        "total_tecnicos": 0,
    }

kpi_grid(
    [
        ("Total tareas", f"{kpis['total_tickets']:,}".replace(",", "."), "Tareas cargadas desde Jira", ""),
        (
            "SLA prioridad",
            f"{kpis['sla_prioridad']}%",
            "% tareas resueltas dentro del plazo por prioridad (verde ≥80%, naranja 50-79%, rojo <50%)",
            sla_tone(kpis['sla_prioridad']),
        ),
        (
            "SLA size",
            f"{kpis['sla_size']}%",
            "% tareas resueltas dentro del plazo por tamaño (verde ≥80%, naranja 50-79%, rojo <50%)",
            sla_tone(kpis['sla_size']),
        ),
        (
            "SLA global",
            format_percent(kpis['sla_global']),
            "Cumplimiento combinado (verde ≥80%, naranja 50-79%, rojo <50%)",
            sla_tone(kpis['sla_global']),
        ),
        ("Tareas resueltas", f"{kpis['tickets_resueltos']:,}".replace(",", "."), "Estado Finalizada", "success"),
        ("Tareas abiertas", f"{kpis['tickets_abiertos']:,}".replace(",", "."), "Aún no finalizadas", "warning"),
    ],
    columns=2,
)

# Cada tarjeta de arriba es clicable: el boton de debajo abre el listado
# de tickets detras de ese numero, para no tener que ir a buscarlo a mano
# mas abajo en el dashboard.
DRILLDOWN_KPIS = {
    "resueltas": ("✅ Ver resueltas", "Tareas resueltas", filtered.get("resuelto") == 1),
    "abiertas": ("🟡 Ver abiertas", "Tareas abiertas", filtered.get("resuelto") == 0),
}

drill_cols = st.columns(2)
for col, (drill_key, (etiqueta, _, _)) in zip(drill_cols, DRILLDOWN_KPIS.items()):
    if col.button(etiqueta, key=f"drill_{drill_key}", width="stretch"):
        actual = st.session_state.get("kpi_drilldown")
        st.session_state["kpi_drilldown"] = None if actual == drill_key else drill_key

drilldown_activo = st.session_state.get("kpi_drilldown")
if drilldown_activo:
    _, titulo, mascara = DRILLDOWN_KPIS[drilldown_activo]
    subset = filtered[mascara.fillna(False)]
    section_title(f"🔎 {titulo}", f"{len(subset)} tarea(s). Clica el mismo boton otra vez para cerrar.")
    if subset.empty:
        empty_state("No hay tareas en este grupo para el periodo/filtros actuales.")
    else:
        st.dataframe(
            subset,
            width="stretch",
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "resumen": stcc.TextColumn("Resumen", width="large"),
                "cliente": "Cliente",
                "asignado_a": "Técnico",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "horas_resolucion": stcc.NumberColumn("Horas resolución", format="%.1f h"),
            },
            column_order=[
                c for c in [
                    "ticket_id", "resumen", "cliente", "asignado_a", "estado",
                    "prioridad", "size", "fecha_creacion", "fecha_resolucion", "horas_resolucion",
                ] if c in subset.columns
            ],
        )

kpi_grid(
    [
        ("Tiempo medio resolución", f"{kpis['dias_resolucion_promedio']} días", "Media de días desde creación hasta cierre", ""),
        ("Clientes activos", kpis['total_clientes'], "Clientes con tareas en este período", ""),
        ("Técnicos", kpis['total_tecnicos'], "Leslie Jara · Carmen Yepes · Jorge Gallego", ""),
    ],
    secondary=True,
)


# =========================
# RENDIMIENTO POR TÉCNICO
# =========================
# El SLA de arriba es una promesa que se cumple o no (por diseño se queda
# estable y en verde si el equipo rinde bien); aqui es donde se ve la
# variacion real de un periodo a otro: quien tarda mas o menos ahora mismo.
section_title(
    "👥 Rendimiento por técnico",
    "Comparativa entre Leslie Jara, Carmen Yepes y Jorge Gallego: volumen de tareas, resueltas, tiempo de resolución y cumplimiento de SLA.",
)

try:
    avg_fig = create_avg_resolution_chart(filtered)
    render_chart_wrapper(avg_fig)
except Exception:
    empty_state("No hay datos suficientes para calcular la resolución media.")

ranking = calculate_technician_ranking(filtered)

if not ranking.empty:
    st.caption("Ranking por volumen de tareas. Las barras de SLA indican el porcentaje de tareas resueltas dentro del plazo.")
    st.dataframe(
        ranking,
        width="stretch",
        hide_index=True,
        column_config={
            "asignado_a": "Técnico",
            "tickets": stcc.NumberColumn("Total tareas", format="%d"),
            "resueltos": stcc.NumberColumn("Resueltas", format="%d"),
            "sla_size": stcc.ProgressColumn("SLA tamaño", format="%.1f%%", min_value=0, max_value=100),
            "sla_prioridad": stcc.ProgressColumn("SLA prioridad", format="%.1f%%", min_value=0, max_value=100),
            "sla_global": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio (días)", format="%.1f días"),
        },
    )
else:
    empty_state("No hay técnicos con datos para los filtros seleccionados.")


# =========================
# BACKLOG — Tareas sin iniciar
# =========================
section_title(
    "🗂 Backlog — Tareas sin iniciar",
    "Todas las tareas en estado Backlog de Jira, independientemente de si tienen técnico asignado o no. "
    "Cuanto más tiempo lleven aquí sin iniciarse, mayor el riesgo de incumplir el SLA.",
)

backlog_detalle = calculate_backlog_detalle(backlog_df)

if not backlog_detalle.empty:
    st.caption("Listado completo de tareas en backlog, ordenadas de más a menos antigua.")
    st.dataframe(
        backlog_detalle,
        width="stretch",
        hide_index=True,
        column_config={
            "ticket_id": "Ticket",
            "resumen": stcc.TextColumn("Descripción de la tarea", width="large"),
            "tipo": "Tipo de actividad",
            "prioridad": "Prioridad",
            "size": "Tamaño",
            "asignado_a": stcc.TextColumn("Técnico asignado"),
            "fecha_creacion": stcc.DatetimeColumn("Fecha creación", format="DD/MM/YYYY"),
            "dias_en_backlog": stcc.NumberColumn("Días en backlog", format="%d días"),
            "antigüedad": "Tramo de antigüedad",
        },
    )
else:
    empty_state("No hay tareas en estado Backlog en Jira.")


# =========================
# SLA POR TAMAÑO
# =========================
section_title(
    "⏳ SLA real vs. objetivo por tamaño (size)",
    "Compara el tiempo medio real de resolución con el objetivo marcado por el size de cada tarea (S=7d, M=14d, L=21d, XL=60d).",
)

sla_size_df = calculate_sla_size_comparison(filtered)

if not sla_size_df.empty:
    render_chart_wrapper(create_sla_comparison_chart(sla_size_df))
    st.dataframe(
        sla_size_df,
        width="stretch",
        hide_index=True,
        column_config={
            "size": "Tamaño",
            "tickets": stcc.NumberColumn("Nº tareas", format="%d"),
            "objetivo": stcc.NumberColumn("Objetivo SLA (días)", format="%.1f días"),
            "real": stcc.NumberColumn("Tiempo real (días)", format="%.1f días"),
            "cumplimiento": stcc.ProgressColumn(
                "% cumplimiento",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
    )
else:
    empty_state("No hay datos suficientes para comparar SLA por tamaño.")


# =========================
# PRESUPUESTO DE CLIENTE VS TIEMPO DE DESARROLLO
# =========================
render_presupuesto_global(filtered)


# =========================
# TICKETS REABERTOS
# =========================
section_title(
    "🔁 Tickets reabiertos",
    "Tickets con señales de reabertura detectadas en el resumen, descripción o estado de Jira.",
)

reopened_df = calculate_reopened_tickets(filtered)
if not reopened_df.empty:
    kpi_grid(
        [
            ("Reabiertos", str(len(reopened_df)), "Tickets con señales de reapertura", "warning"),
            ("% sobre el total", f"{round(len(reopened_df) / len(filtered) * 100, 1)}%", "Proporción de tickets reabiertos", "warning"),
        ]
    )
    st.caption("Listado de tickets con indicios de reapertura.")
    st.dataframe(
        reopened_df,
        width="stretch",
        hide_index=True,
        column_config={
            "ticket_id": "Ticket",
            "resumen": stcc.TextColumn("Descripción", width="large"),
            "tipo": "Tipo",
            "estado": "Estado",
            "cliente": "Cliente",
            "asignado_a": "Técnico",
            "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
            "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
            "prioridad": "Prioridad",
            "size": "Tamaño",
        },
    )
else:
    empty_state("No se detectaron tickets con señales de reapertura en los filtros actuales.")


render_ranking_clientes(filtered, role=role)
render_detalle_cliente(filtered, role, key_prefix="dash_")
