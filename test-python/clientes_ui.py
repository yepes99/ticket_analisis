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
import historial
import limites
import presupuesto as presu
import solicitudes
from charts import create_top_clients_chart
from metrics import calculate_client_ticket_detail, calculate_top_clients
from ui_components import empty_state, kpi_grid, render_chart_wrapper, section_title


# El limite de horas contratadas (bono) es un producto de mantenimiento
# WordPress: solo tiene sentido pedir cambiarlo en estos 3 planes. El resto
# de clientes puede seguir viendo su bono/horas consumidas (se calculan
# igual), pero no se les deja pedir un cambio de limite.
PLANES_CON_LIMITE = {"wp smart", "wp custom", "wp advanced"}


def _plan_permite_cambiar_limite(plan_valor):
    # pd.isna en vez de "or": un Plan vacio puede llegar como pd.NA (columna
    # de pandas/pyarrow), y bool(pd.NA) revienta con TypeError a proposito
    # (NA no admite conversion implicita a booleano, a diferencia de None).
    if pd.isna(plan_valor):
        return False
    return str(plan_valor).strip().casefold() in PLANES_CON_LIMITE


def filtrar_tickets_clientes_wordpress(filtered):
    """
    Deja solo los tickets de clientes en un plan WordPress con limite de
    horas (ver PLANES_CON_LIMITE). El plan de cada cliente es el ultimo
    visto en Jira (mismo criterio que la columna "Plan" del ranking).
    """
    if filtered.empty or "cliente" not in filtered.columns:
        return filtered.iloc[0:0]

    resumen = calculate_top_clients(filtered)
    clientes_wp = set(
        resumen.loc[resumen["plan"].apply(_plan_permite_cambiar_limite), "cliente"]
    )
    return filtered[filtered["cliente"].isin(clientes_wp)]


def horas_tono(horas_totales, limite_actual):
    """Tono (success/warning/danger) y mensaje segun el exceso sobre el limite."""
    if limite_actual is None or pd.isna(limite_actual):
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
    "horas": stcc.TextColumn(
        "Horas consumidas",
        help="Horas de resolucion gastadas en el periodo, sin contar los tickets de compra de bono.",
    ),
    "limite_texto": stcc.TextColumn(
        "Limite contratado",
        help="Suma de los bonos de horas comprados por el cliente. Mientras no tenga ningun bono se usa el valor puesto a mano en 'Gestionar'.",
    ),
    "bono": stcc.TextColumn(
        "Horas disponibles",
        width="medium",
        help=(
            "Limite contratado menos las horas consumidas (con bonos es el saldo del bono): "
            "verde con 10 h o mas, naranja por debajo de 10 h, rojo al agotarse."
        ),
    ),
}

# "bono_comprado"/"bono_disponible"/"horas_consumidas"/"limite" son columnas
# auxiliares: guardan el valor numerico con el que se calculan las celdas
# formateadas ("horas"/"limite_texto"/"bono") y su color, y no deben verse.
RANKING_COLUMN_ORDER = [
    "cliente", "dominios", "tickets", "horas", "limite_texto", "bono",
    "tickets_sin_tiempo", "sla", "tiempo_horas", "plan", "tipo",
]

# Colores de celda de la tabla de ranking, con el mismo semaforo que las
# tarjetas KPI (config.COLOR_VARS) para que verde/naranja/rojo signifiquen
# lo mismo en toda la app.
TONO_CELDA = {
    "success": f"background-color: {config.COLOR_VARS['--success']}; color: #08121b",
    "warning": f"background-color: {config.COLOR_VARS['--warning']}; color: #080d14",
    "danger": f"background-color: {config.COLOR_VARS['--danger']}; color: #fff",
}

# Alto (en px) de la cabecera y de cada fila de un st.dataframe en esta
# version de Streamlit, medido empiricamente. Con un alto fijo "a ojo" (o
# sin alto, que usa un valor por defecto) la ultima fila visible quedaba
# cortada a la mitad antes del scroll interno -- se veia raro. Con un
# multiplo exacto de FILA_ALTO_PX nunca se corta una fila a medias.
CABECERA_ALTO_PX = 70
FILA_ALTO_PX = 36


def _horas_o_guion(serie, index, con_signo=False):
    """
    "6.0 h" / "+2.0 h" para un numero y "—" cuando falta. Sirve para las
    columnas que casi siempre vienen vacias: en una columna numerica un
    hueco se pinta como un "None" gris, que ensucia la tabla entera.
    """
    if serie is None:
        return pd.Series("—", index=index)

    valores = pd.to_numeric(serie, errors="coerce")
    formato = "{:+.1f} h" if con_signo else "{:.1f} h"
    return valores.map(lambda v: "—" if pd.isna(v) else formato.format(v))


# Tipos de columna de Streamlit que exigen un valor numerico de verdad.
_TIPOS_NUMERICOS = {"number", "progress"}


def _sanear_para_mostrar(df, column_config):
    """
    Deja el DataFrame listo para enseñarlo en una tabla, sin "None" sueltos.

    Un None de Python en una columna de tipo object se renderiza como el
    texto literal "None"; y si la columna esta declarada como numerica en
    el column_config, ademas descuadra el formato. Aqui las numericas se
    pasan a numero (los huecos quedan como NaN, que se ve como celda
    vacia) y las de texto se rellenan con cadena vacia.
    """
    tabla = df.copy()
    for columna in tabla.columns:
        # Los helpers de column_config (NumberColumn, TextColumn...) no son
        # clases, devuelven un dict; el tipo se mira dentro de 'type_config'.
        config = column_config.get(columna)
        tipo = config.get("type_config", {}).get("type") if isinstance(config, dict) else None

        if tipo in _TIPOS_NUMERICOS:
            tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")
        elif pd.api.types.is_string_dtype(tabla[columna]) or tabla[columna].dtype == "object":
            # En pandas 3 una columna de texto puede venir como dtype 'str',
            # 'string' u 'object'; is_string_dtype las cubre todas.
            tabla[columna] = tabla[columna].fillna("")
    return tabla


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
    # .astype(object) antes de fillna: si la columna viene entera a NaN (nadie
    # tiene el campo relleno en Jira), pandas/pyarrow la tipa como "null" y
    # rellenarla con un string directamente revienta con ArrowInvalid.
    tabla["plan"] = tabla["plan"].astype(object).fillna("—") if "plan" in tabla.columns else "—"
    tabla["tipo"] = tabla["tipo"].astype(object).fillna("—") if "tipo" in tabla.columns else "—"

    def _disponible_celda(row):
        tono, icono, _ = _tono_disponible(row)
        if tono == "neutral":
            return "—"
        return f"{icono} {row['disponible']:.1f} h"

    tabla["bono"] = tabla.apply(_disponible_celda, axis=1)
    tabla["horas"] = tabla["horas_consumidas"].apply(lambda v: f"{v:.1f} h" if pd.notna(v) else "—")
    tabla["limite_texto"] = tabla.apply(_limite_celda, axis=1)
    return tabla


SUFIJO_ORIGEN = {
    limites.ORIGEN_BONO: "auto",
    limites.ORIGEN_MANUAL: "manual",
    limites.ORIGEN_DEFAULT: "por defecto",
}


def _limite_celda(row):
    """
    Limite contratado con una marca de su origen: "(auto)" cuando sale de la
    suma de bonos comprados, "(manual)" cuando lo puso un Web Admin, y
    "(por defecto)" cuando es el bono de base con el que arranca todo
    cliente sin bonos ni valor manual (ver limites.LIMITE_DEFAULT_HORAS).
    """
    valor = row.get("limite")
    if valor is None or pd.isna(valor):
        return "—"
    sufijo = SUFIJO_ORIGEN.get(row.get("limite_origen"), "manual")
    return f"{valor:.1f} h ({sufijo})"


def _tono_disponible(row):
    """
    Semaforo de las horas que le quedan al cliente. Sin limite contratado
    (ni bonos ni valor manual) no hay nada que evaluar: sale en gris.
    """
    limite = row.get("limite")
    if limite is None or pd.isna(limite):
        return "neutral", "⚪", "Sin horas contratadas definidas"

    disponible = row.get("disponible")
    if disponible is None or pd.isna(disponible):
        disponible = 0.0
    return bono.bono_tono(limite, disponible)


def _estilo_ranking(row):
    """
    Color de fondo por celda: el bono con su semaforo (verde >=10h, naranja
    por debajo, rojo agotado) y las horas consumidas con el exceso sobre el
    limite contratado. Asi se ve de un vistazo que clientes estan en apuros
    sin tener que abrir su detalle.
    """
    estilos = ["" for _ in row.index]

    # Limite contratado y horas disponibles son las dos caras de lo mismo,
    # asi que se pintan con el mismo color.
    tono_saldo, _, _ = _tono_disponible(row)
    if tono_saldo in TONO_CELDA:
        estilos[row.index.get_loc("bono")] = TONO_CELDA[tono_saldo]
        estilos[row.index.get_loc("limite_texto")] = TONO_CELDA[tono_saldo]

    tono_horas, _ = horas_tono(row["horas_consumidas"], row.get("limite"))
    if tono_horas in TONO_CELDA:
        estilos[row.index.get_loc("horas")] = TONO_CELDA[tono_horas]

    return estilos


TICKETS_COLUMN_CONFIG = {
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
    "horas_resolucion": stcc.NumberColumn(
        "Horas resolucion", format="%.1f h",
        help="Desde creacion hasta Finalizada, sin contar el tiempo en Pending Info.",
    ),
    "horas_pending_info": stcc.NumberColumn("Horas Pending Info", format="%.1f h"),
    "horas_trabajo_real": stcc.NumberColumn(
        "Horas trabajo real", format="%.1f h",
        help="Tiempo de desarrollo: desde que se coge el ticket (sale de Backlog) hasta Finalizada/ahora, sin el tiempo en Pending Info.",
    ),
    # Como texto y no como numero a proposito: hoy casi ningun ticket lleva
    # presupuesto, y una celda numerica vacia se pinta con un "None" gris
    # (marcador propio de Streamlit, no se puede cambiar por columna). Con
    # texto se controla y sale un guion, como en el resto de la app.
    "presupuesto_cliente": stcc.TextColumn(
        "Presupuesto cliente",
        help="Campo de Jira 'Presupuesto cliente (en horas)': las horas que el desarrollador estima que le va a costar el ticket.",
    ),
    "desviacion_presupuesto": stcc.TextColumn(
        "Desviacion",
        help="Horas de trabajo real por encima (+) o por debajo (-) de lo estimado.",
    ),
    "presupuesto": stcc.NumberColumn("Budget (antiguo)", format="%.1f h"),
    "diferencia_horas": stcc.NumberColumn("Dif. Budget", format="%.1f h"),
}

# Orden fijo, de lo mas util a lo mas accesorio. Sin esto la tabla enseñaba
# tambien columnas internas sin etiqueta (consumo_presupuesto, los
# sla_*_cumple, dias_resolucion...), que es lo que la hacia ilegible.
TICKETS_COLUMN_ORDER = [
    "ticket_id", "resumen", "estado", "prioridad", "size", "asignado_a",
    "fecha_creacion", "fecha_resolucion",
    "horas_resolucion", "horas_trabajo_real", "horas_pending_info",
    "presupuesto_cliente", "desviacion_presupuesto",
    "plan_servicio", "tipo_producto", "tipo", "cliente_url",
]

# Roles con vista simplificada: sin el grafico (no les aporta, solo la
# tabla les interesa) y a ancho completo para que la tabla sea mas grande
# y comoda de leer.
ROLES_VISTA_SIMPLE_RANKING = {"cs", "lector"}


def _filtrar_ranking(clientes_resumen, texto_cliente, solo_fuera_limite):
    """Aplica los filtros de la tabla de ranking sobre el resumen ya calculado."""
    resultado = clientes_resumen

    if texto_cliente:
        termino = texto_cliente.strip().lower()
        resultado = resultado[
            resultado["cliente"].str.lower().str.contains(termino, na=False)
            | resultado["dominios"].str.lower().str.contains(termino, na=False)
        ]

    if solo_fuera_limite:
        tonos_horas = resultado.apply(
            lambda fila: horas_tono(fila["horas_consumidas"], fila.get("limite"))[0],
            axis=1,
        )
        resultado = resultado[tonos_horas.isin({"warning", "danger"})]

    return resultado


def render_ranking_clientes(filtered, role=None, key_prefix=""):
    """
    key_prefix distingue las keys de los widgets cuando esta funcion se
    llama mas de una vez en la misma pagina (p.ej. "Ranking de clientes" y
    "Clientes WordPress" son dos llamadas independientes en clientes_page.py).
    """
    section_title(
        "Tickets por cliente",
        "Conteo exacto de bugs Jira unicos, con el nombre comercial separado del dominio.",
    )
    clientes_resumen = calculate_top_clients(filtered)
    if clientes_resumen.empty:
        empty_state("No hay clientes para los filtros actuales.")
        return

    col_busqueda, col_limite = st.columns([3, 1.4])
    texto_cliente = col_busqueda.text_input(
        "Buscar cliente",
        placeholder="🔎 Busca por nombre de cliente o dominio...",
        key=f"{key_prefix}ranking_clientes_busqueda",
    )
    solo_fuera_limite = col_limite.checkbox(
        "Solo fuera de limite",
        help="Deja solo los clientes cuyas horas consumidas superan el limite contratado (naranja o rojo).",
        key=f"{key_prefix}ranking_clientes_fuera_limite",
    )

    clientes_resumen = _filtrar_ranking(clientes_resumen, texto_cliente, solo_fuera_limite)

    if clientes_resumen.empty:
        empty_state("Ningun cliente coincide con los filtros de la tabla.")
        return

    # Sin tope: con "muy completa" pedido explicitamente, mejor pagina larga
    # que un scroll interno que corte clientes a medias.
    alto_tabla = _alto_tabla_completa(len(clientes_resumen))

    if role not in ROLES_VISTA_SIMPLE_RANKING:
        # Admin/Soporte: grafico arriba a ancho completo. Antes iba en
        # columna junto a la tabla y la dejaba apretada; ahora la tabla de
        # abajo es tan completa como la que ve CS.
        render_chart_wrapper(create_top_clients_chart(clientes_resumen.head(20)))

    st.caption(
        "**Limite contratado** y **Horas disponibles** van con el mismo semaforo: 🟢 10 h o mas "
        "disponibles · 🟠 por debajo de 10 h · 🔴 agotadas · ⚪ sin limite definido todavia. "
        "Las **horas consumidas** se pintan en naranja/rojo cuando superan el limite contratado. "
        "El limite es la suma de los bonos comprados y, mientras el cliente no tenga ninguno, "
        "el valor que se ponga a mano en *Detalle por cliente → Gestionar horas y limite*."
    )
    st.dataframe(
        _formatear_tabla_ranking(clientes_resumen).style.apply(_estilo_ranking, axis=1),
        width="stretch",
        hide_index=True,
        height=alto_tabla,
        lazy=False,
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

    # astype(str): si una fila trae un valor no textual en 'cliente',
    # sorted() sobre tipos mezclados reventaria.
    clientes_disponibles = sorted(filtered["cliente"].dropna().astype(str).unique().tolist())

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

    plan_valor, plan_detalle = _valor_reciente(detalle_df.get("plan_servicio"))
    tipo_valor, tipo_detalle = _valor_reciente(detalle_df.get("tipo_producto"))
    es_wordpress = _plan_permite_cambiar_limite(plan_valor)

    bono_info = bono.calcular_bono_cliente(filtered, cliente_seleccionado)
    # Mismas horas consumidas que en el ranking: las de los tickets normales,
    # sin contar los tickets de compra de bono (esos suman, no restan).
    horas_totales = bono_info["consumido"]
    limite_manual = limites.obtener_limite(cliente_seleccionado)

    if es_wordpress:
        limite_actual, limite_origen = limites.limite_efectivo(cliente_seleccionado, bono_info["comprado"])

        # Horas que le quedan: con bonos es el saldo del bono, y con un limite
        # puesto a mano es ese limite menos lo consumido. Mismo semaforo.
        disponible = None if limite_actual is None else limite_actual - horas_totales
        saldo_tono, _, saldo_mensaje = bono.bono_tono(limite_actual, disponible if disponible is not None else 0.0)

        horas_tono_str, horas_mensaje = horas_tono(horas_totales, limite_actual)
        if limite_origen == limites.ORIGEN_BONO:
            limite_detalle = f"Suma de {len(bono_info['compras'])} bono(s) de horas comprados"
        elif limite_origen == limites.ORIGEN_MANUAL:
            limite_detalle = "Valor manual · el cliente aun no tiene bonos comprados"
        else:
            limite_detalle = (
                f"Bono de base ({limites.LIMITE_DEFAULT_HORAS:.0f} h) · pidele a un Web Admin que lo cambie "
                "en 'Gestionar horas y limite' de aqui abajo"
            )
        limite_valor_texto = f"{limite_actual:.1f} h" if limite_actual is not None else "Sin definir"
        disponible_valor_texto = f"{disponible:.1f} h" if disponible is not None else "Sin definir"
    else:
        # El limite de horas contratadas (bono) es un producto de
        # mantenimiento WordPress: un cliente en otro plan no tiene ni
        # limite ni saldo que mostrar, solo las horas reales trabajadas.
        limite_origen = None
        limite_actual = None
        disponible = None
        saldo_tono, saldo_mensaje = "neutral", "No aplica a este plan"
        horas_tono_str, horas_mensaje = "", "Solo se compara con un limite en clientes WordPress"
        limite_detalle = "No aplica · este cliente no esta en un plan WordPress"
        limite_valor_texto = "No aplica"
        disponible_valor_texto = "No aplica"

    section_title(
        f"📊 Resumen · {cliente_seleccionado}",
        "Horas consumidas frente al limite contratado y horas que le quedan disponibles.",
    )

    # Fila principal: los tres numeros que importan, con color segun su estado.
    # En clientes fuera de un plan WordPress, limite y disponible salen como
    # "No aplica" (ver es_wordpress mas arriba): no tienen bono que gestionar.
    kpi_grid(
        [
            ("Horas consumidas", f"{horas_totales:.1f} h", horas_mensaje, _kpi_tone(horas_tono_str)),
            ("Limite contratado", limite_valor_texto, limite_detalle, ""),
            ("Horas disponibles", disponible_valor_texto, saldo_mensaje, _kpi_tone(saldo_tono)),
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

    # El resto del detalle va en pestañas en vez de apilado: antes eran dos
    # secciones y tres desplegables seguidos y habia que bajar mucho para
    # llegar a la tabla de tickets.
    nombres_tabs = ["🎟️ Bono y cambios", "💶 Presupuesto", "📋 Tickets"]
    if puede_gestionar:
        nombres_tabs.append("⚙️ Gestionar")
    tabs_detalle = st.tabs(nombres_tabs)

    with tabs_detalle[0]:
        col_bono, col_cambios = st.columns(2)
        with col_bono:
            if bono_info["compras"].empty:
                empty_state(
                    "Sin compras de bono detectadas para este cliente. Se detectan por la "
                    "descripcion del ticket (ej. \"Tipo de tarea: 10h web changes bundle\")."
                )
                if limite_origen == limites.ORIGEN_DEFAULT:
                    st.caption("Bono de base (no es una compra real en Jira)")
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "ticket_id": "— bono de base —",
                                    "fecha_creacion": pd.NaT,
                                    "bono_horas_compradas": limites.LIMITE_DEFAULT_HORAS,
                                }
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "ticket_id": "Ticket",
                            "fecha_creacion": stcc.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
                            "bono_horas_compradas": stcc.NumberColumn("Horas compradas", format="%.1f h"),
                        },
                    )
            else:
                st.caption(f"Compras de bono detectadas ({len(bono_info['compras'])})")
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
        with col_cambios:
            historial.render_cambios_recientes(
                limite=6,
                cliente=cliente_seleccionado,
                titulo=f"Ultimos cambios · {cliente_seleccionado}",
            )

    with tabs_detalle[1]:
        render_presupuesto_cliente(detalle_df, cliente_seleccionado)

    with tabs_detalle[2]:
        render_tickets_cliente(detalle_df, cliente_seleccionado, vista_resumida)

    if puede_gestionar:
        with tabs_detalle[3]:
            if is_admin:
                st.caption("Como Web Admin, tus propias solicitudes tambien quedan pendientes hasta que las apruebes en 'Solicitudes pendientes'.")
            else:
                st.caption("Toda solicitud queda pendiente hasta que un Web Admin la revise y apruebe.")

            puede_cambiar_limite = es_wordpress
            nombres_gestion_tabs = ["Corregir horas de un ticket"]
            if puede_cambiar_limite:
                nombres_gestion_tabs.append("Cambiar limite del cliente")
            gestion_tabs = st.tabs(nombres_gestion_tabs)

            if not puede_cambiar_limite:
                st.caption(
                    f"El limite de horas contratadas solo se gestiona en planes WordPress "
                    f"(WP Smart, WP Custom, WP Advanced). Plan actual de {cliente_seleccionado}: "
                    f"{plan_valor}."
                )

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

            if puede_cambiar_limite:
                with gestion_tabs[1]:
                    if limite_origen == limites.ORIGEN_BONO:
                        st.info(
                            f"El limite de **{cliente_seleccionado}** se calcula solo: son las "
                            f"**{limite_actual:.1f} h** de los bonos que ha comprado. El valor de abajo es el "
                            "respaldo manual y solo se usaria si dejara de tener bonos."
                        )
                    elif limite_origen == limites.ORIGEN_DEFAULT:
                        st.info(
                            f"**{cliente_seleccionado}** todavia no tiene bonos comprados ni un limite puesto a mano, "
                            f"asi que esta usando el bono de base de **{limites.LIMITE_DEFAULT_HORAS:.0f} h**. "
                            "Envia una solicitud aqui abajo para cambiarlo por otro valor."
                        )
                    nuevo_limite = st.number_input(
                        "Limite de horas contratadas",
                        min_value=0.0,
                        value=float(limite_manual) if limite_manual is not None else 0.0,
                        step=1.0,
                        key=f"{key_prefix}nuevo_limite_horas",
                    )
                    if st.button("Enviar solicitud", key=f"{key_prefix}guardar_limite_horas", width="stretch"):
                        solicitudes.crear_solicitud(
                            "limite",
                            cliente_seleccionado,
                            limite_manual,
                            nuevo_limite,
                            st.session_state.get("username") or role,
                        )
                        st.success("Solicitud enviada. Un Web Admin debe aprobarla.")

                    # 'historial_limite', no 'historial': ese nombre es el del
                    # modulo de historial que se usa mas arriba en esta funcion.
                    historial_limite = limites.obtener_historial(cliente_seleccionado)
                    if historial_limite:
                        st.caption("Historico de cambios del limite")
                        st.dataframe(
                            pd.DataFrame(historial_limite),
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


PRESUPUESTO_COLUMN_CONFIG = {
    "ticket_id": "Ticket",
    "resumen": stcc.TextColumn("Descripcion", width="large"),
    "estado": "Estado",
    "asignado_a": "Tecnico",
    "presupuesto_cliente": stcc.NumberColumn("Horas estimadas", format="%.1f h"),
    "horas_trabajo_real": stcc.NumberColumn("Desarrollo real", format="%.1f h"),
    "desviacion_presupuesto": stcc.NumberColumn("Desviacion", format="%+.1f h"),
    "estado_presupuesto": stcc.TextColumn("Acierto de la estimacion", width="medium"),
}

PRESUPUESTO_COLUMN_ORDER = [
    "ticket_id", "resumen", "estado", "asignado_a",
    "presupuesto_cliente", "horas_trabajo_real", "desviacion_presupuesto", "estado_presupuesto",
]


def _tabla_presupuesto_formateada(tabla):
    """Añade la celda de estado (icono + mensaje) a la tabla de presupuestos."""
    formateada = tabla.copy()
    estados = formateada.apply(
        lambda fila: presu.presupuesto_tono(fila.get("presupuesto_cliente"), fila.get("horas_trabajo_real")),
        axis=1,
    )
    formateada["_tono"] = [tono for tono, _, _ in estados]
    formateada["estado_presupuesto"] = [f"{icono} {mensaje}" for _, icono, mensaje in estados]
    return formateada


def _estilo_presupuesto(row):
    color = TONO_CELDA.get(row.get("_tono"), "")
    estilos = ["" for _ in row.index]
    for columna in ("desviacion_presupuesto", "estado_presupuesto"):
        if columna in row.index:
            estilos[row.index.get_loc(columna)] = color
    return estilos


def render_presupuesto_cliente(detalle_df, cliente_seleccionado):
    """
    Horas estimadas por el desarrollador (campo de Jira "Presupuesto
    cliente (en horas)") frente al tiempo de desarrollo real de cada ticket.
    """
    tabla = presu.tickets_con_presupuesto(detalle_df)
    resumen = presu.resumen_presupuesto(detalle_df)

    if tabla.empty:
        empty_state(
            f"Ningun ticket de {cliente_seleccionado} lleva relleno el campo "
            "\"Presupuesto cliente (en horas)\" en Jira. En cuanto el desarrollador lo estime, "
            "aqui se compara con las horas de desarrollo real de cada ticket."
        )
        return

    dentro_tono = "success" if resumen["pasados"] == 0 else ("warning" if resumen["horas_exceso"] <= 5 else "danger")
    kpi_grid(
        [
            ("Tickets estimados", str(resumen["con_presupuesto"]), "Con el campo relleno en Jira", ""),
            ("Horas estimadas", f"{resumen['horas_estimadas']:.1f} h", "Suma de las estimaciones", ""),
            ("Desarrollo real", f"{resumen['horas_desarrollo']:.1f} h", "Suma del tiempo de desarrollo", ""),
            (
                "Horas de mas",
                f"{resumen['horas_exceso']:.1f} h",
                f"{resumen['pasados']} ticket(s) por encima de lo estimado",
                _kpi_tone(dentro_tono),
            ),
        ]
    )

    st.caption(
        "Se compara la estimacion con las **horas de trabajo real** (desde que un tecnico coge "
        "el ticket hasta que lo termina, sin el tiempo en Pending Info), no con el tiempo total desde "
        "que se creo: ese incluye la espera en Backlog, que no es desarrollo."
    )

    formateada = _sanear_para_mostrar(_tabla_presupuesto_formateada(tabla), PRESUPUESTO_COLUMN_CONFIG)
    st.dataframe(
        formateada.style.apply(_estilo_presupuesto, axis=1),
        width="stretch",
        hide_index=True,
        height=_alto_tabla_completa(len(formateada), max_filas=12),
        lazy=False,
        column_config=PRESUPUESTO_COLUMN_CONFIG,
        column_order=[c for c in PRESUPUESTO_COLUMN_ORDER if c in formateada.columns],
    )


def render_presupuesto_global(df):
    """
    Mismo bloque de presupuesto que en el detalle de cliente, pero para
    todos los tickets del periodo y con la columna de cliente a la vista.
    """
    section_title(
        "💶 Estimacion vs. tiempo de desarrollo real",
        "Horas que el desarrollador estimo para el ticket (campo de Jira \"Presupuesto cliente (en horas)\") "
        "frente a las horas de trabajo real que ha costado.",
    )

    tabla = presu.tickets_con_presupuesto(df)
    if tabla.empty:
        empty_state(
            "Ningun ticket del periodo lleva relleno el campo \"Presupuesto cliente (en horas)\" en Jira."
        )
        return

    resumen = presu.resumen_presupuesto(df)
    dentro_tono = "success" if resumen["pasados"] == 0 else ("warning" if resumen["horas_exceso"] <= 5 else "danger")
    kpi_grid(
        [
            ("Tickets estimados", str(resumen["con_presupuesto"]), "Con el campo relleno en Jira", ""),
            ("Horas estimadas", f"{resumen['horas_estimadas']:.1f} h", "Suma de las estimaciones", ""),
            ("Desarrollo real", f"{resumen['horas_desarrollo']:.1f} h", "Suma del tiempo de desarrollo", ""),
            (
                "Horas de mas",
                f"{resumen['horas_exceso']:.1f} h",
                f"{resumen['pasados']} ticket(s) por encima de lo estimado",
                _kpi_tone(dentro_tono),
            ),
        ]
    )

    formateada = _sanear_para_mostrar(_tabla_presupuesto_formateada(tabla), PRESUPUESTO_COLUMN_CONFIG)
    orden = ["ticket_id", "cliente"] + [c for c in PRESUPUESTO_COLUMN_ORDER if c not in ("ticket_id",)]
    st.dataframe(
        formateada.style.apply(_estilo_presupuesto, axis=1),
        width="stretch",
        hide_index=True,
        height=_alto_tabla_completa(len(formateada), max_filas=12),
        lazy=False,
        column_config={**PRESUPUESTO_COLUMN_CONFIG, "cliente": stcc.TextColumn("Cliente", width="medium")},
        column_order=[c for c in dict.fromkeys(orden) if c in formateada.columns],
    )


def render_tickets_cliente(detalle_df, cliente_seleccionado, vista_resumida):
    """Tabla ticket a ticket del cliente, de mas reciente a mas antigua."""
    if vista_resumida:
        empty_state(
            "Vista resumida para Customer Success: horas, presupuesto y estado ya se muestran arriba. "
            "El detalle tecnico de cada ticket no esta disponible en este rol."
        )
        return

    if detalle_df.empty:
        empty_state(f"No hay tareas para {cliente_seleccionado}.")
        return

    st.caption(
        "\"Presupuesto cliente\" son las horas que estimo el desarrollador y se comparan con las "
        "**horas de trabajo real**; la fila se pinta en naranja al pasarse de la estimacion y en rojo "
        "si se pasa mas de un 25%."
    )

    # El tono se calcula con los valores numericos de origen, antes de
    # formatear el presupuesto a texto (si no, "6.0 h" ya no es un numero).
    tabla_historial = detalle_df.copy()
    tonos = tabla_historial.apply(
        lambda fila: presu.presupuesto_tono(fila.get("presupuesto_cliente"), fila.get("horas_trabajo_real"))[0],
        axis=1,
    ) if not tabla_historial.empty else pd.Series(dtype="object")

    tabla_historial["presupuesto_cliente"] = _horas_o_guion(tabla_historial.get("presupuesto_cliente"), tabla_historial.index)
    tabla_historial["desviacion_presupuesto"] = _horas_o_guion(
        tabla_historial.get("desviacion_presupuesto"), tabla_historial.index, con_signo=True
    )
    tabla_historial = _sanear_para_mostrar(tabla_historial, TICKETS_COLUMN_CONFIG)
    tabla_historial["_tono"] = tonos

    def highlight_presupuesto(row):
        # Solo se pinta lo que se ha pasado de presupuesto; lo que va bien se
        # deja limpio para que destaque lo que hay que mirar.
        color = TONO_CELDA.get(row.get("_tono"), "") if row.get("_tono") != "success" else ""
        return [color for _ in row]

    st.dataframe(
        tabla_historial.style.apply(highlight_presupuesto, axis=1),
        width="stretch",
        hide_index=True,
        height=_alto_tabla_completa(len(tabla_historial), max_filas=15),
        lazy=False,
        column_config=TICKETS_COLUMN_CONFIG,
        column_order=[c for c in TICKETS_COLUMN_ORDER if c in tabla_historial.columns],
    )


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
                actual_label = solicitudes.formatear_horas(solicitud.get("valor_actual"))
                propuesto_label = solicitudes.formatear_horas(solicitud.get("valor_propuesto"), defecto="—")
                if solicitud["tipo"] == "horas":
                    tipo_label = "🕒 Horas de resolucion"
                    objetivo_label = f"ticket **{solicitud['ticket_id']}** de {solicitud['cliente']}"
                else:
                    tipo_label = "📈 Limite contratado"
                    objetivo_label = f"cliente **{solicitud['cliente']}**"
                st.markdown(f"**{tipo_label}** — {objetivo_label}")
                st.markdown(
                    f"{actual_label} → **{propuesto_label}** "
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
        actual_label = solicitudes.formatear_horas(solicitud.get("valor_actual"))
        propuesto_label = solicitudes.formatear_horas(solicitud.get("valor_propuesto"), defecto="—")
        if solicitud["tipo"] == "horas":
            objetivo = f"horas del ticket **{solicitud['ticket_id']}**"
        else:
            objetivo = "limite del cliente"
        detalle_revision = ""
        if solicitud["estado"] != "pendiente" and solicitud.get("revisado_por"):
            detalle_revision = f" · revisado por {solicitud['revisado_por']}"
        st.markdown(
            f"{icono} **{etiqueta}** — {objetivo}: {actual_label} → **{propuesto_label}** "
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

    def _fila(s, para_excel):
        # En pantalla las horas van como texto ("—" cuando no hay dato): una
        # celda numerica vacia se pinta con un "None" gris. En el Excel van
        # como numero, que es lo que sirve para sumar o filtrar alli.
        antes, despues = s.get("valor_actual"), s.get("valor_propuesto")
        if para_excel:
            antes = antes if antes is not None else float("nan")
            despues = despues if despues is not None else float("nan")
        else:
            antes = solicitudes.formatear_horas(antes, defecto="—")
            despues = solicitudes.formatear_horas(despues, defecto="—")
        return {
            "Fecha solicitud": s["fecha_solicitud"],
            "Fecha revision": s["fecha_revision"],
            "Tipo": "Horas" if s["tipo"] == "horas" else "Limite",
            "Cliente": s["cliente"],
            "Ticket": s["ticket_id"] or "-",
            "Antes (h)": antes,
            "Despues (h)": despues,
            "Solicitado por": s["solicitado_por"],
            "Revisado por": s["revisado_por"],
            "Estado": "Aprobado" if s["estado"] == "aprobado" else "Rechazado",
        }

    st.dataframe(
        [_fila(s, para_excel=False) for s in resueltas],
        width="stretch",
        hide_index=True,
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([_fila(s, para_excel=True) for s in resueltas]).to_excel(
            writer, sheet_name="Historico", index=False
        )

    st.download_button(
        "⬇️ Descargar histórico en Excel",
        data=output.getvalue(),
        file_name=f"historico_horas_limites_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="descargar_historico_cambios",
    )
