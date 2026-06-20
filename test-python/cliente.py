from urllib.parse import urlparse

import numpy as np
import pandas as pd


CLIENTE_FIELDS = [
    "cliente_web",
    "cliente_domain",
    "cliente_dominio",
    "cliente_empresa",
]

SUBDOMINIOS_RUIDO = ["booking.", "payments.", "reservations.", "holidays."]


def normalizar_cliente(valor):
    if pd.isna(valor):
        return np.nan

    valor = str(valor).strip().lower()

    if valor in ["", "nan", "none"]:
        return np.nan

    valor_tmp = valor if valor.startswith(("http://", "https://")) else f"https://{valor}"

    try:
        parsed = urlparse(valor_tmp)
        dominio = parsed.netloc or parsed.path
        dominio = dominio.lower().replace("www.", "")
        dominio = dominio.split("/")[0].split(":")[0]

        for subdominio in SUBDOMINIOS_RUIDO:
            if dominio.startswith(subdominio):
                dominio = dominio.replace(subdominio, "", 1)

        return dominio
    except ValueError:
        return valor


def completar_cliente(df):
    df = df.copy()
    df["cliente"] = np.nan

    for col in CLIENTE_FIELDS:
        if col in df.columns:
            df["cliente"] = df["cliente"].fillna(df[col])

    if "descripcion" in df.columns:
        dominio_desc = (
            df["descripcion"]
            .astype(str)
            .str.extract(r"https?://([^/|\s]+)", expand=False)
        )
        df["cliente"] = df["cliente"].fillna(dominio_desc)

    if "resumen" in df.columns:
        cliente_resumen = (
            df["resumen"]
            .astype(str)
            .str.extract(r"^([^-–]+)\s*[-–]", expand=False)
            .str.strip()
        )
        df["cliente"] = df["cliente"].fillna(cliente_resumen)

    df["cliente"] = df["cliente"].apply(normalizar_cliente)
    return df