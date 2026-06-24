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
st.sidebar.caption("Sube un CSV de tareas para activar el dashboard.")

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
filtered = df


# =========================
# EXPORTAR
# =========================
st.sidebar.markdown("## Exportar")

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
    title="Dashboard Jira Pro",
    description="Vista ejecutiva para controlar volumen de tareas, cumplimiento SLA y rendimiento por tecnico, size y cliente.",
    timestamp=fecha_dashboard,
)


# =========================
# KPIs PRINCIPALES
# =========================
kpis = calculate_sla_kpis(filtered)

kpi_grid(
    [
        ("Tareas filtradas", f"{kpis['total_tickets']:,}".replace(",", "."), "Volumen actual", ""),
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
        ("Tareas resueltas", f"{kpis['tickets_resueltos']:,}".replace(",", "."), "Cerradas o completadas", "success"),
        ("Tareas abiertas", f"{kpis['tickets_abiertos']:,}".replace(",", "."), "No finalizadas", "warning"),
        ("Tareas incumplidas", f"{kpis['tickets_incumplidos']:,}".replace(",", "."), "SLA global no cumplido", "danger"),
        ("En riesgo SLA", f"{kpis['tickets_en_riesgo']:,}".replace(",", "."), "Riesgo por prioridad", "warning"),
    ]
)

kpi_grid(
    [
        ("Promedio resolución", f"{kpis['dias_resolucion_promedio']} dias", "Media del equipo", ""),
        ("Clientes", kpis['total_clientes'], "Con tareas visibles", ""),
        ("Tecnicos", kpis['total_tecnicos'], "Asignados en el filtro", ""),
    ],
    secondary=True,
)


# =========================
# TENDENCIA Y RESOLUCIÓN
# =========================
section_title("Evolución y resolución", "Tareas creadas, resueltas y tiempos de resolución")

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
            "tickets": stcc.NumberColumn("Tareas", format="%d"),
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
# DISTRIBUCIÓN DE RESOLUCIÓN
# =========================
section_title("Distribución de resolución", "Tiempo de resolución de tareas")

resolution_fig = create_resolution_distribution_chart(filtered)
render_chart_wrapper(resolution_fig)


# =========================
# ESTADO Y PRIORIDAD
# =========================
section_title("Estado y prioridad", "Tareas por estado y por prioridad")

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
            "tickets": stcc.NumberColumn("Tareas", format="%d"),
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
            "tickets": stcc.NumberColumn("Tareas", format="%d"),
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
# CLIENTES - RESUMEN GLOBAL
# =========================
section_title("Clientes con mas tareas", "Todos los clientes por volumen, SLA y tiempo medio")

clientes_df = calculate_top_clients(filtered)

if not clientes_df.empty:
    fig = create_top_clients_chart(clientes_df)
    render_chart_wrapper(fig)

    st.dataframe(
        clientes_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente": "Cliente",
            "tickets": stcc.NumberColumn("Tareas", format="%d"),
            "sla": stcc.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": stcc.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay clientes con datos para los filtros seleccionados.")


# =========================
# CLIENTES - DETALLE POR CLIENTE
# =========================
section_title("Detalle de tareas por cliente", "Selecciona un cliente para ver sus tareas individuales")

clientes_disponibles = sorted(filtered["cliente"].dropna().unique().tolist())

cliente_seleccionado = st.selectbox(
    "Selecciona un cliente",
    options=[""] + clientes_disponibles,
    index=0,
    format_func=lambda x: "Elige un cliente..." if x == "" else x,
)

if cliente_seleccionado:
    detalle_df = calculate_client_ticket_detail(filtered, cliente_seleccionado)

    total = len(detalle_df)
    resueltos = int(detalle_df["resuelto"].sum()) if "resuelto" in detalle_df.columns else 0
    tiempo_medio = round(detalle_df["dias_resolucion"].mean(), 1) if "dias_resolucion" in detalle_df.columns else "-"
    sla_global = round(detalle_df["sla_global_cumple"].mean() * 100, 1) if "sla_global_cumple" in detalle_df.columns else "-"

    kpi_grid(
        [
            ("Tareas", str(total), cliente_seleccionado, ""),
            ("Resueltas", str(resueltos), "Finalizadas", "success"),
            ("Tiempo medio", f"{tiempo_medio} dias", "Promedio resolución", ""),
            ("SLA global", f"{sla_global}%", "Cumplimiento", "success" if isinstance(sla_global, float) and sla_global >= 80 else "danger"),
        ]
    )

    if not detalle_df.empty:
        st.dataframe(
            detalle_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "resumen": "Resumen",
                "tipo": "Tipo",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Size",
                "asignado_a": "Técnico",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "dias_resolucion": stcc.NumberColumn("Días resolución", format="%.1f dias"),
                "horas_resolucion": stcc.NumberColumn("Horas resolución", format="%.1f h"),
                "sla_prioridad_cumple": stcc.CheckboxColumn("SLA prioridad"),
                "sla_size_cumple": stcc.CheckboxColumn("SLA size"),
                "sla_global_cumple": stcc.CheckboxColumn("SLA global"),
                "desviacion_sla": stcc.NumberColumn("Desviación SLA", format="%.1f dias"),
            },
        )
    else:
        empty_state(f"No hay tareas para {cliente_seleccionado} con los filtros actuales.")