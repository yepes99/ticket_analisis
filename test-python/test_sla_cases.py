import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from metrics import calculate_sla_kpis
from sla import completar_sla


class SlaCasesTest(unittest.TestCase):
    def setUp(self):
        self.now = pd.Timestamp("2026-08-27 12:00:00")

    def build_df(self):
        return pd.DataFrame(
            [
                {
                    "ticket_id": "OK-1",
                    "estado": "Finalizada",
                    "prioridad": "High",
                    "size": "S",
                    "fecha_creacion": pd.Timestamp("2026-08-20 10:00"),
                    "fecha_resolucion": pd.Timestamp("2026-08-20 17:00"),
                    "cliente": "A",
                    "asignado_a": "Leslie Jara",
                },
                {
                    "ticket_id": "BAD-1",
                    "estado": "Done",
                    "prioridad": "Highest",
                    "size": "S",
                    "fecha_creacion": pd.Timestamp("2026-08-20 10:00"),
                    "fecha_resolucion": pd.Timestamp("2026-08-21 10:00"),
                    "cliente": "A",
                    "asignado_a": "Leslie Jara",
                },
                {
                    "ticket_id": "OPEN-OK",
                    "estado": "In Progress",
                    "prioridad": "Low",
                    "size": "M",
                    "fecha_creacion": pd.Timestamp("2026-08-26 12:00"),
                    "fecha_resolucion": pd.NaT,
                    "cliente": "B",
                    "asignado_a": "Carmen Yepes",
                },
                {
                    "ticket_id": "RISK-1",
                    "estado": "Backlog",
                    "prioridad": "Medium",
                    "size": "S",
                    "fecha_creacion": pd.Timestamp("2026-08-26 16:00"),
                    "fecha_resolucion": pd.NaT,
                    "cliente": "B",
                    "asignado_a": "Carmen Yepes",
                },
                {
                    "ticket_id": "OPEN-BAD",
                    "estado": "Backlog",
                    "prioridad": "Medium",
                    "size": "S",
                    "fecha_creacion": pd.Timestamp("2026-08-25 11:00"),
                    "fecha_resolucion": pd.NaT,
                    "cliente": "C",
                    "asignado_a": "Jorge Gallego",
                },
                {
                    "ticket_id": "NO-SIZE",
                    "estado": "Finalizada",
                    "prioridad": "Low",
                    "size": None,
                    "fecha_creacion": pd.Timestamp("2026-08-20 10:00"),
                    "fecha_resolucion": pd.Timestamp("2026-08-20 11:00"),
                    "cliente": "C",
                    "asignado_a": "Jorge Gallego",
                },
            ]
        )

    @patch("sla.pd.Timestamp.now")
    def test_sla_cases_are_classified_precisely(self, mock_now):
        mock_now.return_value = self.now

        df = completar_sla(self.build_df()).set_index("ticket_id")

        self.assertEqual(df.loc["OK-1", "sla_prioridad_cumple"], 1)
        self.assertEqual(df.loc["OK-1", "sla_size_cumple"], 1)
        self.assertEqual(df.loc["OK-1", "sla_global_cumple"], 1)

        self.assertEqual(df.loc["BAD-1", "resuelto"], 1)
        self.assertEqual(df.loc["BAD-1", "sla_prioridad_cumple"], 0)
        self.assertEqual(df.loc["BAD-1", "sla_global_cumple"], 0)

        self.assertTrue(np.isnan(df.loc["OPEN-OK", "sla_prioridad_cumple"]))
        self.assertTrue(np.isnan(df.loc["OPEN-OK", "sla_global_cumple"]))
        self.assertEqual(df.loc["OPEN-OK", "en_riesgo_sla"], 0)

        self.assertTrue(np.isnan(df.loc["RISK-1", "sla_prioridad_cumple"]))
        self.assertEqual(df.loc["RISK-1", "en_riesgo_sla"], 1)

        self.assertEqual(df.loc["OPEN-BAD", "sla_prioridad_cumple"], 0)
        self.assertEqual(df.loc["OPEN-BAD", "sla_global_cumple"], 0)
        self.assertEqual(df.loc["OPEN-BAD", "en_riesgo_sla"], 0)

        self.assertEqual(df.loc["NO-SIZE", "sla_prioridad_cumple"], 1)
        self.assertTrue(np.isnan(df.loc["NO-SIZE", "sla_size_cumple"]))
        self.assertTrue(np.isnan(df.loc["NO-SIZE", "sla_global_cumple"]))

        kpis = calculate_sla_kpis(df.reset_index())
        self.assertEqual(kpis["sla_prioridad"], 50.0)
        self.assertEqual(kpis["sla_size"], 100.0)
        self.assertEqual(kpis["sla_global"], 33.3)
        self.assertEqual(kpis["tickets_incumplidos"], 2)
        self.assertEqual(kpis["tickets_en_riesgo"], 1)


if __name__ == "__main__":
    unittest.main()
