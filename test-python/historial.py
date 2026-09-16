"""
Historial de la sesion: ultimas busquedas y ultimos cambios.

Las busquedas recientes viven en st.session_state (son de la sesion de cada
persona, no hay que persistirlas); los cambios recientes salen de las
solicitudes de horas y limite ya registradas en solicitudes.py.
"""

from datetime import datetime

import streamlit as st

import solicitudes

# Cuantas busquedas recientes se recuerdan por tipo.
MAX_RECIENTES = 6

_CLAVE_BUSQUEDAS = "historial_busquedas"

ESTADO_CHIP = {
    "pendiente": ("pendiente", "Pendiente"),
    "aprobado": ("aprobado", "Aprobado"),
    "rechazado": ("rechazado", "Rechazado"),
}


def registrar_busqueda(tipo, valor):
    """
    Apunta una busqueda (tipo "ticket" o "cliente") como la mas reciente.
    Si ya estaba, sube al principio en vez de duplicarse.
    """
    if not valor:
        return

    historial = st.session_state.setdefault(_CLAVE_BUSQUEDAS, {})
    recientes = [v for v in historial.get(tipo, []) if v != valor]
    recientes.insert(0, valor)
    historial[tipo] = recientes[:MAX_RECIENTES]


def busquedas_recientes(tipo):
    return st.session_state.get(_CLAVE_BUSQUEDAS, {}).get(tipo, [])


def limpiar_busquedas():
    st.session_state.pop(_CLAVE_BUSQUEDAS, None)


def _fecha_corta(iso):
    """'2026-09-16T10:35:00' -> '16/09 10:35'. Devuelve el texto tal cual si no parsea."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m %H:%M")
    except ValueError:
        return str(iso)


def cambios_recientes(limite=6, cliente=None):
    """
    Ultimas solicitudes de horas/limite, de la mas reciente a la mas
    antigua, en cualquier estado. Con 'cliente' se limita a ese cliente.
    """
    todas = solicitudes.listar_solicitudes()
    if cliente:
        todas = [s for s in todas if s["cliente"] == cliente]

    todas = sorted(
        todas,
        key=lambda s: s.get("fecha_revision") or s.get("fecha_solicitud") or "",
        reverse=True,
    )
    return todas[:limite]


def _linea_cambio(solicitud):
    """Una fila del timeline de cambios, ya en HTML."""
    from html import escape

    estado = solicitud.get("estado", "pendiente")
    clase, etiqueta = ESTADO_CHIP.get(estado, ("pendiente", estado))

    if solicitud["tipo"] == "horas":
        titulo = f"Horas del ticket {solicitud.get('ticket_id') or '—'}"
    else:
        titulo = "Limite de horas contratadas"

    antes = solicitudes.formatear_horas(solicitud.get("valor_actual"))
    despues = solicitudes.formatear_horas(solicitud.get("valor_propuesto"), defecto="—")

    momento = _fecha_corta(solicitud.get("fecha_revision") or solicitud.get("fecha_solicitud"))
    quien = solicitud.get("revisado_por") or solicitud.get("solicitado_por") or ""

    return (
        f'<li class="tl-item {clase}">'
        f'<div class="tl-head"><span class="tl-title">{escape(titulo)}</span>'
        f'<span class="tl-chip {clase}">{etiqueta}</span></div>'
        f'<div class="tl-body">{escape(solicitud["cliente"])} · <b>{antes} → {despues}</b></div>'
        f'<div class="tl-meta">{escape(momento)} · {escape(quien)}</div>'
        f"</li>"
    )


def render_cambios_recientes(limite=6, cliente=None, titulo="Ultimos cambios"):
    """Timeline compacto de los ultimos cambios de horas y limite."""
    recientes = cambios_recientes(limite=limite, cliente=cliente)
    if not recientes:
        st.markdown(
            f'<div class="tl-empty">Todavia no hay cambios de horas ni de limite'
            f'{" para este cliente" if cliente else ""}.</div>',
            unsafe_allow_html=True,
        )
        return

    filas = "".join(_linea_cambio(s) for s in recientes)
    st.markdown(
        f'<div class="timeline"><div class="tl-caption">{titulo}</div><ul>{filas}</ul></div>',
        unsafe_allow_html=True,
    )
