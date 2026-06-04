
# app.py (versión corregida y ampliada)
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from process import cargar_tickets

st.set_page_config(page_title="Dashboard Jira", layout="wide")

@st.cache_data
def load_data():
    return cargar_tickets()

df = load_data()

st.sidebar.title("Filtros")

clientes = st.sidebar.multiselect("Cliente", sorted(df["cliente"].dropna().unique()))
asignadores = st.sidebar.multiselect("Asignador", sorted(df["asignado_a"].dropna().unique()))
sizes = st.sidebar.multiselect("Size", sorted(df["size"].dropna().unique()))

filtered = df.copy()

if clientes:
    filtered = filtered[filtered["cliente"].isin(clientes)]

if asignadores:
    filtered = filtered[filtered["asignado_a"].isin(asignadores)]

if sizes:
    filtered = filtered[filtered["size"].isin(sizes)]

st.title("📊 Dashboard Jira")

sla_ok = round(filtered["cumple_sla_size"].dropna().mean() * 100, 1) if len(filtered) else 0
riesgo_sla = int(filtered["en_riesgo_sla"].sum())
tiempo_medio = round(filtered["dias_resolucion"].mean(), 1)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Tickets", len(filtered))
c2.metric("SLA", f"{sla_ok}%")
c3.metric("Tiempo Medio", f"{tiempo_medio} días")
c4.metric("Riesgo SLA", riesgo_sla)

st.subheader("SLA Real vs Size")

sla_size = (
    filtered[filtered["sla_size_dias"].notna()]
    .groupby("size")
    .agg(
        tickets=("ticket_id","count"),
        objetivo=("sla_size_dias","mean"),
        real=("dias_resolucion","mean"),
        cumplimiento=("cumple_sla_size","mean")
    )
    .reset_index()
)

if not sla_size.empty:
    sla_size["cumplimiento"] = (sla_size["cumplimiento"]*100).round(1)
    st.dataframe(sla_size, use_container_width=True)

    fig = go.Figure()
    fig.add_bar(name="Objetivo", x=sla_size["size"], y=sla_size["objetivo"])
    fig.add_bar(name="Real", x=sla_size["size"], y=sla_size["real"])
    fig.update_layout(barmode="group")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Ranking Técnicos")

ranking = (
    filtered.groupby("asignado_a")
    .agg(
        tickets=("ticket_id","count"),
        resueltos=("resuelto","sum"),
        sla=("cumple_sla_size","mean"),
        tiempo=("dias_resolucion","mean")
    )
    .reset_index()
)

if not ranking.empty:
    ranking["sla"] = (ranking["sla"]*100).round(1)
    st.dataframe(ranking.sort_values("tickets", ascending=False), use_container_width=True)

st.subheader("Clientes con más tickets")

clientes_df = (
    filtered.groupby("cliente")
    .agg(
        tickets=("ticket_id","count"),
        sla=("cumple_sla_size","mean"),
        tiempo=("dias_resolucion","mean")
    )
    .reset_index()
    .sort_values("tickets", ascending=False)
    .head(20)
)

if not clientes_df.empty:
    clientes_df["sla"] = (clientes_df["sla"]*100).round(1)
    fig = px.bar(clientes_df, x="cliente", y="tickets")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(clientes_df, use_container_width=True)

st.subheader("Backlog por Técnico")

backlog = (
    filtered[filtered["resuelto"] == 0]
    .groupby("asignado_a")
    .size()
    .reset_index(name="abiertos")
)

if not backlog.empty:
    fig = px.bar(backlog, x="asignado_a", y="abiertos")
    st.plotly_chart(fig, use_container_width=True)
