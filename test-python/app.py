"""
Dashboard Jira Pro - Aplicación principal.
"""

from datetime import datetime, timedelta
from io import BytesIO
import math
import streamlit as st

import config
from styles import apply_styles
from auth import check_authentication
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
    calculate_sla_kpis,
    calculate_sla_size_comparison,
    calculate_technician_ranking,
    calculate_technician_sla_summary,
    calculate_top_clients,
    calculate_ticket_trends,
    calculate_status_summary,
    calculate_priority_summary,
    calculate_client_ticket_detail,
    calculate_reopened_tickets,
)
from charts import (
    create_sla_comparison_chart,
    create_status_bar_chart,
    create_priority_bar_chart,
    create_avg_resolution_chart,
    create_technician_sla_chart,
)
from backlog_metrics import (
    calculate_backlog_kpis,
    calculate_backlog_por_antiguedad,
    calculate_backlog_por_prioridad,
    calculate_backlog_por_size,
    calculate_backlog_detalle,
)
from backlog_charts import (
    create_backlog_antiguedad_chart,
    create_backlog_prioridad_chart,
    create_backlog_size_chart,
)
import streamlit.column_config as stcc


def format_percent(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    try:
        return f"{int(round(float(value)))}%"
    except (TypeError, ValueError):
        return "-"


# Técnicos permitidos vienen de la configuración
# (config.TECNICOS_PERMITIDOS)


# =========================
# CONFIGURACIÓN INICIAL
# =========================
def resolve_query_dates(periodo, fecha_personalizada):
    today = datetime.now().date()
    if periodo == "Ultima semana":
        return today - timedelta(days=6), today
    if periodo == "Ultimo mes":
        return today - timedelta(days=30), today
    if periodo == "Ultimo ano":
        return today - timedelta(days=365), today
    if isinstance(fecha_personalizada, (list, tuple)) and len(fecha_personalizada) == 2:
        return fecha_personalizada
    return None, None


st.set_page_config(**config.PAGE_CONFIG)
apply_styles()


# =========================
# AUTENTICACIÓN
# =========================
check_authentication()


# =========================
# SIDEBAR - CARGA DE DATOS
# =========================
st.sidebar.markdown("## Carga de datos")
st.sidebar.caption("Consulta Jira con el token configurado en secretos.")

if "jira_df" not in st.session_state:
    st.session_state["jira_df"] = None
if "jira_source" not in st.session_state:
    st.session_state["jira_source"] = None

ticket_limit = st.sidebar.number_input(
    "Tickets a mostrar",
    min_value=1,
    max_value=5000,
    value=100,
    step=25,
)
periodo = st.sidebar.selectbox(
    "Periodo",
    ["Ultima semana", "Ultimo mes", "Ultimo ano", "Personalizado", "Sin limite de fecha"],
)

fecha_personalizada = None
if periodo == "Personalizado":
    today = datetime.now().date()
    fecha_personalizada = st.sidebar.date_input(
        "Rango de creacion",
        value=(today - timedelta(days=30), today),
        max_value=today,
    )

query_start_date, query_end_date = resolve_query_dates(periodo, fecha_personalizada)

if st.sidebar.button("Consultar Jira", type="primary", use_container_width=True):
    with st.spinner("Consultando Jira..."):
        st.session_state["jira_df"] = load_and_validate_jira_data(
            max_results=int(ticket_limit),
            start_date=query_start_date,
            end_date=query_end_date,
        )
        if query_start_date and query_end_date:
            periodo_label = f"{query_start_date.strftime('%d/%m/%Y')} - {query_end_date.strftime('%d/%m/%Y')}"
        else:
            periodo_label = "sin limite de fecha"
        st.session_state["jira_source"] = f"Jira ({int(ticket_limit)} tickets, {periodo_label})"

st.sidebar.markdown("---")
st.sidebar.caption("Los datos se consultan directamente desde Jira.")


# =========================
# CARGA DE DATOS
# =========================
if st.session_state["jira_df"] is None:
    render_hero_header(
        title="Dashboard Web” Equipo de Soporte",
        description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Leslie Jara Â· Carmen Yepes Â· Jorge Gallego.",
        timestamp=datetime.now().strftime(config.DATE_FORMAT),
    )
    st.info("Elige cantidad de tickets y periodo en la barra lateral para consultar Jira.")
    st.stop()

df = st.session_state["jira_df"]
source = st.session_state.get("jira_source") or "Jira"
st.sidebar.success(f"{len(df)} tickets cargados desde {source}.")

clientes_filter, asignadores_filter, sizes_filter, date_range = render_filters(df)

# El resto del dashboard: solo los 3 técnicos permitidos (defensivo si falta la columna)
if "asignado_a" in df.columns:
    team_df = df[df["asignado_a"].isin(config.TECNICOS_PERMITIDOS)].copy()
else:
    team_df = df.copy()
filtered = apply_filters(
    team_df,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
    date_range=date_range,
)

# Backlog: todas las tareas en estado Backlog con los filtros aplicados
if "estado" in df.columns:
    backlog_source = df[df["estado"].astype(str).str.lower() == "backlog"].copy()
else:
    backlog_source = df.iloc[0:0].copy()

backlog_df = apply_filters(
    backlog_source,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
    date_range=date_range,
)

if filtered.empty:
    st.warning("No se encontraron tareas asignadas a Leslie Jara, Carmen Yepes o Jorge Gallego en los datos de Jira.")
    st.stop()
    # Si no estamos ejecutando como app de Streamlit (p.e. durante import/tests),
    # detener también la ejecución del intérprete para evitar errores posteriores.
    try:
        # `get_script_run_ctx` existe cuando Streamlit está ejecutando el script.
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        try:
            from streamlit.scriptrunner import get_script_run_ctx
        except Exception:
            get_script_run_ctx = lambda: None

    if get_script_run_ctx() is None:
        raise SystemExit


# =========================
# EXPORTAR
# =========================
st.sidebar.markdown("## Exportar")
st.sidebar.caption("Descarga un resumen de los datos actuales.")

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
        "Descargar Excel",
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
        "Descargar PDF",
        data=pdf_buffer,
        file_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
    )
except Exception as exc:
    st.sidebar.info("No hay datos suficientes para generar exportes.")


# =========================
# HEADER
# =========================
fecha_dashboard = datetime.now().strftime(config.DATE_FORMAT)
render_hero_header(
    title="Dashboard Web — Equipo de Soporte",
    description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Leslie Jara · Carmen Yepes · Jorge Gallego.",
    timestamp=fecha_dashboard,
)


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
        ("SLA prioridad", f"{kpis['sla_prioridad']}%", "% tareas resueltas dentro del plazo por prioridad", "success"),
        ("SLA size", f"{kpis['sla_size']}%", "% tareas resueltas dentro del plazo por tamaño", "warning"),
        (
            "SLA global",
            format_percent(kpis['sla_global']),
            "Cumplimiento combinado — objetivo ≥ 80%",
            "success" if kpis['sla_global'] >= 80 else "danger",
        ),
    ]
)

kpi_grid(
    [
        ("Tareas resueltas", f"{kpis['tickets_resueltos']:,}".replace(",", "."), "Estado Finalizada", "success"),
        ("Tareas abiertas", f"{kpis['tickets_abiertos']:,}".replace(",", "."), "Aún no finalizadas", "warning"),
        ("Fuera de SLA", f"{kpis['tickets_incumplidos']:,}".replace(",", "."), "Han incumplido el SLA global", "danger"),
        ("En riesgo", f"{kpis['tickets_en_riesgo']:,}".replace(",", "."), "Abiertas y cerca de incumplir SLA", "warning"),
    ]
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
# BACKLOG — Tareas sin iniciar
# =========================
section_title(
    "🗂 Backlog — Tareas sin iniciar",
    "Todas las tareas en estado Backlog de Jira, independientemente de si tienen técnico asignado o no. "
    "Cuanto más tiempo lleven aquí sin iniciarse, mayor el riesgo de incumplir el SLA.",
)

backlog_kpis = calculate_backlog_kpis(backlog_df)

kpi_grid(
    [
        ("Total en backlog", str(backlog_kpis["total"]), "Tareas sin iniciar en todo Jira", "warning"),
    ]
)

# Tabla resumen por antigüedad, prioridad y size
antiguedad_df = calculate_backlog_por_antiguedad(backlog_df)
prioridad_backlog_df = calculate_backlog_por_prioridad(backlog_df)
size_backlog_df = calculate_backlog_por_size(backlog_df)

if not antiguedad_df.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("⏱ Por antigüedad — tiempo que llevan sin iniciarse")
        st.dataframe(antiguedad_df, use_container_width=True, hide_index=True,
            column_config={
                "antigüedad": "Tramo",
                "tickets": stcc.NumberColumn("Nº tareas", format="%d"),
            })
    with col2:
        st.caption("🔺 Por prioridad — urgencia de las tareas pendientes")
        st.dataframe(prioridad_backlog_df, use_container_width=True, hide_index=True,
            column_config={
                "prioridad": "Prioridad",
                "tickets": stcc.NumberColumn("Nº tareas", format="%d"),
            })
    with col3:
        st.caption("📦 Por tamaño (size) — estimación de esfuerzo")
        st.dataframe(size_backlog_df, use_container_width=True, hide_index=True,
            column_config={
                "size": "Tamaño",
                "tickets": stcc.NumberColumn("Nº tareas", format="%d"),
            })

backlog_detalle = calculate_backlog_detalle(backlog_df)

if not backlog_detalle.empty:
    st.caption("Listado completo de tareas en backlog, ordenadas de más a menos antigua.")
    st.dataframe(
        backlog_detalle,
        use_container_width=True,
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


# Evolución temporal: sección eliminada por petición del usuario.


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
        use_container_width=True,
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


# Distribución de resolución: se ha removido por petición del usuario.


# =========================
# RESOLUCIÓN MEDIA
# =========================
section_title(
    "📊 Resolución media (días)",
    "Promedio de días que tardan en resolverse los tickets. Incluye la media global y por técnico.",
)
try:
    avg_fig = create_avg_resolution_chart(filtered)
    render_chart_wrapper(avg_fig)
except Exception:
    empty_state("No hay datos suficientes para calcular la resolución media.")


# =========================
# RENDIMIENTO POR TÉCNICO
# =========================
section_title(
    "👥 Rendimiento por técnico",
    "Comparativa entre Leslie Jara, Carmen Yepes y Jorge Gallego: volumen de tareas, resueltas y cumplimiento de SLA.",
)

ranking = calculate_technician_ranking(filtered)

if not ranking.empty:
    st.caption("Ranking por volumen de tareas. Las barras de SLA indican el porcentaje de tareas resueltas dentro del plazo.")
    st.dataframe(
        ranking,
        use_container_width=True,
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

tech_sla_df = calculate_technician_sla_summary(filtered)
if not tech_sla_df.empty:
    st.caption("Gráfico de cumplimiento SLA por técnico.")
    render_chart_wrapper(create_technician_sla_chart(tech_sla_df))


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
        use_container_width=True,
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


# Clientes summary removed per request: UI no longer shows global clients table


# =========================
# CLIENTES — DETALLE POR CLIENTE
# =========================
section_title(
    "🔍 Detalle de tareas por cliente",
    "Selecciona un cliente para ver todas sus tareas individuales con su tiempo de resolución y cumplimiento de SLA.",
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

    total = len(detalle_df)
    if "resuelto" in detalle_df.columns:
        resueltos = int(detalle_df["resuelto"].sum())
    elif "estado" in detalle_df.columns:
        resueltos = int(detalle_df["estado"].astype(str).str.lower().eq("finalizada").sum())
    else:
        resueltos = 0

    tiempo_medio = round(detalle_df["dias_resolucion"].mean(), 1) if "dias_resolucion" in detalle_df.columns else "-"

    kpi_grid(
        [
            ("Tareas", str(total), f"Total de {cliente_seleccionado}", ""),
            ("Resueltas", str(resueltos), "En estado Finalizada", "success"),
            ("Tiempo medio", f"{tiempo_medio} días", "Días desde creación hasta cierre", ""),
        ]
    )

    if not detalle_df.empty:
        st.caption("Tareas ordenadas de más reciente a más antigua.")
        st.dataframe(
            detalle_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "resumen": stcc.TextColumn("Descripción", width="large"),
                "tipo": "Tipo",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "asignado_a": "Técnico",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "dias_resolucion": stcc.NumberColumn("Días resolución", format="%.1f días"),
                "horas_resolucion": stcc.NumberColumn("Horas resolución", format="%.1f h"),
                # SLA columns removed per request
            },
        )
    else:
        empty_state(f"No hay tareas para {cliente_seleccionado}.")
