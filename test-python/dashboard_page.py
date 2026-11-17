"""
Dashboard Jira Pro - pagina interna (Web Admin y Soporte).
"""

from datetime import datetime, timedelta
from io import BytesIO
import math
import pandas as pd
import streamlit as st

import busqueda
import config
import framework
import historial
import origen as origen_mod
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
    render_selector_periodo,
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
    mascaras_periodo,
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
    create_tecnico_carga_chart,
)
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
if "jira_fw_df" not in st.session_state:
    st.session_state["jira_fw_df"] = None

query_start_date, query_end_date = render_selector_periodo("dashboard")

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
        # Tareas de Framework Webplus del mismo periodo: es otro proyecto de
        # Jira, asi que va en su propia consulta.
        st.session_state["jira_fw_df"] = load_and_validate_jira_data(
            max_results=None,
            start_date=query_start_date,
            end_date=query_end_date,
            jql=framework.leer_fw_jql(jira_config),
        )
        # Rango con el que se cargaron los datos: los KPI de "creadas en el
        # periodo" / "resueltas en el periodo" se calculan contra el, no
        # contra lo que marque ahora el selector (puede haber cambiado sin
        # volver a consultar).
        st.session_state["jira_rango"] = (query_start_date, query_end_date)
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
        description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Carmen Yepes · Alejandro Poveda.",
        timestamp=datetime.now().strftime(config.DATE_FORMAT),
    )
    st.info("Elige el periodo en la barra lateral para consultar Jira.")
    st.stop()

df = st.session_state["jira_df"]
source = st.session_state.get("jira_source") or "Jira"
rango_inicio, rango_fin = st.session_state.get("jira_rango") or (None, None)
# "Todo el historico" no tiene inicio: todo lo cargado cuenta como del periodo.
hay_rango = rango_inicio is not None
rango_label = (
    f"{rango_inicio.strftime('%d/%m')}–{rango_fin.strftime('%d/%m')}" if hay_rango else ""
)
st.sidebar.success(f"{len(df)} tickets cargados desde {source}.")


# =========================
# HEADER
# =========================
fecha_dashboard = datetime.now().strftime(config.DATE_FORMAT)
render_hero_header(
    title="Dashboard Web — Equipo de Soporte",
    description="Seguimiento de tareas, cumplimiento de SLA y rendimiento del equipo: Carmen Yepes · Alejandro Poveda.",
    timestamp=fecha_dashboard,
)

# El buscador y la ficha del ticket se enseñan aqui, debajo de la cabecera,
# pero se rellenan mas abajo: necesitan 'filtered', que depende de los
# filtros de la barra lateral.
panel_busqueda = st.container()
ficha_ticket = st.container()

clientes_filter, asignadores_filter, sizes_filter, estados_filter, origenes_filter = render_filters(df)

filtered = apply_filters(
    df,
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
    estados=estados_filter,
    origenes=origenes_filter,
)
filtered = apply_resolution_hour_overrides(filtered, solicitudes.obtener_overrides_horas_aprobados())

backlog_df = apply_filters(
    st.session_state["jira_backlog_df"] if st.session_state["jira_backlog_df"] is not None else df.iloc[0:0].copy(),
    clientes=clientes_filter,
    asignadores=asignadores_filter,
    sizes=sizes_filter,
)

# Framework Webplus: solo se le aplica el filtro de tecnico. Los de cliente
# y size no tienen sentido aqui (las tareas de FW no son de un cliente ni
# llevan el campo Size).
fw_df = framework.filtrar_equipo(
    apply_filters(
        st.session_state["jira_fw_df"] if st.session_state["jira_fw_df"] is not None else df.iloc[0:0].copy(),
        asignadores=asignadores_filter,
    )
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
    kpis_export = calculate_sla_kpis(filtered, rango_inicio if hay_rango else None, rango_fin if hay_rango else None)
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
    kpis = calculate_sla_kpis(filtered, rango_inicio if hay_rango else None, rango_fin if hay_rango else None)
except Exception:
    # En un DataFrame vacío o con columnas incompletas,
    # devolvemos valores por defecto para que la UI no falle.
    kpis = {
        "tickets_creados_periodo": 0,
        "tickets_creados_antes": 0,
        "resueltos_creados_periodo": 0,
        "abiertos_creados_periodo": 0,
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

def _num(valor):
    return f"{valor:,}".replace(",", ".")


# Desglose de cada tarjeta: la consulta trae lo que tuvo actividad en el
# periodo, asi que se separa lo creado dentro del rango (lo que cuenta para
# los KPI de entrada) de lo creado antes y movido en el periodo.
mascara_creadas, mascara_resueltas_periodo = mascaras_periodo(
    filtered, rango_inicio if hay_rango else None, rango_fin if hay_rango else None
)

if hay_rango:
    sub_creadas = f"Creadas del {rango_label}"
    if "origen" in filtered.columns:
        creadas_tracker = int((mascara_creadas & filtered["origen"].eq(origen_mod.INTERCOM).fillna(False)).sum())
        creadas_internas = int((mascara_creadas & filtered["origen"].eq(origen_mod.JIRA).fillna(False)).sum())
        sub_creadas += f" · {_num(creadas_tracker)} tracker · {_num(creadas_internas)} internas"
    resueltos_antes = kpis["tickets_resueltos"] - kpis["resueltos_creados_periodo"]
    sub_resueltas = (
        f"Cerradas del {rango_label} · {_num(kpis['resueltos_creados_periodo'])} creadas en el periodo · "
        f"{_num(resueltos_antes)} de antes"
    )
    abiertos_antes = kpis["tickets_abiertos"] - kpis["abiertos_creados_periodo"]
    sub_abiertas = (
        f"Aún no finalizadas · {_num(kpis['abiertos_creados_periodo'])} creadas en el periodo · "
        f"{_num(abiertos_antes)} de antes"
    )
else:
    sub_creadas = "Sin fecha de inicio: cuenta todo lo cargado"
    sub_resueltas = "Estado Finalizada"
    sub_abiertas = "Aún no finalizadas"

# Fila 1: volumen. "Creadas en el periodo" es la cifra de entrada que se usa
# para los KPI (no se muestra el total cargado: mezcla tareas creadas antes
# que solo cambiaron de estado en el periodo).
kpi_grid(
    [
        ("📥 Creadas en el periodo", _num(kpis['tickets_creados_periodo']), sub_creadas, "highlight"),
        ("Tareas resueltas", _num(kpis['tickets_resueltos']), sub_resueltas, "success"),
        ("Tareas abiertas", _num(kpis['tickets_abiertos']), sub_abiertas, "warning"),
    ],
    secondary=True,
)
fila_botones = st.columns(3)

# Fila 2: cumplimiento de SLA.
kpi_grid(
    [
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
    ],
    secondary=True,
)

# Cada tarjeta de arriba es clicable: el boton de debajo abre el listado
# de tickets detras de ese numero, para no tener que ir a buscarlo a mano
# mas abajo en el dashboard.
def _mascara(columna, valor):
    """
    Mascara booleana segura para el drilldown: si la columna no existe
    (datos antiguos en sesion, consulta rara), no selecciona nada en vez
    de reventar al comparar None con un valor.
    """
    if columna not in filtered.columns:
        return pd.Series(False, index=filtered.index)
    return filtered[columna].eq(valor)


DRILLDOWN_KPIS = {
    "creadas": (
        "📥 Ver creadas en el periodo",
        f"Tareas creadas en el periodo ({rango_label})" if hay_rango else "Tareas creadas",
        mascara_creadas,
    ),
    "resueltas": (
        "✅ Ver resueltas",
        f"Tareas resueltas del {rango_label}" if hay_rango else "Tareas resueltas",
        mascara_resueltas_periodo,
    ),
    "abiertas": ("🟡 Ver abiertas", "Tareas abiertas", _mascara("resuelto", 0)),
    # Tracker/internas parten las creadas en el periodo (no todo lo cargado),
    # para que tracker + internas = creadas y cuadre con su tarjeta.
    "tracker": (
        "💬 Ver tareas de tracker",
        "Tareas de tracker ticket creadas en el periodo (entradas desde Intercom)",
        _mascara("origen", origen_mod.INTERCOM).fillna(False) & mascara_creadas,
    ),
    "internas": (
        "🛠️ Ver tareas internas",
        "Tareas internas creadas en el periodo (creadas directamente en Jira)",
        _mascara("origen", origen_mod.JIRA).fillna(False) & mascara_creadas,
    ),
}


def boton_drilldown(contenedor, clave):
    """Boton que abre (o cierra, si ya estaba abierto) el listado de ese grupo."""
    if contenedor.button(DRILLDOWN_KPIS[clave][0], key=f"drill_{clave}", width="stretch"):
        actual = st.session_state.get("kpi_drilldown")
        st.session_state["kpi_drilldown"] = None if actual == clave else clave


# Botones debajo de su tarjeta de la fila de volumen (el total no tiene
# listado propio: son todas). Se pintan aqui porque necesitan DRILLDOWN_KPIS,
# pero van en las columnas reservadas justo debajo de las tarjetas.
boton_drilldown(fila_botones[0], "creadas")
boton_drilldown(fila_botones[1], "resueltas")
boton_drilldown(fila_botones[2], "abiertas")

# Las creadas en el periodo, partidas en dos: lo que entra por Intercom como
# tracker ticket y lo que el equipo abre a mano en Jira. Se calcula sobre
# las creadas (no sobre todo lo cargado) para que sumen lo mismo que la
# tarjeta "Creadas en el periodo".
resumen_origen = origen_mod.resumen_origen(filtered[mascara_creadas])
pct_tracker = resumen_origen["pct_intercom"]
pct_interna = resumen_origen["pct_jira"]
texto_base = "de las creadas en el periodo" if hay_rango else "del total"

kpi_grid(
    [
        (
            "💬 Tareas de tracker ticket",
            _num(resumen_origen["intercom"]),
            f"Entran desde Intercom · {pct_tracker}% {texto_base}" if pct_tracker is not None else "Sin dato de origen",
            "",
        ),
        (
            "🛠️ Tareas internas",
            _num(resumen_origen["jira"]),
            f"Creadas directamente en Jira · {pct_interna}% {texto_base}" if pct_interna is not None else "Sin dato de origen",
            "",
        ),
    ],
    columns=2,
)

col_izq, col_der = st.columns(2)
boton_drilldown(col_izq, "tracker")
boton_drilldown(col_der, "internas")

# Un unico panel de resultados, debajo de todos los botones: asi el listado
# sale siempre en el mismo sitio, se pulse el boton que se pulse.
drilldown_activo = st.session_state.get("kpi_drilldown")
if drilldown_activo:
    _, titulo, mascara = DRILLDOWN_KPIS[drilldown_activo]
    subset = filtered[mascara.fillna(False)]
    section_title(f"🔎 {titulo}", f"{len(subset)} tarea(s). Clica el mismo boton otra vez para cerrar.")
    if subset.empty:
        empty_state("No hay tareas en este grupo para el periodo/filtros actuales.")
    else:
        tabla_drill = subset.copy()
        if "origen" in tabla_drill.columns:
            tabla_drill["origen"] = tabla_drill["origen"].map(origen_mod.etiqueta)
        st.dataframe(
            tabla_drill,
            width="stretch",
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "resumen": stcc.TextColumn("Resumen", width="large"),
                "cliente": "Cliente",
                "asignado_a": "Técnico",
                "estado": "Estado",
                "origen": stcc.TextColumn("Origen", width="medium"),
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY HH:mm"),
                "fecha_asignacion": stcc.DatetimeColumn("Asignado", format="DD/MM/YYYY HH:mm"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY HH:mm"),
                "horas_resolucion": stcc.NumberColumn(
                    "Horas resolución",
                    format="%.1f h",
                    help="Desde que se asigna al técnico hasta que se cierra (horas laborables, sin fines de semana ni Pending Info).",
                ),
            },
            column_order=[
                c for c in [
                    "ticket_id", "resumen", "cliente", "asignado_a", "estado", "origen",
                    "prioridad", "size", "fecha_creacion", "fecha_asignacion", "fecha_resolucion", "horas_resolucion",
                ] if c in tabla_drill.columns
            ],
        )

kpi_grid(
    [
        ("Tiempo medio resolución", f"{kpis['dias_resolucion_promedio']} días", "Media de días desde creación hasta cierre", ""),
        ("Clientes activos", kpis['total_clientes'], "Clientes con tareas en este período", ""),
        ("Técnicos", kpis['total_tecnicos'], "Carmen Yepes · Alejandro Poveda", ""),
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
    "Comparativa entre Carmen Yepes y Alejandro Poveda: volumen de tareas, resueltas, tiempo de resolución y cumplimiento de SLA.",
)

st.caption(
    "Las barras son los días medios que tarda cada uno en cerrar un ticket: **cuantos menos, mejor**. "
    "La línea de arriba es cuántos tickets ha cerrado, y hay que leer las dos cosas juntas: "
    "tardar 5 días de media habiendo cerrado 40 tickets no es lo mismo que tardarlos habiendo cerrado 4. "
    "La línea discontinua marca la media del equipo."
)

try:
    render_chart_wrapper(create_tecnico_carga_chart(filtered))
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
# FRAMEWORK WEBPLUS
# =========================
# Tabla aparte, sin mezclar con nada de WP: son tareas de otro proyecto,
# sin Size ni presupuesto, y sus tiempos no son comparables con los de un
# bug. Aqui lo que interesa es quien tiene que tarea entre manos.
section_title(
    "🧩 Framework Webplus — en qué está cada uno",
    "Tareas del proyecto Framework Webplus asignadas al equipo de soporte, aparte de los tickets de WP. "
    "Primero lo que está en curso.",
)

resumen_fw = framework.resumen_fw(fw_df)

if resumen_fw["total"] == 0:
    empty_state(
        "Ninguna tarea de Framework Webplus asignada a Carmen Yepes o Alejandro Poveda "
        "en el periodo y filtros actuales."
    )
else:
    # Mismas tarjetas que el resumen global de arriba, para que se lea igual.
    kpi_grid(
        [
            ("Total tareas FW", str(resumen_fw["total"]), "Tareas de Framework cargadas desde Jira", ""),
            ("Resueltas", str(resumen_fw["resueltas"]), "Ya finalizadas", "success"),
            ("En curso", str(resumen_fw["abiertas"]), "Aún sin cerrar", "warning" if resumen_fw["abiertas"] else ""),
            (
                "Tiempo medio",
                f"{resumen_fw['dias_medios']} días" if resumen_fw["dias_medios"] is not None else "—",
                "Desde creación hasta cierre",
                "",
            ),
        ]
    )

    # Una tarjeta por tecnico: de un vistazo, quien esta metido en Framework.
    carga_fw = framework.carga_por_tecnico(fw_df)
    kpi_grid(
        [
            (
                tecnico,
                str(datos_tecnico["total"]),
                f"{datos_tecnico['abiertas']} en curso" if datos_tecnico["total"] else "Sin tareas de Framework",
                "warning" if datos_tecnico["abiertas"] else "",
            )
            for tecnico, datos_tecnico in carga_fw.items()
        ],
        secondary=True,
    )

    st.dataframe(
        framework.detalle_fw(fw_df),
        width="stretch",
        hide_index=True,
        column_config={
            "asignado_a": stcc.TextColumn("Técnico", width="medium"),
            "ticket_id": "Tarea",
            "resumen": stcc.TextColumn("En qué consiste", width="large"),
            "tipo": "Tipo",
            "estado": "Estado",
            "prioridad": "Prioridad",
            "fecha_creacion": stcc.DatetimeColumn("Creada", format="DD/MM/YYYY"),
            "fecha_resolucion": stcc.TextColumn("Resuelta"),
            "dias_resolucion": stcc.TextColumn("Días en resolverse"),
        },
    )


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
