"""
Generación de gráficos y visualizaciones.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import PLOT_TEMPLATE, PLOT_COLORS


def apply_chart_layout(fig, title=None):
    """
    Aplica estilos y configuración estándar a un gráfico Plotly.
    """
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
        bargap=0.18,
        bargroupgap=0.08,
    )

    if title:
        layout_options["title_text"] = title
    else:
        layout_options["title_text"] = ""

    fig.update_layout(**layout_options)
    fig.update_xaxes(showgrid=False, linecolor="#253449", tickfont=dict(color="#c7d2df"))
    fig.update_yaxes(gridcolor="#1d2a3a", linecolor="#253449", tickfont=dict(color="#c7d2df"))
    return fig


def create_ticket_trend_chart(df):
    """
    Crea gráfico de tendencia de tickets creados y resueltos.
    """
    fig = px.line(
        df,
        x="fecha",
        y=["creados", "resueltos"],
        markers=True,
        labels={"value": "Tickets", "fecha": "Fecha", "variable": "Tipo"},
        title="Evolución de tickets creados y resueltos",
    )
    apply_chart_layout(fig)
    fig.update_layout(xaxis=dict(tickformat="%d/%m/%Y"))
    return fig


def create_resolution_distribution_chart(df):
    """
    Crea histograma de tiempos de resolución.
    """
    fig = px.histogram(
        df,
        x="dias_resolucion",
        nbins=28,
        title="Distribución de tiempo de resolución",
        labels={"dias_resolucion": "Días de resolución", "count": "Tickets"},
        marginal="box",
        color_discrete_sequence=[PLOT_COLORS[1]],
    )
    apply_chart_layout(fig)
    fig.update_traces(marker_line_width=0.6, marker_line_color="#0e1720", opacity=0.92)
    return fig


def create_status_bar_chart(df):
    """
    Crea gráfico de barras de tickets por estado.
    """
    fig = px.bar(
        df,
        x="estado",
        y="tickets",
        color="estado",
        title="Tickets por estado",
        labels={"estado": "Estado", "tickets": "Tickets"},
        color_discrete_sequence=PLOT_COLORS,
    )
    apply_chart_layout(fig)
    fig.update_layout(xaxis_tickangle=-25, showlegend=False)
    fig.update_traces(
        marker_line_width=0.6,
        marker_line_color="#0e1720",
        opacity=0.94,
        hovertemplate="%{x}<br>Tickets: %{y}<extra></extra>",
        text=df["tickets"],
        textposition="outside",
    )
    return fig


def create_priority_bar_chart(df):
    """
    Crea gráfico de barras de tickets por prioridad.
    """
    fig = px.bar(
        df,
        x="prioridad",
        y="tickets",
        color="prioridad",
        title="Tickets por prioridad",
        labels={"prioridad": "Prioridad", "tickets": "Tickets"},
        color_discrete_sequence=PLOT_COLORS,
    )
    apply_chart_layout(fig)
    fig.update_layout(xaxis_tickangle=-25, showlegend=False)
    fig.update_traces(
        marker_line_width=0.6,
        marker_line_color="#0e1720",
        opacity=0.94,
        hovertemplate="%{x}<br>Tickets: %{y}<extra></extra>",
        text=df["tickets"],
        textposition="outside",
    )
    return fig


def create_technician_sla_chart(top_tech_df):
    """
    Crea gráfico de SLA por técnico.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="SLA global",
            x=top_tech_df["asignado_a"],
            y=top_tech_df["sla_global"],
            marker=dict(color=PLOT_COLORS[0], line=dict(width=0.6, color="#0e1720")),
            opacity=0.95,
            hovertemplate="%{x}<br>SLA global: %{y}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="SLA size",
            x=top_tech_df["asignado_a"],
            y=top_tech_df["sla_size"],
            marker=dict(color=PLOT_COLORS[1], line=dict(width=0.6, color="#0e1720")),
            opacity=0.95,
            hovertemplate="%{x}<br>SLA size: %{y}%<extra></extra>",
        )
    )
    fig.update_layout(barmode="group", xaxis_tickangle=-45, yaxis=dict(range=[0, 100], title="%"))
    apply_chart_layout(fig, title="SLA por técnico (Top 15)")
    return fig


def create_sla_comparison_chart(sla_size_df):
    """
    Crea gráfico comparativo de SLA objetivo vs real por size.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Objetivo SLA",
            x=sla_size_df["size"],
            y=sla_size_df["objetivo"],
            marker=dict(line=dict(width=0.6, color="#0e1720")),
            opacity=0.92,
            hovertemplate="%{x}<br>Objetivo: %{y} días<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Tiempo real",
            x=sla_size_df["size"],
            y=sla_size_df["real"],
            marker=dict(line=dict(width=0.6, color="#0e1720")),
            opacity=0.92,
            hovertemplate="%{x}<br>Real: %{y} días<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    apply_chart_layout(fig)
    fig.update_layout(height=320)
    return fig


def create_top_clients_chart(clientes_df):
    """
    Crea gráfico horizontal de clientes con más tickets.
    """
    fig = px.bar(
        clientes_df.sort_values("tickets", ascending=True),
        x="tickets",
        y="cliente",
        orientation="h",
        labels={"tickets": "Tickets", "cliente": "Cliente"},
    )
    apply_chart_layout(fig)
    fig.update_layout(height=460)
    fig.update_traces(
        marker_line_width=0.6,
        marker_line_color="#0e1720",
        opacity=0.94,
        hovertemplate="%{y}<br>Tickets: %{x}<extra></extra>",
        text=clientes_df.sort_values("tickets", ascending=True)["tickets"],
        textposition="inside",
        texttemplate="%{text}",
        insidetextanchor="middle",
    )
    return fig
