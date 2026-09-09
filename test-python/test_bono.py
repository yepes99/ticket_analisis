import unittest

import pandas as pd

from bono import BONO_ALERTA_HORAS, bono_tono, calcular_bono_cliente, extraer_horas_bono


class ExtraerHorasBonoTest(unittest.TestCase):
    def test_detecta_texto_estandar(self):
        self.assertEqual(
            extraer_horas_bono("Tipo de tarea: 10h web changes bundle"),
            10.0,
        )

    def test_detecta_decimales_con_coma(self):
        self.assertEqual(
            extraer_horas_bono("Tipo de tarea: 2,5h web changes bundle"),
            2.5,
        )

    def test_ignora_texto_sin_bundle(self):
        self.assertIsNone(extraer_horas_bono("Ticket normal, tardara 5h aprox"))

    def test_ignora_bundle_sin_numero(self):
        self.assertIsNone(extraer_horas_bono("web changes bundle sin horas"))

    def test_ignora_descripcion_vacia(self):
        self.assertIsNone(extraer_horas_bono(None))
        self.assertIsNone(extraer_horas_bono(""))


class CalcularBonoClienteTest(unittest.TestCase):
    def test_ejemplo_compra_uso_y_recompra(self):
        # Compra 10h, se usan 9h, se compra otro bono de 10h -> 11h disponibles.
        df = pd.DataFrame(
            [
                {
                    "cliente": "Aloha Florida",
                    "ticket_id": "WP-1",
                    "fecha_creacion": pd.Timestamp("2026-01-01"),
                    "bono_horas_compradas": 10.0,
                    "horas_resolucion": None,
                },
                {
                    "cliente": "Aloha Florida",
                    "ticket_id": "WP-2",
                    "fecha_creacion": pd.Timestamp("2026-01-05"),
                    "bono_horas_compradas": None,
                    "horas_resolucion": 9.0,
                },
                {
                    "cliente": "Aloha Florida",
                    "ticket_id": "WP-3",
                    "fecha_creacion": pd.Timestamp("2026-01-10"),
                    "bono_horas_compradas": 10.0,
                    "horas_resolucion": None,
                },
            ]
        )

        resultado = calcular_bono_cliente(df, "Aloha Florida")

        self.assertEqual(resultado["comprado"], 20.0)
        self.assertEqual(resultado["consumido"], 9.0)
        self.assertEqual(resultado["disponible"], 11.0)
        self.assertEqual(len(resultado["compras"]), 2)

    def test_cliente_sin_bono(self):
        df = pd.DataFrame(
            [
                {
                    "cliente": "Otro Cliente",
                    "ticket_id": "WP-9",
                    "fecha_creacion": pd.Timestamp("2026-01-01"),
                    "bono_horas_compradas": None,
                    "horas_resolucion": 3.0,
                },
            ]
        )

        resultado = calcular_bono_cliente(df, "Otro Cliente")

        self.assertEqual(resultado["comprado"], 0.0)
        self.assertEqual(resultado["disponible"], 0.0)


class BonoTonoTest(unittest.TestCase):
    def test_sin_bono_es_neutral(self):
        tono, _, _ = bono_tono(0.0, 0.0)
        self.assertEqual(tono, "neutral")

    def test_agotado_es_danger(self):
        tono, _, _ = bono_tono(10.0, 0.0)
        self.assertEqual(tono, "danger")

    def test_cerca_de_agotarse_es_danger(self):
        tono, _, _ = bono_tono(10.0, BONO_ALERTA_HORAS)
        self.assertEqual(tono, "danger")

    def test_bono_holgado_es_success(self):
        tono, _, _ = bono_tono(10.0, 5.0)
        self.assertEqual(tono, "success")


if __name__ == "__main__":
    unittest.main()
