from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from process import cargar_tickets


# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Dashboard Jira",
    page_icon="J",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_CSS = """
<style>
:root {
    --app-bg: #080d14;
    --surface: #101823;
    --surface-soft: #151f2c;
    --surface-muted: #1d2a3a;
    --ink: #f3f7fb;
    --ink-soft: #c7d2df;
    --muted: #8ea0b5;
    --line: #253449;
    --brand: #46a6ff;
    --brand-strong: #78bdff;
    --success: #42d392;
    --warning: #f5b84b;
    --danger: #ff6b6b;
    --shadow: 0 22px 52px rgba(0, 0, 0, 0.34);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 15% 0%, rgba(70, 166, 255, 0.12), transparent 32rem),
        linear-gradient(180deg, #080d14 0%, #0b111a 42%, #080d14 100%);
    color: var(--ink);
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(8, 13, 20, 0.86);
    backdrop-filter: blur(10px);
}

[data-testid="block-container"] {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1440px;
}

[data-testid="stSidebar"] {
    background: #0b1522;
    border-right: 1px solid rgba(255,255,255,0.08);
}

[data-testid="stSidebar"] * {
    color: #e8eef6;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] .stCaptionContainer {
    color: rgba(232,238,246,0.72);
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12);
}

.stButton > button {
    border-radius: 8px;
    border: 1px solid var(--brand);
    background: linear-gradient(180deg, var(--brand) 0%, #227bd0 100%);
    color: #06101d;
    font-weight: 700;
    min-height: 2.75rem;
    transition: all 160ms ease;
}

.stButton > button:hover {
    border-color: var(--brand-strong);
    background: linear-gradient(180deg, var(--brand-strong) 0%, #3490e6 100%);
    color: #06101d;
    box-shadow: 0 12px 28px rgba(70, 166, 255, 0.24);
}

.stTextInput input,
[data-baseweb="select"] > div,
[data-testid="stFileUploader"] section {
    background: #0c141f;
    border-radius: 8px;
    border-color: var(--line);
    color: var(--ink);
}

.stTextInput input::placeholder {
    color: #6f8195;
}

label,
[data-testid="stWidgetLabel"],
[data-testid="stMarkdownContainer"] p {
    color: var(--ink-soft);
}

[data-testid="stMetric"] {
    background: linear-gradient(180deg, #121d2a 0%, #0f1723 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    box-shadow: var(--shadow);
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
}

[data-testid="stMetricValue"] {
    color: var(--ink);
}

.app-shell {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
}

.hero {
    background:
        linear-gradient(135deg, rgba(24, 36, 52, 0.98) 0%, rgba(16, 24, 35, 0.98) 56%, rgba(13, 36, 56, 0.96) 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.35rem 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
}

.hero-topline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.55rem;
}

.eyebrow {
    color: var(--brand);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.timestamp {
    color: var(--muted);
    font-size: 0.88rem;
    white-space: nowrap;
}

.hero h1 {
    color: var(--ink);
    font-size: 2.15rem;
    font-weight: 800;
    line-height: 1.08;
    margin: 0;
}

.hero p {
    color: var(--ink-soft);
    max-width: 840px;
    margin: 0.65rem 0 0;
    line-height: 1.55;
}

.login-wrap {
    max-width: 760px;
    margin: 7vh auto 1.2rem;
    background: linear-gradient(135deg, rgba(18, 29, 42, 0.98), rgba(12, 20, 31, 0.98));
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 2.3rem 2.5rem;
    box-shadow: var(--shadow);
}

.login-wrap h1 {
    color: var(--ink);
    margin: 0 0 0.45rem;
    font-size: 2rem;
}

.login-wrap p {
    color: var(--ink-soft);
    margin: 0 0 1.5rem;
    line-height: 1.5;
}

.section-title {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.35rem 0 0.7rem;
}

.section-title h2 {
    color: var(--ink);
    font-size: 1.12rem;
    margin: 0;
}

.section-title span {
    color: var(--muted);
    font-size: 0.88rem;
}

.empty-state {
    background: var(--surface);
    border: 1px dashed var(--line);
    border-radius: 8px;
    padding: 1.4rem;
    color: var(--ink-soft);
}

.stDataFrame {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem;
    margin: 1rem 0 0.35rem;
}

.kpi-grid.secondary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 0.75rem;
}

.kpi-card {
    position: relative;
    overflow: hidden;
    min-height: 108px;
    background: linear-gradient(180deg, #121d2a 0%, #0f1723 100%);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem;
    box-shadow: var(--shadow);
}

.kpi-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    background: linear-gradient(90deg, var(--brand), var(--success));
}

.kpi-card.success::before {
    background: linear-gradient(90deg, var(--success), #8cf0bd);
}

.kpi-card.warning::before {
    background: linear-gradient(90deg, var(--warning), #ffe08a);
}

.kpi-card.danger::before {
    background: linear-gradient(90deg, var(--danger), #ff9a9a);
}

.kpi-label {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1.25;
    margin: 0 0 0.65rem;
}

.kpi-value {
    color: var(--ink);
    font-size: 2rem;
    font-weight: 850;
    line-height: 1;
    margin: 0;
}

.kpi-sub {
    color: var(--ink-soft);
    font-size: 0.78rem;
    margin-top: 0.65rem;
}

.chart-wrap {
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow: hidden;
    background: var(--surface);
    box-shadow: var(--shadow);
}

div[data-testid="stAlert"] {
    background: #101823;
    border: 1px solid var(--line);
    color: var(--ink-soft);
}

@media (max-width: 900px) {
    [data-testid="block-container"] {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1.1rem;
        padding-bottom: 2rem;
    }

    .hero h1 {
        font-size: 1.65rem;
    }

    .hero-topline,
    .section-title {
        align-items: flex-start;
        flex-direction: column;
    }

    .timestamp {
        white-space: normal;
    }

    .login-wrap {
        max-width: 100%;
        margin-top: 2rem;
        padding: 1.65rem;
    }

    .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .kpi-grid.secondary {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 640px) {
    [data-testid="block-container"] {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }

    .hero {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.85rem;
    }

    .hero h1 {
        font-size: 1.42rem;
        line-height: 1.15;
    }

    .hero p,
    .login-wrap p {
        font-size: 0.94rem;
    }

    .login-wrap {
        margin-top: 0.75rem;
        padding: 1.2rem;
    }

    .login-wrap h1 {
        font-size: 1.55rem;
    }

    .section-title {
        gap: 0.3rem;
        margin-top: 1rem;
    }

    .section-title h2 {
        font-size: 1rem;
    }

    .section-title span {
        font-size: 0.78rem;
    }

    [data-testid="stMetric"] {
        padding: 0.9rem 1rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.55rem;
    }

    .stButton > button {
        min-height: 2.9rem;
    }

    .kpi-grid,
    .kpi-grid.secondary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.65rem;
        margin-top: 0.75rem;
    }

    .kpi-card {
        min-height: 96px;
        border-radius: 12px;
        padding: 0.85rem;
    }

    .kpi-label {
        font-size: 0.74rem;
        margin-bottom: 0.5rem;
    }

    .kpi-value {
        font-size: 1.55rem;
    }

    .kpi-sub {
        font-size: 0.72rem;
        margin-top: 0.5rem;
    }

    .chart-wrap {
        border-radius: 12px;
    }

    div[data-testid="stDataFrame"] {
        font-size: 0.78rem;
    }
}

@media (max-width: 390px) {
    .kpi-grid,
    .kpi-grid.secondary {
        grid-template-columns: 1fr;
    }
}
</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)

PLOT_TEMPLATE = "plotly_dark"
PLOT_COLORS = ["#46a6ff", "#42d392", "#f5b84b", "#ff6b6b", "#9aa9bc", "#b491ff"]


def apply_chart_layout(fig, title=None):
    layout_options = dict(
        template=PLOT_TEMPLATE,
        colorway=PLOT_COLORS,
        plot_bgcolor="#101823",
        paper_bgcolor="#101823",
        height=380,
        font=dict(color="#f3f7fb", family="Inter, Segoe UI, Arial, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=20, r=20, t=52 if title else 24, b=42),
        hoverlabel=dict(bgcolor="#f3f7fb", font_color="#080d14"),
    )

    if title:
        layout_options["title_text"] = title
    else:
        layout_options["title_text"] = ""

    fig.update_layout(**layout_options)
    fig.update_xaxes(showgrid=False, linecolor="#253449", tickfont=dict(color="#c7d2df"))
    fig.update_yaxes(gridcolor="#1d2a3a", linecolor="#253449", tickfont=dict(color="#c7d2df"))
    return fig


def pct(series):
    if series.empty:
        return 0.0
    value = series.mean()
    if pd.isna(value):
        return 0.0
    return round(value * 100, 1)


def section_title(title, detail=None):
    detail_html = f"<span>{detail}</span>" if detail else ""
    st.markdown(
        f"<div class='section-title'><h2>{title}</h2>{detail_html}</div>",
        unsafe_allow_html=True,
    )


def empty_state(message):
    st.markdown(f"<div class='empty-state'>{message}</div>", unsafe_allow_html=True)


def kpi_grid(items, secondary=False):
    grid_class = "kpi-grid secondary" if secondary else "kpi-grid"
    cards = []
    for label, value, subtext, tone in items:
        tone_class = f" {tone}" if tone else ""
        cards.append(
            "<div class=\"kpi-card{tone}\">"
            "<div class=\"kpi-label\">{label}</div>"
            "<div class=\"kpi-value\">{value}</div>"
            "<div class=\"kpi-sub\">{subtext}</div>"
            "</div>".format(
                tone=tone_class,
                label=escape(str(label)),
                value=escape(str(value)),
                subtext=escape(str(subtext)),
            )
        )

    st.markdown(
        f"<div class=\"{grid_class}\">{''.join(cards)}</div>",
        unsafe_allow_html=True,
    )


def login():
    _, login_col, _ = st.columns([0.5, 2.2, 0.5])

    with login_col:
        st.markdown(
            """
            <div class="login-wrap">
                <div class="eyebrow">Acceso privado</div>
                <h1>Dashboard Jira Pro</h1>
                <p>Introduce tus credenciales para consultar metricas de tickets, cumplimiento SLA y rendimiento operativo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input("Usuario", placeholder="usuario@empresa.com")
        password = st.text_input("Contrasena", type="password", placeholder="Contrasena segura")

        col1, col2 = st.columns(2, gap="medium")
        if col1.button("Entrar", use_container_width=True):
            if username == st.secrets.get("APP_USER") and password == st.secrets.get("APP_PASSWORD"):
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Usuario o contrasena incorrectos")

        if col2.button("Limpiar", use_container_width=True):
            st.rerun()


if "auth" not in st.session_state:
    login()
    st.stop()


# =========================
# SIDEBAR
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

if uploaded_file is None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-topline">
                <span class="eyebrow">Dashboard operativo</span>
                <span class="timestamp">Esperando archivo CSV</span>
            </div>
            <h1>Dashboard Jira Pro</h1>
            <p>Sube un archivo CSV desde la barra lateral para visualizar KPIs, SLAs, ranking de tecnicos y clientes con mayor volumen de tickets.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Sube un CSV para comenzar.")
    st.stop()


# =========================
# CARGA DE DATOS
# =========================
@st.cache_data
def load_data(file):
    if hasattr(file, "seek"):
        file.seek(0)
    return cargar_tickets(file)


try:
    df = load_data(uploaded_file)
except Exception as exc:
    st.error(f"Error cargando CSV: {exc}")
    if hasattr(exc, "args") and exc.args:
        st.write("Revisa la cabecera del CSV y los nombres de columna esperados.")
    st.stop()


# =========================
# VALIDACION
# =========================
required_cols = ["cliente", "asignado_a", "size"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Faltan columnas: {missing}")
    st.write("Columnas detectadas:", df.columns.tolist())
    st.stop()


# =========================
# FILTROS
# =========================
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

filtered = df.copy()

if clientes:
    filtered = filtered[filtered["cliente"].isin(clientes)]

if asignadores:
    filtered = filtered[filtered["asignado_a"].isin(asignadores)]

if sizes:
    filtered = filtered[filtered["size"].isin(sizes)]


# =========================
# HEADER
# =========================
fecha_dashboard = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-topline">
            <span class="eyebrow">Dashboard operativo</span>
            <span class="timestamp">Generado el {fecha_dashboard}</span>
        </div>
        <h1>Dashboard Jira Pro</h1>
        <p>Vista ejecutiva para controlar volumen de tickets, cumplimiento SLA y rendimiento por tecnico, size y cliente.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# KPI SLA
# =========================
sla_prioridad = pct(filtered["sla_prioridad_cumple"])
sla_size = pct(filtered["sla_size_cumple"])
sla_global = pct(filtered["sla_global_cumple"])
tickets_resueltos = int(filtered["resuelto"].sum()) if "resuelto" in filtered else 0


# =========================
# KPIS
# =========================
kpi_grid(
    [
        ("Tickets filtrados", f"{len(filtered):,}".replace(",", "."), "Volumen actual", ""),
        ("SLA prioridad", f"{sla_prioridad}%", "Cumplimiento por prioridad", "success"),
        ("SLA size", f"{sla_size}%", "Cumplimiento por size", "warning"),
        ("SLA global", f"{sla_global}%", "Indicador principal", "success" if sla_global >= 80 else "danger"),
    ]
)

kpi_grid(
    [
        ("Tickets resueltos", f"{tickets_resueltos:,}".replace(",", "."), "Cerrados o completados", ""),
        ("Clientes", filtered["cliente"].nunique(), "Con tickets visibles", ""),
        ("Tecnicos", filtered["asignado_a"].nunique(), "Asignados en el filtro", ""),
    ],
    secondary=True,
)


# =========================
# SLA SIZE VS REAL
# =========================
section_title("SLA real vs size", "Objetivo medio frente a dias reales de resolucion")

sla_size_df = (
    filtered[filtered["sla_size_dias"].notna()]
    .groupby("size")
    .agg(
        tickets=("ticket_id", "count"),
        objetivo=("sla_size_dias", "mean"),
        real=("dias_resolucion", "mean"),
        cumplimiento=("sla_size_cumple", "mean"),
    )
    .reset_index()
)

if not sla_size_df.empty:
    sla_size_df["objetivo"] = sla_size_df["objetivo"].round(1)
    sla_size_df["real"] = sla_size_df["real"].round(1)
    sla_size_df["cumplimiento"] = (sla_size_df["cumplimiento"] * 100).round(1)

    fig = go.Figure()
    fig.add_bar(name="Objetivo SLA", x=sla_size_df["size"], y=sla_size_df["objetivo"])
    fig.add_bar(name="Tiempo real", x=sla_size_df["size"], y=sla_size_df["real"])
    fig.update_layout(barmode="group")
    apply_chart_layout(fig)
    fig.update_layout(height=320)
    st.markdown("<div class='chart-wrap'>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    st.markdown("</div>", unsafe_allow_html=True)

    st.dataframe(
        sla_size_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "size": "Size",
            "tickets": st.column_config.NumberColumn("Tickets", format="%d"),
            "objetivo": st.column_config.NumberColumn("Objetivo SLA", format="%.1f dias"),
            "real": st.column_config.NumberColumn("Real", format="%.1f dias"),
            "cumplimiento": st.column_config.ProgressColumn(
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
# RANKING
# =========================
section_title("Ranking de tecnicos", "Rendimiento agregado por asignado")

ranking = (
    filtered.groupby("asignado_a")
    .agg(
        tickets=("ticket_id", "count"),
        resueltos=("resuelto", "sum"),
        sla_size=("sla_size_cumple", "mean"),
        sla_prioridad=("sla_prioridad_cumple", "mean"),
        sla_global=("sla_global_cumple", "mean"),
        tiempo=("dias_resolucion", "mean"),
    )
    .reset_index()
)

if not ranking.empty:
    ranking["sla_size"] = (ranking["sla_size"] * 100).round(1)
    ranking["sla_prioridad"] = (ranking["sla_prioridad"] * 100).round(1)
    ranking["sla_global"] = (ranking["sla_global"] * 100).round(1)
    ranking["tiempo"] = ranking["tiempo"].round(1)

    st.dataframe(
        ranking.sort_values("tickets", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "asignado_a": "Tecnico",
            "tickets": st.column_config.NumberColumn("Tickets", format="%d"),
            "resueltos": st.column_config.NumberColumn("Resueltos", format="%d"),
            "sla_size": st.column_config.ProgressColumn("SLA size", format="%.1f%%", min_value=0, max_value=100),
            "sla_prioridad": st.column_config.ProgressColumn("SLA prioridad", format="%.1f%%", min_value=0, max_value=100),
            "sla_global": st.column_config.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": st.column_config.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay tecnicos con datos para los filtros seleccionados.")


# =========================
# CLIENTES TOP
# =========================
section_title("Clientes con mas tickets", "Top 20 por volumen")

clientes_df = (
    filtered.groupby("cliente")
    .agg(
        tickets=("ticket_id", "count"),
        sla=("sla_global_cumple", "mean"),
        tiempo=("dias_resolucion", "mean"),
    )
    .reset_index()
    .sort_values("tickets", ascending=False)
    .head(20)
)

if not clientes_df.empty:
    clientes_df["sla"] = (clientes_df["sla"] * 100).round(1)
    clientes_df["tiempo"] = clientes_df["tiempo"].round(1)

    fig = px.bar(
        clientes_df.sort_values("tickets", ascending=True),
        x="tickets",
        y="cliente",
        orientation="h",
        labels={"tickets": "Tickets", "cliente": "Cliente"},
    )
    apply_chart_layout(fig)
    fig.update_layout(height=460)
    st.markdown("<div class='chart-wrap'>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})
    st.markdown("</div>", unsafe_allow_html=True)

    st.dataframe(
        clientes_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente": "Cliente",
            "tickets": st.column_config.NumberColumn("Tickets", format="%d"),
            "sla": st.column_config.ProgressColumn("SLA global", format="%.1f%%", min_value=0, max_value=100),
            "tiempo": st.column_config.NumberColumn("Tiempo medio", format="%.1f dias"),
        },
    )
else:
    empty_state("No hay clientes con datos para los filtros seleccionados.")
