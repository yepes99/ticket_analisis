"""
Deteccion y calculo del bono de horas por cliente.

No existe un campo dedicado en Jira para esto: los bonos se compran a
traves de un ticket cuya descripcion contiene un texto como
"Tipo de tarea: 10h web changes bundle". Cada ticket asi detectado suma
sus horas al bono acumulado del cliente; el resto de tickets normales del
cliente van restando de ese saldo segun se resuelven (horas_resolucion).
"""

import re

import pandas as pd

BONO_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*h\b", re.IGNORECASE)
BONO_KEYWORD = "bundle"

# Umbral de alerta en rojo: el ejemplo de referencia es un bono de 10h del
# que se han usado 9h (1h disponible todavia) -> por debajo de esto se
# considera que el bono esta a punto de agotarse.
BONO_ALERTA_HORAS = 1.0


def extraer_horas_bono(descripcion):
    """
    Devuelve las horas compradas si el ticket es una compra de bono (su
    descripcion contiene "Xh ... bundle"), o None si no lo es.
    """
    if not isinstance(descripcion, str) or not descripcion:
        return None

    texto = descripcion.lower()
    if BONO_KEYWORD not in texto:
        return None

    match = BONO_PATTERN.search(texto)
    if not match:
        return None

    return float(match.group(1).replace(",", "."))


def completar_bono_horas(df):
    """Añade 'bono_horas_compradas' (NaN si el ticket no es una compra de bono)."""
    df = df.copy()
    df["bono_horas_compradas"] = df["descripcion"].apply(extraer_horas_bono)
    return df


def calcular_bono_cliente(filtered, cliente):
    """
    Calcula el saldo del bono de horas de un cliente:
    - comprado: suma de horas de todas las compras de bono detectadas.
    - consumido: horas de resolucion de los tickets normales (no de compra).
    - disponible: comprado - consumido. Se acumula entre varias compras,
      ej. se compran 10h, se usan 9h (1h disponible) y se compran otras
      10h -> 11h disponibles.
    """
    sub = filtered[filtered["cliente"] == cliente]

    if "bono_horas_compradas" not in sub.columns:
        return {
            "comprado": 0.0,
            "consumido": 0.0,
            "disponible": 0.0,
            "compras": pd.DataFrame(columns=["ticket_id", "fecha_creacion", "bono_horas_compradas"]),
        }

    es_compra = sub["bono_horas_compradas"].notna()

    compras = sub.loc[es_compra, ["ticket_id", "fecha_creacion", "bono_horas_compradas"]].copy()
    comprado = float(sub.loc[es_compra, "bono_horas_compradas"].sum())

    horas_normales = pd.to_numeric(sub.loc[~es_compra, "horas_resolucion"], errors="coerce")
    consumido = float(horas_normales.sum(skipna=True))

    # Sin ningun bono comprado no hay saldo que mostrar (no tiene sentido
    # un disponible negativo para un cliente que nunca ha comprado bono).
    disponible = comprado - consumido if comprado > 0 else 0.0

    return {
        "comprado": comprado,
        "consumido": consumido,
        "disponible": disponible,
        "compras": compras.sort_values("fecha_creacion", ascending=False),
    }


def detectar_bonos_sin_cliente(df):
    """
    Compras de bono detectadas que no se han podido atribuir a ningun
    cliente real (columna 'cliente' == "Sin cliente"). El bono se asocia
    al cliente exactamente igual que cualquier otro ticket (ver
    cliente.completar_cliente): por el prefijo "Cliente | ..." del resumen,
    o si no por el campo Domain/Web. Si el ticket de compra no lleva
    ninguno de los dos, sus horas quedan huerfanas y no suman al bono de
    nadie -- esto sirve para detectarlo y poder corregirlo en Jira.
    """
    if "bono_horas_compradas" not in df.columns or "cliente" not in df.columns:
        return df.iloc[0:0]

    huerfanos = df["bono_horas_compradas"].notna() & df["cliente"].eq("Sin cliente")
    cols = [c for c in ["ticket_id", "resumen", "fecha_creacion", "bono_horas_compradas"] if c in df.columns]
    return df.loc[huerfanos, cols]


def bono_tono(comprado, disponible):
    """Tono, icono y mensaje segun el estado del bono de un cliente."""
    if comprado <= 0:
        return "neutral", "⚪", "Sin bono de horas contratado"
    if disponible <= 0:
        return "danger", "🔴", "Bono agotado"
    if disponible <= BONO_ALERTA_HORAS:
        return "danger", "🔴", f"Bono a punto de agotarse ({disponible:.1f} h disponibles)"
    return "success", "🟢", "Bono activo"
