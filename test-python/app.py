import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from process import cargar_tickets

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Dashboard Jira", layout="wide")

# =========================
# LOGIN
# =========================
def login():
    st.markdown(
        """
        <style>
        .login-box {
            max-width: 420px;
            margin: auto;
            padding: 2.5rem;
            border-radius: 14px;
            background-color: #0e1117;
            border: 1px solid #262730;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='login-box'>", unsafe_allow_html=True)

    st.title("🔐 Dashboard Jira Pro")
    st.caption("Introduce tus credenciales para acceder")

    username = st.text_input("👤 Usuario", placeholder="Usuario")
    password = st.text_input("🔑 Contraseña", type="password", placeholder="Contraseña")

    col1, col2 = st.columns(2)

    login_btn = col1.button("Entrar", use_container_width=True)
    col2.button("Limpiar", use_container_width=True)

    if login_btn:
        if username == st.secrets["APP_USER"] and password == st.secrets["APP_PASSWORD"]:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

    st.markdown("</div>", unsafe_allow_html=True)


if "auth" not in st.session_state:
    login()
    st.stop()

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("## 📁 Carga de datos")
st.sidebar.caption("Sube tu CSV de tickets")

uploaded_file = st.sidebar.file_uploader(
    "Arrastra o selecciona el archivo",
    type=["csv"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("🔒 Datos procesados en memoria")

if uploaded_file is None:
    st.title("📊 Dashboard Jira Pro")
    st.info("Sube un CSV para comenzar")
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
    st.error(f"❌ Error cargando CSV: {exc}")
    if hasattr(exc, 'args') and exc.args:
        st.write("Revisa la cabecera del CSV y los nombres de columna esperados.")
    st.stop()

# =========================
# VALIDACIÓN
# =========================
required_cols = ["cliente", "asignado_a", "size"]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"❌ Faltan columnas: {missing}")
    st.write("Columnas detectadas:", df.columns.tolist())
    st.stop()

# =========================
# FILTROS
# =========================
st.sidebar.markdown("## 🔎 Filtros")

clientes = st.sidebar.multiselect(
    "Cliente",
    sorted(df["cliente"].dropna().unique())
)

asignadores = st.sidebar.multiselect(
    "Asignador",
    sorted(df["asignado_a"].dropna().unique())
)

sizes = st.sidebar.multiselect(
    "Size",
    sorted(df["size"].dropna().unique())
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
st.title("📊 Dashboard Jira Pro")

fecha_dashboard = datetime.now().strftime("%d/%m/%Y %H:%M")
st.caption(f"Dashboard generado el {fecha_dashboard}")

# =========================
# KPI SLA
# =========================
sla_prioridad = round(filtered["sla_prioridad_cumple"].mean() * 100, 1)
sla_size = round(filtered["sla_size_cumple"].mean() * 100, 1)
sla_global = round(filtered["sla_global_cumple"].mean() * 100, 1)

# =========================
# KPIs
# =========================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Tickets", len(filtered))
c2.metric("SLA Prioridad", f"{sla_prioridad}%")
c3.metric("SLA Size", f"{sla_size}%")
c4.metric("SLA Global", f"{sla_global}%")

# =========================
# SLA SIZE VS REAL
# =========================
st.subheader("SLA Real vs Size")

sla_size_df = (
    filtered[filtered["sla_size_dias"].notna()]
    .groupby("size")
    .agg(
        tickets=("ticket_id", "count"),
        objetivo=("sla_size_dias", "mean"),
        real=("dias_resolucion", "mean"),
        cumplimiento=("sla_size_cumple", "mean")
    )
    .reset_index()
)

if not sla_size_df.empty:
    sla_size_df["cumplimiento"] = (sla_size_df["cumplimiento"] * 100).round(1)

    st.dataframe(sla_size_df, use_container_width=True)

    fig = go.Figure()
    fig.add_bar(name="Objetivo", x=sla_size_df["size"], y=sla_size_df["objetivo"])
    fig.add_bar(name="Real", x=sla_size_df["size"], y=sla_size_df["real"])
    fig.update_layout(barmode="group")

    st.plotly_chart(fig, use_container_width=True)

# =========================
# RANKING
# =========================
st.subheader("Ranking Técnicos")

ranking = (
    filtered.groupby("asignado_a")
    .agg(
        tickets=("ticket_id", "count"),
        resueltos=("resuelto", "sum"),
        sla_size=("sla_size_cumple", "mean"),
        sla_prioridad=("sla_prioridad_cumple", "mean"),
        sla_global=("sla_global_cumple", "mean"),
        tiempo=("dias_resolucion", "mean")
    )
    .reset_index()
)

if not ranking.empty:
    ranking["sla_size"] = (ranking["sla_size"] * 100).round(1)
    ranking["sla_prioridad"] = (ranking["sla_prioridad"] * 100).round(1)
    ranking["sla_global"] = (ranking["sla_global"] * 100).round(1)

    st.dataframe(
        ranking.sort_values("tickets", ascending=False),
        use_container_width=True
    )

# =========================
# CLIENTES TOP
# =========================
st.subheader("Clientes con más tickets")

clientes_df = (
    filtered.groupby("cliente")
    .agg(
        tickets=("ticket_id", "count"),
        sla=("sla_global_cumple", "mean"),
        tiempo=("dias_resolucion", "mean")
    )
    .reset_index()
    .sort_values("tickets", ascending=False)
    .head(20)
)

if not clientes_df.empty:
    clientes_df["sla"] = (clientes_df["sla"] * 100).round(1)

    fig = px.bar(clientes_df, x="cliente", y="tickets")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(clientes_df, use_container_width=True)