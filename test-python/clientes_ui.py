"""
Componentes de UI de clientes (ranking, detalle, solicitudes pendientes).

Se reutilizan tanto en el Dashboard (app.py, visible para Web Admin y
Soporte) como en la pagina dedicada Clientes (pages/1_Clientes.py, con
acceso ademas para CS y Lector), para no duplicar la logica en dos sitios.
"""

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
import streamlit.column_config as stcc

import bono
import config
import limites
import solicitudes
from charts import create_top_clients_chart
from metrics import calculate_client_ticket_detail, calculate_top_clients
from ui_components import empty_state, kpi_grid, render_chart_wrapper, section_title


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


def _kpi_tone(tono):
    """kpi_grid solo tiene estilo para success/warning/danger; el resto (p.ej. 'neutral') es tarjeta normal."""
    return tono if tono in {"success", "warning", "danger"} else ""


def _valor_reciente(serie):
    """
    Ultimo valor no vacio de una columna (p.ej. Plan o Tipo), asumiendo que
    la serie viene ordenada de mas reciente a mas antigua. Si el cliente ha
    tenido varios valores distintos en el periodo, lo indica en el detalle
    en vez de ocultarlo.
    """
    valores = serie.dropna() if serie is not None else pd.Series(dtype="object")
    if valores.empty:
        return "Sin dato", "Aun no rellenado en Jira"

    distintos = valores.unique()
    detalle = "Valor actual en Jira" if len(distintos) == 1 else f"Ultimo valor · {len(distintos)} valores distintos en el periodo"
    return str(valores.iloc[0]), detalle


RANKING_COLUMN_CONFIG = {
    "cliente": stcc.TextColumn("Cliente", width="medium"),
    "dominios": stcc.TextColumn("Domain / URL", width="medium"),
    "tickets": stcc.NumberColumn("Tickets Bug", format="%d"),
    "tickets_sin_tiempo": stcc.NumberColumn("Sin tiempo", format="%d"),
    "sla": stcc.TextColumn("SLA global"),
    "tiempo_horas": stcc.TextColumn("Tiempo medio"),
    "plan": stcc.TextColumn("Plan", width="medium"),
    "tipo": stcc.TextColumn("Tipo", width="medium"),
    "bono": stcc.TextColumn("Bono de horas", width="medium"),
}

# "bono_comprado"/"bono_disponible" son columnas auxiliares (solo para
# calcular la celda "bono" formateada) que no deben verse en la tabla.
RANKING_COLUMN_ORDER = [
    "cliente", "dominios", "tickets", "tickets_sin_tiempo", "sla", "tiempo_horas", "plan", "tipo", "bono",
]

# Alto (en px) de la cabecera y de cada fila de un st.dataframe en esta
# version de Streamlit, medido empiricamente. Con un alto fijo "a ojo" (o
# sin alto, que usa un valor por defecto) la ultima fila visible quedaba
# cortada a la mitad antes del scroll interno -- se veia raro. Con un
# multiplo exacto de FILA_ALTO_PX nunca se corta una fila a medias.
CABECERA_ALTO_PX = 70
FILA_ALTO_PX = 36


def _alto_tabla_completa(n_filas, max_filas=None):
    """
    Alto exacto (cabecera + N filas completas, nunca una fila a medias)
    para que quepan todas las filas sin scroll interno. Con max_filas se
    pone un tope (para listas muy largas) que tambien cae en un multiplo
    exacto de fila, asi que el corte sigue siendo limpio.
    """
    filas = max(n_filas, 1)
    if max_filas:
        filas = min(filas, max_filas)
    return CABECERA_ALTO_PX + filas * FILA_ALTO_PX


def _formatear_tabla_ranking(clientes_resumen):
    """
    "sla"/"tiempo_horas" salen de un .mean() que puede dar NaN (cliente sin
    tickets resueltos todavia); "plan"/"tipo" pueden no estar rellenados en
    Jira. Un valor nulo en una NumberColumn de Streamlit se renderiza como
    el texto literal "None", asi que todo esto se formatea a texto aqui
    mismo (con un guion para "sin datos") y se muestra como TextColumn.
    """
    tabla = clientes_resumen.copy()
    tabla["sla"] = tabla["sla"].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
    tabla["tiempo_horas"] = tabla["tiempo_horas"].apply(lambda v: f"{v:.1f} h" if pd.notna(v) else "—")
    tabla["plan"] = tabla["plan"].fillna("—") if "plan" in tabla.columns else "—"
    tabla["tipo"] = tabla["tipo"].fillna("—") if "tipo" in tabla.columns else "—"

    def _bono_celda(row):
        comprado = row.get("bono_comprado", 0.0)
        disponible = row.get("bono_disponible", 0.0)
        tono, icono, _ = bono.bono_tono(comprado, disponible)
        if tono == "neutral":
            return "—"
        return f"{icono} {disponible:.1f} h"

    tabla["bono"] = tabla.apply(_bono_celda, axis=1)
    return tabla

# Roles con vista simplificada: sin el grafico (no les aporta, solo la
# tabla les interesa) y a ancho completo para que la tabla sea mas grande
# y comoda de leer.
ROLES_VISTA_SIMPLE_RANKING = {"cs", "lector"}


def render_ranking_clientes(filtered, role=None):
    section_title(
        "Tickets por cliente",
        "Conteo exacto de bugs Jira unicos, con el nombre comercial separado del dominio.",
    )
    clientes_resumen = calculate_top_clients(filtered)
    if clientes_resumen.empty:
        empty_state("No hay clientes para los filtros actuales.")
        return

    busqueda = st.text_input(
        "Buscar cliente",
        placeholder="🔎 Busca por nombre de cliente o dominio...",
        key="ranking_clientes_busqueda",
    )
    if busqueda:
        termino = busqueda.strip().lower()
        clientes_resumen = clientes_resumen[
            clientes_resumen["cliente"].str.lower().str.contains(termino, na=False)
            | clientes_resumen["dominios"].str.lower().str.contains(termino, na=False)
        ]

    if clientes_resumen.empty:
        empty_state(f"Ningun cliente coincide con \"{busqueda}\".")
        return

    # Sin tope: con "muy completa" pedido explicitamente, mejor pagina larga
    # que un scroll interno que corte clientes a medias.
    alto_tabla = _alto_tabla_completa(len(clientes_resumen))

    if role not in ROLES_VISTA_SIMPLE_RANKING:
        # Admin/Soporte: grafico arriba a ancho completo. Antes iba en
        # columna junto a la tabla y la dejaba apretada; ahora la tabla de
        # abajo es tan completa como la que ve CS.
        render_chart_wrapper(create_top_clients_chart(clientes_resumen.head(20)))

    st.dataframe(
        _formatear_tabla_ranking(clientes_resumen),
        width="stretch",
        hide_index=True,
        height=alto_tabla,
        column_config=RANKING_COLUMN_CONFIG,
        column_order=RANKING_COLUMN_ORDER,
    )


def render_detalle_cliente(filtered, role, key_prefix=""):
    """
    Selector de cliente + resumen en tarjetas KPI (horas, limite, bono,
    tareas, Plan, Tipo) + gestion + tabla de tickets. Usa el mismo
    lenguaje visual (kpi_grid/section_title) que el resto del dashboard.

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
    bono_info = bono.calcular_bono_cliente(filtered, cliente_seleccionado)

    horas_tono_str, horas_mensaje = horas_tono(horas_totales, limite_actual)
    bono_tono_str, _, bono_mensaje = bono.bono_tono(bono_info["comprado"], bono_info["disponible"])
    limite_detalle = "Configurado a mano en 'Gestionar' abajo" if limite_actual is not None else "Configurable en 'Gestionar' abajo"
    plan_valor, plan_detalle = _valor_reciente(detalle_df.get("plan_servicio"))
    tipo_valor, tipo_detalle = _valor_reciente(detalle_df.get("tipo_producto"))

    section_title(
        f"📊 Resumen · {cliente_seleccionado}",
        "Horas consumidas frente al limite contratado y saldo del bono de horas.",
    )

    # Fila principal: los tres numeros que importan, con color segun su estado.
    kpi_grid(
        [
            ("Horas consumidas", f"{horas_totales:.1f} h", horas_mensaje, _kpi_tone(horas_tono_str)),
            (
                "Limite contratado",
                f"{limite_actual:.1f} h" if limite_actual is not None else "Sin definir",
                limite_detalle,
                "",
            ),
            (
                "Bono disponible",
                f"{bono_info['disponible']:.1f} h" if bono_info["comprado"] > 0 else "Sin bono",
                bono_mensaje,
                _kpi_tone(bono_tono_str),
            ),
        ],
        secondary=True,
    )

    # Fila secundaria: volumen de tareas y los campos Plan/Tipo de Jira.
    kpi_grid(
        [
            ("Tareas", str(total), f"Total de {cliente_seleccionado}", ""),
            ("Resueltas", str(resueltos), "En estado Finalizada", ""),
            ("Plan", plan_valor, plan_detalle, ""),
            ("Tipo", tipo_valor, tipo_detalle, ""),
        ]
    )

    if not bono_info["compras"].empty:
        with st.expander(f"🎟️ Compras de bono detectadas ({len(bono_info['compras'])})", expanded=False):
            st.caption(
                "Tickets cuya descripcion contiene un texto de compra de bono "
                "(ej. \"Tipo de tarea: 10h web changes bundle\")."
            )
            st.dataframe(
                bono_info["compras"],
                width="stretch",
                hide_index=True,
                height=_alto_tabla_completa(len(bono_info["compras"]), max_filas=8),
                column_config={
                    "ticket_id": "Ticket",
                    "fecha_creacion": stcc.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
                    "bono_horas_compradas": stcc.NumberColumn("Horas compradas", format="%.1f h"),
                },
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

    section_title(
        f"📋 Historial de tareas · {cliente_seleccionado}",
        "Detalle ticket a ticket, ordenado de mas reciente a mas antigua.",
    )

    if vista_resumida:
        empty_state(
            "Vista resumida para Customer Success: horas, presupuesto y estado ya se muestran arriba. "
            "El detalle tecnico de cada ticket no esta disponible en este rol."
        )
    elif not detalle_df.empty:
        st.caption(
            "\"Presupuesto\" es el campo Budget de Jira; cuando las horas consumidas de un ticket lo superan "
            "en mas de 8h la fila se marca en naranja, y en mas de 10h en rojo."
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

        # Solo para mostrar: celdas de texto vacias en vez de <NA>, que el
        # widget de tabla de Streamlit renderiza como el texto literal "None".
        tabla_historial = detalle_df.copy()
        for col in ("plan_servicio", "tipo_producto"):
            if col in tabla_historial.columns:
                tabla_historial[col] = tabla_historial[col].fillna("")

        st.dataframe(
            tabla_historial.style.apply(highlight_diferencia_horas, axis=1),
            width="stretch",
            hide_index=True,
            height=_alto_tabla_completa(len(tabla_historial), max_filas=15),
            column_config={
                "ticket_id": "Ticket",
                "cliente_nombre": "Cliente",
                "cliente_domain": "Domain",
                "cliente_url": stcc.LinkColumn("URL", display_text="Abrir URL"),
                "resumen": stcc.TextColumn("Descripcion", width="large"),
                "tipo": "Tipo de incidencia",
                "plan_servicio": "Plan",
                "tipo_producto": "Tipo",
                "estado": "Estado",
                "prioridad": "Prioridad",
                "size": "Tamaño",
                "asignado_a": "Tecnico",
                "fecha_creacion": stcc.DatetimeColumn("Creado", format="DD/MM/YYYY"),
                "fecha_resolucion": stcc.DatetimeColumn("Resuelto", format="DD/MM/YYYY"),
                "horas_resolucion": stcc.NumberColumn("Horas resolucion", format="%.1f h", help="Desde creacion hasta Finalizada, sin contar el tiempo en Pending Info."),
                "horas_pending_info": stcc.NumberColumn("Horas Pending Info", format="%.1f h"),
                "horas_trabajo_real": stcc.NumberColumn("Horas trabajo real", format="%.1f h", help="Desde que se coge el ticket (sale de Backlog) hasta Finalizada/ahora."),
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


def render_historico_cambios():
    """
    Historico global de TODOS los cambios de horas y limite ya resueltos
    (aprobados o rechazados), de todos los clientes. Solo para Web Admin.
    Incluye descarga en Excel para guardar constancia fuera del dashboard.
    """
    resueltas = [s for s in solicitudes.listar_solicitudes() if s["estado"] != "pendiente"]
    if not resueltas:
        empty_state("Todavia no hay cambios de horas o limite resueltos.")
        return

    resueltas = sorted(resueltas, key=lambda s: s.get("fecha_revision") or "", reverse=True)

    filas = [
        {
            "Fecha solicitud": s["fecha_solicitud"],
            "Fecha revision": s["fecha_revision"],
            "Tipo": "Horas" if s["tipo"] == "horas" else "Limite",
            "Cliente": s["cliente"],
            "Ticket": s["ticket_id"] or "-",
            "Antes (h)": s["valor_actual"] if s["valor_actual"] is not None else float("nan"),
            "Despues (h)": s["valor_propuesto"],
            "Solicitado por": s["solicitado_por"],
            "Revisado por": s["revisado_por"],
            "Estado": "Aprobado" if s["estado"] == "aprobado" else "Rechazado",
        }
        for s in resueltas
    ]

    st.dataframe(
        filas,
        width="stretch",
        hide_index=True,
        column_config={
            "Antes (h)": stcc.NumberColumn(format="%.1f h"),
            "Despues (h)": stcc.NumberColumn(format="%.1f h"),
        },
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(filas).to_excel(writer, sheet_name="Historico", index=False)

    st.download_button(
        "⬇️ Descargar histórico en Excel",
        data=output.getvalue(),
        file_name=f"historico_horas_limites_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="descargar_historico_cambios",
    )
