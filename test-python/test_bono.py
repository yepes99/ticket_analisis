import unittest

import pandas as pd

from bono import (
    BONO_AVISO_HORAS,
    BONO_VERDE_HORAS,
    bono_tono,
    calcular_bono_cliente,
    calcular_bono_por_cliente,
    detectar_bonos_sin_cliente,
    extraer_horas_bono,
)


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

    def test_saldo_negativo_es_danger(self):
        tono, _, _ = bono_tono(10.0, -3.0)
        self.assertEqual(tono, "danger")

    def test_cerca_de_agotarse_es_warning(self):
        tono, _, _ = bono_tono(10.0, BONO_AVISO_HORAS)
        self.assertEqual(tono, "warning")

    def test_por_debajo_del_umbral_verde_es_warning(self):
        tono, _, _ = bono_tono(10.0, 5.0)
        self.assertEqual(tono, "warning")

    def test_justo_en_el_umbral_verde_es_success(self):
        tono, _, _ = bono_tono(10.0, BONO_VERDE_HORAS)
        self.assertEqual(tono, "success")

    def test_bono_holgado_es_success(self):
        tono, _, _ = bono_tono(20.0, 12.0)
        self.assertEqual(tono, "success")


class CalcularBonoPorClienteTest(unittest.TestCase):
    def test_calcula_varios_clientes_a_la_vez(self):
        df = pd.DataFrame(
            [
                {"cliente": "A", "ticket_id": "WP-1", "bono_horas_compradas": 10.0, "horas_resolucion": None},
                {"cliente": "A", "ticket_id": "WP-2", "bono_horas_compradas": None, "horas_resolucion": 9.0},
                {"cliente": "B", "ticket_id": "WP-3", "bono_horas_compradas": None, "horas_resolucion": 5.0},
            ]
        )

        resumen = calcular_bono_por_cliente(df)

        self.assertEqual(resumen.loc["A", "comprado"], 10.0)
        self.assertEqual(resumen.loc["A", "disponible"], 1.0)
        # "B" nunca compro bono: disponible se queda en 0, no en negativo.
        self.assertEqual(resumen.loc["B", "comprado"], 0.0)
        self.assertEqual(resumen.loc["B", "disponible"], 0.0)

    def test_sin_columna_bono_devuelve_vacio(self):
        df = pd.DataFrame([{"cliente": "A", "ticket_id": "WP-1"}])
        self.assertTrue(calcular_bono_por_cliente(df).empty)


class DetectarBonosSinClienteTest(unittest.TestCase):
    def test_detecta_compra_sin_cliente_atribuido(self):
        df = pd.DataFrame(
            [
                {
                    "ticket_id": "WP-1",
                    "resumen": "Bevalle | 10h web changes bundle",
                    "fecha_creacion": pd.Timestamp("2026-01-01"),
                    "bono_horas_compradas": 10.0,
                    "cliente": "Bevalle",
                },
                {
                    "ticket_id": "WP-2",
                    "resumen": "10h web changes bundle",
                    "fecha_creacion": pd.Timestamp("2026-01-02"),
                    "bono_horas_compradas": 10.0,
                    "cliente": "Sin cliente",
                },
                {
                    "ticket_id": "WP-3",
                    "resumen": "Ticket normal, no es bono",
                    "fecha_creacion": pd.Timestamp("2026-01-03"),
                    "bono_horas_compradas": None,
                    "cliente": "Sin cliente",
                },
            ]
        )

        huerfanos = detectar_bonos_sin_cliente(df)

        self.assertEqual(list(huerfanos["ticket_id"]), ["WP-2"])

    def test_sin_huerfanos_devuelve_vacio(self):
        df = pd.DataFrame(
            [
                {
                    "ticket_id": "WP-1",
                    "resumen": "Bevalle | 10h web changes bundle",
                    "fecha_creacion": pd.Timestamp("2026-01-01"),
                    "bono_horas_compradas": 10.0,
                    "cliente": "Bevalle",
                },
            ]
        )

        self.assertTrue(detectar_bonos_sin_cliente(df).empty)


if __name__ == "__main__":
    unittest.main()
