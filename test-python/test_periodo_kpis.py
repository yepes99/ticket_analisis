import unittest
from datetime import date

import pandas as pd

from metrics import calculate_sla_kpis, mascaras_periodo


def _df():
    filas = [
        # creada en el periodo y cerrada en el periodo
        {"ticket_id": "WP-1", "fecha_creacion": "2026-11-09 10:00", "fecha_resolucion": "2026-11-10 10:00", "resuelto": 1},
        # creada en el periodo, sigue abierta
        {"ticket_id": "WP-2", "fecha_creacion": "2026-11-12 10:00", "fecha_resolucion": None, "resuelto": 0},
        # creada antes, cerrada en el periodo
        {"ticket_id": "WP-3", "fecha_creacion": "2026-11-05 10:00", "fecha_resolucion": "2026-11-08 09:00", "resuelto": 1},
        # creada antes, cerrada antes (entra por otro cambio de estado)
        {"ticket_id": "WP-4", "fecha_creacion": "2026-11-04 10:00", "fecha_resolucion": "2026-11-06 09:00", "resuelto": 1},
        # creada antes, sigue abierta
        {"ticket_id": "WP-5", "fecha_creacion": "2026-11-03 10:00", "fecha_resolucion": None, "resuelto": 0},
        # creada el ultimo dia del rango a ultima hora: cuenta
        {"ticket_id": "WP-6", "fecha_creacion": "2026-11-13 23:30", "fecha_resolucion": None, "resuelto": 0},
    ]
    df = pd.DataFrame(filas)
    df["fecha_creacion"] = pd.to_datetime(df["fecha_creacion"])
    df["fecha_resolucion"] = pd.to_datetime(df["fecha_resolucion"])
    for col in ["sla_prioridad_cumple", "sla_size_cumple", "sla_global_cumple"]:
        df[col] = 1.0
    df["cliente"] = "x"
    df["asignado_a"] = "Carmen Yepes"
    return df


INICIO, FIN = date(2026, 11, 8), date(2026, 11, 13)


class PeriodoKpisTest(unittest.TestCase):
    def test_mascaras(self):
        creadas, resueltas = mascaras_periodo(_df(), INICIO, FIN)
        self.assertEqual(list(creadas), [True, True, False, False, False, True])
        self.assertEqual(list(resueltas), [True, False, True, False, False, False])

    def test_kpis_con_rango(self):
        kpis = calculate_sla_kpis(_df(), INICIO, FIN)
        self.assertEqual(kpis["total_tickets"], 6)
        self.assertEqual(kpis["tickets_creados_periodo"], 3)
        self.assertEqual(kpis["tickets_creados_antes"], 3)
        self.assertEqual(kpis["tickets_resueltos"], 2)  # WP-4 se cerro antes del rango
        self.assertEqual(kpis["resueltos_creados_periodo"], 1)
        self.assertEqual(kpis["tickets_abiertos"], 3)
        self.assertEqual(kpis["abiertos_creados_periodo"], 2)

    def test_sin_rango_cuenta_todo(self):
        kpis = calculate_sla_kpis(_df())
        self.assertEqual(kpis["tickets_creados_periodo"], 6)
        self.assertEqual(kpis["tickets_creados_antes"], 0)
        self.assertEqual(kpis["tickets_resueltos"], 3)
        self.assertEqual(kpis["tickets_abiertos"], 3)


if __name__ == "__main__":
    unittest.main()
