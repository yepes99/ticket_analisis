from pathlib import Path

import pandas as pd

from categorias import completar_categorias
from cliente import completar_cliente
from sla import completar_sla



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

    df_raw = pd.read_csv(input_file, low_memory=False)
    existing_cols = {
        original: renamed
        for original, renamed in COLUMN_MAPPING.items()
        if original in df_raw.columns
    }

    return df_raw[list(existing_cols.keys())].rename(columns=existing_cols).copy()


def convertir_fechas(df):
    df = df.copy()

    for col in DATE_FIELDS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format=DATE_FORMAT, errors="coerce")

    return df


def completar_fechas_analiticas(df):
    df = df.copy()
    df["mes_creacion"] = df["fecha_creacion"].dt.to_period("M").astype(str)
    return df
