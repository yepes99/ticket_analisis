from pathlib import Path
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


def _resolver_ruta_referencia():
    """
    Busca el fichero clients-transformados.csv en varias ubicaciones posibles,
    para que funcione tanto ejecutando desde el directorio del proyecto como
    desde cualquier otro working directory (ej: streamlit run app.py).
    """
    candidatos = [
        # Relativo al propio cliente.py (lo más habitual)
        Path(__file__).parent / "output" / "clients-transformados.csv",
        # Relativo al working directory en el momento de ejecución
        Path.cwd() / "output" / "clients-transformados.csv",
        # Por si output está al mismo nivel que el script
        Path(__file__).parent / "clients-transformados.csv",
        Path.cwd() / "clients-transformados.csv",
    ]
    for ruta in candidatos:
        if ruta.exists():
            return ruta
    return None


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


def cargar_tabla_clientes(path=None):
    """
    Carga el CSV de referencia y devuelve un dict {dominio_normalizado: company_name}.
    Intenta varias rutas posibles. Devuelve dict vacío si no encuentra el fichero.
    """
    ruta = path or _resolver_ruta_referencia()

    if ruta is None:
        return {}

    try:
        ref = pd.read_csv(ruta)

        # Necesitamos al menos web_url y company_name
        if "web_url" not in ref.columns or "company_name" not in ref.columns:
            return {}

        tabla = {}

        for _, row in ref.iterrows():
            nombre = row.get("company_name")
            url = row.get("web_url")

            # Si no hay nombre válido, intentar con la columna 'cliente'
            if pd.isna(nombre) or str(nombre).strip() == "":
                nombre = row.get("cliente", np.nan)

            if pd.isna(nombre) or str(nombre).strip() == "":
                continue

            # Registrar por web_url normalizada
            if not pd.isna(url) and str(url).strip() not in ("", "nan"):
                dominio = normalizar_cliente(url)
                if not pd.isna(dominio) and dominio not in tabla:
                    tabla[dominio] = str(nombre).strip()

        return tabla

    except Exception:
        return {}


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

    # Normalizar dominios
    df["cliente"] = df["cliente"].apply(normalizar_cliente)

    # Enriquecer con company_name desde el CSV de referencia
    tabla_clientes = cargar_tabla_clientes()
    if tabla_clientes:
        df["cliente"] = df["cliente"].map(
            lambda dominio: tabla_clientes.get(dominio, dominio)
            if not pd.isna(dominio)
            else np.nan
        )

    return df