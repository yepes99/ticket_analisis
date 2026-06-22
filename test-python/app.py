"""
Dashboard Jira Pro - Aplicación principal.

Orquestador que integra autenticación, carga de datos, cálculo de métricas
y renderizado de visualizaciones.
"""

from datetime import datetime
import streamlit as st

# Imports internos
import config
from styles import apply_styles
from auth import check_authentication
from data import load_and_validate_data, show_welcome_if_no_file, render_filters, apply_filters
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
    calculate_top_clients,
    calculate_ticket_trends,
    calculate_status_summary,
    calculate_priority_summary,
    calculate_technician_sla_summary,
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
import streamlit.column_config as stcc


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
st.sidebar.caption("Sube un CSV de tickets para activar el dashboard.")

uploaded_file = st.sidebar.file_uploader(
    "Selecciona un CSV",
    type=["csv"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("Los datos se procesan en memoria durante la sesion.")


# =========================
# VALIDACIÓN DE ARCHIVO
# =========================
if uploaded_file is None:
    show_welcome_if_no_file()
    st.stop()


# =========================
# CARGA Y VALIDACIÓN DE DATOS
# =========================
df = load_and_validate_data(uploaded_file)


# =========================
# FILTROS
# =========================
clientes, asignadores, sizes, date_range = render_filters(df)
filtered = apply_filters(df, clientes, asignadores, sizes, date_range)

# =========================
# EXPORTAR
# =========================
st.sidebar.markdown("## Exportar")

# Preparar datos resumidos para el reporte (se usan los mismos cálculos que en el dashboard)
kpis_export = calculate_sla_kpis(filtered)
trend_export = calculate_ticket_trends(filtered)
sla_size_export = calculate_sla_size_comparison(filtered)
ranking_export = calculate_technician_ranking(filtered)
clientes_export = calculate_top_clients(filtered, config.TOP_CLIENTES)
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
st.sidebar.download_button(
    "Descargar PDF",
    data=pdf_bytes,
    file_name=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
    mime="application/pdf",
)


# =========================
# HEADER
# =========================
fecha_dashboard = datetime.now().strftime(config.DATE_FORMAT)
render_hero_header(
    title="Dashboard Jira Pro",
    description="Vista ejecutiva para controlar volumen de tickets, cumplimiento SLA y rendimiento por tecnico, size y cliente.",
    timestamp=fecha_dashboard,
)


# =========================
# KPIs PRINCIPALES
# =========================
kpis = calculate_sla_kpis(filtered)

kpi_grid(
    [
        ("Tickets filtrados", f"{kpis['total_tickets']:,}".replace(",", "."), "Volumen actual", ""),
        ("SLA prioridad", f"{kpis['sla_prioridad']}%", "Cumplimiento por prioridad", "success"),
        ("SLA size", f"{kpis['sla_size']}%", "Cumplimiento por size", "warning"),
        (
            "SLA global",
            f"{kpis['sla_global']}%",
            "Indicador principal",
            "success" if kpis['sla_global'] >= 80 else "danger",
        ),
    ]
)

kpi_grid(
    [
        ("Tickets resueltos", f"{kpis['tickets_resueltos']:,}".replace(",", "."), "Cerrados o completados", "success"),
        ("Tickets abiertos", f"{kpis['tickets_abiertos']:,}".replace(",", "."), "No finalizados", "warning"),
        ("Tickets incumplidos", f"{kpis['tickets_incumplidos']:,}".replace(",", "."), "SLA global no cumplido", "danger"),
        ("En riesgo SLA", f"{kpis['tickets_en_riesgo']:,}".replace(",", "."), "Riesgo por prioridad", "warning"),
    ]
)

kpi_grid(
    [
        ("Promedio resolución", f"{kpis['dias_resolucion_promedio']} dias", "Media del equipo", ""),
        ("Clientes", kpis['total_clientes'], "Con tickets visibles", ""),
        ("Tecnicos", kpis['total_tecnicos'], "Asignados en el filtro", ""),
    ],
    secondary=True,
)


# =========================
# TENDENCIA Y RESOLUCIÓN
# =========================
section_title("Evolución y resolución", "Tickets creados, resueltos y tiempos de resolución")

trend_df = calculate_ticket_trends(filtered)
resolution_fig = create_resolution_distribution_chart(filtered)

if not trend_df.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig = create_ticket_trend_chart(trend_df)
        render_chart_wrapper(fig)
    with col2:
        render_chart_wrapper(resolution_fig)
else:
    render_chart_wrapper(resolution_fig)


# =========================
# SLA SIZE VS REAL
# =========================
section_title("SLA real vs size", "Objetivo medio frente a dias reales de resolucion")

sla_size_df = calculate_sla_size_comparison(filtered)

if not sla_size_df.empty:
    fig = create_sla_comparison_chart(sla_size_df)
    render_chart_wrapper(fig)

    st.dataframe(
        sla_size_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "size": "Size",
            "tickets": stcc.NumberColumn("Tickets", format="%d"),
            "objetivo": stcc.NumberColumn("Objetivo SLA", format="%.1f dias"),
            "real": stcc.NumberColumn("Real", format="%.1f dias"),
            "cumplimiento": stcc.ProgressColumn(
                "Cumplimiento",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
    )
else:
    empty_state("No hay datos suficientes para comparar SLA por size con los filtros actuales.")


# =========================
# RESOLUCIÓN
# =========================
section_title("Distribución de resolución", "Tiempo de resolución de tickets")

resolution_fig = create_resolution_distribution_chart(filtered)
render_chart_wrapper(resolution_fig)


# =========================
# ESTADO Y PRIORIDAD
# =========================
section_title("Estado y prioridad", "Tickets por estado y por prioridad")

status_df = calculate_status_summary(filtered)
priority_df = calculate_priority_summary(filtered)

col1, col2 = st.columns(2)
with col1:
    status_fig = create_status_bar_chart(status_df)
    render_chart_wrapper(status_fig)
with col2:
    priority_fig = create_priority_bar_chart(priority_df)
    render_chart_wrapper(priority_fig)


# =========================
# RANKING DE TÉCNICOS
# =========================
section_title("Ranking de tecnicos", "Rendimiento agregado por asignado")

ranking = calculate_technician_ranking(filtered)

if not ranking.empty:
    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True,
        column_config={
            "asignado_a": "Tecnico",
            "tickets": stcc.NumberColumn("Tickets", format="%d"),
            "resueltos": stcc.NumberColumn("Resueltos", format="%d"),
            "sla_size": stcc.ProgressColumn("SLA size", format="%.1f%%", min_value=0, max_value=100),
            "sla_prioridad": stcc.ProgressColumn("SLA prioridad", format="%.1f%%", min_value=0, max_value=100),
            "sla_global": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay tecnicos con datos para los filtros seleccionados.")


# =========================
# CLIENTES TOP
# =========================
section_title("Clientes con mas tickets", "Top 20 por volumen")

clientes_df = calculate_top_clients(filtered, config.TOP_CLIENTES)


# =========================
# SLA POR TÉCNICO
# =========================
section_title("SLA por técnico", "Top técnicos por cumplimiento")

tech_sla_df = calculate_technician_sla_summary(filtered)
if not tech_sla_df.empty:
    tech_sla_fig = create_technician_sla_chart(tech_sla_df)
    render_chart_wrapper(tech_sla_fig)

    st.dataframe(
        tech_sla_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "asignado_a": "Tecnico",
            "tickets": stcc.NumberColumn("Tickets", format="%d"),
            "resueltos": stcc.NumberColumn("Resueltos", format="%d"),
            "sla_size": stcc.ProgressColumn("SLA size", format="%.1f%%", min_value=0, max_value=100),
            "sla_prioridad": stcc.ProgressColumn("SLA prioridad", format="%.1f%%", min_value=0, max_value=100),
            "sla_global": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay datos suficientes para mostrar SLA por técnico.")


# =========================
# CLIENTES TOP
# =========================
section_title("Clientes con mas tickets", "Top 20 por volumen")

if not clientes_df.empty:
    fig = create_top_clients_chart(clientes_df)
    render_chart_wrapper(fig)

    st.dataframe(
        clientes_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente": "Cliente",
            "tickets": stcc.NumberColumn("Tickets", format="%d"),
            "sla": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay clientes con datos para los filtros seleccionados.")
