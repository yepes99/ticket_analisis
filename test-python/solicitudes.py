"""
Solicitudes de cambio que requieren aprobacion de un Web Admin:
- "horas": corregir las horas de resolucion de un ticket concreto.
- "limite": cambiar el limite de horas contratadas de un cliente.

Web Admin, Soporte y CS pueden crear solicitudes; solo Web Admin las aprueba
o rechaza. Se persisten en un JSON local, compartido por todos los usuarios
(no depende de la sesion del navegador de quien solicita o aprueba).

De momento esto es un JSON en disco a falta de decidir si se centraliza en
otro sitio (email, Slack, una base de datos) mas adelante.
"""

import json
from datetime import datetime
from pathlib import Path


SOLICITUDES_PATH = Path(__file__).resolve().parent / "data" / "solicitudes.json"

TIPOS = {"horas", "limite"}


def _cargar():
    if not SOLICITUDES_PATH.exists():
        return []
    with SOLICITUDES_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _guardar(solicitudes):
    SOLICITUDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SOLICITUDES_PATH.open("w", encoding="utf-8") as fh:
        json.dump(solicitudes, fh, ensure_ascii=False, indent=2)


def crear_solicitud(tipo, cliente, valor_actual, valor_propuesto, solicitado_por, ticket_id=None):
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de solicitud no soportado: {tipo}")

    solicitudes = _cargar()
    nuevo_id = max((s["id"] for s in solicitudes), default=0) + 1
    solicitudes.append(
        {
            "id": nuevo_id,
            "tipo": tipo,
            "ticket_id": ticket_id,
            "cliente": cliente,
            "valor_actual": float(valor_actual) if valor_actual is not None else None,
            "valor_propuesto": float(valor_propuesto),
            "solicitado_por": solicitado_por,
            "fecha_solicitud": datetime.now().isoformat(timespec="seconds"),
            "estado": "pendiente",
            "revisado_por": None,
            "fecha_revision": None,
        }
    )
    _guardar(solicitudes)
    return nuevo_id


def listar_solicitudes(estado=None, tipo=None):
    solicitudes = _cargar()
    if estado:
        solicitudes = [s for s in solicitudes if s["estado"] == estado]
    if tipo:
        solicitudes = [s for s in solicitudes if s["tipo"] == tipo]
    return solicitudes


def contar_pendientes():
    return len(listar_solicitudes(estado="pendiente"))


def resolver_solicitud(solicitud_id, aprobar, revisor):
    """
    Marca la solicitud como aprobada o rechazada y la devuelve.
    No aplica el cambio en si (eso lo hace quien llama, segun el tipo).
    """
    solicitudes = _cargar()
    resuelta = None
    for s in solicitudes:
        if s["id"] == solicitud_id:
            s["estado"] = "aprobado" if aprobar else "rechazado"
            s["revisado_por"] = revisor
            s["fecha_revision"] = datetime.now().isoformat(timespec="seconds")
            resuelta = dict(s)
            break
    _guardar(solicitudes)
    return resuelta


def obtener_overrides_horas_aprobados():
    """Horas propuestas de cada solicitud de tipo 'horas' aprobada, por ticket_id."""
    return {
        s["ticket_id"]: s["valor_propuesto"]
        for s in listar_solicitudes(estado="aprobado", tipo="horas")
    }
