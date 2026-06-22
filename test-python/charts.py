"""
Generación de gráficos y visualizaciones.
"""

import plotly.express as px
import plotly.graph_objects as go
from config import PLOT_TEMPLATE, PLOT_COLORS


def apply_chart_layout(fig, title=None):
    """
    Aplica estilos y configuración estándar a un gráfico Plotly.
    
    Args:
        fig: Figura de Plotly
        title (str, optional): Título del gráfico
        
    Returns:
        Figura de Plotly con estilos aplicados
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
    )

    if title:
        layout_options["title_text"] = title
    else:
        layout_options["title_text"] = ""

    fig.update_layout(**layout_options)
    fig.update_xaxes(showgrid=False, linecolor="#253449", tickfont=dict(color="#c7d2df"))
    fig.update_yaxes(gridcolor="#1d2a3a", linecolor="#253449", tickfont=dict(color="#c7d2df"))
    return fig


def create_sla_comparison_chart(sla_size_df):
    """
    Crea gráfico comparativo de SLA objetivo vs real por size.
    
    Args:
        sla_size_df (pd.DataFrame): DataFrame con datos de SLA por size
        
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    fig.add_bar(name="Objetivo SLA", x=sla_size_df["size"], y=sla_size_df["objetivo"])
    fig.add_bar(name="Tiempo real", x=sla_size_df["size"], y=sla_size_df["real"])
    fig.update_layout(barmode="group")
    apply_chart_layout(fig)
    fig.update_layout(height=320)
    return fig


def create_top_clients_chart(clientes_df):
    """
    Crea gráfico horizontal de clientes con más tickets.
    
    Args:
        clientes_df (pd.DataFrame): DataFrame con datos de clientes ordenados
        
    Returns:
        Figura de Plotly
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
    return fig
