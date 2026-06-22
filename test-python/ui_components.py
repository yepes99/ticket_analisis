"""
Componentes reutilizables de interfaz de usuario.
"""

from html import escape
import streamlit as st
from datetime import datetime
from uuid import uuid4


def section_title(title, detail=None):
    """
    Renderiza un título de sección con detalle opcional.
    
    Args:
        title (str): Título principal
        detail (str, optional): Texto de detalle a la derecha
    """
    detail_html = f"<span>{detail}</span>" if detail else ""
    st.markdown(
        f"<div class='section-title'><h2>{title}</h2>{detail_html}</div>",
        unsafe_allow_html=True,
    )


def empty_state(message):
    """
    Renderiza un estado vacío con mensaje.
    
    Args:
        message (str): Mensaje a mostrar
    """
    st.markdown(f"<div class='empty-state'>{message}</div>", unsafe_allow_html=True)


def kpi_grid(items, secondary=False):
    """
    Renderiza una grilla de KPI cards.
    
    Args:
        items (list): Lista de tuplas (label, value, subtext, tone)
        secondary (bool): Si True, usa grid de 3 columnas
    """
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


def render_hero_header(title, description, timestamp=None):
    """
    Renderiza un header tipo 'hero' con título y descripción.
    
    Args:
        title (str): Título principal
        description (str): Descripción/subtítulo
        timestamp (str, optional): Timestamp a mostrar
    """
    timestamp_html = f"<span class='timestamp'>Generado el {timestamp}</span>" if timestamp else ""
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-topline">
                <span class="eyebrow">Dashboard operativo</span>
                {timestamp_html}
            </div>
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_welcome_header():
    """Renderiza el header de bienvenida inicial (sin datos)."""
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


def render_login_form():
    """
    Renderiza el formulario de login.
    
    Returns:
        tuple: (username, password) si el usuario intenta entrar, (None, None) si no
    """
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
        return username, password, col1, col2


def render_chart_wrapper(fig, use_container_width=True, key=None):
    """
    Renderiza un gráfico dentro de un wrapper estilizado.
    
    Args:
        fig: Figura de plotly
        use_container_width (bool): Usa todo el ancho del contenedor
    """
    st.markdown("<div class='chart-wrap'>", unsafe_allow_html=True)
    # Generar key único si no se proporciona: usar título de la figura cuando exista
    if key is None:
        title_text = None
        try:
            title_text = getattr(getattr(fig, "layout", None), "title", None)
            if title_text is not None:
                title_text = getattr(title_text, "text", None)
        except Exception:
            title_text = None

        if title_text:
            safe = str(title_text).strip().replace(" ", "_").replace("/", "_")
            key = f"plotly_{safe}"
        else:
            key = f"plotly_{uuid4().hex}"

    st.plotly_chart(
        fig,
        use_container_width=use_container_width,
        config={"displayModeBar": False, "responsive": True},
        key=key,
    )
    st.markdown("</div>", unsafe_allow_html=True)
