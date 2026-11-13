import unittest

import pandas as pd

from sla import _fecha_asignacion, _horas_pending_desde

T = ["Carmen Yepes", "Alejandro Poveda"]
CREADO = pd.Timestamp("2026-11-10 09:00")
CORTE = pd.Timestamp("2026-11-12 18:00")


def c(fecha, de, a):
    return {"fecha": pd.Timestamp(fecha), "de": de, "a": a}


class FechaAsignacionTest(unittest.TestCase):
    def test_primera_asignacion_a_tecnico(self):
        hist = [c("2026-11-10 10:30", None, "Carmen Yepes")]
        self.assertEqual(_fecha_asignacion(hist, CREADO, "Carmen Yepes", CORTE, T), pd.Timestamp("2026-11-10 10:30"))

    def test_pasa_por_otra_persona_antes_del_equipo(self):
        hist = [c("2026-11-10 10:00", None, "Ruben Sales"), c("2026-11-11 08:00", "Ruben Sales", "Alejandro Poveda")]
        self.assertEqual(_fecha_asignacion(hist, CREADO, "Alejandro Poveda", CORTE, T), pd.Timestamp("2026-11-11 08:00"))

    def test_reasignacion_entre_tecnicos_cuenta_desde_la_primera(self):
        hist = [c("2026-11-10 10:00", None, "Carmen Yepes"), c("2026-11-11 08:00", "Carmen Yepes", "Alejandro Poveda")]
        self.assertEqual(_fecha_asignacion(hist, CREADO, "Alejandro Poveda", CORTE, T), pd.Timestamp("2026-11-10 10:00"))

    def test_nacio_asignado_a_tecnico(self):
        hist = [c("2026-11-11 08:00", "Carmen Yepes", "Alejandro Poveda")]
        self.assertEqual(_fecha_asignacion(hist, CREADO, "Alejandro Poveda", CORTE, T), CREADO)

    def test_sin_cambios_y_con_asignado(self):
        self.assertEqual(_fecha_asignacion([], CREADO, "Carmen Yepes", CORTE, T), CREADO)

    def test_asignacion_posterior_al_cierre_no_cuenta(self):
        hist = [c("2026-11-13 08:00", None, "Carmen Yepes")]
        self.assertEqual(_fecha_asignacion(hist, CREADO, "Carmen Yepes", CORTE, T), CREADO)


class PendingDesdeTest(unittest.TestCase):
    def test_solo_cuenta_pending_tras_asignar(self):
        hist = [
            c("2026-11-10 09:30", "Backlog", "Pending Info"),
            c("2026-11-10 11:30", "Pending Info", "To develop"),  # 2h, 1h antes de asignar
            c("2026-11-10 12:00", "To develop", "Pending Info"),
            c("2026-11-10 13:00", "Pending Info", "Developing"),  # 1h
        ]
        horas = _horas_pending_desde(hist, pd.Timestamp("2026-11-10 10:30"), CORTE)
        self.assertAlmostEqual(horas, 2.0)


if __name__ == "__main__":
    unittest.main()
