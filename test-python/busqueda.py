"""
Panel de busqueda, compartido por el Dashboard y la pagina de Clientes.

Es un desplegable con dos buscadores independientes:
- Ticket: lista los tickets del periodo cargado y deja escribir cualquier
  clave. Si la clave no esta en lo cargado (porque es de otra fecha) se
  consulta directamente a Jira, para que buscar un ticket no dependa del
  periodo que se haya elegido en la barra lateral.
- Cliente: deja la pagina filtrada por ese cliente.

Se pueden usar a la vez o por separado. Elegir un ticket ademas enseña su
ficha completa arriba, con cliente, horas, SLA, tecnico y fechas.
"""

import re
from html import escape

import pandas as pd
import streamlit as st

from config import PROJECT_KEY
from process import cargar_tickets_jira
from ui_components import kpi_grid, section_title

# Una clave de Jira ya normalizada: "WP-30966". Solo se consulta a Jira
# cuando lo tecleado encaja aqui (ademas, evita meter texto libre en el JQL).
CLAVE_VALIDA = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")

# Lo que la gente escribe: "WP-30966", "wp30966", "wp 30966" o solo "30966".
_CLAVE_TECLEADA = re.compile(r"^(?:([A-Za-z]+)[-_ ]?)?(\d+)$")

# Recorte del resumen en la etiqueta del desplegable, para que la opcion no
# se coma el ancho de la columna.
RESUMEN_MAX = 60


def normalizar_clave(valor, prefijo=PROJECT_KEY):
    """
    Pasa lo tecleado a una clave de Jira: "wp30966", "30966" o "WP-30966"
    devuelven todos "WP-30966". Si no parece una clave, devuelve el texto
    tal cual en mayusculas (no se usara para consultar Jira).
    """
    texto = str(valor or "").strip()
    if not texto:
        return ""

    match = _CLAVE_TECLEADA.match(texto)
    if not match:
        return texto.upper()

    proyecto = (match.group(1) or prefijo).upper()
    return f"{proyecto}-{match.group(2)}"


@st.cache_data(show_spinner="Buscando el ticket en Jira...", ttl=300)
def _consultar_jira_por_clave(clave):
    """
    Trae un unico ticket de Jira por su clave, saltandose el periodo y el
    JQL del dashboard. Devuelve None si la consulta falla (token, red...),
    que es distinto de "la clave no existe" (DataFrame vacio).
    """
    try:
        return cargar_tickets_jira(jql=f'key = "{clave}"')
    except Exception:
        return None


def _etiquetas_tickets(df):
    """
    {ticket_id: "WP-30966 · Bajas Web"} para las opciones del desplegable,
    de mas reciente a mas antiguo (lo que se busca suele ser reciente).
    """
    if df is None or df.empty or "ticket_id" not in df.columns:
        return {}

    datos = df.sort_values("fecha_creacion", ascending=False) if "fecha_creacion" in df.columns else df
    datos = datos.drop_duplicates(subset="ticket_id")

    claves = datos["ticket_id"].astype(str)
    if "resumen" in datos.columns:
        resumen = datos["resumen"].fillna("").astype(str).str.strip()
        largos = resumen.str.len() > RESUMEN_MAX
        resumen = resumen.mask(largos, resumen.str[:RESUMEN_MAX].str.rstrip() + "…")
    else:
        resumen = pd.Series("", index=datos.index)

    etiquetas = (claves + " · " + resumen).mask(resumen.eq(""), claves)
    return dict(zip(claves, etiquetas))


def _limpiar_busqueda(key_prefix):
    """Deja los dos desplegables del panel sin seleccion."""
    st.session_state[f"{key_prefix}busqueda_ticket"] = None
    st.session_state[f"{key_prefix}busqueda_cliente"] = None


def render_panel_busqueda(df, key_prefix=""):
    """
    Desplegable con el buscador de tickets y el de clientes.
    Devuelve (ticket, cliente); cada uno None si no se ha elegido nada.
    """
    etiquetas = _etiquetas_tickets(df)
    clientes = sorted(df["cliente"].dropna().unique().tolist()) if "cliente" in df.columns else []

    with st.expander("🔎 Buscar ticket o cliente", expanded=False):
        col_ticket, col_cliente = st.columns(2)

        ticket = col_ticket.selectbox(
            "Ticket",
            options=list(etiquetas),
            index=None,
            format_func=lambda valor: etiquetas.get(valor, valor),
            placeholder="Elige o escribe un ticket (WP-30966)",
            accept_new_options=True,
            key=f"{key_prefix}busqueda_ticket",
            help=(
                "El desplegable lista los tickets del periodo cargado. Si el ticket es de "
                "otra fecha, escribe su clave (WP-30966 o solo 30966) y se consulta a Jira."
            ),
        )

        cliente = col_cliente.selectbox(
            "Cliente",
            options=clientes,
            index=None,
            placeholder="Elige un cliente",
            key=f"{key_prefix}busqueda_cliente",
            help="Deja toda la pagina filtrada por ese cliente.",
        )

        if ticket or cliente:
            # Va por callback: el estado de un widget no se puede tocar una vez
            # instanciado, pero si antes del rerun que dispara el boton.
            st.button(
                "Limpiar busqueda",
                key=f"{key_prefix}busqueda_limpiar",
                on_click=_limpiar_busqueda,
                args=(key_prefix,),
            )

    return ticket, cliente


def resolver_ticket(df, ticket):
    """
    Busca el ticket primero en los datos ya cargados y, si no esta, en Jira.

    Devuelve (origen, fila) con origen "local", "jira", "no_existe" o
    "error"; fila es None salvo en los dos primeros casos.
    """
    clave = normalizar_clave(ticket)
    if not clave:
        return "no_existe", None

    if df is not None and not df.empty and "ticket_id" in df.columns:
        local = df[df["ticket_id"].astype(str).str.upper().eq(clave)]
        if not local.empty:
            return "local", local.iloc[0]

    if not CLAVE_VALIDA.match(clave):
        return "no_existe", None

    remoto = _consultar_jira_por_clave(clave)
    if remoto is None:
        return "error", None
    if remoto.empty:
        return "no_existe", None
    return "jira", remoto.iloc[0]


def aplicar_busqueda(df, ticket, cliente):
    """
    Filtra la pagina por el cliente y/o el ticket elegidos.

    Un ticket que no esta en los datos cargados (es de otra fecha) no vacia
    la pagina: su ficha se enseña aparte y el resto sigue con sus filtros.
    """
    if df is None or df.empty:
        return df

    resultado = df

    if cliente and "cliente" in resultado.columns:
        resultado = resultado[resultado["cliente"].eq(cliente)]

    clave = normalizar_clave(ticket)
    if clave and "ticket_id" in resultado.columns:
        del_ticket = resultado[resultado["ticket_id"].astype(str).str.upper().eq(clave)]
        if not del_ticket.empty:
            resultado = del_ticket

    return resultado


def _texto(fila, columna, defecto="—"):
    valor = fila.get(columna)
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return defecto
    texto = str(valor).strip()
    return texto or defecto


def _horas(fila, columna):
    valor = pd.to_numeric(fila.get(columna), errors="coerce")
    return "—" if pd.isna(valor) else f"{valor:.1f} h"


def _fecha(fila, columna):
    valor = fila.get(columna)
    if valor is None or pd.isna(valor):
        return "—"
    try:
        return pd.Timestamp(valor).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return "—"


def _sla_resumen(fila):
    """Etiqueta y tono del SLA global de un ticket (cumple / en riesgo / incumple)."""
    cumple = pd.to_numeric(fila.get("sla_global_cumple"), errors="coerce")
    if pd.isna(cumple):
        return "Sin evaluar", ""
    if cumple >= 1:
        return "✅ Cumple", "success"
    if pd.to_numeric(fila.get("en_riesgo_sla"), errors="coerce") == 1:
        return "🟠 En riesgo", "warning"
    return "🔴 Incumple", "danger"


def render_ficha_ticket(df, ticket):
    """Ficha completa del ticket elegido en el buscador."""
    if not ticket:
        return

    clave = normalizar_clave(ticket)
    origen, fila = resolver_ticket(df, ticket)

    if origen == "error":
        st.warning(f"No se ha podido consultar {clave} en Jira. Revisa la conexion o el token.")
        return
    if origen == "no_existe":
        st.warning(f"No existe ningun ticket {clave} en Jira.")
        return
    if origen == "jira":
        st.info(
            f"ℹ️ {clave} no esta en el periodo cargado: su ficha viene directamente de Jira. "
            "El resto de la pagina sigue con el periodo y los filtros actuales."
        )

    sla_label, sla_tono = _sla_resumen(fila)

    section_title(
        f"🔎 Ticket {_texto(fila, 'ticket_id')}",
        "Ficha del ticket elegido en el buscador.",
    )

    kpi_grid(
        [
            ("Cliente", _texto(fila, "cliente"), _texto(fila, "cliente_domain", "Sin dominio"), ""),
            ("Estado", _texto(fila, "estado"), _texto(fila, "tipo", "Sin tipo"), ""),
            ("Horas resolucion", _horas(fila, "horas_resolucion"), f"Presupuesto: {_horas(fila, 'presupuesto')}", ""),
            ("SLA global", sla_label, "Cumplimiento combinado de prioridad y size", sla_tono),
        ]
    )

    kpi_grid(
        [
            ("Tecnico", _texto(fila, "asignado_a"), "Asignado en Jira", ""),
            ("Prioridad · Size", f"{_texto(fila, 'prioridad')} · {_texto(fila, 'size')}", "Segun Jira", ""),
            ("Creado", _fecha(fila, "fecha_creacion"), f"Resuelto: {_fecha(fila, 'fecha_resolucion')}", ""),
        ],
        secondary=True,
    )

    with st.container(border=True):
        st.markdown(f"**Resumen:** {escape(_texto(fila, 'resumen'))}")
        url = _texto(fila, "cliente_url", "")
        if url:
            st.markdown(f"**Web del cliente:** [{escape(url)}]({url})")
