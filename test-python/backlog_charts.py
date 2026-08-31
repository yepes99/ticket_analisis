"""
Gráficos de backlog - añadir al final de charts.py
"""

import plotly.express as px
import plotly.graph_objects as go


ORDEN_ANTIGUEDAD = ["0-1 semana", "1-2 semanas", "2-4 semanas", "Más de 1 mes", "Sin fecha"]
ORDEN_PRIORIDAD = ["Supone un impedimento", "Highest", "High", "Medium", "Low", "Lowest"]


def create_backlog_antiguedad_chart(df):
    """
    Barras horizontales por tramo de antigüedad.
    """
    if df.empty:
        return go.Figure()

    fig = px.bar(
        df,
        x="tickets",
        y="antigüedad",
        orientation="h",
        text="tickets",
        category_orders={"antigüedad": ORDEN_ANTIGUEDAD},
        color="antigüedad",
        color_discrete_map={
            "0-1 semana": "#4CAF50",
            "1-2 semanas": "#FFC107",
            "2-4 semanas": "#FF9800",
            "Más de 1 mes": "#F44336",
            "Sin fecha": "#9E9E9E",
        },
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Tickets por antigüedad",
        xaxis_title="Tickets",
        yaxis_title="",
        showlegend=False,
        height=280,
    )
    return fig


def create_backlog_prioridad_chart(df):
    """
    Barras horizontales por prioridad.
    """
    if df.empty:
        return go.Figure()

    fig = px.bar(
        df,
        x="tickets",
        y="prioridad",
        orientation="h",
        text="tickets",
        category_orders={"prioridad": ORDEN_PRIORIDAD},
        color="prioridad",
        color_discrete_map={
            "Supone un impedimento": "#B71C1C",
            "Highest": "#F44336",
            "High": "#FF9800",
            "Medium": "#FFC107",
            "Low": "#4CAF50",
            "Lowest": "#81C784",
            "Sin prioridad": "#9E9E9E",
        },
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Tickets por prioridad",
        xaxis_title="Tickets",
        yaxis_title="",
        showlegend=False,
        height=280,
    )
    return fig


def create_backlog_size_chart(df):
    """
    Barras por size.
    """
    if df.empty:
        return go.Figure()

    orden_size = ["S", "M", "L", "XL", "Sin size"]

    fig = px.bar(
        df,
        x="size",
        y="tickets",
        text="tickets",
        category_orders={"size": orden_size},
        color="size",
        color_discrete_map={
            "S": "#42A5F5",
            "M": "#7E57C2",
            "L": "#26A69A",
            "XL": "#EF5350",
            "Sin size": "#9E9E9E",
        },
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Tickets por size",
        xaxis_title="Size",
        yaxis_title="Tickets",
        showlegend=False,
        height=280,
    )
    return fig