import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from process import cargar_tickets
from datetime import datetime

st.set_page_config(page_title="Dashboard Jira", layout="wide")

# =========================
# CARGA DE DATOS
# =========================
@st.cache_data
def load_data():
    return cargar_tickets()

df = load_data()

# =========================
# FILTROS
# =========================
st.sidebar.title("Filtros")

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
st.title("📊 Dashboard Jira")

fecha_dashboard = datetime.now().strftime("%d/%m/%Y %H:%M")

fecha_datos = None
if "fecha_actualizacion" in df.columns and df["fecha_actualizacion"].notna().any():
    fecha_datos = df["fecha_actualizacion"].max()

if fecha_datos is not None:
    st.caption(
        f"Dashboard generado el {fecha_dashboard} | "
        f"Datos actualizados hasta: {fecha_datos.strftime('%d/%m/%Y %H:%M')}"
    )
else:
    st.caption(f"Dashboard generado el {fecha_dashboard}")

# =========================
# KPI SLA PRO
# =========================
sla_prioridad = round(filtered["sla_prioridad_cumple"].mean() * 100, 1)
sla_size = round(filtered["sla_size_cumple"].mean() * 100, 1)
sla_global = round(filtered["sla_global_cumple"].mean() * 100, 1)

riesgo_sla = int(
    ((filtered["sla_prioridad_cumple"] == 0) |
     (filtered["sla_size_cumple"] == 0)).sum()
)

tiempo_medio = (
    round(filtered["dias_resolucion"].mean(), 1)
    if filtered["dias_resolucion"].notna().any()
    else 0
)

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
# RANKING TÉCNICOS
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