import unittest
from datetime import date

from periodos import PERIODOS, describir_rango, resolve_query_dates

HOY = date(2026, 11, 13)  # viernes


class PeriodosTest(unittest.TestCase):
    def r(self, periodo, rango=None):
        return resolve_query_dates(periodo, 2026, rango, today=HOY)

    def test_esta_semana(self):
        self.assertEqual(self.r("Esta semana"), (date(2026, 11, 9), HOY))

    def test_semana_pasada(self):
        self.assertEqual(self.r("Semana pasada"), (date(2026, 11, 2), date(2026, 11, 8)))

    def test_este_mes(self):
        self.assertEqual(self.r("Este mes"), (date(2026, 11, 1), HOY))

    def test_mes_pasado(self):
        self.assertEqual(self.r("Mes pasado"), (date(2026, 10, 1), date(2026, 10, 31)))

    def test_mes_pasado_en_enero(self):
        inicio, fin = resolve_query_dates("Mes pasado", 2027, today=date(2027, 1, 15))
        self.assertEqual((inicio, fin), (date(2026, 12, 1), date(2026, 12, 31)))

    def test_personalizado(self):
        self.assertEqual(self.r("Personalizado", (date(2026, 11, 8), date(2026, 11, 13))),
                         (date(2026, 11, 8), date(2026, 11, 13)))

    def test_personalizado_al_reves_falla(self):
        with self.assertRaises(ValueError):
            self.r("Personalizado", (date(2026, 11, 13), date(2026, 11, 8)))

    def test_todos_los_periodos_resuelven(self):
        for periodo in PERIODOS:
            rango = (date(2026, 11, 1), HOY) if periodo == "Personalizado" else None
            self.r(periodo, rango)

    def test_describir(self):
        self.assertEqual(describir_rango(date(2026, 11, 8), date(2026, 11, 13)),
                         "Del 08/11/2026 al 13/11/2026 · 6 días")
        self.assertEqual(describir_rango(date(2026, 11, 8), date(2026, 11, 8)),
                         "Del 08/11/2026 al 08/11/2026 · 1 día")


if __name__ == "__main__":
    unittest.main()
