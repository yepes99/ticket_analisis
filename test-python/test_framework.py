import unittest

import pandas as pd

import framework


def _df(filas):
    return pd.DataFrame(filas)


TAREAS = [
    {"ticket_id": "FW-1", "asignado_a": "Jorge Gallego", "tipo": "Tarea", "resuelto": 1, "dias_resolucion": 17.0},
    {"ticket_id": "FW-2", "asignado_a": "Jorge Gallego", "tipo": "Tarea", "resuelto": 0, "dias_resolucion": None},
    {"ticket_id": "FW-3", "asignado_a": "Leslie Jara", "tipo": "Error", "resuelto": 0, "dias_resolucion": None},
    # De otro equipo: no es carga de soporte.
    {"ticket_id": "FW-4", "asignado_a": "Ruben Sales", "tipo": "Tarea", "resuelto": 1, "dias_resolucion": 3.0},
    # Sin asignar.
    {"ticket_id": "FW-5", "asignado_a": None, "tipo": "Tarea", "resuelto": 0, "dias_resolucion": None},
    # Los Epic son contenedores, no trabajo.
    {"ticket_id": "FW-6", "asignado_a": "Jorge Gallego", "tipo": "Epic", "resuelto": 0, "dias_resolucion": None},
]


class FiltrarEquipoTest(unittest.TestCase):
    def test_solo_el_equipo_de_soporte(self):
        tareas = framework.filtrar_equipo(_df(TAREAS))
        self.assertEqual(tareas["ticket_id"].tolist(), ["FW-1", "FW-2", "FW-3"])

    def test_descarta_los_epic(self):
        tareas = framework.filtrar_equipo(_df(TAREAS))
        self.assertNotIn("FW-6", tareas["ticket_id"].tolist())

    def test_df_vacio_no_falla(self):
        self.assertTrue(framework.filtrar_equipo(_df(TAREAS).iloc[0:0]).empty)

    def test_sin_columna_asignado_no_falla(self):
        self.assertTrue(framework.filtrar_equipo(_df(TAREAS).drop(columns=["asignado_a"])).empty)

    def test_none_no_falla(self):
        self.assertTrue(framework.filtrar_equipo(None).empty)


class ResumenFwTest(unittest.TestCase):
    def test_cifras(self):
        resumen = framework.resumen_fw(framework.filtrar_equipo(_df(TAREAS)))
        self.assertEqual(resumen["total"], 3)
        self.assertEqual(resumen["resueltas"], 1)
        self.assertEqual(resumen["abiertas"], 2)
        self.assertAlmostEqual(resumen["dias_medios"], 17.0)
        self.assertEqual(resumen["tecnicos"], 2)

    def test_sin_tareas_resueltas_no_hay_media(self):
        sin_resolver = _df([{"ticket_id": "FW-9", "asignado_a": "Leslie Jara", "tipo": "Tarea",
                             "resuelto": 0, "dias_resolucion": None}])
        self.assertIsNone(framework.resumen_fw(sin_resolver)["dias_medios"])

    def test_vacio(self):
        self.assertEqual(framework.resumen_fw(None)["total"], 0)


class TareasPorTecnicoTest(unittest.TestCase):
    def test_incluye_a_los_que_no_tienen_ninguna(self):
        # Carmen no tiene tareas de FW: tiene que salir con 0, no ausente,
        # para que en la comparativa se lea "no ha tocado el framework".
        conteo = framework.tareas_por_tecnico(framework.filtrar_equipo(_df(TAREAS)))
        self.assertEqual(conteo, {"Leslie Jara": 1, "Carmen Yepes": 0, "Jorge Gallego": 2, "Alejandro Poveda": 0})

    def test_vacio_devuelve_todos_a_cero(self):
        self.assertEqual(set(framework.tareas_por_tecnico(None).values()), {0})


class DetalleFwTest(unittest.TestCase):
    def test_dias_sin_resolver_salen_con_guion(self):
        tabla = framework.detalle_fw(framework.filtrar_equipo(_df(TAREAS)))
        self.assertEqual(sorted(tabla["dias_resolucion"].tolist()), ["17.0 días", "—", "—"])

    def test_sin_fecha_de_resolucion_sale_sin_cerrar(self):
        con_fechas = _df([
            {"ticket_id": "FW-1", "asignado_a": "Leslie Jara", "tipo": "Tarea",
             "fecha_creacion": pd.Timestamp("2026-09-01"), "fecha_resolucion": pd.Timestamp("2026-09-05"),
             "dias_resolucion": 4.0},
            {"ticket_id": "FW-2", "asignado_a": "Leslie Jara", "tipo": "Tarea",
             "fecha_creacion": pd.Timestamp("2026-09-02"), "fecha_resolucion": None,
             "dias_resolucion": None},
        ])
        tabla = framework.detalle_fw(con_fechas)
        self.assertEqual(sorted(tabla["fecha_resolucion"].tolist()), ["05/09/2026", "Sin cerrar"])

    def test_vacio_devuelve_tabla_con_columnas(self):
        tabla = framework.detalle_fw(None)
        self.assertTrue(tabla.empty)
        self.assertIn("ticket_id", tabla.columns)


class LeerJqlTest(unittest.TestCase):
    def test_por_defecto(self):
        self.assertEqual(framework.leer_fw_jql({}), 'project = "Framework Webplus"')

    def test_lo_de_los_secretos_manda(self):
        self.assertEqual(framework.leer_fw_jql({"FW_JQL": 'project = "Otro"'}), 'project = "Otro"')

    def test_sin_config(self):
        self.assertEqual(framework.leer_fw_jql(None), 'project = "Framework Webplus"')


if __name__ == "__main__":
    unittest.main()
