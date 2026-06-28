"""
Dashboard Jira Pro - Aplicación principal.
"""

from datetime import datetime
from io import BytesIO
import streamlit as st

import config
from styles import apply_styles
from auth import check_authentication
from data import load_and_validate_data, show_welcome_if_no_file
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
)
from charts import (
    create_sla_comparison_chart,
    create_top_clients_chart,
    create_ticket_trend_chart,
    create_resolution_distribution_chart,
    create_status_bar_chart,
    create_priority_bar_chart,
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


# =========================
# TÉCNICOS PERMITIDOS
# =========================
TECNICOS_PERMITIDOS = ["Leslie Jara", "Carmen Yepes", "Jorge Gallego"]


# =========================
# CONFIGURACIÓN INICIAL
# =========================
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
st.sidebar.caption("Sube un CSV de tickets exportado desde Jira para activar el dashboard.")

uploaded_file = st.sidebar.file_uploader(
    "Selecciona un CSV",
    type=["csv"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("Los datos se procesan en memoria durante la sesión y no se almacenan.")


# =========================
# VALIDACIÓN DE ARCHIVO
# =========================
if uploaded_file is None:
    show_welcome_if_no_file()
    st.stop()


# =========================
# CARGA DE DATOS
# =========================
df = load_and_validate_data(uploaded_file)

# Backlog: todas las tareas en estado Backlog, sin filtrar por técnico
backlog_df = df[df["estado"].str.lower() == "backlog"].copy()

# El resto del dashboard: solo los 3 técnicos permitidos
filtered = df[df["asignado_a"].isin(TECNICOS_PERMITIDOS)].copy()

if filtered.empty:
    st.warning("No se encontraron tareas asignadas a Leslie Jara, Carmen Yepes o Jorge Gallego en este CSV.")
    st.stop()


# =========================
# EXPORTAR
# =========================
st.sidebar.markdown("## Exportar")
st.sidebar.caption("Descarga un resumen de los datos actuales.")

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

kpis = calculate_sla_kpis(filtered)

kpi_grid(
    [
        ("Total tareas", f"{kpis['total_tickets']:,}".replace(",", "."), "Tareas cargadas en el CSV", ""),
        ("SLA prioridad", f"{kpis['sla_prioridad']}%", "% tareas resueltas dentro del plazo por prioridad", "success"),
        ("SLA size", f"{kpis['sla_size']}%", "% tareas resueltas dentro del plazo por tamaño", "warning"),
        (
            "SLA global",
            f"{kpis['sla_global']}%",
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
    "Todas las tareas en estado Backlog del CSV, independientemente de si tienen técnico asignado o no. "
    "Cuanto más tiempo lleven aquí sin iniciarse, mayor el riesgo de incumplir el SLA.",
)

backlog_kpis = calculate_backlog_kpis(backlog_df)

kpi_grid(
    [
        ("Total en backlog", str(backlog_kpis["total"]), "Tareas sin iniciar en todo el CSV", "warning"),
        ("Tiempo medio en backlog", f"{backlog_kpis['tiempo_medio']} días", "Promedio de días desde creación", ""),
        ("Sin tamaño (size)", str(backlog_kpis["sin_size"]), "No se puede estimar esfuerzo ni SLA", "danger" if backlog_kpis["sin_size"] > 0 else ""),
        ("Sin prioridad", str(backlog_kpis["sin_prioridad"]), "No se puede calcular SLA de prioridad", "danger" if backlog_kpis["sin_prioridad"] > 0 else ""),
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
            "prioridad": "Prioridad",
            "size": "Tamaño",
            "asignado_a": stcc.TextColumn("Técnico asignado"),
            "fecha_creacion": stcc.DatetimeColumn("Fecha creación", format="DD/MM/YYYY"),
            "dias_en_backlog": stcc.NumberColumn("Días en backlog", format="%d días"),
            "antigüedad": "Tramo de antigüedad",
        },
    )
else:
    empty_state("No hay tareas en estado Backlog en este CSV.")


# =========================
# EVOLUCIÓN TEMPORAL
# =========================
section_title(
    "📈 Evolución temporal",
    "Tareas creadas vs. resueltas por día — permite ver si el equipo resuelve más de lo que entra o acumula carga.",
)

trend_df = calculate_ticket_trends(filtered)
resolution_fig = create_resolution_distribution_chart(filtered)

if not trend_df.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Creadas vs. resueltas por día")
        render_chart_wrapper(create_ticket_trend_chart(trend_df))
    with col2:
        st.caption("Distribución del tiempo de resolución en días")
        render_chart_wrapper(resolution_fig)
else:
    render_chart_wrapper(resolution_fig)


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


# =========================
# DISTRIBUCIÓN DE RESOLUCIÓN
# =========================
section_title(
    "📊 Distribución del tiempo de resolución",
    "Histograma de cuántos días tardan en resolverse las tareas — útil para detectar colas o tareas atascadas.",
)

render_chart_wrapper(create_resolution_distribution_chart(filtered))


# =========================
# ESTADO Y PRIORIDAD
# =========================
section_title(
    "🏷 Estado y prioridad",
    "Distribución actual de tareas por estado (en qué fase están) y por prioridad (cuántas son urgentes).",
)

status_df = calculate_status_summary(filtered)
priority_df = calculate_priority_summary(filtered)

col1, col2 = st.columns(2)
with col1:
    st.caption("Estado actual de las tareas")
    render_chart_wrapper(create_status_bar_chart(status_df))
with col2:
    st.caption("Prioridad asignada")
    render_chart_wrapper(create_priority_bar_chart(priority_df))


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
# CLIENTES — RESUMEN GLOBAL
# =========================
section_title(
    "🏢 Clientes",
    "Todos los clientes con tareas en este período, ordenados por volumen. Incluye su SLA global y tiempo medio de resolución.",
)

clientes_df = calculate_top_clients(filtered)

if not clientes_df.empty:
    render_chart_wrapper(create_top_clients_chart(clientes_df))
    st.dataframe(
        clientes_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente": "Cliente",
            "tickets": stcc.NumberColumn("Nº tareas", format="%d"),
            "sla": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio (días)", format="%.1f días"),
        },
    )
else:
    empty_state("No hay clientes con datos para los filtros seleccionados.")


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
    resueltos = int(detalle_df["resuelto"].sum()) if "resuelto" in detalle_df.columns else 0
    tiempo_medio = round(detalle_df["dias_resolucion"].mean(), 1) if "dias_resolucion" in detalle_df.columns else "-"
    sla_global = round(detalle_df["sla_global_cumple"].mean() * 100, 1) if "sla_global_cumple" in detalle_df.columns else "-"

    kpi_grid(
        [
            ("Tareas", str(total), f"Total de {cliente_seleccionado}", ""),
            ("Resueltas", str(resueltos), "En estado Finalizada", "success"),
            ("Tiempo medio", f"{tiempo_medio} días", "Días desde creación hasta cierre", ""),
            ("SLA global", f"{sla_global}%", "% tareas dentro del plazo", "success" if isinstance(sla_global, float) and sla_global >= 80 else "danger"),
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
                "sla_prioridad_cumple": stcc.CheckboxColumn("✓ SLA prioridad"),
                "sla_size_cumple": stcc.CheckboxColumn("✓ SLA tamaño"),
                "sla_global_cumple": stcc.CheckboxColumn("✓ SLA global"),
                "desviacion_sla": stcc.NumberColumn("Desviación SLA (días)", format="%.1f días"),
            },
        )
    else:
        empty_state(f"No hay tareas para {cliente_seleccionado}.")