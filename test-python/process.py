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

def normalize_str(value):
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))



INPUT_FILE = Path(__file__).with_name("data.csv")
SNAPSHOT_FILE = Path(__file__).resolve().parent / "output" / "jira_snapshot.csv"
DATE_FORMAT = "%d/%b/%y %I:%M %p"
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
    "size": ["Size", "Campo personalizado (Size)"],
    "cliente_web": ["Web del Cliente / Empresa", "Campo personalizado (Web del Cliente / Empresa)"],
    "cliente_domain": ["Domain", "Campo personalizado (Domain)"],
    "cliente_dominio": ["Dominio", "Campo personalizado (Dominio)"],
    "cliente_empresa": ["Cliente / Empresa", "Campo personalizado (Cliente / Empresa)"],
}

COLUMN_MAPPING = {
    "Clave de incidencia": "ticket_id",
    "ID de la incidencia": "ticket_num",
    "Resumen": "resumen",
    "Tipo de Incidencia": "tipo",
    "Estado": "estado",
    "Categoría de estado": "categoria_estado",
    "Prioridad": "prioridad",
    "Resolución": "resolucion",
    "Clave del proyecto": "proyecto_clave",
    "Nombre del proyecto": "proyecto_nombre",
    "Persona asignada": "asignado_a",
    "Informador": "informador",
    "Creada": "fecha_creacion",
    "Actualizada": "fecha_actualizacion",
    "Resuelta": "fecha_resolucion",
    "Descripción": "descripcion",
    "Campo personalizado (Web del Cliente / Empresa)": "cliente_web",
    "Campo personalizado (Domain)": "cliente_domain",
    "Campo personalizado (Dominio)": "cliente_dominio",
    "Campo personalizado (Cliente / Empresa)": "cliente_empresa",
    "Campo personalizado (Size)": "size",
}

DATE_FIELDS = ["fecha_creacion", "fecha_actualizacion", "fecha_resolucion"]
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


def cargar_tickets(input_file=INPUT_FILE):
    if hasattr(input_file, "read") and not isinstance(input_file, (str, Path)):
        try:
            input_file.seek(0)
            return cargar_tickets_csv(input_file)
        except Exception:
            return cargar_tickets_jira()

    if isinstance(input_file, (str, Path)) and Path(input_file).exists():
        return cargar_tickets_csv(input_file)

    return cargar_tickets_jira()


def cargar_tickets_csv(input_file):
    df = cargar_columnas(input_file)
    df = convertir_fechas(df)
    df = completar_cliente(df)
    df = completar_categorias(df)
    df = completar_sla(df)
    df = completar_fechas_analiticas(df)
    return df


def cargar_tickets_jira(max_results=10, page_size=100, pause_seconds=0.2):
    jira_config = leer_config_jira()
    payload = consultar_jira_paginas(
        jira_config,
        max_results=max_results,
        page_size=page_size,
        pause_seconds=pause_seconds,
    )
    df = transformar_payload_jira(payload)
    return procesar_tickets_jira(df)


def procesar_tickets_jira(df):
    df = convertir_fechas(df)
    df = completar_cliente(df)
    df = completar_categorias(df)
    df = completar_sla(df)
    df = completar_fechas_analiticas(df)
    return df


def leer_config_jira():
    try:
        return dict(st.secrets["JIRA"])
    except Exception:
        pass

    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        raise FileNotFoundError(
            "No se encontro la configuracion de Jira. En Streamlit Cloud agrega "
            "la seccion [JIRA] en App settings > Secrets."
        )

    with secrets_path.open("rb") as fh:
        return tomllib.load(fh)["JIRA"]


def resolver_campo_jira(jira_config, field_name):
    explicit = jira_config.get(f"{field_name.upper()}_FIELD")
    if explicit:
        return explicit
    return None


def consultar_campos_jira(jira_config):
    url = jira_config["API_URL"].rstrip("/") + "/rest/api/3/field"
    response = requests.get(
        url,
        headers={"Accept": "application/json"},
        auth=(jira_config["EMAIL"], jira_config["TOKEN"]),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def preparar_campos_jira(jira_config):
    resolved = {
        logical_name: resolver_campo_jira(jira_config, logical_name)
        for logical_name in JIRA_FIELD_ALIASES
    }

    missing = [name for name, field_id in resolved.items() if not field_id]
    if missing:
        try:
            fields_by_name = {
                normalize_str(field.get("name")): field.get("id")
                for field in consultar_campos_jira(jira_config)
                if field.get("name") and field.get("id")
            }
            for logical_name in missing:
                for alias in JIRA_FIELD_ALIASES[logical_name]:
                    field_id = fields_by_name.get(normalize_str(alias))
                    if field_id:
                        resolved[logical_name] = field_id
                        break
        except requests.RequestException:
            pass

    field_ids = [field for field in resolved.values() if field]
    return ",".join(JIRA_BASE_FIELDS + field_ids), resolved


def consultar_jira(jira_config, max_results=10, next_page_token=None, fields=None):
    url = jira_config["API_URL"].rstrip("/") + "/rest/api/3/search/jql"
    params = {
        "jql": jira_config["JQL"],
        "maxResults": max_results,
        "fields": fields or ",".join(JIRA_BASE_FIELDS),
    }
    if next_page_token:
        params["nextPageToken"] = next_page_token

    response = requests.get(
        url,
        headers={"Accept": "application/json"},
        auth=(jira_config["EMAIL"], jira_config["TOKEN"]),
        params=params,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def consultar_jira_paginas(jira_config, max_results=10, page_size=100, pause_seconds=0.2):
    all_issues = []
    next_page_token = None
    fields, field_map = preparar_campos_jira(jira_config)

    while True:
        remaining = None if max_results is None else max_results - len(all_issues)
        if remaining is not None and remaining <= 0:
            break

        current_page_size = page_size if remaining is None else min(page_size, remaining)
        payload = consultar_jira(
            jira_config,
            max_results=current_page_size,
            next_page_token=next_page_token,
            fields=fields,
        )
        issues = payload.get("issues", [])
        all_issues.extend(issues)

        next_page_token = payload.get("nextPageToken")
        if payload.get("isLast", True) or not next_page_token or not issues:
            break

        if pause_seconds:
            time.sleep(pause_seconds)

    return {"issues": all_issues, "field_map": field_map}


def transformar_payload_jira(payload):
    issues = payload.get("issues", [])
    field_map = payload.get("field_map", {})
    rows = []
    for issue in issues:
        fields = issue.get("fields", {})
        rows.append({
            "ticket_id": issue.get("key"),
            "ticket_num": issue.get("id"),
            "resumen": fields.get("summary"),
            "tipo": extraer_propiedad_jira(fields.get("issuetype"), "name"),
            "estado": extraer_propiedad_jira(fields.get("status"), "name"),
            "categoria_estado": None,
            "prioridad": extraer_propiedad_jira(fields.get("priority"), "name"),
            "resolucion": None,
            "proyecto_clave": extraer_propiedad_jira(fields.get("project"), "key"),
            "proyecto_nombre": extraer_propiedad_jira(fields.get("project"), "name"),
            "asignado_a": extraer_propiedad_jira(fields.get("assignee"), "displayName"),
            "informador": None,
            "fecha_creacion": fields.get("created"),
            "fecha_actualizacion": fields.get("updated"),
            "fecha_resolucion": fields.get("resolutiondate"),
            "descripcion": extraer_texto_jira(fields.get("description")),
            "cliente_web": extraer_valor_campo_jira(fields, field_map.get("cliente_web")),
            "cliente_domain": extraer_valor_campo_jira(fields, field_map.get("cliente_domain")),
            "cliente_dominio": extraer_valor_campo_jira(fields, field_map.get("cliente_dominio")),
            "cliente_empresa": extraer_valor_campo_jira(fields, field_map.get("cliente_empresa")),
            "size": extraer_valor_campo_jira(fields, field_map.get("size")),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"], errors="coerce")
    df["fecha_actualizacion"] = pd.to_datetime(df["fecha_actualizacion"], errors="coerce")
    df["fecha_resolucion"] = pd.to_datetime(df["fecha_resolucion"], errors="coerce")
    return df


def extraer_propiedad_jira(value, key):
    return value.get(key) if isinstance(value, dict) else None


def extraer_valor_campo_jira(fields, field_id):
    if not field_id:
        return None

    value = fields.get(field_id)
    if isinstance(value, dict):
        for key in ("value", "name", "displayName"):
            if value.get(key):
                return value[key]
        return extraer_texto_jira(value)
    if isinstance(value, list):
        values = [extraer_valor_lista_jira(item) for item in value]
        values = [item for item in values if item]
        return ", ".join(values) if values else None
    return value


def extraer_valor_lista_jira(value):
    if isinstance(value, dict):
        for key in ("value", "name", "displayName"):
            if value.get(key):
                return str(value[key])
        return extraer_texto_jira(value)
    if value is None:
        return None
    return str(value)


def extraer_texto_jira(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [extraer_texto_jira(item) for item in value]
        return " ".join(part for part in parts if part)
    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text")
        parts = [extraer_texto_jira(item) for item in value.get("content", [])]
        return " ".join(part for part in parts if part)
    return str(value)


def guardar_snapshot_jira(df, path=SNAPSHOT_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def cargar_snapshot_jira(path=SNAPSHOT_FILE):
    path = Path(path)
    df = pd.read_csv(path, low_memory=False, encoding="utf-8", encoding_errors="ignore")
    df = convertir_fechas(df)
    if "mes_creacion" not in df.columns and "fecha_creacion" in df.columns:
        df = completar_fechas_analiticas(df)
    return df


def cargar_columnas(input_file):
    if hasattr(input_file, "seek"):
        input_file.seek(0)

    df_raw = pd.read_csv(input_file, low_memory=False, encoding="utf-8", encoding_errors="ignore")
    normalized_headers = {normalize_str(col): col for col in df_raw.columns}

    existing_cols = {}
    for original, renamed in COLUMN_MAPPING.items():
        normalized_key = normalize_str(original)
        if normalized_key in normalized_headers:
            existing_cols[normalized_headers[normalized_key]] = renamed

    if not existing_cols:
        raise ValueError("No se encontraron columnas válidas en el CSV. Revisa la cabecera del archivo.")

    return df_raw[list(existing_cols.keys())].rename(columns=existing_cols).copy()


def convertir_fechas(df):
    df = df.copy()

    for col in DATE_FIELDS:
        if col in df.columns:
            df[col] = parse_jira_date(df[col])

    return df


def parse_jira_date(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return normalizar_datetime(pd.to_datetime(series, errors="coerce"), series.index)

    values = series.astype("string").str.strip().str.lower()

    for spanish, english in SPANISH_MONTHS.items():
        values = values.str.replace(f"/{spanish}/", f"/{english}/", regex=False)

    parsed = normalizar_datetime(
        pd.to_datetime(values, format=DATE_FORMAT, errors="coerce"),
        series.index,
    )
    fallback = normalizar_datetime(
        pd.to_datetime(values, errors="coerce"),
        series.index,
    )
    return parsed.where(parsed.notna(), fallback)


def normalizar_datetime(values, index):
    parsed = pd.Series(values, index=index)
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_localize(None)
    parsed = pd.to_datetime(parsed, errors="coerce")
    return parsed.astype("datetime64[ns]")


def completar_fechas_analiticas(df):
    df = df.copy()
    df["mes_creacion"] = df["fecha_creacion"].dt.to_period("M").astype(str)
    return df
