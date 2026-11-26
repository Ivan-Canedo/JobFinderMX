"""Prueba de la tabla de metrópolis, sin red.

Uso:
    python3 -I -B -m unittest discover -s herramientas/pruebas

herramientas/metropolis.json lleva la delimitación oficial de las metrópolis del país, de 2020 (ADR 0014); su
«fecha» es la del archivo de datos abiertos del que salió. Es para que el paso 4 de /configurar desglose una zona
metropolitana en sus municipios. Ningún script la usa: la lee una línea de Python del paso 4, que imprime solo
las metrópolis cuyo nombre coincide con lo que nombró el titular. Por eso, como la tabla de países, la tabla real solo se
revisa en su formato, y la línea del paso se corre contra una tabla ficticia.
"""
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
TIPOS = {"Zona metropolitana", "Metrópoli municipal", "Zona conurbada"}
PASO_4 = RAIZ / ".claude" / "skills" / "configurar" / "paso-4-preferencias.md"


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


def linea_del_paso_4():
    """El código de la línea `python3 -I -c "..."` del paso 4 que lee la tabla de metrópolis."""
    lineas = [linea for linea in PASO_4.read_text(encoding="utf-8").splitlines()
              if "metropolis.json" in linea and " -c " in linea]
    if len(lineas) != 1:
        raise AssertionError(f"el paso 4 debe traer una sola línea de Python que lea la tabla; trae {len(lineas)}")
    m = re.search(r'python3 -I -c "(.+)" ', lineas[0])
    if not m:
        raise AssertionError(f"la línea no tiene la forma python3 -I -c \"...\" NOMBRE: {lineas[0]}")
    return m.group(1)


FICTICIA = {
    "fuente": "Tabla ficticia de prueba",
    "fecha": "2025-01-01",
    "metropolis": [
        {"nombre": "Cordoba", "tipo": "Zona metropolitana", "municipios": [
            {"nombre": "Córdoba", "entidad": "Veracruz de Ignacio de la Llave", "clave": "30044"}]},
        {"nombre": "Moroleon-Uriangato", "tipo": "Zona metropolitana", "municipios": [
            {"nombre": "Moroleón", "entidad": "Guanajuato", "clave": "11021"},
            {"nombre": "Uriangato", "entidad": "Guanajuato", "clave": "11041"}]},
        {"nombre": "Puebla-Tlaxcala", "tipo": "Zona metropolitana", "municipios": [
            {"nombre": "Puebla", "entidad": "Puebla", "clave": "21114"},
            {"nombre": "Zacatelco", "entidad": "Tlaxcala", "clave": "29044"}]},
        {"nombre": "Tlaxcala-Apizaco", "tipo": "Zona metropolitana", "municipios": [
            {"nombre": "Tlaxcala", "entidad": "Tlaxcala", "clave": "29033"}]},
        {"nombre": "León", "tipo": "Zona metropolitana", "municipios": [
            {"nombre": "León", "entidad": "Guanajuato", "clave": "11020"}]},
    ],
}


class LineaDelPaso4(unittest.TestCase):
    """La línea del paso 4, corrida en una copia ficticia con la tabla de arriba."""

    @classmethod
    def setUpClass(cls):
        cls.codigo = linea_del_paso_4()
        cls.dir = tempfile.TemporaryDirectory()
        tabla = pathlib.Path(cls.dir.name) / "herramientas" / "metropolis.json"
        tabla.parent.mkdir()
        tabla.write_text(json.dumps(FICTICIA, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def metropolis_que_imprime(self, nombre):
        r = subprocess.run([sys.executable, "-I", "-c", self.codigo, nombre], cwd=self.dir.name,
                           capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        # Solo ASCII: se lee igual en una terminal de Windows en cp1252
        salida = r.stdout.decode("ascii")
        return [json.loads(linea) for linea in salida.splitlines() if linea.strip()]

    def nombres(self, nombre):
        return [m["nombre"] for m in self.metropolis_que_imprime(nombre)]

    def test_imprime_solo_la_metropoli_que_coincide(self):
        self.assertEqual(self.nombres("León"), ["León"])

    def test_compara_sin_acentos_ni_mayusculas(self):
        self.assertEqual(self.nombres("CÓRDOBA"), ["Cordoba"])
        self.assertEqual(self.nombres("moroleón"), ["Moroleon-Uriangato"])
        self.assertEqual(self.nombres("leon"), ["León"])

    def test_una_parte_del_nombre_da_cada_metropoli_que_la_lleva(self):
        self.assertEqual(self.nombres("tlaxcala"), ["Puebla-Tlaxcala", "Tlaxcala-Apizaco"])

    def test_trae_la_metropoli_completa_con_sus_municipios(self):
        self.assertEqual(self.metropolis_que_imprime("Puebla"), [FICTICIA["metropolis"][2]])

    def test_sin_coincidencia_no_imprime_ninguna(self):
        self.assertEqual(self.metropolis_que_imprime("Atlantis"), [])

    def test_ignora_los_espacios_de_sobra(self):
        self.assertEqual(self.nombres("  León "), ["León"])

    def test_un_nombre_vacio_no_imprime_la_tabla_completa(self):
        self.assertEqual(self.metropolis_que_imprime(""), [])
        self.assertEqual(self.metropolis_que_imprime("   "), [])


if __name__ == "__main__":
    unittest.main()
