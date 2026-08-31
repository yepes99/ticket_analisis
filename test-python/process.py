from pathlib import Path
import time
import unicodedata

import pandas as pd
import requests
import streamlit as st
import tomllib

from categorias import completar_categorias
from cliente import completar_cliente
from sla import completar_sla


DATE_FORMAT = "%d/%b/%y %I:%M %p"

DATE_FIELDS = [
    "fecha_creacion",
    "fecha_actualizacion",
    "fecha_resolucion",
]

JIRA_BASE_FIELDS = [
    "summary",
    "issuetype",
    "assignee",
    "status",
    "created",
    "updated",
    "resolutiondate",
    "priority",
    "project",
    "description",
]

JIRA_FIELD_ALIASES = {
    "size": [
        "Size",
        "Campo personalizado (Size)",
    ],
    "cliente_web": [
        "Web del Cliente / Empresa",
        "Campo personalizado (Web del Cliente / Empresa)",
    ],
    "cliente_domain": [
        "Domain",
        "Campo personalizado (Domain)",
    ],
    "cliente_dominio": [
        "Dominio",
        "Campo personalizado (Dominio)",
    ],
    "cliente_empresa": [
        "Cliente / Empresa",
        "Campo personalizado (Cliente / Empresa)",
    ],
    "presupuesto": [
        "Budget",
        "Campo personalizado (Budget)",
    ],
    "es_wordpress": [
        "¿Es WordPress?",
        "Es WordPress",
        "WordPress",
    ],
    "plan_servicio": [
        "Plan Web",
        "Plan",
    ],
}

JIRA_COLUMNS = [
    "ticket_id",
    "ticket_num",
    "resumen",
    "tipo",
    "estado",
    "categoria_estado",
    "prioridad",
    "resolucion",
    "proyecto_clave",
    "proyecto_nombre",
    "asignado_a",
    "informador",
    "fecha_creacion",
    "fecha_actualizacion",
    "fecha_resolucion",
    "descripcion",
    "cliente_web",
    "cliente_domain",
    "cliente_dominio",
    "cliente_empresa",
    "size",
    "presupuesto",
    "es_wordpress",
    "plan_servicio",
]

SPANISH_MONTHS = {
    "ene": "Jan",
    "feb": "Feb",
    "mar": "Mar",
    "abr": "Apr",
    "may": "May",
    "jun": "Jun",
    "jul": "Jul",
    "ago": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "oct": "Oct",
    "nov": "Nov",
    "dic": "Dec",
}


def normalize_str(value):
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)

    return "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )


def cargar_tickets_jira(
    max_results=None,
    start_date=None,
    end_date=None,
    page_size=100,
    pause_seconds=0.2,
    jql=None,
):
    """
    Carga los tickets desde Jira.

    IMPORTANTE:
    No filtramos aquí por tipo == "bug".

    Jira puede devolver el nombre del tipo de incidencia
    localizado, por ejemplo "Error" en lugar de "Bug".

    El filtrado de bugs ya lo realiza el JQL configurado:
        project = WP AND type = Bug
    """

    jira_config = leer_config_jira()

    payload = consultar_jira_paginas(
        jira_config,
        max_results=max_results,
        start_date=start_date,
        end_date=end_date,
        page_size=page_size,
        pause_seconds=pause_seconds,
        jql=jql,
    )

    df = transformar_payload_jira(payload)

    df = procesar_tickets_jira(df)

    return df


def procesar_tickets_jira(df):
    df = convertir_fechas(df)

    df = completar_cliente(df)

    df = completar_categorias(df)

    df = completar_sla(df)

    df = completar_fechas_analiticas(df)

    return df


def leer_config_jira():
    """
    Primero intenta leer los secrets de Streamlit.

    Si no están disponibles, utiliza:
        .streamlit/secrets.toml
    """

    try:
        return dict(st.secrets["JIRA"])
    except Exception:
        pass

    secrets_path = (
        Path(__file__).resolve().parent
        / ".streamlit"
        / "secrets.toml"
    )

    if not secrets_path.exists():
        raise FileNotFoundError(
            "No se encontro la configuracion de Jira. "
            "En Streamlit Cloud agrega la seccion [JIRA] "
            "en App settings > Secrets."
        )

    with secrets_path.open("rb") as fh:
        return tomllib.load(fh)["JIRA"]


def resolver_campo_jira(jira_config, field_name):
    explicit = jira_config.get(
        f"{field_name.upper()}_FIELD"
    )

    return explicit or None


def consultar_campos_jira(jira_config):
    url = (
        jira_config["API_URL"].rstrip("/")
        + "/rest/api/3/field"
    )

    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
        },
        auth=(
            jira_config["EMAIL"],
            jira_config["TOKEN"],
        ),
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def preparar_campos_jira(jira_config):
    resolved = {
        logical_name: resolver_campo_jira(
            jira_config,
            logical_name,
        )
        for logical_name in JIRA_FIELD_ALIASES
    }

    missing = [
        name
        for name, field_id in resolved.items()
        if not field_id
    ]

    if missing:
        try:
            fields_by_name = {
                normalize_str(field.get("name")): field.get("id")
                for field in consultar_campos_jira(jira_config)
                if field.get("name")
                and field.get("id")
            }

            for logical_name in missing:
                for alias in JIRA_FIELD_ALIASES[logical_name]:

                    field_id = fields_by_name.get(
                        normalize_str(alias)
                    )

                    if field_id:
                        resolved[logical_name] = field_id
                        break

        except requests.RequestException:
            pass

    field_ids = [
        field
        for field in resolved.values()
        if field
    ]

    return (
        ",".join(JIRA_BASE_FIELDS + field_ids),
        resolved,
    )


def formatear_fecha_jql(value):
    if value is None:
        return None

    return pd.Timestamp(value).strftime(
        "%Y-%m-%d"
    )


def componer_jql(
    base_jql,
    start_date=None,
    end_date=None,
):
    """
    Añade filtros de fecha al JQL existente.

    Con inicio y fin (p.ej. "Ultima semana"), el periodo se interpreta como
    "actividad en el periodo": incluye un ticket si se creo O se actualizo
    dentro del rango, aunque se creara antes. Si no fuera asi, un tecnico
    que trabaja sobre tickets antiguos (los actualiza/resuelve pero no los
    crea) desaparece de cualquier periodo corto aunque este trabajando
    activamente en el.

    Ejemplo, con start_date="2026-07-28" y end_date="2026-08-28":

    project = WP AND type = Bug

    se convierte en:

    (project = WP AND type = Bug) AND (
        (created >= "2026-07-28" AND created < "2026-08-29")
        OR (updated >= "2026-07-28" AND updated < "2026-08-29")
    )

    Si solo se indica end_date (sin start_date, p.ej. "Todo el historico",
    sin limite inferior), se filtra solo por fecha de creacion.
    """

    start_value = formatear_fecha_jql(start_date)
    end_value = formatear_fecha_jql(end_date)

    if not start_value and not end_value:
        return base_jql

    end_exclusive = None
    if end_value:
        end_exclusive = (
            pd.Timestamp(end_value) + pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

    def rango(campo):
        partes = []
        if start_value:
            partes.append(f'{campo} >= "{start_value}"')
        if end_exclusive:
            partes.append(f'{campo} < "{end_exclusive}"')
        return " AND ".join(partes)

    if start_value:
        filtro_fecha = f"({rango('created')}) OR ({rango('updated')})"
    else:
        filtro_fecha = rango("created")

    order_clause = ""
    jql_body = base_jql.strip()
    order_marker = " order by "
    marker_pos = jql_body.lower().find(order_marker)

    if marker_pos >= 0:
        order_clause = jql_body[marker_pos:]
        jql_body = jql_body[:marker_pos].strip()

    return (
        f"({jql_body}) AND "
        f"({filtro_fecha})"
        f"{order_clause}"
    )


def consultar_jira(
    jira_config,
    max_results=100,
    next_page_token=None,
    fields=None,
    start_date=None,
    end_date=None,
    jql=None,
):
    url = (
        jira_config["API_URL"].rstrip("/")
        + "/rest/api/3/search/jql"
    )

    base_jql = (
        jql
        if jql
        else jira_config["JQL"]
    )

    params = {
        "jql": componer_jql(
            base_jql,
            start_date=start_date,
            end_date=end_date,
        ),
        "maxResults": max_results,
        "fields": (
            fields
            if fields
            else ",".join(JIRA_BASE_FIELDS)
        ),
    }

    if next_page_token:
        params["nextPageToken"] = next_page_token

    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
        },
        auth=(
            jira_config["EMAIL"],
            jira_config["TOKEN"],
        ),
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def consultar_jira_paginas(
    jira_config,
    max_results=100,
    start_date=None,
    end_date=None,
    page_size=100,
    pause_seconds=0.2,
    jql=None,
):
    all_issues = []

    next_page_token = None

    fields, field_map = preparar_campos_jira(
        jira_config
    )

    while True:

        remaining = (
            None
            if max_results is None
            else max_results - len(all_issues)
        )

        if (
            remaining is not None
            and remaining <= 0
        ):
            break

        current_page_size = (
            page_size
            if remaining is None
            else min(page_size, remaining)
        )

        payload = consultar_jira(
            jira_config,
            max_results=current_page_size,
            next_page_token=next_page_token,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            jql=jql,
        )

        issues = payload.get(
            "issues",
            [],
        )

        all_issues.extend(issues)

        next_page_token = payload.get(
            "nextPageToken"
        )

        if (
            payload.get("isLast", True)
            or not next_page_token
            or not issues
        ):
            break

        if pause_seconds:
            time.sleep(
                pause_seconds
            )

    return {
        "issues": all_issues,
        "field_map": field_map,
    }


def parsear_fecha_jira(series):
    """
    Convierte fechas de Jira (ISO 8601 con offset, p.ej. "+02:00") a
    datetime naive en hora local de Madrid.

    Jira devuelve cada fecha con el offset vigente en ese momento (CEST
    +02:00 en verano, CET +01:00 en invierno). Si el rango de tickets
    mezcla ambos offsets, pd.to_datetime sin utc=True falla con
    "Mixed timezones detected" (pandas >= 2). Se normaliza a UTC primero
    y se convierte a Europe/Madrid despues, para que el resultado siga
    siendo comparable con pd.Timestamp.now() (hora local, naive) en el
    resto del calculo de SLA/horas.
    """
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert("Europe/Madrid").dt.tz_localize(None)


def transformar_payload_jira(payload):
    issues = payload.get(
        "issues",
        [],
    )

    field_map = payload.get(
        "field_map",
        {},
    )

    rows = []

    for issue in issues:

        fields = issue.get(
            "fields",
            {},
        )

        rows.append(
            {
                "ticket_id": issue.get(
                    "key"
                ),

                "ticket_num": issue.get(
                    "id"
                ),

                "resumen": fields.get(
                    "summary"
                ),

                "tipo": extraer_propiedad_jira(
                    fields.get("issuetype"),
                    "name",
                ),

                "estado": extraer_propiedad_jira(
                    fields.get("status"),
                    "name",
                ),

                "categoria_estado": extraer_categoria_estado(
                    fields.get("status")
                ),

                "prioridad": extraer_propiedad_jira(
                    fields.get("priority"),
                    "name",
                ),

                "resolucion": None,

                "proyecto_clave": extraer_propiedad_jira(
                    fields.get("project"),
                    "key",
                ),

                "proyecto_nombre": extraer_propiedad_jira(
                    fields.get("project"),
                    "name",
                ),

                "asignado_a": extraer_propiedad_jira(
                    fields.get("assignee"),
                    "displayName",
                ),

                "informador": None,

                "fecha_creacion": fields.get(
                    "created"
                ),

                "fecha_actualizacion": fields.get(
                    "updated"
                ),

                "fecha_resolucion": fields.get(
                    "resolutiondate"
                ),

                "descripcion": extraer_texto_jira(
                    fields.get("description")
                ),

                "cliente_web": extraer_valor_campo_jira(
                    fields,
                    field_map.get("cliente_web"),
                ),

                "cliente_domain": extraer_valor_campo_jira(
                    fields,
                    field_map.get("cliente_domain"),
                ),

                "cliente_dominio": extraer_valor_campo_jira(
                    fields,
                    field_map.get("cliente_dominio"),
                ),

                "cliente_empresa": extraer_valor_campo_jira(
                    fields,
                    field_map.get("cliente_empresa"),
                ),

                "size": extraer_valor_campo_jira(
                    fields,
                    field_map.get("size"),
                ),

                "presupuesto": extraer_valor_campo_jira(
                    fields,
                    field_map.get("presupuesto"),
                ),

                "es_wordpress": extraer_valor_campo_jira(
                    fields,
                    field_map.get("es_wordpress"),
                ),

                "plan_servicio": extraer_valor_campo_jira(
                    fields,
                    field_map.get("plan_servicio"),
                ),
            }
        )

    df = pd.DataFrame(
        rows,
        columns=JIRA_COLUMNS,
    )

    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=["ticket_id"],
        keep="first",
    ).reset_index(drop=True)

    df["fecha_creacion"] = parsear_fecha_jira(df["fecha_creacion"])
    df["fecha_actualizacion"] = parsear_fecha_jira(df["fecha_actualizacion"])
    df["fecha_resolucion"] = parsear_fecha_jira(df["fecha_resolucion"])

    df["presupuesto"] = pd.to_numeric(
        df["presupuesto"],
        errors="coerce",
    )

    return df


def extraer_propiedad_jira(
    value,
    key,
):
    if isinstance(value, dict):
        return value.get(key)

    return None


def extraer_categoria_estado(status_value):
    """
    Devuelve la statusCategory de Jira ("new", "indeterminate" o "done").

    Es la senal fiable de si un ticket esta realmente resuelto: a
    diferencia de resolutiondate, Jira la actualiza al reabrir un ticket
    (resolutiondate se queda con la fecha antigua en muchos workflows).
    """
    if not isinstance(status_value, dict):
        return None

    category = status_value.get("statusCategory")
    if isinstance(category, dict):
        return category.get("key")

    return None


def extraer_valor_campo_jira(
    fields,
    field_id,
):
    if not field_id:
        return None

    value = fields.get(field_id)

    if isinstance(value, dict):

        for key in (
            "value",
            "name",
            "displayName",
        ):
            if value.get(key):
                return value[key]

        return extraer_texto_jira(
            value
        )

    if isinstance(value, list):

        values = [
            extraer_valor_lista_jira(item)
            for item in value
        ]

        values = [
            item
            for item in values
            if item
        ]

        return (
            ", ".join(values)
            if values
            else None
        )

    return value


def extraer_valor_lista_jira(value):
    if isinstance(value, dict):

        for key in (
            "value",
            "name",
            "displayName",
        ):
            if value.get(key):
                return str(
                    value[key]
                )

        return extraer_texto_jira(
            value
        )

    if value is None:
        return None

    return str(value)


def extraer_texto_jira(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, list):

        parts = [
            extraer_texto_jira(item)
            for item in value
        ]

        return " ".join(
            part
            for part in parts
            if part
        )

    if isinstance(value, dict):

        if value.get("type") == "text":
            return value.get("text")

        parts = [
            extraer_texto_jira(item)
            for item in value.get(
                "content",
                [],
            )
        ]

        return " ".join(
            part
            for part in parts
            if part
        )

    return str(value)


def convertir_fechas(df):
    df = df.copy()

    for col in DATE_FIELDS:

        if col in df.columns:
            df[col] = parse_jira_date(
                df[col]
            )

    return df


def parse_jira_date(series):

    if pd.api.types.is_datetime64_any_dtype(
        series
    ):
        return normalizar_datetime(
            pd.to_datetime(
                series,
                errors="coerce",
            ),
            series.index,
        )

    values = (
        series
        .astype("string")
        .str.strip()
        .str.lower()
    )

    for spanish, english in SPANISH_MONTHS.items():

        values = values.str.replace(
            f"/{spanish}/",
            f"/{english}/",
            regex=False,
        )

    parsed = normalizar_datetime(
        pd.to_datetime(
            values,
            format=DATE_FORMAT,
            errors="coerce",
        ),
        series.index,
    )

    fallback = normalizar_datetime(
        pd.to_datetime(
            values,
            errors="coerce",
        ),
        series.index,
    )

    return parsed.where(
        parsed.notna(),
        fallback,
    )


def normalizar_datetime(
    values,
    index,
):
    parsed = pd.Series(
        values,
        index=index,
    )

    if isinstance(
        parsed.dtype,
        pd.DatetimeTZDtype,
    ):
        parsed = parsed.dt.tz_localize(
            None
        )

    parsed = pd.to_datetime(
        parsed,
        errors="coerce",
    )

    return parsed.astype(
        "datetime64[ns]"
    )


def completar_fechas_analiticas(df):
    df = df.copy()

    df["mes_creacion"] = (
        df["fecha_creacion"]
        .dt.to_period("M")
        .astype(str)
    )

    return df