import unittest

import numpy as np
import pandas as pd

from presupuesto import presupuesto_tono, resumen_presupuesto, tickets_con_presupuesto
from sla import completar_presupuesto


def _df(filas):
    df = pd.DataFrame(filas)
    for columna in ("presupuesto", "presupuesto_cliente", "horas_trabajo_real", "horas_transcurridas"):
        if columna not in df.columns:
            df[columna] = np.nan
    return df


class PresupuestoTonoTest(unittest.TestCase):
    def test_sin_presupuesto_es_neutral(self):
        self.assertEqual(presupuesto_tono(None, 5.0)[0], "neutral")

    def test_presupuesto_cero_es_neutral(self):
        # Un 0 no es un presupuesto: dividir por el daria infinito.
        self.assertEqual(presupuesto_tono(0.0, 5.0)[0], "neutral")

    def test_sin_tiempo_de_desarrollo_es_neutral(self):
        self.assertEqual(presupuesto_tono(6.0, None)[0], "neutral")

    def test_dentro_de_presupuesto_es_success(self):
        self.assertEqual(presupuesto_tono(6.0, 4.0)[0], "success")

    def test_justo_en_el_presupuesto_es_success(self):
        self.assertEqual(presupuesto_tono(6.0, 6.0)[0], "success")

    def test_poco_por_encima_es_warning(self):
        self.assertEqual(presupuesto_tono(6.0, 7.0)[0], "warning")

    def test_justo_en_el_25_por_ciento_es_warning(self):
        self.assertEqual(presupuesto_tono(6.0, 7.5)[0], "warning")

    def test_mas_de_un_25_por_ciento_es_danger(self):
        # El caso real de WP-31048: 6 h estimadas, 8.04 h de desarrollo.
        self.assertEqual(presupuesto_tono(6.0, 8.04)[0], "danger")


class CompletarPresupuestoTest(unittest.TestCase):
    def test_desviacion_usa_el_tiempo_de_desarrollo(self):
        df = completar_presupuesto(_df([
            {"presupuesto_cliente": 6.0, "horas_trabajo_real": 8.0, "horas_transcurridas": 100.0},
        ]))
        # 8 - 6, no 100 - 6: el tiempo en Backlog no es desarrollo.
        self.assertAlmostEqual(df["desviacion_presupuesto"].iloc[0], 2.0)
        self.assertAlmostEqual(df["consumo_presupuesto"].iloc[0], 8.0 / 6.0)

    def test_sin_presupuesto_no_hay_desviacion(self):
        df = completar_presupuesto(_df([{"horas_trabajo_real": 8.0, "horas_transcurridas": 10.0}]))
        self.assertTrue(pd.isna(df["desviacion_presupuesto"].iloc[0]))
        self.assertTrue(pd.isna(df["consumo_presupuesto"].iloc[0]))

    def test_presupuesto_cero_no_divide(self):
        df = completar_presupuesto(_df([{"presupuesto_cliente": 0.0, "horas_trabajo_real": 8.0}]))
        self.assertTrue(pd.isna(df["consumo_presupuesto"].iloc[0]))

    def test_sin_columnas_no_falla(self):
        df = completar_presupuesto(pd.DataFrame({"horas_transcurridas": [4.0]}))
        self.assertIn("presupuesto_cliente", df.columns)
        self.assertIn("desviacion_presupuesto", df.columns)


class ResumenPresupuestoTest(unittest.TestCase):
    def setUp(self):
        self.df = completar_presupuesto(_df([
            {"ticket_id": "WP-1", "presupuesto_cliente": 6.0, "horas_trabajo_real": 8.0},
            {"ticket_id": "WP-2", "presupuesto_cliente": 10.0, "horas_trabajo_real": 4.0},
            {"ticket_id": "WP-3", "presupuesto_cliente": None, "horas_trabajo_real": 30.0},
            {"ticket_id": "WP-4", "presupuesto_cliente": 5.0, "horas_trabajo_real": None},
        ]))

    def test_solo_cuenta_los_que_llevan_presupuesto(self):
        # Ordenados por desviacion de mayor a menor (primero el que mas se ha
        # pasado) y con los que aun no tienen desarrollo al final.
        self.assertEqual(tickets_con_presupuesto(self.df)["ticket_id"].tolist(), ["WP-1", "WP-2", "WP-4"])

    def test_cifras_del_resumen(self):
        resumen = resumen_presupuesto(self.df)
        self.assertAlmostEqual(resumen["horas_estimadas"], 21.0)
        self.assertEqual(resumen["con_presupuesto"], 3)
        self.assertEqual(resumen["pasados"], 1)
        self.assertEqual(resumen["dentro"], 1)
        self.assertAlmostEqual(resumen["horas_exceso"], 2.0)

    def test_df_vacio_no_falla(self):
        resumen = resumen_presupuesto(pd.DataFrame())
        self.assertEqual(resumen["con_presupuesto"], 0)
        self.assertTrue(tickets_con_presupuesto(pd.DataFrame()).empty)


if __name__ == "__main__":
    unittest.main()
