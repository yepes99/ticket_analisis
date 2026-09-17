"""
Limite de horas contratadas por cliente, con historico de cambios.

Se persiste en un JSON local (data/limites_horas.json). En Streamlit Cloud
el sistema de archivos es efimero, asi que el historico se pierde en cada
redeploy/reinicio salvo que se migre a un almacen externo.
"""

import json
from datetime import datetime
from pathlib import Path


LIMITES_PATH = Path(__file__).resolve().parent / "data" / "limites_horas.json"


def _cargar():
    if not LIMITES_PATH.exists():
        return {}
    with LIMITES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _guardar(datos):
    LIMITES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LIMITES_PATH.open("w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


def obtener_limite(cliente):
    return _cargar().get(cliente, {}).get("limite_horas")


def obtener_limites_manuales():
    """
    Mapa {cliente: limite_horas} con todos los limites puestos a mano. Sirve
    para resolver el limite de muchos clientes de golpe (ranking) sin releer
    el JSON una vez por cliente.
    """
    return {
        cliente: registro.get("limite_horas")
        for cliente, registro in _cargar().items()
        if registro.get("limite_horas") is not None
    }


def obtener_historial(cliente):
    return _cargar().get(cliente, {}).get("historial", [])


def actualizar_limite(cliente, nuevo_valor, usuario="admin"):
    datos = _cargar()
    registro = datos.setdefault(cliente, {"limite_horas": None, "historial": []})
    valor_anterior = registro.get("limite_horas")
    registro["limite_horas"] = float(nuevo_valor)
    registro["historial"].append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "usuario": usuario,
            "valor_anterior": valor_anterior,
            "valor_nuevo": float(nuevo_valor),
        }
    )
    _guardar(datos)


# Origen del limite contratado que se enseña en la UI.
ORIGEN_BONO = "bono"
ORIGEN_MANUAL = "manual"
ORIGEN_DEFAULT = "default"

# Bono de base con el que arranca todo cliente mientras no tenga ni bonos
# comprados en Jira ni un limite puesto a mano via 'Gestionar horas y limite'.
LIMITE_DEFAULT_HORAS = 10.0


def limite_efectivo(cliente, bono_comprado=0.0, manuales=None):
    """
    Limite de horas contratadas que hay que enseñar para un cliente, junto
    con su origen.

    El limite ES la suma de los bonos de horas que el cliente ha comprado
    (ver bono.calcular_bono_por_cliente): cada bono que se compra amplia lo
    contratado, y el saldo disponible es ese limite menos las horas ya
    consumidas. Mientras un cliente no tenga ningun bono detectado en Jira
    se usa el valor puesto a mano en 'Gestionar' y, si tampoco lo tiene, el
    bono de base LIMITE_DEFAULT_HORAS -- todo cliente arranca con ese bono
    hasta que se corrija a mano (pidiendolo a un Web Admin) o Jira detecte
    su primera compra.

    Con 'manuales' (ver obtener_limites_manuales) se evita releer el JSON
    en cada llamada cuando se resuelven muchos clientes seguidos.

    Devuelve (valor, origen).
    """
    comprado = float(bono_comprado or 0.0)
    if comprado > 0:
        return comprado, ORIGEN_BONO

    manual = obtener_limite(cliente) if manuales is None else manuales.get(cliente)
    if manual is not None:
        return float(manual), ORIGEN_MANUAL

    return LIMITE_DEFAULT_HORAS, ORIGEN_DEFAULT
