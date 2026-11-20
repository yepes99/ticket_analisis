"""
De donde viene cada ticket: de Intercom (tracker ticket) o interno.

Un ticket es un tracker de Intercom (de soporte web) si se cumplen las dos:
1. El informador es la persona de soporte que atiende Intercom (Carmen
   Yepes, ver INFORMADORES_INTERCOM).
2. Viene de Intercom: tiene la etiqueta "Intercom" en Jira, o lo creo la
   integracion de Intercom (cuenta "Admin Avantio"). Lo normal es que tenga
   la etiqueta; lo segundo cubre los pocos que entraron sin ella.

Todo lo demas es interno, aunque venga de Intercom: si el informador es
otra persona (p.ej. alguien de CS), no es un tracker de soporte web aunque
lleve la etiqueta (casos reales: WP-31529, WP-31560 de Jennifer Urbas). En
Intercom esos tickets estan en otros equipos, no en "Web changes".

El creador no se puede cambiar en Jira, por eso sirve para saber por donde
entro; el informador dice quien lo gestiono despues.
"""

import pandas as pd

# Cuenta con la que la integracion de Intercom crea los tickets en Jira.
CUENTA_INTERCOM = "Admin Avantio"

# Informadores a los que se pasa el ticket cuando viene de Intercom.
INFORMADORES_INTERCOM = {"Carmen Yepes"}

# Etiqueta de Jira que marca un ticket como de Intercom (sin distinguir
# mayusculas).
ETIQUETA_INTERCOM = "intercom"

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


def _tiene_etiqueta_intercom(etiquetas):
    if not isinstance(etiquetas, (list, tuple, set)):
        return False
    return any(str(e).strip().lower() == ETIQUETA_INTERCOM for e in etiquetas)


def completar_origen(df):
    """Añade la columna 'origen' con Intercom / Jira / Sin dato."""
    df = df.copy()

    tiene_creador = "creador" in df.columns
    tiene_etiquetas = "etiquetas" in df.columns
    if not tiene_creador and not tiene_etiquetas:
        df["origen"] = DESCONOCIDO
        return df

    vacio = pd.Series(pd.NA, index=df.index, dtype="string")
    creador = df["creador"].astype("string").str.strip() if tiene_creador else vacio
    informador = df["informador"].astype("string").str.strip() if "informador" in df.columns else vacio
    con_etiqueta = (
        df["etiquetas"].map(_tiene_etiqueta_intercom).astype(bool)
        if tiene_etiquetas
        else pd.Series(False, index=df.index)
    )

    viene_de_intercom = con_etiqueta | creador.eq(CUENTA_INTERCOM).fillna(False)
    informador_soporte = informador.isin(INFORMADORES_INTERCOM).fillna(False)
    es_intercom = viene_de_intercom & informador_soporte

    df["origen"] = pd.Series(JIRA, index=df.index, dtype="object")
    df.loc[es_intercom, "origen"] = INTERCOM
    # Sin creador ni etiqueta no se puede saber de donde vino.
    sin_creador = (creador.isna() | creador.eq("")).fillna(True)
    df.loc[sin_creador & ~con_etiqueta, "origen"] = DESCONOCIDO
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
