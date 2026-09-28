"""
Generación de gráficos y visualizaciones.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import PLOT_TEMPLATE, PLOT_COLORS, TECNICOS_PERMITIDOS


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


def create_avg_resolution_chart(df):
    """
    Crea un gráfico de barras con la resolución media (días).

    - Una barra `Todos` con la media global sobre tickets resueltos.
    - Barras por técnico (`asignado_a`) con su media (si existen asignados).
    """
    # Filtrar solo tickets con dias_resolucion válidos
    if "dias_resolucion" not in df.columns:
        # DataFrame sin la columna, devolver figura vacía
        fig = px.bar(title="Resolución media (días)")
        return apply_chart_layout(fig)

    resolved = df[df["dias_resolucion"].notna()].copy()
    if resolved.empty:
        fig = px.bar(title="Resolución media (días)")
        return apply_chart_layout(fig)

    overall = resolved["dias_resolucion"].mean()

    # Media por técnico (solo los tecnicos permitidos) si existe la columna
    if "asignado_a" in resolved.columns:
        by_tech = (
            resolved[resolved["asignado_a"].isin(TECNICOS_PERMITIDOS)]
            .groupby("asignado_a")["dias_resolucion"]
            .mean()
            .reset_index()
        )
        # Prepend overall as first row
        rows = [{"asignado_a": "Todos", "dias_resolucion": overall}]
        rows += by_tech.to_dict(orient="records")
        plot_df = pd.DataFrame(rows)
        x = "asignado_a"
        labels = {"asignado_a": "Técnico", "dias_resolucion": "Días (media)"}
    else:
        plot_df = pd.DataFrame([{"asignado_a": "Todos", "dias_resolucion": overall}])
        x = "asignado_a"
        labels = {"asignado_a": "", "dias_resolucion": "Días (media)"}

    fig = px.bar(
        plot_df,
        x=x,
        y="dias_resolucion",
        labels=labels,
        title="Resolución media (días)",
        color_discrete_sequence=[PLOT_COLORS[2]],
    )
    apply_chart_layout(fig)
    fig.update_traces(marker_line_width=0.6, marker_line_color="#0e1720", opacity=0.95)
    fig.update_layout(yaxis_title="Días (media)")
    return fig


def datos_carga_tecnico(df):
    """
    Por tecnico: cuantos tickets ha resuelto y cuantos dias de media ha
    tardado, mas la media del equipo.

    Los dos numeros salen de la misma base (los tickets ya resueltos, que
    son los unicos con dias_resolucion), para que la linea de tickets
    explique de verdad de donde sale la media de dias de al lado.
    """
    columnas = ["asignado_a", "tickets_resueltos", "dias_medios"]
    if "dias_resolucion" not in df.columns or "asignado_a" not in df.columns:
        return pd.DataFrame(columns=columnas), None

    resueltos = df[df["dias_resolucion"].notna()]
    resueltos = resueltos[resueltos["asignado_a"].isin(TECNICOS_PERMITIDOS)]
    if resueltos.empty:
        return pd.DataFrame(columns=columnas), None

    por_tecnico = (
        resueltos.groupby("asignado_a")
        .agg(
            tickets_resueltos=("ticket_id", "nunique"),
            dias_medios=("dias_resolucion", "mean"),
        )
        .reset_index()
        .sort_values("tickets_resueltos", ascending=False)
    )
    por_tecnico["dias_medios"] = por_tecnico["dias_medios"].round(1)

    return por_tecnico, round(float(resueltos["dias_resolucion"].mean()), 1)


def create_tecnico_carga_chart(df):
    """
    Dias medios de resolucion (barras, eje izquierdo) y numero de tickets
    resueltos (linea, eje derecho) de cada tecnico, en el mismo grafico.

    Los dias sueltos no dicen nada: tardar 5 dias de media habiendo cerrado
    40 tickets no es lo mismo que tardarlos habiendo cerrado 4. Por eso van
    juntos, y la linea discontinua marca la media del equipo para ver de un
    vistazo quien esta por encima y quien por debajo.

    Solo mira tickets de WP. Las tareas de Framework Webplus van en su
    propia tabla (ver framework.py): son de otro proyecto y sus tiempos no
    son comparables con los de un bug de WP.
    """
    por_tecnico, media_equipo = datos_carga_tecnico(df)

    fig = go.Figure()
    if por_tecnico.empty:
        return apply_chart_layout(fig)

    fig.add_bar(
        x=por_tecnico["asignado_a"],
        y=por_tecnico["dias_medios"],
        name="Dias medios por ticket",
        marker_color=PLOT_COLORS[2],
        marker_line_width=0.6,
        marker_line_color="#0e1720",
        opacity=0.95,
        width=0.5,
        text=[f"{v:.1f} d" for v in por_tecnico["dias_medios"]],
        # Dentro de la barra: fuera chocaba con la linea de la media del
        # equipo, que pasaba por encima del texto y lo dejaba ilegible.
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#080d14", size=15),
        textangle=0,
        cliponaxis=False,
        hovertemplate="%{x}<br>Media: %{y:.1f} dias por ticket<extra></extra>",
    )

    # Sin texto en los puntos: la linea cruza las barras (justo lo que se
    # quiere ver, quien tarda mas cierra menos) y el numero encima caia
    # sobre el naranja y no se leia. Va debajo del nombre, en el eje X.
    fig.add_trace(
        go.Scatter(
            x=por_tecnico["asignado_a"],
            y=por_tecnico["tickets_resueltos"],
            name="Tickets resueltos",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=PLOT_COLORS[0], width=3),
            marker=dict(size=11, line=dict(width=2, color="#0e1720")),
            hovertemplate="%{x}<br>%{y} tickets resueltos<extra></extra>",
        )
    )

    if media_equipo is not None:
        # Bien visible y con la etiqueta dentro de una cajita: en gris
        # apagado se confundia con las lineas de la cuadricula y no quedaba
        # claro a que se referia.
        fig.add_hline(
            y=media_equipo,
            line_dash="dash",
            line_width=2,
            line_color="#f3f7fb",
            annotation_text=f"<b>Media del equipo: {media_equipo:.1f} días por ticket</b>",
            annotation_position="top left",
            annotation_font=dict(color="#f3f7fb", size=13),
            annotation_bgcolor="#1d2a3a",
            annotation_bordercolor="#f3f7fb",
            annotation_borderwidth=1,
            annotation_borderpad=4,
            annotation_yshift=8,
        )

    apply_chart_layout(fig)
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=list(por_tecnico["asignado_a"]),
            ticktext=[
                f"{nombre}<br><span style='color:{PLOT_COLORS[0]}'>{tickets} tickets</span>"
                for nombre, tickets in zip(por_tecnico["asignado_a"], por_tecnico["tickets_resueltos"])
            ],
        ),
        yaxis=dict(title="Dias medios por ticket (menos = mejor)", rangemode="tozero"),
        yaxis2=dict(
            title="Tickets resueltos",
            overlaying="y",
            side="right",
            showgrid=False,
            rangemode="tozero",
            tickfont=dict(color="#c7d2df"),
        ),
        # Sitio arriba para las etiquetas de la linea y la anotacion de la media.
        margin=dict(l=20, r=20, t=70, b=56),
        height=420,
        # A la izquierda: a la derecha se montaba con el eje de tickets.
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
    )
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
        # "inside" giraba la etiqueta 90 grados cuando no cabia en barras muy
        # cortas (clientes con 1 ticket), dejando un simbolo ilegible. Con
        # "outside" + textangle=0 la etiqueta siempre queda horizontal, justo
        # despues de la barra, quepa o no dentro.
        textposition="outside",
        texttemplate="%{text}",
        textangle=0,
        cliponaxis=False,
    )
    return fig
