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
    domain_source = df["cliente_domain"].copy() if "cliente_domain" in df.columns else pd.Series(np.nan, index=df.index)
    df["cliente_nombre"] = np.nan
    df["cliente_domain"] = np.nan
    df["cliente_url"] = domain_source

    df["cliente_domain"] = domain_source.apply(normalizar_cliente)

    for col in ["cliente_dominio", "cliente_web", "cliente_empresa"]:
        if col in df.columns:
            domain_values = df[col].apply(normalizar_cliente)
            df["cliente_domain"] = df["cliente_domain"].fillna(domain_values)

    if "resumen" in df.columns:
        df["cliente_nombre"] = (
            df["resumen"]
            .astype("string")
            .str.extract(r"^\s*([^|\-\u2013]+?)\s*(?:\||\-|\u2013)", expand=False)
            .str.strip()
            .replace({"": np.nan})
        )

    if "descripcion" in df.columns:
        dominio_desc = (
            df["descripcion"]
            .astype(str)
            .str.extract(r"https?://([^/|\s]+)", expand=False)
        )
        df["cliente_domain"] = df["cliente_domain"].fillna(dominio_desc.apply(normalizar_cliente))

    df["cliente"] = df["cliente_nombre"].fillna(df["cliente_domain"])
    df["cliente"] = df["cliente"].fillna("Sin cliente")
    return df
