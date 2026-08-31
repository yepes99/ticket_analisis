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
