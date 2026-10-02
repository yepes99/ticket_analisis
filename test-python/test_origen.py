import unittest

import pandas as pd

import origen


def _df(creadores):
    return pd.DataFrame({"ticket_id": [f"WP-{i}" for i in range(len(creadores))], "creador": creadores})


class CompletarOrigenTest(unittest.TestCase):
    def test_la_cuenta_de_integracion_es_intercom(self):
        df = origen.completar_origen(_df(["Admin Avantio"]))
        self.assertEqual(df["origen"].iloc[0], origen.INTERCOM)

    def test_una_persona_es_jira_directo(self):
        df = origen.completar_origen(_df(["Carmen Yepes"]))
        self.assertEqual(df["origen"].iloc[0], origen.JIRA)

    def test_sin_creador_no_se_inventa(self):
        df = origen.completar_origen(_df([None, ""]))
        self.assertEqual(df["origen"].tolist(), [origen.DESCONOCIDO, origen.DESCONOCIDO])

    def test_tolera_espacios_alrededor(self):
        df = origen.completar_origen(_df(["  Admin Avantio  "]))
        self.assertEqual(df["origen"].iloc[0], origen.INTERCOM)

    def test_sin_columna_creador(self):
        df = origen.completar_origen(pd.DataFrame({"ticket_id": ["WP-1"]}))
        self.assertEqual(df["origen"].iloc[0], origen.DESCONOCIDO)

    def test_no_modifica_el_original(self):
        entrada = _df(["Admin Avantio"])
        origen.completar_origen(entrada)
        self.assertNotIn("origen", entrada.columns)


class ResumenOrigenTest(unittest.TestCase):
    def test_cuenta_y_porcentaje(self):
        df = origen.completar_origen(_df(["Admin Avantio"] * 3 + ["Carmen Yepes"]))
        resumen = origen.resumen_origen(df)
        self.assertEqual(resumen["total"], 4)
        self.assertEqual(resumen["intercom"], 3)
        self.assertEqual(resumen["jira"], 1)
        self.assertEqual(resumen["pct_intercom"], 75.0)
        self.assertEqual(resumen["pct_jira"], 25.0)

    def test_vacio_no_divide_entre_cero(self):
        for vacio in (pd.DataFrame(), None):
            self.assertIsNone(origen.resumen_origen(vacio)["pct_intercom"])
            self.assertIsNone(origen.resumen_origen(vacio)["pct_jira"])


class EtiquetaTest(unittest.TestCase):
    def test_usa_el_vocabulario_del_equipo(self):
        # "tracker ticket" e "interna" es como lo llama el equipo; entre
        # parentesis queda de donde sale, para que no haya que adivinarlo.
        self.assertEqual(origen.etiqueta(origen.INTERCOM), "💬 Tracker (Intercom)")
        self.assertEqual(origen.etiqueta(origen.JIRA), "🛠️ Interna (Jira)")

    def test_valor_nulo_o_raro(self):
        self.assertEqual(origen.etiqueta(None), "⚪ Sin dato")
        self.assertEqual(origen.etiqueta(float("nan")), "⚪ Sin dato")


if __name__ == "__main__":
    unittest.main()
