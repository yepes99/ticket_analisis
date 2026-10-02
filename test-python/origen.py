"""
De donde viene cada ticket: de Intercom o creado directamente en Jira.

No hay ningun campo de Jira que lo diga (Source, Customer Request Type y
Plan Channel existen pero estan vacios en todos los tickets). La huella
esta en el **creador**: cuando el ticket nace de una conversacion de
Intercom lo crea la cuenta de integracion "Admin Avantio". Despues se
cambia el informador a la persona que lo atendio, pero el creador no se
puede cambiar en Jira, asi que aguanta como marca de origen.

Por eso se usa 'creador' y no 'informador': el informador dice *quien* lo
gestiono, el creador dice *por donde entro*.
"""

import pandas as pd

# Cuenta con la que la integracion de Intercom crea los tickets en Jira.
CUENTA_INTERCOM = "Admin Avantio"

INTERCOM = "Intercom"
JIRA = "Jira"
DESCONOCIDO = "Sin dato"

ICONOS = {
    INTERCOM: "💬",
    JIRA: "🛠️",
    DESCONOCIDO: "⚪",
}

# Como lo llama el equipo: lo que entra por Intercom es un "tracker ticket",
# y lo que se abre a mano en Jira es una tarea "interna".
NOMBRES = {
    INTERCOM: "Tracker (Intercom)",
    JIRA: "Interna (Jira)",
    DESCONOCIDO: "Sin dato",
}


def completar_origen(df):
    """Añade la columna 'origen' con Intercom / Jira / Sin dato."""
    df = df.copy()

    if "creador" not in df.columns:
        df["origen"] = DESCONOCIDO
        return df

    creador = df["creador"].astype("string").str.strip()
    df["origen"] = pd.Series(JIRA, index=df.index, dtype="object")
    df.loc[creador.eq(CUENTA_INTERCOM), "origen"] = INTERCOM
    df.loc[creador.isna() | creador.eq(""), "origen"] = DESCONOCIDO
    return df


def etiqueta(origen):
    """"💬 Tracker (Intercom)" / "🛠️ Interna (Jira)", para enseñar en una tabla."""
    texto = str(origen) if origen is not None and not pd.isna(origen) else DESCONOCIDO
    return f"{ICONOS.get(texto, ICONOS[DESCONOCIDO])} {NOMBRES.get(texto, texto)}"


def resumen_origen(df):
    """
    Cuantos tickets vienen de cada sitio y que porcentaje es Intercom.
    Devuelve 'pct_intercom' a None si no hay tickets que contar.
    """
    vacio = {"total": 0, "intercom": 0, "jira": 0, "sin_dato": 0, "pct_intercom": None, "pct_jira": None}
    if df is None or df.empty or "origen" not in df.columns:
        return vacio

    cuenta = df["origen"].value_counts()
    total = int(cuenta.sum())
    if not total:
        return vacio

    intercom = int(cuenta.get(INTERCOM, 0))
    jira = int(cuenta.get(JIRA, 0))
    return {
        "total": total,
        "intercom": intercom,
        "jira": jira,
        "sin_dato": int(cuenta.get(DESCONOCIDO, 0)),
        "pct_intercom": round(intercom / total * 100, 1),
        "pct_jira": round(jira / total * 100, 1),
    }
