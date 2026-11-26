"""Prueba de la tabla de metrópolis, sin red.

Uso:
    python3 -I -B -m unittest discover -s herramientas/pruebas

herramientas/metropolis.json lleva la delimitación oficial de las metrópolis del país, de 2020 (ADR 0014); su
«fecha» es la del archivo de datos abiertos del que salió. Es para que el paso 4 de /configurar desglose una zona
metropolitana en sus municipios. Ningún script la usa, así que, como la tabla de países, solo se revisa su formato.
"""
import datetime as dt
import json
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
TIPOS = {"Zona metropolitana", "Metrópoli municipal", "Zona conurbada"}


class TablaDeMetropolis(unittest.TestCase):
    """La tabla real de la plantilla. Solo su formato: su contenido sale de los datos abiertos oficiales."""

    @classmethod
    def setUpClass(cls):
        cls.tabla = json.loads((RAIZ / "herramientas" / "metropolis.json").read_text(encoding="utf-8"))

    def test_lleva_arriba_la_fuente_y_la_fecha(self):
        self.assertIsInstance(self.tabla, dict)
        self.assertEqual(list(self.tabla)[:2], ["fuente", "fecha"])
        self.assertIsInstance(self.tabla["fuente"], str)
        self.assertTrue(self.tabla["fuente"].strip())
        dt.date.fromisoformat(self.tabla["fecha"])

    def test_cada_metropoli_tiene_nombre_unico_tipo_oficial_y_municipios(self):
        metropolis = self.tabla["metropolis"]
        self.assertIsInstance(metropolis, list)
        self.assertGreater(len(metropolis), 80)
        nombres = [m.get("nombre") for m in metropolis]
        self.assertEqual(len(nombres), len(set(nombres)))
        for m in metropolis:
            with self.subTest(m.get("nombre")):
                self.assertEqual(set(m), {"nombre", "tipo", "municipios"})
                self.assertIsInstance(m["nombre"], str)
                self.assertTrue(m["nombre"].strip())
                self.assertIn(m["tipo"], TIPOS)
                self.assertIsInstance(m["municipios"], list)
                self.assertTrue(m["municipios"])
        self.assertEqual({m["tipo"] for m in metropolis}, TIPOS)

    def test_cada_municipio_tiene_nombre_entidad_y_clave_de_inegi_sin_repetirse_en_su_metropoli(self):
        for m in self.tabla["metropolis"]:
            with self.subTest(m["nombre"]):
                claves = []
                for mun in m["municipios"]:
                    self.assertEqual(set(mun), {"nombre", "entidad", "clave"})
                    for campo in ("nombre", "entidad"):
                        self.assertIsInstance(mun[campo], str)
                        self.assertTrue(mun[campo].strip())
                    # Clave geoestadística: dos dígitos de la entidad y tres del municipio
                    self.assertRegex(mun["clave"], r"^(0[1-9]|[12]\d|3[0-2])\d{3}$")
                    claves.append(mun["clave"])
                self.assertEqual(len(claves), len(set(claves)))
                nombres = [(mun["entidad"], mun["nombre"]) for mun in m["municipios"]]
                self.assertEqual(len(nombres), len(set(nombres)))


if __name__ == "__main__":
    unittest.main()
