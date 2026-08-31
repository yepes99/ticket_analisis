import re
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

# Prefijos de flujo de trabajo, no nombres de cliente. Si el texto antes del
# separador es uno de estos, se descarta y se cae al dominio (ver mas abajo);
# de lo contrario tickets como "CLONE - <cliente real>..." o
# "TEST-<cliente real>..." se agrupaban bajo un cliente falso "CLONE"/"TEST".
PREFIJOS_NO_CLIENTE = {"clone", "test", "copy", "demo", "draft", "duplicate", "duplicado"}

NOMBRE_CLIENTE_RE = re.compile(r"^\s*([^|]+?)\s*\|")
NOMBRE_CLIENTE_GUION_RE = re.compile(r"^\s*([^\-–]+?)\s*(?:-|–)")
PREFIJO_SUCIO_RE = re.compile(
    r"^(?:" + "|".join(PREFIJOS_NO_CLIENTE) + r")\s*[-–:]\s*",
    re.IGNORECASE,
)


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


def extraer_nombre_cliente(resumen):
    """
    Extrae el nombre de cliente del resumen del ticket.

    Prioriza el separador "|" (el mas usado y sin ambiguedad); solo si no
    aparece se recurre al guion, que puede formar parte de un nombre de
    cliente compuesto (p.ej. "TAL-FANAL VILLAGE"). Descarta prefijos de
    flujo de trabajo como "CLONE"/"TEST" que no son clientes reales.
    """
    if pd.isna(resumen):
        return np.nan

    texto = str(resumen)
    match = NOMBRE_CLIENTE_RE.match(texto) or NOMBRE_CLIENTE_GUION_RE.match(texto)
    if not match:
        return np.nan

    nombre = match.group(1).strip()
    nombre = PREFIJO_SUCIO_RE.sub("", nombre).strip()
    if not nombre or nombre.lower() in PREFIJOS_NO_CLIENTE:
        return np.nan

    return nombre


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
        df["cliente_nombre"] = df["resumen"].apply(extraer_nombre_cliente)

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
