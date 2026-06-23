from pathlib import Path
import unicodedata

import pandas as pd

from categorias import completar_categorias
from cliente import completar_cliente
from sla import completar_sla

def normalize_str(value):
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))



INPUT_FILE = Path(__file__).with_name("data.csv")
DATE_FORMAT = "%d/%b/%y %I:%M %p"

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
    df = cargar_columnas(input_file)
    df = convertir_fechas(df)
    df = completar_cliente(df)
    df = completar_categorias(df)
    df = completar_sla(df)
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
    values = series.astype("string").str.strip().str.lower()

    for spanish, english in SPANISH_MONTHS.items():
        values = values.str.replace(f"/{spanish}/", f"/{english}/", regex=False)

    return pd.to_datetime(values, format=DATE_FORMAT, errors="coerce")


def completar_fechas_analiticas(df):
    df = df.copy()
    df["mes_creacion"] = df["fecha_creacion"].dt.to_period("M").astype(str)
    return df
