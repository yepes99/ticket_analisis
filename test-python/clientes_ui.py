"""
Componentes de UI de clientes (ranking, detalle, solicitudes pendientes).

Se reutilizan tanto en el Dashboard (app.py, visible para Web Admin y
Soporte) como en la pagina dedicada Clientes (pages/1_Clientes.py, con
acceso ademas para CS y Lector), para no duplicar la logica en dos sitios.
"""

import pandas as pd
import streamlit as st
import streamlit.column_config as stcc

import config
import limites
import solicitudes
from charts import create_top_clients_chart
from metrics import calculate_client_ticket_detail, calculate_top_clients
from ui_components import empty_state, kpi_grid, render_chart_wrapper, section_title


TONE_HEX = {
    "success": config.COLOR_VARS["--success"],
    "warning": config.COLOR_VARS["--warning"],
    "danger": config.COLOR_VARS["--danger"],
}
TONE_ICON = {"success": "🟢", "warning": "🟠", "danger": "🔴"}


def horas_tono(horas_totales, limite_actual):
    """Tono (success/warning/danger) y mensaje segun el exceso sobre el limite."""
    if limite_actual is None:
        return "neutral", "Sin limite contratado definido"

    exceso = horas_totales - limite_actual
    if exceso > 10:
        return "danger", f"{exceso:.1f} h por encima del limite contratado"
    if exceso > 8:
        return "warning", f"{exceso:.1f} h por encima del limite contratado"
    return "success", "Dentro del limite contratado"


def render_horas_banner(cliente, horas_totales, limite_actual):
    """Tarjeta grande y coloreada con las horas consumidas frente al limite."""
    tono, mensaje = horas_tono(horas_totales, limite_actual)
    color = TONE_HEX.get(tono, config.COLOR_VARS["--muted"])
    icono = TONE_ICON.get(tono, "⚪")
    limite_label = f"{limite_actual:.1f} h contratadas" if limite_actual is not None else "sin limite definido"

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}26, {color}0d);
            border: 1px solid {color}55;
            border-left: 6px solid {color};
            border-radius: 12px;
            padding: 1.1rem 1.4rem;
            margin: 0.9rem 0 1.1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        ">
            <div>
                <div style="font-size:0.78rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;">
                    Horas consumidas · {cliente}
                </div>
                <div style="font-size:2.3rem;font-weight:850;color:var(--ink);line-height:1;margin-top:.3rem;">
                    {horas_totales:.1f} h
                </div>
                <div style="font-size:0.82rem;color:var(--ink-soft);margin-top:.35rem;">{limite_label}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:2rem;line-height:1;">{icono}</div>
                <div style="font-size:0.85rem;font-weight:700;color:{color};max-width:240px;margin-top:.3rem;">
                    {mensaje}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ranking_clientes(filtered):
    section_title(
        "Tickets por cliente",
        "Conteo exacto de bugs Jira unicos, con el nombre comercial separado del dominio.",
    )
    clientes_resumen = calculate_top_clients(filtered)
    if not clientes_resumen.empty:
        chart_col, table_col = st.columns([1, 1.35], gap="large")
        with chart_col:
            render_chart_wrapper(create_top_clients_chart(clientes_resumen.head(20)))
        with table_col:
            st.dataframe(
                clientes_resumen,
                width="stretch",
                hide_index=True,
                column_config={
                    "cliente": stcc.TextColumn("Cliente", width="medium"),
                    "dominios": stcc.TextColumn("Domain / URL", width="large"),
                    "tickets": stcc.NumberColumn("Tickets Bug", format="%d"),
                    "tickets_sin_tiempo": stcc.NumberColumn("Sin tiempo", format="%d"),
                    "sla": stcc.NumberColumn("SLA global", format="%.1f%%"),
                    "tiempo_horas": stcc.NumberColumn("Tiempo medio", format="%.1f h"),
                },
            )
    else:
        empty_state("No hay clientes para los filtros actuales.")


def render_detalle_cliente(filtered, role, key_prefix=""):
    """
    Selector de cliente + banner de horas + KPIs + gestion + tabla de tickets.

    key_prefix distingue las keys de los widgets cuando esta funcion se
    llama mas de una vez en la misma pagina (Dashboard y Clientes son
    scripts separados, pero por si acaso).
    """
    is_admin = role == "admin"
    puede_gestionar = role in {"admin", "soporte", "cs"}
    vista_resumida = role == "cs"

    section_title(
        "🔍 Detalle de tareas por cliente",
        "Selecciona un cliente para ver sus tareas, su tiempo de resolucion y el consumo frente al limite de horas contratado.",
    )

    clientes_disponibles = sorted(filtered["cliente"].dropna().unique().tolist())

    cliente_seleccionado = st.selectbox(
        "Selecciona un cliente para ver su detalle",
        options=[""] + clientes_disponibles,
        index=0,
        format_func=lambda x: "— Elige un cliente —" if x == "" else x,
        key=f"{key_prefix}cliente_seleccionado",
    )

    if not cliente_seleccionado:
        return

    detalle_df = calculate_client_ticket_detail(filtered, cliente_seleccionado)

    total = len(detalle_df)
    if "resuelto" in detalle_df.columns:
        resueltos = int(detalle_df["resuelto"].sum())
    elif "estado" in detalle_df.columns:
        resueltos = int(detalle_df["estado"].astype(str).str.lower().eq("finalizada").sum())
    else:
        resueltos = 0

    horas_totales = pd.to_numeric(detalle_df.get("horas_resolucion"), errors="coerce").sum()
    limite_actual = limites.obtener_limite(cliente_seleccionado)

    # Tarjeta grande y coloreada: lo primero que se ve
    render_horas_banner(cliente_seleccionado, horas_totales, limite_actual)

    # KPIs secundarios, sin dramatismo de color
    kpi_grid(
        [
            ("Tareas", str(total), f"Total de {cliente_seleccionado}", ""),
            ("Resueltas", str(resueltos), "En estado Finalizada", ""),
            (
                "Limite contratado",
                f"{limite_actual:.1f} h" if limite_actual is not None else "Sin definir",
                "Configurable en 'Gestionar' abajo",
                "",
            ),
        ],
        secondary=True,
    )

    if puede_gestionar:
        with st.expander("⚙️ Gestionar horas y limite", expanded=False):
            if is_admin:
                st.caption("Como Web Admin, tus propias solicitudes tambien quedan pendientes hasta que las apruebes en 'Solicitudes pendientes'.")
            else:
                st.caption("Toda solicitud queda pendiente hasta que un Web Admin la revise y apruebe.")

            gestion_tabs = st.tabs(["Corregir horas de un ticket", "Cambiar limite del cliente"])

            with gestion_tabs[0]:
                ticket_options = detalle_df["ticket_id"].dropna().astype(str).tolist()
                if ticket_options:
                    ticket_to_edit = st.selectbox("Ticket", ticket_options, key=f"{key_prefix}ticket_to_edit")
                    current_hours = detalle_df.loc[
                        detalle_df["ticket_id"].astype(str).eq(ticket_to_edit), "horas_resolucion"
                    ].iloc[0]
                    propuesta_horas = st.number_input(
                        "Horas propuestas",
                        min_value=0.0,
                        value=float(current_hours) if pd.notna(current_hours) else 0.0,
                        step=0.25,
                        key=f"{key_prefix}corrected_hours",
                    )
                    if st.button("Enviar solicitud", key=f"{key_prefix}save_hours_correction", width="stretch"):
                        solicitudes.crear_solicitud(
                            "horas",
                            cliente_seleccionado,
                            float(current_hours) if pd.notna(current_hours) else None,
                            propuesta_horas,
                            st.session_state.get("username") or role,
                            ticket_id=ticket_to_edit,
                        )
                        st.success("Solicitud enviada. Un Web Admin debe aprobarla.")
                else:
                    empty_state("No hay tickets para corregir.")

            with gestion_tabs[1]:
                nuevo_limite = st.number_input(
                    "Limite de horas contratadas",
                    min_value=0.0,
                    value=float(limite_actual) if limite_actual is not None else 0.0,
                    step=1.0,
                    key=f"{key_prefix}nuevo_limite_horas",
                )
                if st.button("Enviar solicitud", key=f"{key_prefix}guardar_limite_horas", width="stretch"):
                    solicitudes.crear_solicitud(
                        "limite",
                        cliente_seleccionado,
                        limite_actual,
                        nuevo_limite,
                        st.session_state.get("username") or role,
                    )
                    st.success("Solicitud enviada. Un Web Admin debe aprobarla.")

                historial = limites.obtener_historial(cliente_seleccionado)
                if historial:
                    st.caption("Historico de cambios del limite")
                    st.dataframe(
                        pd.DataFrame(historial),
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "timestamp": "Fecha",
                            "usuario": "Usuario",
                            "valor_anterior": stcc.NumberColumn("Antes", format="%.1f h"),
                            "valor_nuevo": stcc.NumberColumn("Despues", format="%.1f h"),
                        },
                    )

            render_solicitudes_cliente(cliente_seleccionado)

    st.markdown("---")

    if vista_resumida:
        empty_state(
            "Vista resumida para Customer Success: horas, presupuesto y estado ya se muestran arriba. "
            "El detalle tecnico de cada ticket no esta disponible en este rol."
        )
    elif not detalle_df.empty:
        st.caption(
            "Tareas ordenadas de mas reciente a mas antigua. \"Presupuesto\" es el campo Budget de Jira; "
            "cuando las horas consumidas de un ticket lo superan en mas de 8h la fila se marca en naranja, y en mas de 10h en rojo."
        )

        def highlight_diferencia_horas(row):
            diff = pd.to_numeric(row.get("diferencia_horas"), errors="coerce")
            if pd.isna(diff):
                color = ""
            elif diff > 10:
                color = f"background-color: {config.COLOR_VARS['--danger']}; color: #fff"
            elif diff > 8:
                color = f"background-color: {config.COLOR_VARS['--warning']}; color: #080d14"
            else:
                color = ""
            return [color for _ in row]

        st.dataframe(
            detalle_df.style.apply(highlight_diferencia_horas, axis=1),
            width="stretch",
            hide_index=True,
            column_config={
                "ticket_id": "Ticket",
                "cliente_nombre": "Cliente",
                "cliente_domain": "Domain",
                "cliente_url": stcc.LinkColumn("URL", display_text="Abrir URL"),
                "resumen": stcc.TextColumn("Descripcion", width="large"),
                "tipo": "Tipo",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "asignado_a": "Tecnico",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "horas_resolucion": stcc.NumberColumn("Horas resolucion", format="%.1f h"),
                "presupuesto": stcc.NumberColumn("Presupuesto", format="%.1f h"),
                "diferencia_horas": stcc.NumberColumn("Diferencia", format="%.1f h"),
            },
        )
    else:
        empty_state(f"No hay tareas para {cliente_seleccionado}.")


def render_solicitudes_pendientes():
    """Panel de aprobacion de solicitudes. Solo debe llamarse para Web Admin."""
    pendientes = solicitudes.listar_solicitudes(estado="pendiente")
    if not pendientes:
        empty_state("No hay solicitudes pendientes ahora mismo.")
        return

    section_title(
        "🔔 Solicitudes pendientes",
        "Cambios de horas o de limite pedidos por Soporte/CS. Requieren tu aprobacion.",
    )
    for solicitud in pendientes:
        revisor = st.session_state.get("username") or "admin"
        with st.container(border=True):
            info_col, action_col = st.columns([4, 1.6])
            with info_col:
                actual = solicitud["valor_actual"]
                actual_label = f"{actual:.1f} h" if actual is not None else "sin dato"
                if solicitud["tipo"] == "horas":
                    tipo_label = "🕒 Horas de resolucion"
                    objetivo_label = f"ticket **{solicitud['ticket_id']}** de {solicitud['cliente']}"
                else:
                    tipo_label = "📈 Limite contratado"
                    objetivo_label = f"cliente **{solicitud['cliente']}**"
                st.markdown(f"**{tipo_label}** — {objetivo_label}")
                st.markdown(
                    f"{actual_label} → **{solicitud['valor_propuesto']:.1f} h** "
                    f"&nbsp;·&nbsp; pedido por *{solicitud['solicitado_por']}*"
                )
            with action_col:
                btn_col1, btn_col2 = st.columns(2)
                if btn_col1.button("✅ Aprobar", key=f"aprobar_{solicitud['id']}", width="stretch"):
                    aprobada = solicitudes.resolver_solicitud(solicitud["id"], True, revisor)
                    if aprobada["tipo"] == "limite":
                        limites.actualizar_limite(
                            aprobada["cliente"],
                            aprobada["valor_propuesto"],
                            usuario=f"{aprobada['solicitado_por']} (aprobado por {revisor})",
                        )
                    st.rerun()
                if btn_col2.button("❌ Rechazar", key=f"rechazar_{solicitud['id']}", width="stretch"):
                    solicitudes.resolver_solicitud(solicitud["id"], False, revisor)
                    st.rerun()


ESTADO_BADGE = {
    "pendiente": ("🟡", "Pendiente"),
    "aprobado": ("🟢", "Aprobado"),
    "rechazado": ("🔴", "Rechazado"),
}


def render_solicitudes_cliente(cliente):
    """
    Historial de solicitudes (horas y limite) de un cliente, con su estado.

    Para que quien pide un cambio (Soporte/CS) vea si se acepto o se
    rechazo, sin tener que preguntarle al Web Admin.
    """
    todas = [s for s in solicitudes.listar_solicitudes() if s["cliente"] == cliente]
    if not todas:
        return

    todas = sorted(todas, key=lambda s: s["fecha_solicitud"], reverse=True)
    st.caption("Solicitudes de este cliente")
    for solicitud in todas:
        icono, etiqueta = ESTADO_BADGE.get(solicitud["estado"], ("⚪", solicitud["estado"]))
        actual = solicitud["valor_actual"]
        actual_label = f"{actual:.1f} h" if actual is not None else "sin dato"
        if solicitud["tipo"] == "horas":
            objetivo = f"horas del ticket **{solicitud['ticket_id']}**"
        else:
            objetivo = "limite del cliente"
        detalle_revision = ""
        if solicitud["estado"] != "pendiente" and solicitud.get("revisado_por"):
            detalle_revision = f" · revisado por {solicitud['revisado_por']}"
        st.markdown(
            f"{icono} **{etiqueta}** — {objetivo}: {actual_label} → **{solicitud['valor_propuesto']:.1f} h** "
            f"(pedido por {solicitud['solicitado_por']}{detalle_revision})"
        )
