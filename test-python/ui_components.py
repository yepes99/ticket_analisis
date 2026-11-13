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


def kpi_grid(items, secondary=False, columns=None):
    """
    Renderiza una grilla de KPI cards.

    Args:
        items (list): Lista de tuplas (label, value, subtext, tone)
        secondary (bool): Si True, usa grid de 3 columnas
        columns (int|None): Numero de columnas exacto (anula 'secondary'),
            para cuadrar el numero de tarjetas sin dejar hueco en blanco.
    """
    grid_class = "kpi-grid secondary" if secondary else "kpi-grid"
    style_attr = ""
    if columns:
        style_attr = f" style=\"grid-template-columns: repeat({int(columns)}, minmax(0, 1fr));\""
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
        f"<div class=\"{grid_class}\"{style_attr}>{''.join(cards)}</div>",
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
                <span class="timestamp">Esperando datos de Jira</span>
            </div>
            <h1>Dashboard Jira Pro</h1>
            <p>La app carga los tickets directamente desde Jira para visualizar KPIs, SLAs, ranking de técnicos y clientes con mayor volumen de tickets.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login_form(subtitulo=None, form_key=0):
    """
    Renderiza el formulario de login.

    Args:
        subtitulo (str, optional): texto que explica que rol puede acceder
            aqui, para que quede claro en que pantalla se esta entrando.
        form_key (int): se incrusta en las keys de los campos. El boton
            "Limpiar" lo incrementa para forzar un widget nuevo: si solo se
            borra session_state[key] y se hace rerun, el input de texto se
            queda con el valor tecleado (el frontend no lo resetea porque
            sigue siendo el mismo componente); con una key distinta, Streamlit
            monta un input realmente vacio.

    Returns:
        tuple: (username, password, col1, col2)
    """
    _, login_col, _ = st.columns([1, 1.15, 1])

    with login_col:
        detalle = subtitulo or "Introduce tus credenciales para consultar metricas de tickets, cumplimiento SLA y rendimiento operativo."
        st.markdown(
            f"""
            <div class="login-wrap">
                <div class="login-icon">🔐</div>
                <div class="eyebrow">Acceso privado</div>
                <h1>Dashboard Jira Pro</h1>
                <p>{escape(detalle)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input("Usuario", placeholder="usuario@empresa.com", key=f"login_username_{form_key}")
        password = st.text_input("Contrasena", type="password", placeholder="Contrasena segura", key=f"login_password_{form_key}")

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
        width="stretch" if use_container_width else "content",
        config={"displayModeBar": False, "responsive": True},
        key=key,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_selector_periodo(key_prefix):
    """
    Selector de periodo de la barra lateral (compartido por Dashboard y
    Clientes). Devuelve (start_date, end_date) o para la pagina si las
    fechas personalizadas no son validas.

    En "Personalizado" van dos campos separados (Desde / Hasta) en formato
    dd/mm/aaaa, en vez de un unico calendario de rango (habia que pinchar
    dos veces y no quedaba claro que faltaba la segunda fecha). Debajo se
    ensena siempre el rango exacto que se va a consultar.
    """
    from periodos import (
        PERIODOS,
        available_years,
        describir_rango,
        etiqueta_periodo,
        resolve_query_dates,
        _lunes,
    )

    periodo = st.sidebar.selectbox(
        "Periodo",
        PERIODOS,
        format_func=etiqueta_periodo,
        key=f"{key_prefix}_periodo",
    )

    hoy = datetime.now().date()
    selected_year = hoy.year
    if periodo == "Ano":
        selected_year = st.sidebar.selectbox("Año", available_years(), key=f"{key_prefix}_year")

    custom_range = None
    if periodo == "Personalizado":
        col_desde, col_hasta = st.sidebar.columns(2)
        desde = col_desde.date_input(
            "Desde",
            value=_lunes(hoy),
            max_value=hoy,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_desde",
        )
        hasta = col_hasta.date_input(
            "Hasta",
            value=hoy,
            max_value=hoy,
            format="DD/MM/YYYY",
            key=f"{key_prefix}_hasta",
        )
        if desde is None or hasta is None:
            st.sidebar.warning("Rellena las dos fechas.")
            st.stop()
        if desde > hasta:
            st.sidebar.error("La fecha «Desde» tiene que ser anterior o igual a «Hasta».")
            st.stop()
        custom_range = (desde, hasta)

    start_date, end_date = resolve_query_dates(periodo, selected_year, custom_range)
    st.sidebar.caption(f"📅 {describir_rango(start_date, end_date)}")
    return start_date, end_date
