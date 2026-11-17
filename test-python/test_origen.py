import unittest

import pandas as pd

import origen


def _df(creadores, informadores=None, etiquetas=None):
    n = len(creadores)
    return pd.DataFrame({
        "ticket_id": [f"WP-{i}" for i in range(n)],
        "creador": creadores,
        "informador": informadores if informadores is not None else ["Carmen Yepes"] * n,
        "etiquetas": etiquetas if etiquetas is not None else [[] for _ in range(n)],
    })


class CompletarOrigenTest(unittest.TestCase):
    def test_integracion_y_pasado_a_carmen_es_intercom(self):
        df = origen.completar_origen(_df(["Admin Avantio"], ["Carmen Yepes"]))
        self.assertEqual(df["origen"].iloc[0], origen.INTERCOM)

    def test_integracion_pasado_a_otra_persona_es_interna(self):
        # Caso real WP-31529: Admin Avantio -> Jennifer Urbas, sin etiqueta.
        df = origen.completar_origen(_df(["Admin Avantio"], ["Jennifer Urbas"]))
        self.assertEqual(df["origen"].iloc[0], origen.JIRA)

    def test_etiqueta_intercom_basta(self):
        df = origen.completar_origen(_df(["Admin Avantio", "Rodwane Serhan"], ["Jennifer Urbas", "Rodwane Serhan"],
                                         [["Intercom"], ["intercom", "otra"]]))
        self.assertEqual(df["origen"].tolist(), [origen.INTERCOM, origen.INTERCOM])

    def test_creado_a_mano_sin_etiqueta_es_interna(self):
        df = origen.completar_origen(_df(["Carmen Yepes"], ["Carmen Yepes"]))
        self.assertEqual(df["origen"].iloc[0], origen.JIRA)

    def test_integracion_sin_cambiar_informador_es_interna(self):
        df = origen.completar_origen(_df(["Admin Avantio"], ["Admin Avantio"]))
        self.assertEqual(df["origen"].iloc[0], origen.JIRA)

    def test_sin_creador_no_se_inventa(self):
        df = origen.completar_origen(_df([None, ""]))
        self.assertEqual(df["origen"].tolist(), [origen.DESCONOCIDO, origen.DESCONOCIDO])

    def test_sin_creador_pero_con_etiqueta_es_intercom(self):
        df = origen.completar_origen(_df([None], etiquetas=[["Intercom"]]))
        self.assertEqual(df["origen"].iloc[0], origen.INTERCOM)

    def test_tolera_espacios_alrededor(self):
        df = origen.completar_origen(_df(["  Admin Avantio  "], [" Carmen Yepes "]))
        self.assertEqual(df["origen"].iloc[0], origen.INTERCOM)

    def test_sin_columnas(self):
        df = origen.completar_origen(pd.DataFrame({"ticket_id": ["WP-1"]}))
        self.assertEqual(df["origen"].iloc[0], origen.DESCONOCIDO)

    def test_no_modifica_el_original(self):
        entrada = _df(["Admin Avantio"])
        origen.completar_origen(entrada)
        self.assertNotIn("origen", entrada.columns)


class ResumenOrigenTest(unittest.TestCase):
    def test_cuenta_y_porcentaje(self):
        df = origen.completar_origen(_df(["Admin Avantio"] * 3 + ["Admin Avantio"],
                                         ["Carmen Yepes"] * 3 + ["Jennifer Urbas"]))
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
