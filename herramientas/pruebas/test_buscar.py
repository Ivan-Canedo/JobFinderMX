"""Pruebas del script de búsqueda, sin red.

Uso:
    python3 -I -B -m unittest discover -s herramientas/pruebas

Cada prueba arma una copia ficticia con el script, un 04, un 06 y, si busca en una bolsa de empleo, un 05.
La configuración que falta se prueba por la línea de comandos, porque el script se detiene antes de
cualquier petición. La clasificación de ubicaciones y cada adaptador se prueban corriendo main() con un
portal falso de su plataforma (Workday, Eightfold, Workable, SmartRecruiters u Oracle Recruiting Cloud) en
lugar de la red. La bolsa OCC Mundial se prueba con OccFalso, que reemplaza la red misma (urlopen), para
ejercitar el pedir() real que distinguirá sus señales anti-bot. Los anuncios y los lugares son ficticios,
con los códigos XA, XB, XC y XD, que la norma ISO reserva y no son países.
"""
import contextlib
import datetime as dt
import html
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import urllib.error
import urllib.parse
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "herramientas" / "buscar.py"

PAISES = {"XA": ["País A", "Country A"], "XB": ["País B", "Country B"], "XC": ["País C", "Country C"]}
# La tabla de países que lee el script junto a sí mismo, ficticia: las pruebas no dependen de CLDR. «Tierra Z» es
# también un nombre de XA en la prueba de la prioridad de 04
TABLA_DE_PAISES = {"XY": ["Country Y", "País Y", "XYY"], "XZ": ["Country Z", "País Z", "XZZ", "Tierra Z"]}


def preferencias(localidades, alcance="ninguno", paises_remoto=(), **cambios):
    """Bloque de 04/PREF-UBICACION lleno, con los cambios que pida la prueba."""
    bloque = {"paises": PAISES, "localidades": localidades,
              "remoto": {"alcance": alcance, "paises": list(paises_remoto)},
              "zona_horaria": "UTC", "moneda": "XTS"}
    bloque.update(cambios)
    return bloque


def grupo(pais, divisiones=(), nombres=(), incluidas=None):
    """Un grupo de localidades; sin incluidas, el grupo no lleva el campo, como una copia anterior a la 2.3."""
    g = {"pais": pais, "divisiones": list(divisiones), "zona": None, "nombres": list(nombres)}
    if incluidas is not None:
        g["incluidas"] = list(incluidas)
    return g


def modulo_04(bloque):
    texto = bloque if isinstance(bloque, str) else json.dumps(bloque, ensure_ascii=False, indent=2)
    return f"# 04 — Preferencias laborales\n\n## PREF-UBICACION — Región\n\nRegión.\n\n```json\n{texto}\n```\n"


def ficha(eid, configuracion):
    texto = configuracion if isinstance(configuracion, str) else json.dumps(configuracion, indent=2)
    return f"## {eid} — Empresa ficticia\n\n### Configuración\n\n```json\n{texto}\n```\n\n### Identidad\n\n- Ficticia.\n"


def modulo_06(fichas, bolsas=None):
    """06 con esas fichas de empresa y, si se dan, el catálogo de bolsas con sus fichas; sin bolsas, sin la sección
    CAT-BOLSAS, como una copia anterior a ella."""
    filas = "".join(f"| {eid} | Empresa ficticia | Objetivo | 0.1 | 2026-10-16 |\n" for eid in fichas)
    texto = ("# 06 — Empresas objetivo y fichas\n\n## CAT-EMPRESAS — Catálogo\n\n"
             "| ID | Empresa | Estado | Versión de ficha | Fecha de comprobación |\n"
             "| --- | --- | --- | --- | --- |\n" + filas + "\n## CAT-REGLAS — Mantenimiento\n\n- Reglas.\n\n")
    if bolsas is not None:
        texto += ("## CAT-BOLSAS — Bolsas de empleo\n\n| ID | Bolsa | Versión de ficha | Fecha de comprobación |\n"
                  "| --- | --- | --- | --- |\n"
                  + "".join(f"| {bid} | Bolsa ficticia | 0.1 | 2026-11-22 |\n" for bid in bolsas) + "\n")
    return texto + "\n".join(fichas.values()) + "\n" + "\n".join((bolsas or {}).values())


def ficha_bolsa(bid, configuracion):
    texto = configuracion if isinstance(configuracion, str) else json.dumps(configuracion, indent=2)
    return f"## {bid} — Bolsa ficticia\n\n### Configuración\n\n```json\n{texto}\n```\n"


def terminos(**familias):
    """Bloque de 05/HAB-TERMINOS: ROL-ID → (términos, títulos)."""
    return {rol.replace("_", "-"): {"terminos": list(t), "titulos": list(ti)} for rol, (t, ti) in familias.items()}


def modulo_05(bloque):
    texto = bloque if isinstance(bloque, str) else json.dumps(bloque, ensure_ascii=False, indent=2)
    return (f"# 05 — Mapa de habilidades y roles\n\n## HAB-ROLES — Familias\n\n- Familias.\n\n"
            f"## HAB-TERMINOS — Términos de búsqueda\n\nTérminos.\n\n```json\n{texto}\n```\n\n## HAB-FUENTES\n\n- F.\n")


class CopiaFicticia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)
        (self.dir / "herramientas").mkdir()
        shutil.copy(SCRIPT, self.dir / "herramientas")
        (self.dir / "herramientas" / "paises.json").write_text(json.dumps(TABLA_DE_PAISES, ensure_ascii=False),
                                                                encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def escribir(self, modulo_04_texto=None, modulo_06_texto=None, modulo_05_texto=None):
        if modulo_04_texto is not None:
            (self.dir / "04_PREFERENCIAS_LABORALES.md").write_text(modulo_04_texto, encoding="utf-8")
        if modulo_05_texto is not None:
            (self.dir / "05_MAPA_HABILIDADES_Y_ROLES.md").write_text(modulo_05_texto, encoding="utf-8")
        if modulo_06_texto is not None:
            (self.dir / "06_EMPRESAS_OBJETIVO.md").write_text(modulo_06_texto, encoding="utf-8")

    def correr(self, *argumentos):
        """El script de la copia por su línea de comandos."""
        return subprocess.run([sys.executable, "-I", "-B", str(self.dir / "herramientas" / "buscar.py"), *argumentos],
                              capture_output=True, text=True, timeout=60)


class ConfiguracionFaltante(CopiaFicticia):
    def assertFallaSinBuscar(self, r, *textos):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        for t in textos:
            self.assertIn(t, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_sin_04_falla_con_un_mensaje_claro(self):
        self.escribir(None, modulo_06({}))
        self.assertFallaSinBuscar(self.correr(), "04_PREFERENCIAS_LABORALES.md")

    def test_con_el_bloque_de_04_sin_llenar_pide_configurarlo(self):
        plantilla = {"paises": {}, "localidades": [], "remoto": {"alcance": None, "paises": []},
                     "zona_horaria": None, "moneda": None}
        self.escribir(modulo_04(plantilla), modulo_06({}))
        self.assertFallaSinBuscar(self.correr(), "PREF-UBICACION", "/configurar", "paso 4")

    def test_un_bloque_de_04_que_no_cumple_sus_reglas_falla_con_un_mensaje_claro(self):
        en_xa = [grupo("XA", nombres=["Ciudad A1"])]
        casos = {
            "sin bloque": ("# 04\n\n## PREF-UBICACION — Región\n\nSin bloque.\n", "```json"),
            "JSON inválido": (modulo_04('{"paises": {},}'), "JSON"),
            "país sin nombres": (modulo_04(preferencias([grupo("XD", nombres=["Ciudad D1"])])), "XD"),
            "alcance desconocido": (modulo_04(preferencias(en_xa, alcance="mundo")), "remoto.alcance"),
            "remoto por países sin países": (modulo_04(preferencias(en_xa, alcance="paises")), "remoto.paises"),
            "nada que buscar": (modulo_04(preferencias([], alcance="ninguno")), "localidades"),
            "zona horaria inexistente": (modulo_04(preferencias(en_xa, zona_horaria="Region/Inexistente")),
                                         "zona_horaria"),
            "localidad sin lista": (modulo_04(preferencias([{"pais": "XA", "nombres": "Ciudad A1"}])), "localidades"),
        }
        for caso, (texto, campo) in casos.items():
            with self.subTest(caso):
                self.escribir(texto, modulo_06({}))
                self.assertFallaSinBuscar(self.correr(), "PREF-UBICACION", campo)

    def test_sin_06_falla_con_un_mensaje_claro(self):
        self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])), None)
        self.assertFallaSinBuscar(self.correr(), "06_EMPRESAS_OBJETIVO.md")

    def test_con_el_catalogo_vacio_pide_agregar_empresas(self):
        self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])), modulo_06({}))
        self.assertFallaSinBuscar(self.correr(), "CAT-EMPRESAS", "/configurar", "paso 7")

    def test_una_empresa_que_no_esta_en_el_catalogo_falla_y_nombra_las_que_hay(self):
        self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])),
                      modulo_06({"EMP-ACME": ficha("EMP-ACME", {"plataforma": "workday", "portal": "https://x"})}))
        self.assertFallaSinBuscar(self.correr("EMP-OTRA"), "EMP-OTRA", "EMP-ACME")

    def test_una_ficha_sin_configuracion_usable_sale_como_fallo_sin_detener_las_demas(self):
        sin_bloque = "## EMP-SINBLOQUE — Empresa ficticia\n\n### Configuración\n\n«pendiente»\n"
        fichas = {
            "EMP-SINBLOQUE": sin_bloque,
            "EMP-ROTA": ficha("EMP-ROTA", '{"plataforma": "workday",}'),
            "EMP-SINPORTAL": ficha("EMP-SINPORTAL", {"plataforma": "workday"}),
            "EMP-OTRAPLATAFORMA": ficha("EMP-OTRAPLATAFORMA", {"plataforma": "inexistente", "portal": "https://x"}),
            "EMP-SINFICHA": "",
        }
        self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])), modulo_06(fichas))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        errores = {e["empresa_id"]: e["error"] for e in json.loads(r.stdout)["empresas"]}
        self.assertEqual(list(errores), list(fichas))
        for eid, texto in (("EMP-SINBLOQUE", "```json"), ("EMP-ROTA", "JSON"), ("EMP-SINPORTAL", "portal"),
                           ("EMP-OTRAPLATAFORMA", "workday"), ("EMP-SINFICHA", "## EMP-SINFICHA")):
            with self.subTest(eid):
                self.assertIn(f"[FALLO] {eid}: ", r.stderr)
                self.assertIn(texto, errores[eid])

    def test_solo_remoto_con_sin_remotas_falla_porque_no_habria_nada_que_buscar(self):
        self.escribir(modulo_04(preferencias([], alcance="cualquiera")),
                      modulo_06({"EMP-ACME": ficha("EMP-ACME", {"plataforma": "workday", "portal": "https://x"})}))
        self.assertFallaSinBuscar(self.correr("--sin-remotas"), "--sin-remotas", "remoto")

    def test_con_copia_lee_el_04_y_el_06_de_esa_carpeta_y_no_los_de_la_del_script(self):
        # La del script queda sin módulos: si los leyera de ahí, fallaría por el 04 que falta.
        otra = self.dir / "otra copia"
        otra.mkdir()
        (otra / "04_PREFERENCIAS_LABORALES.md").write_text(
            modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])), encoding="utf-8")
        (otra / "06_EMPRESAS_OBJETIVO.md").write_text(
            modulo_06({"EMP-ACME": ficha("EMP-ACME", {"plataforma": "workday", "portal": "https://x"})}),
            encoding="utf-8")
        self.assertFallaSinBuscar(self.correr("--copia", str(otra), "EMP-OTRA"), "EMP-OTRA", "EMP-ACME")

    def test_con_una_copia_que_no_existe_falla_y_la_nombra(self):
        self.assertFallaSinBuscar(self.correr("--copia", str(self.dir / "no existe")), "--copia", "no existe")

    def test_sin_la_tabla_de_paises_o_con_una_que_no_sirve_falla_con_un_mensaje_claro(self):
        tabla = self.dir / "herramientas" / "paises.json"
        casos = {"ausente": None, "JSON inválido": '{"XZ": ["Country Z"],}', "código en minúsculas": '{"xz": ["Z"]}',
                 "país sin nombres": '{"XZ": []}'}
        for caso, texto in casos.items():
            with self.subTest(caso):
                tabla.unlink(missing_ok=True)
                if texto is not None:
                    tabla.write_text(texto, encoding="utf-8")
                self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A1"])])), modulo_06({}))
                self.assertFallaSinBuscar(self.correr(), "paises.json", "tabla de países")

    def test_incluidas_fuera_de_un_grupo_de_division_completa_falla_y_dice_que_ahi_van_en_nombres(self):
        casos = {
            "grupo con nombres": grupo("XA", ["Estado A"], ["Ciudad A1"], incluidas=["Localidad A3"]),
            "grupo de país completo": grupo("XA", incluidas=["Localidad A3"]),
        }
        for caso, g in casos.items():
            with self.subTest(caso):
                self.escribir(modulo_04(preferencias([g])), modulo_06({}))
                self.assertFallaSinBuscar(self.correr(), "PREF-UBICACION", "incluidas", "nombres")

    def test_incluidas_que_no_es_una_lista_de_textos_falla(self):
        self.escribir(modulo_04(preferencias([{**grupo("XA", ["Estado A"]), "incluidas": "Localidad A3"}])),
                      modulo_06({}))
        self.assertFallaSinBuscar(self.correr(), "PREF-UBICACION", "incluidas")


class TablaDePaises(unittest.TestCase):
    """La tabla real de la plantilla. Solo su formato: las pruebas de la lógica usan una ficticia."""

    def test_cada_pais_tiene_su_codigo_alfa_2_y_nombres_que_no_repite_otro_pais(self):
        tabla = json.loads((RAIZ / "herramientas" / "paises.json").read_text(encoding="utf-8"))
        self.assertIsInstance(tabla, dict)
        self.assertGreater(len(tabla), 200)
        duenos = {}
        for codigo, nombres in tabla.items():
            with self.subTest(codigo):
                self.assertRegex(codigo, r"^[A-Z]{2}$")
                self.assertIsInstance(nombres, list)
                self.assertTrue(nombres)
                for n in nombres:
                    self.assertIsInstance(n, str)
                    self.assertTrue(n.strip())
                    # Como compara el script: sin mayúsculas ni acentos
                    sin_acentos = "".join(c for c in unicodedata.normalize("NFKD", n.casefold())
                                          if not unicodedata.combining(c))
                    duenos.setdefault(" ".join(sin_acentos.split()), set()).add(codigo)
        self.assertEqual({n: d for n, d in duenos.items() if len(d) > 1}, {})


class WorkdayFalso:
    """La API de Workday de un sitio ficticio: robots.txt, facetas y listado por facetas (POST) y detalle (GET).

    Cada anuncio es un dict con id, ubicaciones (la primera es la principal), pais y, si no es
    presencial, modalidad; con modalidad None no publica remoteType, ni en la faceta ni en el detalle.
    Como en Workday, los valores de faceta solo existen si algún anuncio los tiene, y parámetros
    distintos se combinan con «y»."""

    PLATAFORMA = "workday"
    HOST = "https://acme.wd1.myworkdayjobs.com"
    PORTAL = HOST + "/Acme"
    API = HOST + "/wday/cxs/acme/Acme"

    def __init__(self, anuncios, faceta_de_pais=True, faceta_de_remoto=True, extra_en_total=0,
                 robots="User-agent: *\nDisallow: /refreshFacet/\n"):
        self.anuncios = {f"/job/Lugar/Puesto_{a['id']}": a for a in anuncios}
        self.faceta_de_pais, self.faceta_de_remoto = faceta_de_pais, faceta_de_remoto
        self.extra_en_total, self.robots = extra_en_total, robots
        self.listados = []

    def valores(self, a):
        """{parámetro: descriptor} de las facetas de un anuncio."""
        v = {"locations": a["ubicaciones"][0]}
        if self.faceta_de_pais:
            v["Location_Country"] = a["pais"]
        if self.faceta_de_remoto and a.get("modalidad", "On-site") is not None:
            v["remoteType"] = a.get("modalidad", "On-site")
        return v

    def facetas(self):
        por_parametro = {}
        for a in self.anuncios.values():
            for p, d in self.valores(a).items():
                por_parametro.setdefault(p, {})[f"{p}:{d}"] = d

        def faceta(p):
            return {"facetParameter": p, "values": [{"descriptor": d, "id": i, "count": 1}
                                                    for i, d in por_parametro.get(p, {}).items()]}

        # Como en algunos sitios, «locations» viene anidada dentro de «locationMainGroup»
        return [faceta(p) for p in ("Location_Country", "remoteType") if p in por_parametro] + [
            {"facetParameter": "locationMainGroup", "values": [faceta("locations")]}]

    def __call__(self, url, cuerpo=None, intentos=3, como_json=True, extra=None):
        if url == self.HOST + "/robots.txt":
            return self.robots
        if url == self.API + "/jobs":
            aplicadas = cuerpo["appliedFacets"]
            if cuerpo["offset"] == 0 and cuerpo["limit"] > 1:
                self.listados.append(aplicadas)
            elegidos = [(ruta, a) for ruta, a in self.anuncios.items()
                        if all(f"{p}:{self.valores(a).get(p)}" in ids for p, ids in aplicadas.items())]
            pagina = elegidos[cuerpo["offset"]:cuerpo["offset"] + cuerpo["limit"]]
            return {"total": len(elegidos) + self.extra_en_total, "facets": self.facetas(), "jobPostings": [
                {"title": f"Puesto {a['id']}", "externalPath": ruta, "locationsText": a["ubicaciones"][0]}
                for ruta, a in pagina]}
        ruta = url.removeprefix(self.API)
        if ruta in self.anuncios:
            a = self.anuncios[ruta]
            return {"jobPostingInfo": {
                "jobReqId": a["id"], "title": f"Puesto {a['id']}", "location": a["ubicaciones"][0],
                "additionalLocations": a["ubicaciones"][1:], "remoteType": a.get("modalidad"),
                "startDate": "2026-10-01", "canApply": True, "externalUrl": self.PORTAL + ruta,
                "jobDescription": "<p>Descripción ficticia.</p>"}}
        raise AssertionError(f"petición inesperada: {url}")


OCTUBRE_1 = int(dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc).timestamp())  # 00:00 UTC


class EightfoldFalso:
    """La API pcsx de Eightfold de un sitio ficticio: robots.txt, listado (GET, 10 por página) y detalle (GET).

    Cada anuncio es un dict con id, ubicaciones, normalizadas (como standardizedLocations, que terminan en el
    código del país) y, si no es presencial, modalidad (workLocationOption). Como el buscador real, location
    busca por país solo con los nombres que reconoce, y ahí también trae las remotas abiertas a otros países
    (en_todas); «Remote» trae las remotas, y cualquier otro lugar, las que lo nombran, con un radio
    (distance). El filtro de modalidad solo existe si el sitio lo tiene."""

    PLATAFORMA = "eightfold"
    HOST = "https://empleos.acme.example"
    PORTAL = HOST + "/careers?domain=acme.example"
    # La forma de los sitios reales: todo prohibido salvo el buscador y su API
    ROBOTS = "User-agent: *\nDisallow: /\nAllow: /$\nAllow: /careers\nAllow: /api/pcsx\n"

    def __init__(self, anuncios, reconocidos=None, filtro_de_modalidad=True, extra_en_total=0, robots=ROBOTS,
                 orden="timestamp", sin_pcsx=False):
        self.anuncios = {9000 + i: a for i, a in enumerate(anuncios)}
        self.reconocidos = reconocidos if reconocidos is not None else {
            n: c for c, nombres in PAISES.items() for n in nombres}
        self.filtro_de_modalidad, self.extra_en_total, self.robots = filtro_de_modalidad, extra_en_total, robots
        self.orden, self.sin_pcsx = orden, sin_pcsx
        self.listados, self.detalles = [], []

    @staticmethod
    def codigos(a):
        return {s.rsplit(",", 1)[-1].strip() for s in a.get("normalizadas", [])}

    def elegir(self, q):
        """(IDs de los anuncios que trae la búsqueda, appliedFilters)."""
        elegidos, aplicados = list(self.anuncios), {}
        lugar = q.get("location", [None])[0]
        if lugar:
            aplicados = {"includeRemote": ["0"], "includeRelocation": ["0"]}
            if lugar in self.reconocidos:
                elegidos = [i for i in elegidos if self.reconocidos[lugar] in self.codigos(self.anuncios[i])
                            or self.anuncios[i].get("en_todas")]
            elif lugar == "Remote":
                aplicados["includeRemote"] = ["1"]
                elegidos = [i for i in elegidos if self.anuncios[i].get("modalidad") == "remote_local"]
            else:
                aplicados["distance"] = ["80"]
                elegidos = [i for i in elegidos
                            if any(lugar.lower() in u.lower() for u in self.anuncios[i]["ubicaciones"])]
        for p, valores in q.items():
            if p == "filter_work_location_option" and self.filtro_de_modalidad:
                elegidos = [i for i in elegidos if self.anuncios[i].get("modalidad", "onsite") in valores]
            elif p == "filter_job_family":
                elegidos = [i for i in elegidos if self.anuncios[i].get("familia", "").lower() in valores]
            elif p == "query":
                elegidos = [i for i in elegidos if valores[0].lower() in self.anuncios[i].get("titulo", "").lower()]
            elif p != "location":
                raise AssertionError(f"parámetro inesperado: {p}")
        return elegidos, aplicados

    def filtros(self):
        familias = sorted({a["familia"] for a in self.anuncios.values() if "familia" in a})
        filtros = [{"filterName": "job_family", "options": [{"label": f, "value": f.lower()} for f in familias]}]
        if self.filtro_de_modalidad:
            filtros.append({"filterName": "work_location_option", "options": [
                {"label": "On-site", "value": "onsite"}, {"label": "Hybrid", "value": "hybrid"},
                {"label": "Virtual", "value": "remote_local"}]})
        return filtros

    def posicion(self, i):
        a = self.anuncios[i]
        return {"id": i, "displayJobId": a["id"], "name": a.get("titulo", f"Puesto {a['id']}"),
                "locations": a["ubicaciones"], "standardizedLocations": a.get("normalizadas", []),
                "postedTs": a.get("ts", OCTUBRE_1), "department": a.get("familia"),
                "workLocationOption": a.get("modalidad", "onsite"), "locationFlexibility": None,
                "positionUrl": f"/careers/job/{i}"}

    def __call__(self, url, cuerpo=None, intentos=3, como_json=True, extra=None):
        if url == self.HOST + "/robots.txt":
            return self.robots
        ruta, _, consulta = url.partition("?")
        q = urllib.parse.parse_qs(consulta)
        if q.pop("domain", None) != ["acme.example"]:
            raise AssertionError(f"petición sin el dominio de la ficha: {url}")
        if ruta == self.HOST + "/api/pcsx/search":
            if self.sin_pcsx:
                raise self.script.Fallo(f"HTTP 403 en {url}", 403)
            if q.pop("sort_by", None) != ["timestamp"]:
                raise AssertionError(f"listado sin orden estable: {url}")
            inicio = int(q.pop("start")[0])
            if inicio == 0:
                self.listados.append(q)
            elegidos, aplicados = self.elegir(q)
            return {"status": 200, "data": {
                "positions": [self.posicion(i) for i in elegidos[inicio:inicio + 10]],
                "count": len(elegidos) + self.extra_en_total, "sortBy": self.orden, "appliedFilters": aplicados,
                "filterDef": {"allFilters": self.filtros()}}}
        if ruta == self.HOST + "/api/pcsx/position_details":
            i = int(q["position_id"][0])
            self.detalles.append(i)
            a = self.anuncios[i]
            return {"status": 200, "data": {
                "id": a.get("id_en_detalle", i), "jobDescription": "<p>Descripción ficticia.</p>",
                "positionUserActions": {"applyAction": {"status": a.get("estado", "allowed")}}}}
        raise AssertionError(f"petición inesperada: {url}")


class WorkableFalso:
    """La API de Workable de una cuenta ficticia: listado v3 (POST, 10 por página, con token) y detalle v2 (GET).

    Cada anuncio es un dict con id (shortcode), lugares [(ciudad, región, país, código)] y, si no es
    presencial, modalidad (workplace); remota (el booleano remote) sigue a la modalidad salvo que se dé. Como
    la API real, location filtra por código de país, y por ciudad o región si se dan, pero también trae las
    remotas abiertas a cualquier país (en_todas)."""

    PLATAFORMA = "workable"
    SITIO = "https://apply.workable.com"
    PORTAL = SITIO + "/acme/"
    LISTADO = SITIO + "/api/v3/accounts/acme/jobs"
    DETALLE = SITIO + "/api/v2/accounts/acme/jobs/"
    ROBOTS = "User-agent: *\nContent-Signal: search=yes, ai-input=yes, ai-train=no\nDisallow:\n"

    def __init__(self, anuncios, extra_en_total=0, robots=ROBOTS):
        self.anuncios = {a["id"]: a for a in anuncios}
        self.extra_en_total, self.robots = extra_en_total, robots
        self.listados, self.detalles = [], []

    @staticmethod
    def lugares(a):
        return [{"city": c, "region": r, "country": p, "countryCode": cc} for c, r, p, cc in a["lugares"]]

    @staticmethod
    def remota(a):
        return a.get("remota", a.get("modalidad") == "remote")

    def pasa(self, a, cuerpo):
        if cuerpo["remote"] and not self.remota(a):
            return False
        if cuerpo["location"] and not a.get("en_todas") and not any(
                all(lugar.get(k) == v for k, v in filtro.items())
                for filtro in cuerpo["location"] for lugar in self.lugares(a)):
            return False
        return cuerpo["query"].lower() in f"puesto {a['id']}".lower()

    def __call__(self, url, cuerpo=None, intentos=3, como_json=True, extra=None):
        if url == self.SITIO + "/robots.txt":
            return self.robots
        if url == self.LISTADO:
            if "token" not in cuerpo:
                self.listados.append({k: v for k, v in cuerpo.items() if v})
            elegidos = [a for a in self.anuncios.values() if self.pasa(a, cuerpo)]
            inicio = int(cuerpo.get("token", 0))
            pagina = elegidos[inicio:inicio + 10]
            # Como la API real, trae nextPage con cada página llena, aunque la siguiente salga vacía
            return {"total": len(elegidos) + self.extra_en_total, "results": [
                {"shortcode": a["id"], "title": f"Puesto {a['id']}", "locations": self.lugares(a),
                 "workplace": a.get("modalidad", "on_site"), "remote": self.remota(a),
                 "published": a.get("publicada", "2026-10-01T00:00:00.000Z")} for a in pagina],
                **({"nextPage": str(inicio + 10)} if len(pagina) == 10 else {})}
        if url.startswith(self.DETALLE):
            sc = url.removeprefix(self.DETALLE)
            self.detalles.append(sc)
            a = self.anuncios[sc]
            return {"shortcode": a.get("id_en_detalle", sc), "state": a.get("estado", "published"),
                    "department": ["Ingeniería"], "description": "<p>Descripción ficticia.</p>",
                    "requirements": "<p>Requisitos ficticios.</p>", "benefits": "<p></p>"}
        raise AssertionError(f"petición inesperada: {url}")


class SmartRecruitersFalso:
    """El sitio de carreras de SmartRecruiters de una empresa ficticia: robots.txt de sus tres hosts, listado
    agrupado (GET, HTML), «Show more» de cada grupo y página de cada publicación (GET, HTML).

    Cada publicación es un dict con id, lugar (como lo escribe el listado), los microdatos del detalle
    (detalle: localidad, región y país), modalidad (workplaceType), ref (la del listado) y ref_detalle (la
    jobRefCode de la página). Como el sitio real: agrupa por ubicación o por departamento; sin filtros, da tres
    grupos por página, y con un filtro, todos en cada página; un grupo de más de 10 muestra 9 y su «Show more»;
    el texto bajo el título es el lugar si el sitio no agrupa por ubicación, y el tipo de empleo si agrupa."""

    PLATAFORMA = "smartrecruiters"
    CARRERAS = "https://careers.smartrecruiters.com"
    PUBLICACIONES = "https://jobs.smartrecruiters.com"
    WWW = "https://www.smartrecruiters.com"
    PORTAL = CARRERAS + "/Acme"
    ROBOTS_WWW = "User-agent: *\nDisallow: /search/\nDisallow: /OtraEmpresa/*\n"

    def __init__(self, publicaciones, agrupar="location", extra_en_total=0, robots_www=ROBOTS_WWW):
        self.publicaciones = {p["id"]: p for p in publicaciones}
        self.agrupar, self.extra_en_total, self.robots_www = agrupar, extra_en_total, robots_www
        self.listados, self.completados, self.detalles = [], [], []

    def pasa(self, p, q):
        modalidad = p.get("modalidad", "on_site").replace("_", "").upper()
        texto = q.get("search", [""])[0].lower()
        return (q.get("locationType", [modalidad])[0] == modalidad
                and (texto in p["lugar"].lower() or texto in f"puesto {p['id']}".lower()))

    def grupos(self, q):
        """[(nombre, valor del «Show more», publicaciones)], en orden de nombre."""
        grupos = {}
        for p in self.publicaciones.values():
            if self.pasa(p, q):
                grupos.setdefault(p["lugar"] if self.agrupar == "location" else p["departamento"], []).append(p)
        return [(nombre, f"{nombre}, XX" if self.agrupar == "location" else str(i), pubs)
                for i, (nombre, pubs) in enumerate(sorted(grupos.items()))]

    def li(self, p):
        desc = "Full-time" if self.agrupar == "location" else p["lugar"]
        return (f'<li class="opening-job job column wide-7of16 medium-1of2"><a href="{self.PUBLICACIONES}/Acme/'
                f'{p["id"]}-puesto-{p["id"]}" aria-label="Puesto {p["id"]} - {p.get("ref") or "undefined"}" '
                f'class="link--block details js-job-ad-link"><h4 class="details-title job-title">Puesto {p["id"]}</h4>'
                f'<p class="details-desc job-desc"><span class="margin--right--s">{html.escape(desc)}</span></p>'
                "</a></li>")

    def seccion(self, i, nombre, valor, pubs):
        total = len(pubs) + (self.extra_en_total if i == 0 else 0)
        mas = (f'<li class="opening-job job column js-more-container"><ul class="list--dotted"><li><a data-page="0" '
               f'data-value="{urllib.parse.quote(valor)}" data-type="{self.agrupar}" data-more="/Acme/api/more" '
               f'href="?search=&amp;page=0" class="link details-desc js-more">Show more jobs</a></li></ul></li>')
        return (f'<section data-qty="{total}" class="openings-section opening opening--grouped js-group"><header '
                f'class="opening-header"><ul class="list--dotted title-list"><li><h3 class="opening-title title">'
                f'{html.escape(nombre)}</h3></li><li><span class="title">{total} jobs</span></li></ul></header><ul '
                f'class="opening-jobs js-group-list">' + "".join(self.li(p) for p in (pubs[:9] if total > 10 else pubs))
                + (mas if total > 10 else "") + "</ul></section>")

    def detalle(self, p):
        localidad, region, pais = p["detalle"]
        ref = f"\n  'jobRefCode': '{p['ref_detalle']}'," if p.get("ref_detalle") else ""
        return (f'<html><head><link href="{self.PUBLICACIONES}/Acme/{p.get("id_en_detalle", p["id"])}-puesto" '
                f"rel=\"canonical\"><script>gtmDataLayer.push({{\n  'postingId': '{p['id']}',{ref}\n}});</script>"
                "</head>"
                f'<body><span itemprop="addressLocality" content="{localidad}"></span><span itemprop="addressRegion" '
                f'content="{region}"></span><span itemprop="addressCountry" content="{pais}"></span><meta '
                f'itemprop="datePosted" content="{p.get("publicada", "2026-10-01T00:00:00.000Z")}"><spl-job-location '
                f'formattedAddress="{localidad}, {pais}" workplaceDescription="" '
                f'workplaceType="{p.get("modalidad", "on_site")}"></spl-job-location>'
                f'<li class="job-detail">Department: Ingeniería</li><section class="job-section" '
                f'id="st-companyDescription"><p>Empresa ficticia.</p></section><section class="job-section" '
                f'id="st-jobDescription"><p>Descripción ficticia.</p></section><section class="job-section" '
                f'id="st-qualifications"><p>Requisitos ficticios.</p></section>'
                + ('<button data-sr-track="apply">I\'m interested</button>' if p.get("abierta", True) else "")
                + "</body></html>")

    def __call__(self, url, cuerpo=None, intentos=3, como_json=True, extra=None):
        if url == self.CARRERAS + "/robots.txt":
            # Como el real: redirige a una página que no es un robots.txt
            return "<!DOCTYPE html>\n<html><head><title>Job Search</title></head><body>Busca empleo</body></html>"
        if url == self.PUBLICACIONES + "/robots.txt":
            raise self.script.Fallo(f"HTTP 404 en {url}", 404)
        if url == self.WWW + "/robots.txt":
            return self.robots_www
        ruta, _, consulta = url.partition("?")
        q = urllib.parse.parse_qs(consulta)
        pagina = int(q.pop("page", ["0"])[0])
        if ruta == self.CARRERAS + "/Acme/api/groups":
            if pagina == 0:
                self.listados.append(q)
            grupos = list(enumerate(self.grupos(q)))
            # Sin filtros, el sitio reparte los grupos en páginas; con un filtro, los repite todos en cada página
            return "".join(self.seccion(i, *g) for i, g in (grupos if q else grupos[3 * pagina:3 * pagina + 3]))
        if ruta == self.CARRERAS + "/Acme/api/more":
            tipo, valor = q.pop("type")[0], q.pop("value")[0]
            if pagina == 0:
                self.completados.append(valor)
            pubs = next(g[2] for g in self.grupos(q) if g[1] == valor and tipo == self.agrupar)
            # La página 0 repite las 9 que ya muestra el grupo; las siguientes traen 10
            inicio = 0 if pagina == 0 else 9 + 10 * (pagina - 1)
            return "".join(self.li(p) for p in pubs[inicio:9 if pagina == 0 else inicio + 10])
        if ruta.startswith(self.PUBLICACIONES + "/Acme/"):
            pid = ruta.rsplit("/", 1)[1].split("-")[0]
            self.detalles.append(pid)
            return self.detalle(self.publicaciones[pid])
        raise AssertionError(f"petición inesperada: {url}")


class OracleFalso:
    """La API REST de Oracle Recruiting Cloud de un sitio ficticio: robots.txt, listado con el finder findReqs (GET,
    25 por página) y detalle con ById (GET).

    Cada requisición es un dict con id, lugares [(nombre, código)] (el primero es el principal), modalidad
    (WorkplaceType; Onsite si no se da) y familia. Como la API real, location filtra por país solo con los nombres
    que reconoce, y con otro no filtra; un país cuenta también por sus ubicaciones secundarias. Las facetas solo
    traen los valores que tiene alguna requisición del resultado. extra_en_total: requisiciones que el total y la
    faceta de ubicaciones cuentan, pero que el listado no trae."""

    PLATAFORMA = "oraclerecruitingcloud"
    HOST = "https://acme.fa.xx1.oraclecloud.com"
    PORTAL = HOST + "/hcmUI/CandidateExperience/en/sites/CX_1"
    API = HOST + "/hcmRestApi/resources/latest"
    MODALIDADES = {"Onsite": "ORA_ON_SITE", "Hybrid": "ORA_HYBRID", "Remote": "ORA_REMOTE"}

    def __init__(self, requisiciones, reconocidos=None, extra_en_total=0, robots=None):
        self.requisiciones = {r["id"]: r for r in requisiciones}
        self.reconocidos = reconocidos if reconocidos is not None else {PAISES[c][1]: c for c in PAISES}
        self.extra_en_total, self.robots = extra_en_total, robots
        self.listados, self.detalles = [], []

    @staticmethod
    def finder(url):
        """{parámetro: valor} del finder de la URL, con su nombre en «finder»."""
        nombre, _, parametros = url.split("finder=", 1)[1].partition(";")
        return {"finder": nombre, **{k: urllib.parse.unquote(v) for k, _, v in
                                     (p.partition("=") for p in parametros.split(","))}}

    def elegir(self, f):
        elegidas = list(self.requisiciones.values())
        codigo = self.reconocidos.get(f.get("location"))
        if codigo:
            elegidas = [r for r in elegidas if codigo in {c for _, c in r["lugares"]}]
        if "selectedWorkplaceTypesFacet" in f:
            pedidas = f["selectedWorkplaceTypesFacet"].split(";")
            elegidas = [r for r in elegidas if self.MODALIDADES[r.get("modalidad", "Onsite")] in pedidas]
        if "selectedCategoriesFacet" in f:
            elegidas = [r for r in elegidas if f"CAT-{r.get('familia')}" in f["selectedCategoriesFacet"].split(";")]
        if "keyword" in f:
            elegidas = [r for r in elegidas if f["keyword"].lower() in f"puesto {r['id']}".lower()]
        return elegidas

    def facetas(self, elegidas):
        nombres = {c: n for n, c in self.reconocidos.items()}

        def cuenta(valores, extra=0):
            return [{"Id": i, "Name": n, "TotalCount": valores.count((i, n)) + extra}
                    for i, n in dict.fromkeys(valores)]

        return {"locationsFacet": cuenta([(f"LOC-{c}", nombres.get(c, c)) for r in elegidas for c in
                                          dict.fromkeys(c for _, c in r["lugares"])], self.extra_en_total),
                "workplaceTypesFacet": cuenta([(self.MODALIDADES[m], m) for m in
                                               (r.get("modalidad", "Onsite") for r in elegidas)]),
                "categoriesFacet": cuenta([(f"CAT-{r['familia']}", r["familia"]) for r in elegidas if "familia" in r])}

    def requisicion(self, r):
        (principal, codigo), secundarias = r["lugares"][0], r["lugares"][1:]
        return {"Id": r["id"], "Title": f"Puesto {r['id']}", "PostedDate": "2026-10-01", "PrimaryLocation": principal,
                "PrimaryLocationCountry": codigo, "WorkplaceType": r.get("modalidad", "Onsite"),
                "WorkplaceTypeCode": self.MODALIDADES[r.get("modalidad", "Onsite")], "JobFunction": r.get("familia"),
                "secondaryLocations": [{"Name": n, "CountryCode": c} for n, c in secundarias]}

    def __call__(self, url, cuerpo=None, intentos=3, como_json=True, extra=None):
        if url == self.HOST + "/robots.txt":
            if self.robots is None:
                raise self.script.Fallo(f"HTTP 404 en {url}", 404)
            return self.robots
        if url.startswith(self.API + "/recruitingCEJobRequisitions?"):
            f = self.finder(url)
            if (f["finder"], f["siteNumber"], f["sortBy"]) != ("findReqs", "CX_1", "POSTING_DATES_DESC"):
                raise AssertionError(f"listado sin el sitio o el orden de la ficha: {url}")
            inicio, limite = int(f.pop("offset")), int(f["limit"])
            if inicio == 0:
                self.listados.append({k: v for k, v in f.items()
                                      if k not in ("finder", "siteNumber", "sortBy", "limit", "facetsList")})
            elegidas = self.elegir(f)
            return {"items": [{"TotalJobsCount": len(elegidas) + self.extra_en_total,
                               "requisitionList": [self.requisicion(r) for r in elegidas[inicio:inicio + limite]],
                               **self.facetas(elegidas)}]}
        if url.startswith(self.API + "/recruitingCEJobRequisitionDetails?"):
            f = self.finder(url)
            rid = f["Id"].strip('"')
            self.detalles.append(rid)
            r = self.requisiciones[rid]
            return {"items": [{"Id": r.get("id_en_detalle", rid), "Title": f"Puesto {rid}",
                               "ExternalPostedStartDate": r.get("publicada", "2026-10-01T00:00:00+00:00"),
                               "ExternalPostedEndDate": r.get("cierre"), "WorkplaceType": r.get("modalidad", "Onsite"),
                               "JobFunction": r.get("familia"),
                               "ExternalDescriptionStr": "<p>Descripción ficticia.</p>",
                               "ExternalResponsibilitiesStr": "<ul><li>Responsabilidad ficticia.</li></ul>",
                               "ExternalQualificationsStr": None}]}
        raise AssertionError(f"petición inesperada: {url}")


CAMPOS_DE_VACANTES_Y_OBSERVACIONES = {"empresa_id", "job_id", "titulo", "url_oficial", "ubicacion_literal",
                                      "modalidad_literal", "region_relacionada", "fecha_publicacion",
                                      "estado_vigencia", "motivo", "url_fuente"}


class ConPortalFalso(CopiaFicticia):
    def buscar(self, bloque_04, portal, *argumentos, consulta=None, codigo_esperado=0, red=None, nube=False):
        """Corre main() del script de la copia con el portal falso en lugar de la red. Con red, el portal solo da la
        configuración: la red falsa reemplaza urllib.request.urlopen, las esperas entre intentos se anotan en
        self.esperas sin esperar, y se ejercita el pedir() real. nube: corre como Code en la nube
        (CLAUDE_CODE_REMOTE=true); si no, sin la variable."""
        configuracion = {"plataforma": portal.PLATAFORMA, "portal": portal.PORTAL, "consulta": consulta}
        self.escribir(modulo_04(bloque_04), modulo_06({"EMP-ACME": ficha("EMP-ACME", configuracion)}))
        especificacion = importlib.util.spec_from_file_location("buscar_copia", self.dir / "herramientas" / "buscar.py")
        script = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(script)
        self.esperas = []
        if red is None:
            script.pedir = portal
            portal.script = script  # para que el portal falso responda con los errores del script
            sustituir = contextlib.nullcontext()
        else:
            sustituir = contextlib.ExitStack()
            sustituir.enter_context(mock.patch.object(script.urllib.request, "urlopen", red))
            sustituir.enter_context(mock.patch.object(script.time, "sleep", self.esperas.append))
        entorno = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
        if nube:
            entorno["CLAUDE_CODE_REMOTE"] = "true"
        salida, errores, codigo = io.StringIO(), io.StringIO(), 0
        with mock.patch.object(sys, "argv", ["buscar.py", *argumentos]), sustituir, \
                mock.patch.dict(os.environ, entorno, clear=True), \
                contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            try:
                script.main()
            except SystemExit as e:
                codigo = e.code
        self.assertEqual(codigo, codigo_esperado, errores.getvalue())
        self.assertNotIn("Traceback", errores.getvalue())
        return json.loads(salida.getvalue())["empresas"][0], errores.getvalue()

    def regiones(self, r, lista="vacantes"):
        return {v["job_id"]: v["region_relacionada"] for v in r[lista]}

    def listados(self, portal):
        """Las facetas de cada listado que pidió el script, con los IDs ordenados."""
        return [{p: sorted(ids) for p, ids in aplicadas.items()} for aplicadas in portal.listados]


class ClasificacionDeUbicaciones(ConPortalFalso):
    def test_varias_ciudades_de_una_zona_metropolitana(self):
        bloque = preferencias([grupo("XA", ["Estado A", "Edo. A"], ["Ciudad A", "Municipio A2", "Municipio A3"])])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A, Estado A, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Municipio A3"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["MUNICIPIO A2, estado a"]},
            {"id": "R-4", "pais": "País A", "ubicaciones": ["Municipio A9, Edo. A, País A"]},
            {"id": "R-5", "pais": "País A", "ubicaciones": ["Ciudad A, Estado A, País A", "Ciudad B1, País B"]},
            {"id": "R-6", "pais": "País A", "ubicaciones": ["Ciudad Alta, Estado A5, País A"]},
            {"id": "R-7", "pais": "País B", "ubicaciones": ["Ciudad B1, País B"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(portal.listados, [{"Location_Country": ["Location_Country:País A"]}])
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (6, 6, True))
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-2": "Dentro", "R-3": "Dentro",
                                            "R-4": "Indeterminada", "R-5": "Incluye"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad Alta, Estado A5, País A"])
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]}
        self.assertEqual(revisar["R-4"], ["Municipio A9, Edo. A, País A"])
        for v in r["vacantes"]:
            self.assertLessEqual(CAMPOS_DE_VACANTES_Y_OBSERVACIONES, set(v))
            self.assertEqual(v["estado_vigencia"], "Confirmada abierta")
        self.assertIn("[OK] EMP-ACME: 6/6 únicos; 4 en la región", errores)
        self.assertIn("revisar ubicación: Municipio A9, Edo. A, País A (1 vacante: R-4)", errores)

    def test_las_vacantes_con_la_misma_ubicacion_por_revisar_dan_una_sola_linea(self):
        bloque = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])])
        portal = WorkdayFalso(
            [{"id": f"R-{i}", "pais": "País A", "ubicaciones": ["Ciudad A9, Estado A, País A"]} for i in range(1, 6)]
            + [{"id": "R-6", "pais": "País A", "ubicaciones": ["Ciudad A8, Estado A, País A"]},
               {"id": "R-7", "pais": "País A", "ubicaciones": ["Ciudad A8, Estado A, País A"]},
               {"id": "R-8", "pais": "País A", "ubicaciones": ["Ciudad A1, Estado A, País A"]},
               # Con dos ubicaciones por revisar, sale en las dos líneas
               {"id": "R-9", "pais": "País A",
                "ubicaciones": ["Ciudad A9, Estado A, País A", "Ciudad A8, Estado A, País A"]}])
        r, errores = self.buscar(bloque, portal)
        # El JSON no cambia: cada vacante lleva su ubicación por revisar
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]}
        self.assertEqual(revisar, {**{f"R-{i}": ["Ciudad A9, Estado A, País A"] for i in range(1, 6)},
                                   "R-6": ["Ciudad A8, Estado A, País A"], "R-7": ["Ciudad A8, Estado A, País A"],
                                   "R-8": [], "R-9": ["Ciudad A9, Estado A, País A", "Ciudad A8, Estado A, País A"]})
        lineas = [linea.strip() for linea in errores.splitlines() if "revisar ubicación:" in linea]
        self.assertEqual(lineas, [
            "revisar ubicación: Ciudad A9, Estado A, País A (6 vacantes: R-1, R-2, R-3, R-4, R-5, R-9)",
            "revisar ubicación: Ciudad A8, Estado A, País A (3 vacantes: R-6, R-7, R-9)"])

    def test_una_ubicacion_que_solo_nombra_el_pais_queda_por_revisar(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"]), grupo("XB", divisiones=["Provincia B1"])])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A1, País A", "Country A"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["Multiple Locations"]},
            {"id": "R-4", "pais": "País B", "ubicaciones": ["Country B"]},
            {"id": "R-5", "pais": "País B", "ubicaciones": ["Ciudad B9, Provincia B1, País B"]},
            {"id": "R-6", "pais": "País B", "ubicaciones": ["Ciudad B9, Provincia B2, País B"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Indeterminada", "R-2": "Incluye", "R-3": "Indeterminada",
                                            "R-4": "Indeterminada", "R-5": "Dentro"})
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]}
        self.assertEqual(revisar, {"R-1": ["País A"], "R-2": ["Country A"], "R-3": ["Multiple Locations"],
                                   "R-4": ["Country B"], "R-5": []})
        self.assertEqual(r["fuera_de_region"], ["Ciudad B9, Provincia B2, País B"])
        for lugar, job_id in (("País A", "R-1"), ("Country A", "R-2"), ("Multiple Locations", "R-3"),
                              ("Country B", "R-4")):
            self.assertIn(f"revisar ubicación: {lugar} (1 vacante: {job_id})", errores)
        self.assertFalse([linea for linea in errores.splitlines()
                          if "revisar ubicación:" in linea and "R-5" in linea])

    def test_varios_paises_con_remoto_desde_algunos(self):
        bloque = preferencias([grupo("XA"), grupo("XB", divisiones=["Provincia B1"])],
                              alcance="paises", paises_remoto=["XA", "XC"])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A7, País A"]},
            {"id": "R-2", "pais": "País B", "ubicaciones": ["Ciudad B9, Provincia B1, País B"]},
            {"id": "R-3", "pais": "País B", "ubicaciones": ["Ciudad B9, Provincia B2, País B"]},
            {"id": "R-4", "pais": "País C", "ubicaciones": ["Ciudad C1, País C"], "modalidad": "Remote"},
            {"id": "R-5", "pais": "País C", "ubicaciones": ["Ciudad C2, País C"]},
            {"id": "R-6", "pais": "País D", "ubicaciones": ["Ciudad D1, País D"], "modalidad": "Remote"},
            {"id": "R-7", "pais": "País A", "ubicaciones": ["Ciudad A8, País A"], "modalidad": "Remote"},
            {"id": "R-8", "pais": "País B", "ubicaciones": ["Ciudad B8, Provincia B3, País B"], "modalidad": "Remote"},
            # Otro lugar que contiene el nombre del país completo
            {"id": "R-9", "pais": "País A", "ubicaciones": ["Nuevo País A - Ciudad N1"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.listados(portal), [
            {"Location_Country": ["Location_Country:País A", "Location_Country:País B"]},
            {"remoteType": ["remoteType:Remote"], "Location_Country": ["Location_Country:País A",
                                                                       "Location_Country:País C"]},
        ])
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-2": "Dentro", "R-7": "Dentro"})
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"R-4": "Fuera"})
        # R-8 es remota, pero de un país que 04 no acepta para el remoto
        self.assertEqual(sorted(r["fuera_de_region"]), ["Ciudad B8, Provincia B3, País B",
                                                        "Ciudad B9, Provincia B2, País B", "Nuevo País A - Ciudad N1"])
        # R-7 sale en los dos listados y cuenta una vez
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (7, 7, True))
        self.assertIn("remoteType", r["remotas_revision"])
        self.assertIn("[OK] EMP-ACME: 7/7 únicos; 3 en la región; remotas fuera de la región: 1", errores)

    def test_solo_remoto_desde_cualquier_pais_lista_solo_las_remotas(self):
        anuncios = [
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Remote - Ciudad A2, País A"], "modalidad": "Remote"},
            {"id": "R-3", "pais": "País D", "ubicaciones": ["Remote"], "modalidad": "Remote"},
            {"id": "R-4", "pais": "País D", "ubicaciones": ["Ciudad D1, País D"], "modalidad": "Hybrid"},
        ]
        filtros = {
            "faceta de remoto": (True, [{"remoteType": ["remoteType:Remote"]}]),
            # Sin faceta de remoto, el portal marca las remotas en sus ubicaciones «Remote …»
            "ubicaciones «Remote»": (False, [{"locations": ["locations:Remote",
                                                            "locations:Remote - Ciudad A2, País A"]}]),
        }
        for caso, (faceta_de_remoto, esperados) in filtros.items():
            with self.subTest(caso):
                portal = WorkdayFalso(anuncios, faceta_de_remoto=faceta_de_remoto)
                r, errores = self.buscar(preferencias([], alcance="cualquiera"), portal)
                self.assertEqual(self.listados(portal), esperados)
                self.assertEqual(self.regiones(r), {"R-3": "Indeterminada"})
                self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"R-2": "Fuera"})
                self.assertIn("[OK] EMP-ACME: 2/2 únicos; 0 en la región; remotas fuera de la región: 1", errores)

    def test_sin_modalidad_publicada_una_ubicacion_remota_cuenta_como_remota(self):
        bloque = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])], alcance="paises", paises_remoto=["XA"])
        portal = WorkdayFalso([
            # Sin remoteType: la faceta de remoto no las trae, solo el listado de la región
            {"id": "R-1", "pais": "País A", "ubicaciones": ["País A (Remote)"], "modalidad": None},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A7, País A (Remote)"], "modalidad": None},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]},
            # Por revisar en la región porque nombra la división sin una localidad aceptada, pero ya es remota en el
            # alcance
            {"id": "R-4", "pais": "País A", "ubicaciones": ["Ciudad X, Estado A, País A (Remote)"], "modalidad": None},
            # Para que el portal tenga faceta de remoto: su listado, acotado a XA, no la trae
            {"id": "R-9", "pais": "País C", "ubicaciones": ["Ciudad C1, País C"], "modalidad": "Remote"},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Indeterminada", "R-3": "Dentro", "R-4": "Indeterminada"})
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"R-2": "Fuera"})
        self.assertEqual({v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]},
                         {"R-1": [], "R-3": [], "R-4": []})
        self.assertEqual(r["remotas_fuera_de_region"][0]["ubicaciones_por_revisar"], [])
        self.assertEqual(r["fuera_de_region"], [])
        self.assertNotIn("revisar ubicación", errores)
        self.assertNotIn("revisar:", errores)

    def test_si_la_modalidad_publicada_contradice_la_ubicacion_gana_la_modalidad(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="paises", paises_remoto=["XA"])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["País A (Remote)"], "modalidad": "On-site"},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A7, País A (Remote)"], "modalidad": "On-site"},
            # Para que el portal tenga faceta de remoto: su listado, acotado a XA, no la trae
            {"id": "R-9", "pais": "País C", "ubicaciones": ["Ciudad C1, País C"], "modalidad": "Remote"},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Indeterminada"})
        self.assertEqual(r["vacantes"][0]["ubicaciones_por_revisar"], ["País A (Remote)"])
        self.assertEqual(r["remotas_fuera_de_region"], [])
        self.assertEqual(r["fuera_de_region"], ["Ciudad A7, País A (Remote)"])
        self.assertIn("revisar ubicación: País A (Remote) (1 vacante: R-1)", errores)
        self.assertIn("revisar: R-1 la modalidad publicada («On-site») contradice la ubicación («País A (Remote)»)",
                      errores)

    def test_sin_remoto_en_04_una_ubicacion_remota_no_cuenta_como_remota_en_el_alcance(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="ninguno")
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["País A (Remote)"], "modalidad": None},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A7, País A (Remote)"], "modalidad": None},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Indeterminada"})
        self.assertEqual(r["vacantes"][0]["ubicaciones_por_revisar"], ["País A (Remote)"])
        self.assertEqual(r["remotas_fuera_de_region"], [])
        self.assertEqual(r["fuera_de_region"], ["Ciudad A7, País A (Remote)"])
        self.assertIn("revisar ubicación: País A (Remote) (1 vacante: R-1)", errores)

    def test_una_ciudad_homonima_en_otro_pais_de_04_queda_fuera(self):
        bloque = preferencias([grupo("XA", ["Provincia A1"], ["Ciudad A1"]), grupo("XB", ["Provincia B1"])])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A1, País C"]},
            {"id": "R-3", "pais": "País B", "ubicaciones": ["Ciudad B1, Provincia A1, País B"]},
            {"id": "R-4", "pais": "País B", "ubicaciones": ["Ciudad B2, Provincia B1"]},
        ])
        r, _ = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-4": "Dentro"})
        self.assertEqual(sorted(r["fuera_de_region"]), ["Ciudad A1, País C", "Ciudad B1, Provincia A1, País B"])

    def test_una_ciudad_homonima_de_su_division_solo_cuenta_en_el_lugar_de_la_localidad(self):
        bloque = preferencias([grupo("XA", ["Estado A", "Valle de A"], ["Estado A", "Valle de A"])],
                              paises={**PAISES, "XA": ["País A", "XAA"]})
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Estado A, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Estado A, Estado A, País A"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["Ciudad X, Estado A, País A"]},
            {"id": "R-4", "pais": "País A", "ubicaciones": ["XAA.Estado A"]},
            # Con una palabra general en el nombre
            {"id": "R-5", "pais": "País A", "ubicaciones": ["Valle de A, País A"]},
            # Otro lugar que contiene el nombre no es la localidad
            {"id": "R-6", "pais": "País A", "ubicaciones": ["Nuevo Estado A, País A"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-2": "Dentro", "R-3": "Indeterminada",
                                            "R-4": "Dentro", "R-5": "Dentro", "R-6": "Indeterminada"})
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]}
        self.assertEqual(revisar["R-3"], ["Ciudad X, Estado A, País A"])
        self.assertEqual(revisar["R-6"], ["Nuevo Estado A, País A"])
        self.assertIn("revisar ubicación: Ciudad X, Estado A, País A (1 vacante: R-3)", errores)

    def test_un_grupo_de_division_completa_revisa_la_localidad_que_no_escribe_su_division(self):
        bloque = preferencias([grupo("XA", ["Estado A"])], paises={**PAISES, "XA": ["País A", "XAA"]})
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Localidad A3, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Localidad A3, País A"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["XAA.Localidad A4"]},
            # Otra parte entre la localidad y el país es otra división
            {"id": "R-4", "pais": "País A", "ubicaciones": ["Localidad Z, Estado Z, País A"]},
            {"id": "R-5", "pais": "País A", "ubicaciones": ["Localidad A5, Estado A, País A"]},
            # Workday no da el país de cada vacante: sin el país en la ubicación no hay red de seguridad
            {"id": "R-6", "pais": "País A", "ubicaciones": ["Localidad A6"]},
            # Lo que no está entre la localidad y el país, o es solo un número, no es otra división
            {"id": "R-7", "pais": "País A", "ubicaciones": ["Localidad A7, País A (Edificio 1)"]},
            {"id": "R-8", "pais": "País A", "ubicaciones": ["Localidad A8, 12345, País A"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Indeterminada", "R-2": "Indeterminada", "R-3": "Indeterminada",
                                            "R-5": "Dentro", "R-7": "Indeterminada", "R-8": "Indeterminada"})
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["vacantes"]}
        self.assertEqual(revisar, {"R-1": ["Localidad A3, País A"], "R-2": ["Localidad A3, País A"],
                                   "R-3": ["XAA.Localidad A4"], "R-5": [],
                                   "R-7": ["Localidad A7, País A (Edificio 1)"], "R-8": ["Localidad A8, 12345, País A"]})
        self.assertEqual(sorted(r["fuera_de_region"]), ["Localidad A6", "Localidad Z, Estado Z, País A"])
        self.assertIn("revisar ubicación: Localidad A3, País A (2 vacantes: R-1, R-2)", errores)
        self.assertIn("revisar ubicación: XAA.Localidad A4 (1 vacante: R-3)", errores)

    def test_una_localidad_de_incluidas_sale_dentro_aunque_no_escriba_su_division(self):
        bloque = preferencias([grupo("XA", ["Estado A"], incluidas=["Localidad A3", "Localidad Ä4"]),
                               grupo("XB", nombres=["Ciudad B1"])],
                              paises={**PAISES, "XA": ["País A", "XAA"]})
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Localidad A3, País A"]},
            # Se compara como nombres: sin mayúsculas ni acentos
            {"id": "R-2", "pais": "País A", "ubicaciones": ["XAA.LOCALIDAD A4"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["Localidad A9, País A"]},
            # En otro país de 04, la localidad homónima no es del grupo
            {"id": "R-4", "pais": "País B", "ubicaciones": ["Localidad A3, País B"]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-2": "Dentro", "R-3": "Indeterminada"})
        self.assertEqual(r["fuera_de_region"], ["Localidad A3, País B"])
        self.assertNotIn("Localidad A3, País A", errores)

    def test_un_grupo_sin_incluidas_sigue_siendo_valido(self):
        sin_campo = {"pais": "XA", "divisiones": ["Estado A"], "zona": None, "nombres": []}
        portal = WorkdayFalso([{"id": "R-1", "pais": "País A", "ubicaciones": ["Localidad A5, Estado A, País A"]}])
        r, _ = self.buscar(preferencias([sin_campo]), portal)
        self.assertEqual(self.regiones(r), {"R-1": "Dentro"})

    def test_avisa_por_cada_pais_de_la_region_que_el_portal_no_ofrece(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"]), grupo("XB", nombres=["Ciudad B1"])])
        portal = WorkdayFalso([{"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]}])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.listados(portal), [{"Location_Country": ["Location_Country:País A"]}])
        self.assertEqual(self.regiones(r), {"R-1": "Dentro"})
        self.assertIn("revisar: el portal no ofrece XB", errores)
        self.assertNotIn("no ofrece XA", errores)

    def test_sin_faceta_de_pais_se_lista_por_las_ubicaciones_que_nombran_el_pais_como_una_parte(self):
        # Los portales escriben «País - Ciudad», «Ciudad, País (Edificio)» o «Remote - País»; «Nuevo País A»
        # es otro lugar aunque contenga «País A».
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["País A - Ciudad A1"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A9, País A (Edificio 1)"]},
            {"id": "R-3", "pais": "País A", "ubicaciones": ["País A - Remote"], "modalidad": "Remote"},
            {"id": "R-4", "pais": "País A", "ubicaciones": ["Remote - País A"], "modalidad": "Remote"},
            {"id": "R-5", "pais": "País N", "ubicaciones": ["Nuevo País A - Remote"], "modalidad": "Remote"},
            {"id": "R-6", "pais": "País N", "ubicaciones": ["Nuevo País A - Ciudad N1"]},
        ], faceta_de_pais=False, faceta_de_remoto=False)
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="paises", paises_remoto=["XA"])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.listados(portal), [
            {"locations": ["locations:Ciudad A9, País A (Edificio 1)", "locations:País A - Ciudad A1",
                           "locations:País A - Remote", "locations:Remote - País A"]},
            {"locations": ["locations:País A - Remote", "locations:Remote - País A"]},
        ])
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-3": "Indeterminada", "R-4": "Indeterminada"})

    def test_una_ubicacion_codigo_punto_ciudad_nombra_el_pais_del_codigo(self):
        # Algunos sitios de Workday escriben «MEX.Ciudad»; el código va entre los nombres del país en 04, y un
        # punto entre abreviaturas («U.S.A.») no separa partes
        paises = {**PAISES, "XA": ["País A", "XAA"], "XB": ["P.A.Í.S. B"]}
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["XAA.Ciudad A7"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["XAA.Remote"], "modalidad": "Remote"},
            {"id": "R-3", "pais": "País B", "ubicaciones": ["Ciudad B1, P.A.Í.S. B"]},
            {"id": "R-4", "pais": "País C", "ubicaciones": ["XCC.Ciudad C1"]},
        ], faceta_de_pais=False, faceta_de_remoto=False)
        bloque = preferencias([grupo("XA"), grupo("XB")], alcance="paises", paises_remoto=["XA"], paises=paises)
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.listados(portal), [
            {"locations": ["locations:Ciudad B1, P.A.Í.S. B", "locations:XAA.Ciudad A7", "locations:XAA.Remote"]},
            {"locations": ["locations:XAA.Remote"]},
        ])
        self.assertEqual(self.regiones(r), {"R-1": "Dentro", "R-2": "Dentro", "R-3": "Dentro"})
        self.assertNotIn("no ofrece", errores)


class ConsultaDeLaFicha(ConPortalFalso):
    def test_la_consulta_de_la_ficha_reemplaza_el_listado_por_paises(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A"])])
        portal = WorkdayFalso([
            {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A, País A"]},
            {"id": "R-2", "pais": "País A", "ubicaciones": ["Ciudad A9, País A"]},
        ])
        consulta = {"facetas": {"locations": ["ciudad a, pais a", "Ciudad Inexistente"]}, "texto": ""}
        r, errores = self.buscar(bloque, portal, consulta=consulta)
        self.assertEqual(portal.listados, [{"locations": ["locations:Ciudad A, País A"]}])
        self.assertEqual(self.regiones(r), {"R-1": "Dentro"})
        self.assertIn("revisar: la faceta locations no ofrece «Ciudad Inexistente»", errores)

    def test_una_consulta_sin_valores_que_el_portal_ofrezca_no_lista_nada(self):
        portal = WorkdayFalso([{"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A, País A"]}])
        consulta = {"facetas": {"locations": ["Ciudad Inexistente"]}}
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A"])]), portal, consulta=consulta)
        self.assertEqual(portal.listados, [])
        self.assertEqual((r["total_reportado"], r["vacantes"]), (0, []))
        self.assertIn("revisar: la faceta locations no ofrece «Ciudad Inexistente»", errores)

    def test_una_consulta_mal_formada_sale_como_fallo(self):
        portal = WorkdayFalso([{"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A, País A"]}])
        for consulta in ({}, {"facetas": {"locations": "Ciudad A"}}, {"texto": 5}, {"filtro": "x"}):
            with self.subTest(consulta=consulta):
                r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A"])]), portal,
                                         consulta=consulta, codigo_esperado=1)
                self.assertIn("consulta", r["error"])
                self.assertIn("06/CAT-PLATAFORMAS", r["error"])
        self.assertEqual(portal.listados, [])


class ComprobacionesDeWorkday(ConPortalFalso):
    EN_XA = [{"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A, País A"]}]

    def test_si_los_ids_unicos_no_igualan_el_total_la_busqueda_queda_incompleta(self):
        portal = WorkdayFalso(self.EN_XA, extra_en_total=1)
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A"])]), portal)
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (2, 1, False))
        self.assertIn("[INCOMPLETA] EMP-ACME: 1/2 únicos", errores)

    def test_si_robots_txt_prohibe_la_api_no_se_usa(self):
        portal = WorkdayFalso(self.EN_XA, robots="User-agent: *\nDisallow: /wday/\n")
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A"])]), portal, codigo_esperado=1)
        self.assertIn("[FALLO] EMP-ACME: ", errores)
        self.assertIn("robots.txt", r["error"])
        self.assertEqual(portal.listados, [])

    def test_un_portal_que_no_es_de_workday_sale_como_fallo(self):
        self.escribir(modulo_04(preferencias([grupo("XA", nombres=["Ciudad A"])])), modulo_06({"EMP-ACME": ficha(
            "EMP-ACME", {"plataforma": "workday", "portal": "https://empleos.example.com/Acme", "consulta": None})}))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("[FALLO] EMP-ACME: ", r.stderr)
        self.assertIn("myworkdayjobs.com", r.stderr)


class RedSinSalida:
    """La red de un entorno que no deja salir la petición: urlopen lanza el URLError que da urllib ante ese error de
    conexión. Anota cada URL que se pidió."""

    def __init__(self, error):
        self.error, self.pedidas = error, []

    def __call__(self, req, timeout=None):
        self.pedidas.append(req.full_url)
        raise urllib.error.URLError(self.error)


class HostBloqueadoPorLaLista(ConPortalFalso):
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A"])])

    def test_el_proxy_de_la_nube_nombra_el_host_y_donde_agregarlo_tras_un_solo_intento(self):
        # El proxy de Code en la nube responde 403 al CONNECT de un host fuera de la lista de dominios
        red = RedSinSalida(OSError("Tunnel connection failed: 403 Forbidden"))
        r, errores = self.buscar(self.BLOQUE, WorkdayFalso([]), codigo_esperado=1, red=red)
        self.assertEqual(red.pedidas, [WorkdayFalso.HOST + "/robots.txt"])
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] EMP-ACME: "))
        self.assertTrue(fallo.endswith(": acme.wd1.myworkdayjobs.com"), fallo)
        self.assertIn("lista de dominios del entorno de la nube", fallo)
        self.assertIn("claude.ai/code (entorno → red → Custom)", fallo)
        self.assertNotIn("no se pudo leer", r["error"])

    def test_sin_red_por_otra_causa_conserva_el_mensaje_del_robots_txt(self):
        red = RedSinSalida(OSError("[Errno -3] Temporary failure in name resolution"))
        r, _ = self.buscar(self.BLOQUE, WorkdayFalso([]), codigo_esperado=1, red=red)
        self.assertEqual(len(red.pedidas), 3)
        self.assertIn(f"no se pudo leer {WorkdayFalso.HOST}/robots.txt", r["error"])
        self.assertNotIn("lista de dominios", r["error"])


class RedConLimite:
    """La red de un sitio que responde HTTP 429 a todo, con ese cuerpo y Retry-After. Anota cada URL que se
    pidió."""

    def __init__(self, cuerpo, retry_after="7"):
        self.cuerpo, self.retry_after, self.pedidas = cuerpo, retry_after, []

    def __call__(self, req, timeout=None):
        self.pedidas.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {"Retry-After": self.retry_after},
                                     io.BytesIO(self.cuerpo))


class WorkableEnLaNube(ConPortalFalso):
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A"])])
    # Lo que responde Cloudflare cuando Workable bloquea las IP de la nube
    BLOQUEO = b"error code: 1015"
    PAGINA_429 = b"<!DOCTYPE html><html><head><title>Error 429 - Internal Server Error</title></head></html>"

    def test_en_la_nube_el_bloqueo_de_cloudflare_manda_a_code_local_tras_un_solo_intento(self):
        red = RedConLimite(self.BLOQUEO)
        r, errores = self.buscar(self.BLOQUE, WorkableFalso([]), codigo_esperado=1, red=red, nube=True)
        self.assertEqual(red.pedidas, [WorkableFalso.SITIO + "/robots.txt"])
        self.assertEqual(self.esperas, [])
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] EMP-ACME: "))
        self.assertIn("apply.workable.com bloquea las IP de Code en la nube", fallo)
        self.assertIn("busca esta empresa en Code local", fallo)
        self.assertNotIn("no se pudo leer", r["error"])

    def test_en_code_local_el_mismo_429_se_reintenta_con_retry_after(self):
        red = RedConLimite(self.BLOQUEO)
        r, _ = self.buscar(self.BLOQUE, WorkableFalso([]), codigo_esperado=1, red=red)
        self.assertEqual(len(red.pedidas), 3)
        self.assertEqual(self.esperas, [7, 7])
        self.assertIn(f"no se pudo leer {WorkableFalso.SITIO}/robots.txt (HTTP 429", r["error"])
        self.assertNotIn("Code local", r["error"])

    def test_en_la_nube_un_retry_after_de_horas_manda_a_code_local_tras_un_solo_intento(self):
        # Lo que responde Workable a las IP de la nube si se le pide como navegador: su página, sin el 1015
        red = RedConLimite(self.PAGINA_429, retry_after="55291")
        r, errores = self.buscar(self.BLOQUE, WorkableFalso([]), codigo_esperado=1, red=red, nube=True)
        self.assertEqual(red.pedidas, [WorkableFalso.SITIO + "/robots.txt"])
        self.assertEqual(self.esperas, [])
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] EMP-ACME: "))
        self.assertIn("apply.workable.com bloquea las IP de Code en la nube (HTTP 429, pide esperar 15.4 h)", fallo)
        self.assertIn("busca esta empresa en Code local", fallo)
        self.assertNotIn("no se pudo leer", r["error"])

    def test_en_code_local_un_retry_after_de_horas_se_reintenta_esperando_hasta_un_minuto(self):
        red = RedConLimite(self.PAGINA_429, retry_after="55291")
        r, _ = self.buscar(self.BLOQUE, WorkableFalso([]), codigo_esperado=1, red=red)
        self.assertEqual(len(red.pedidas), 3)
        self.assertEqual(self.esperas, [60, 60])
        self.assertNotIn("Code local", r["error"])

    def test_en_la_nube_un_429_con_otro_cuerpo_se_reintenta_con_retry_after(self):
        red = RedConLimite(b"Too Many Requests")
        r, _ = self.buscar(self.BLOQUE, WorkableFalso([]), codigo_esperado=1, red=red, nube=True)
        self.assertEqual(len(red.pedidas), 3)
        self.assertEqual(self.esperas, [7, 7])
        self.assertNotIn("Code local", r["error"])


class AdaptadorDeEightfold(ConPortalFalso):
    def test_lista_cada_pais_de_la_region_con_el_primer_nombre_que_el_buscador_reconoce(self):
        bloque = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"]), grupo("XB", nombres=["Ciudad B1"])],
                              zona_horaria="Etc/GMT+12")
        portal = EightfoldFalso([
            {"id": "E-1", "ubicaciones": ["Ciudad A1, Estado A, País A"], "normalizadas": ["Ciudad A1, EA, XA"],
             "estado": "log_in"},
            # Publicada el 2 de octubre a las 03:00 UTC: en UTC−12 todavía es el 1
            {"id": "E-2", "ubicaciones": ["Ciudad A9, Estado A, País A"], "normalizadas": ["Ciudad A9, EA, XA"],
             "ts": OCTUBRE_1 + 27 * 3600},
            {"id": "E-3", "ubicaciones": ["Ciudad A7, Estado A7, País A"], "normalizadas": ["Ciudad A7, E7, XA"]},
            {"id": "E-4", "ubicaciones": ["Ciudad B1, País B"], "normalizadas": ["Ciudad B1, PB, XB"],
             "estado": "closed"},
            {"id": "E-5", "ubicaciones": ["Ciudad C1, País C"], "normalizadas": ["Ciudad C1, PC, XC"]},
        ], reconocidos={"Country A": "XA", "País B": "XB"})
        r, errores = self.buscar(bloque, portal)
        # La primera página sin filtros da los filtros del buscador; «País A» no es un país para el buscador
        self.assertEqual(portal.listados, [{}, {"location": ["País A"]}, {"location": ["Country A"]},
                                           {"location": ["País B"]}])
        self.assertEqual(self.regiones(r), {"E-1": "Dentro", "E-2": "Indeterminada", "E-4": "Dentro"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad A7, Estado A7, País A"])
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (4, 4, True))
        # Solo se lee el detalle de las que se entregan
        self.assertEqual(sorted(portal.detalles), [9000, 9001, 9003])
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        for v in vacantes.values():
            self.assertLessEqual(CAMPOS_DE_VACANTES_Y_OBSERVACIONES, set(v))
            self.assertEqual(v["descripcion"], "Descripción ficticia.")
        # 07/BUS-FECHAS: a las 00:00 UTC queda la fecha UTC; con hora real, la de la zona de 04
        self.assertEqual({j: v["fecha_publicacion"] for j, v in vacantes.items()},
                         {"E-1": "2026-10-01", "E-2": "2026-10-01", "E-4": "2026-10-01"})
        self.assertEqual({j: v["estado_vigencia"] for j, v in vacantes.items()},
                         {"E-1": "Confirmada abierta", "E-2": "Confirmada abierta", "E-4": "Revisar"})
        self.assertEqual(vacantes["E-1"]["url_oficial"], EightfoldFalso.HOST + "/careers/job/9000")
        self.assertIn("[OK] EMP-ACME: 4/4 únicos; 2 en la región", errores)
        self.assertIn("revisar vigencia: E-4 ", errores)

    def test_avisa_si_el_buscador_no_reconoce_ningun_nombre_de_un_pais(self):
        portal = EightfoldFalso([{"id": "E-1", "ubicaciones": ["Ciudad A1, País A"], "normalizadas": ["XA"]}],
                                reconocidos={})
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal)
        self.assertEqual(portal.listados, [{}, {"location": ["País A"]}, {"location": ["Country A"]}])
        self.assertEqual((r["total_reportado"], r["vacantes"]), (0, []))
        self.assertIn("revisar: el buscador no reconoce como país ningún nombre de XA", errores)

    def test_las_remotas_salen_del_filtro_de_modalidad_acotado_a_los_paises_del_remoto(self):
        bloque = preferencias([grupo("XB", nombres=["Ciudad B1"])], alcance="paises", paises_remoto=["XA", "XC"])
        portal = EightfoldFalso([
            {"id": "E-1", "ubicaciones": ["Ciudad B1, País B"], "normalizadas": ["Ciudad B1, PB, XB"]},
            {"id": "E-2", "ubicaciones": ["País A (Virtual)"], "normalizadas": ["XA"], "modalidad": "remote_local"},
            {"id": "E-3", "ubicaciones": ["Ciudad C1, País C"], "normalizadas": ["Ciudad C1, PC, XC"],
             "modalidad": "remote_local"},
            {"id": "E-4", "ubicaciones": ["Ciudad D1, País D"], "normalizadas": ["Ciudad D1, PD, XD"],
             "modalidad": "remote_local"},
            {"id": "E-5", "ubicaciones": ["Ciudad B2, País B"], "normalizadas": ["Ciudad B2, PB, XB"],
             "modalidad": "remote_local"},
            {"id": "E-6", "ubicaciones": ["Ciudad C2, País C"], "normalizadas": ["Ciudad C2, PC, XC"],
             "modalidad": "hybrid"},
        ])
        r, errores = self.buscar(bloque, portal)
        remoto = {"filter_work_location_option": ["remote_local"]}
        self.assertEqual(portal.listados, [{}, {"location": ["País B"]}, {"location": ["País A"], **remoto},
                                           {"location": ["País C"], **remoto}])
        self.assertEqual(self.regiones(r), {"E-1": "Dentro"})
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"E-2": "Fuera", "E-3": "Fuera"})
        # E-5 es remota, pero de un país que 04 no acepta para el remoto
        self.assertEqual(r["fuera_de_region"], ["Ciudad B2, País B"])
        self.assertIn("work_location_option", r["remotas_revision"])
        self.assertIn("[OK] EMP-ACME: 4/4 únicos; 1 en la región; remotas fuera de la región: 2", errores)

    def test_con_el_filtro_de_modalidad_por_pais_el_alcance_se_decide_por_codigo_de_pais(self):
        portal = EightfoldFalso([
            {"id": "E-1", "ubicaciones": ["Ciudad A1, País A"], "normalizadas": ["Ciudad A1, PA, XA"],
             "modalidad": "remote_local"},
            # Una remota de otro país que la búsqueda por país también trae
            {"id": "E-2", "ubicaciones": ["Ciudad D1, País D"], "normalizadas": ["Ciudad D1, PD, XD"],
             "modalidad": "remote_local", "en_todas": True},
        ])
        r, _ = self.buscar(preferencias([], alcance="paises", paises_remoto=["XA"]), portal)
        self.assertEqual(portal.listados, [{}, {"location": ["País A"],
                                                "filter_work_location_option": ["remote_local"]}])
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"E-1": "Fuera"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad D1, País D"])

    def test_sin_filtro_de_modalidad_las_remotas_salen_de_la_busqueda_remote_con_su_alcance_por_codigo(self):
        anuncios = [
            {"id": "E-1", "ubicaciones": ["Remote", "Ciudad A1, País A"],
             "normalizadas": ["Remote", "Ciudad A1, PA, XA"], "modalidad": "remote_local"},
            {"id": "E-2", "ubicaciones": ["Ciudad A2, País A"], "normalizadas": ["PA,XA"], "modalidad": "remote_local"},
            # Un país que 04 no nombra: por el nombre, podría estar en el alcance; por el código, no
            {"id": "E-3", "ubicaciones": ["Ciudad D1, País D"], "normalizadas": ["Ciudad D1, PD, XD"],
             "modalidad": "remote_local"},
            {"id": "E-4", "ubicaciones": ["Ciudad A3, País A"], "normalizadas": ["Ciudad A3, PA, XA"]},
        ]
        casos = {"paises": (["XA"], {"E-2": "Fuera"}, ["Ciudad D1, País D"]),
                 "cualquiera": ([], {"E-2": "Fuera", "E-3": "Fuera"}, [])}
        for alcance, (paises_remoto, remotas, fuera) in casos.items():
            with self.subTest(alcance):
                portal = EightfoldFalso(anuncios, filtro_de_modalidad=False)
                r, _ = self.buscar(preferencias([], alcance=alcance, paises_remoto=paises_remoto), portal)
                self.assertEqual(portal.listados, [{}, {"location": ["Remote"]}])
                self.assertEqual(self.regiones(r), {"E-1": "Indeterminada"})
                self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), remotas)
                self.assertEqual(r["fuera_de_region"], fuera)
                self.assertIn("«Remote»", r["remotas_revision"])

    def test_la_consulta_de_la_ficha_reemplaza_el_listado_por_paises(self):
        portal = EightfoldFalso([
            {"id": "E-1", "ubicaciones": ["Ciudad A1, País A"], "familia": "Ingeniería", "titulo": "Analista de datos"},
            {"id": "E-2", "ubicaciones": ["Ciudad A1, País A"], "familia": "Finanzas", "titulo": "Analista de datos"},
            {"id": "E-3", "ubicaciones": ["Ciudad A2, País A"], "familia": "Ingeniería", "titulo": "Analista de datos"},
            {"id": "E-4", "ubicaciones": ["Ciudad A1, País A"], "familia": "Ingeniería", "titulo": "Contador"},
        ])
        consulta = {"ubicaciones": ["Ciudad A1"], "filtros": {"job_family": ["ingenieria", "Inexistente"]},
                    "texto": "datos"}
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta)
        self.assertEqual(portal.listados, [{}, {"location": ["Ciudad A1"], "filter_job_family": ["ingeniería"],
                                                "query": ["datos"]}])
        self.assertEqual(self.regiones(r), {"E-1": "Dentro"})
        self.assertIn("revisar: el filtro job_family no ofrece «Inexistente»", errores)

    def test_una_consulta_mal_formada_sale_como_fallo(self):
        portal = EightfoldFalso([{"id": "E-1", "ubicaciones": ["Ciudad A1, País A"]}])
        for consulta in ({}, {"ubicaciones": "Ciudad A1"}, {"filtros": {"job_family": "x"}}, {"texto": 5},
                         {"facetas": {"locations": ["Ciudad A1"]}}):
            with self.subTest(consulta=consulta):
                r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta,
                                   codigo_esperado=1)
                self.assertIn("consulta", r["error"])
                self.assertIn("06/CAT-PLATAFORMAS", r["error"])
        self.assertEqual(portal.listados, [])


class ComprobacionesDeEightfold(ConPortalFalso):
    EN_XA = [{"id": "E-1", "ubicaciones": ["Ciudad A1, País A"], "normalizadas": ["Ciudad A1, PA, XA"]}]
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A1"])])

    def test_si_los_ids_unicos_no_igualan_el_total_la_busqueda_queda_incompleta(self):
        r, errores = self.buscar(self.BLOQUE, EightfoldFalso(self.EN_XA, extra_en_total=1))
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (2, 1, False))
        self.assertIn("[INCOMPLETA] EMP-ACME: 1/2 únicos", errores)

    def test_un_listado_sin_el_orden_estable_sale_como_fallo(self):
        r, _ = self.buscar(self.BLOQUE, EightfoldFalso(self.EN_XA, orden="distance"), codigo_esperado=1)
        self.assertIn("timestamp", r["error"])

    def test_un_detalle_con_otro_id_deja_la_vacante_con_la_evidencia_del_listado(self):
        portal = EightfoldFalso([{**self.EN_XA[0], "id_en_detalle": 1}])
        r, errores = self.buscar(self.BLOQUE, portal)
        v = r["vacantes"][0]
        self.assertEqual(v["estado_vigencia"], "Confirmada abierta")
        self.assertIn("detalle no consultado", v["motivo"])
        self.assertIn("otro ID", v["motivo"])
        self.assertIn("revisar vigencia: E-1 ", errores)

    def test_un_portal_sin_la_api_pcsx_sale_como_fallo(self):
        r, errores = self.buscar(self.BLOQUE, EightfoldFalso(self.EN_XA, sin_pcsx=True), codigo_esperado=1)
        self.assertIn("[FALLO] EMP-ACME: ", errores)
        self.assertIn("pcsx", r["error"])

    def test_un_portal_sin_el_dominio_de_la_empresa_sale_como_fallo(self):
        self.escribir(modulo_04(self.BLOQUE), modulo_06({"EMP-ACME": ficha("EMP-ACME", {
            "plataforma": "eightfold", "portal": EightfoldFalso.HOST + "/careers", "consulta": None})}))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("[FALLO] EMP-ACME: ", r.stderr)
        self.assertIn("?domain=<dominio>", r.stderr)


class ReglasDeRobotsTxt(ConPortalFalso):
    def test_gana_la_regla_mas_larga_del_grupo_del_agente_igual_en_cualquier_python(self):
        # Hasta Python 3.12, urllib.robotparser aplicaba la primera regla que coincide, no la más larga (RFC 9309)
        casos = {
            "Disallow: / antes de un Allow más largo": ("User-agent: *\nDisallow: /\nAllow: /api/pcsx\n", True),
            "ruta prohibida": ("User-agent: *\nDisallow: /api/\n", False),
            "consultas prohibidas con comodín": ("User-agent: *\nDisallow: /*?\n", False),
            "Disallow vacío": ("User-agent: *\nDisallow:\n", True),
            "grupo de otro agente": ("User-agent: OtroBot\nDisallow: /\n", True),
            "grupo propio antes que el de *": ("User-agent: Mozilla\nDisallow: /api/\n\nUser-agent: *\nAllow: /\n",
                                               False),
            "empate entre Allow y Disallow": ("User-agent: *\nDisallow: /api/pcsx\nAllow: /api/pcsx\n", True),
            "fin de ruta con $": ("User-agent: *\nDisallow: /api/pcsx/search$\n", True),
        }
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"])])
        for caso, (robots, permitido) in casos.items():
            with self.subTest(caso):
                portal = EightfoldFalso([{"id": "E-1", "ubicaciones": ["Ciudad A1, País A"]}], robots=robots)
                r, _ = self.buscar(bloque, portal, codigo_esperado=0 if permitido else 1)
                if permitido:
                    self.assertNotIn("error", r)
                else:
                    self.assertIn("robots.txt", r["error"])
                    self.assertEqual(portal.listados, [])


class AdaptadorDeWorkable(ConPortalFalso):
    def test_lista_por_los_codigos_de_pais_de_la_region_en_paginas_de_diez(self):
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"]), grupo("XB", divisiones=["Provincia B1"])],
                              zona_horaria="Etc/GMT+12")
        portal = WorkableFalso([{"id": f"WA{i:02}", "lugares": [("Ciudad A1", "Provincia A1", "País A", "XA")]}
                                for i in range(17)] + [
            # Publicada el 2 de octubre a las 03:00 UTC: en UTC−12 todavía es el 1
            {"id": "WB1", "lugares": [("Ciudad B1", "Provincia B1", "País B", "XB")],
             "publicada": "2026-10-02T03:00:00.000Z"},
            {"id": "WB2", "lugares": [("Ciudad B2", "Provincia B2", "País B", "XB")]},
            {"id": "WC1", "lugares": [("Ciudad C1", None, "País C", "XC")]},
            # Una remota abierta a cualquier país, que el filtro de país también trae
            {"id": "WD1", "lugares": [("", None, "País D", "XD")], "modalidad": "remote", "en_todas": True},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(portal.listados, [{"location": [{"countryCode": "XA"}, {"countryCode": "XB"}]}])
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (20, 20, True))
        self.assertEqual(set(self.regiones(r).values()), {"Dentro"})
        self.assertEqual(len(r["vacantes"]), 18)
        self.assertEqual(r["fuera_de_region"], ["Ciudad B2, Provincia B2, País B", "País D"])
        self.assertEqual(sorted(portal.detalles), sorted(v["job_id"] for v in r["vacantes"]))
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        self.assertLessEqual(CAMPOS_DE_VACANTES_Y_OBSERVACIONES, set(vacantes["WB1"]))
        self.assertEqual({vacantes[j]["fecha_publicacion"] for j in ("WA00", "WB1")}, {"2026-10-01"})
        self.assertEqual(vacantes["WA00"]["url_oficial"], "https://apply.workable.com/acme/j/WA00/")
        self.assertEqual(vacantes["WA00"]["ubicacion_literal"], "Ciudad A1, Provincia A1, País A")
        self.assertEqual(vacantes["WA00"]["departamento"], "Ingeniería")
        self.assertEqual(vacantes["WA00"]["descripcion"], "Descripción ficticia.\n\nRequisitos ficticios.")
        self.assertEqual(vacantes["WA00"]["estado_vigencia"], "Confirmada abierta")
        self.assertIn("[OK] EMP-ACME: 20/20 únicos; 18 en la región", errores)

    def test_la_red_de_seguridad_de_division_completa_toma_el_pais_que_da_la_plataforma(self):
        # La cuenta no escribe el país, pero da su código: la plataforma sitúa la vacante en XA
        bloque = preferencias([grupo("XA", ["Estado A"])])
        portal = WorkableFalso([
            {"id": "W1", "lugares": [("Localidad A6", None, None, "XA")]},
            {"id": "W2", "lugares": [("Localidad A7", "Estado Z", None, "XA")]},
            {"id": "W3", "lugares": [("Localidad A8", "Estado A", None, "XA")]},
        ])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r), {"W1": "Indeterminada", "W3": "Dentro"})
        self.assertEqual(r["fuera_de_region"], ["Localidad A7, Estado Z"])
        self.assertIn("revisar ubicación: Localidad A6 (1 vacante: W1)", errores)

    def test_las_remotas_salen_del_filtro_de_remoto_con_su_alcance_por_codigo_de_pais(self):
        anuncios = [
            {"id": "W1", "lugares": [("Ciudad A1", None, "País A", "XA")]},
            {"id": "W2", "lugares": [("Ciudad A2", None, "País A", "XA")], "modalidad": "remote"},
            {"id": "W3", "lugares": [("", None, "País D", "XD")], "modalidad": "remote", "en_todas": True},
            {"id": "W4", "lugares": [("Ciudad C1", None, "País C", "XC")], "modalidad": "remote"},
            # Remota por el booleano remote, aunque workplace diga otra cosa
            {"id": "W5", "lugares": [("Ciudad A3", None, "País A", "XA")], "modalidad": "hybrid", "remota": True},
        ]
        casos = {
            "paises": (["XA"], [{"remote": [True], "location": [{"countryCode": "XA"}]}],
                       {"W2": "Fuera", "W5": "Fuera"}, ["País D"]),
            "cualquiera": ([], [{"remote": [True]}], {"W2": "Fuera", "W3": "Fuera", "W4": "Fuera", "W5": "Fuera"}, []),
        }
        for alcance, (paises_remoto, listados, remotas, fuera) in casos.items():
            with self.subTest(alcance):
                portal = WorkableFalso(anuncios)
                r, _ = self.buscar(preferencias([], alcance=alcance, paises_remoto=paises_remoto), portal)
                self.assertEqual(portal.listados, listados)
                self.assertEqual(r["vacantes"], [])
                self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), remotas)
                self.assertEqual(r["fuera_de_region"], fuera)
                self.assertIn("remote", r["remotas_revision"])

    def test_la_consulta_de_la_ficha_reemplaza_el_listado_por_paises(self):
        portal = WorkableFalso([{"id": "W1", "lugares": [("Ciudad A1", None, "País A", "XA")]},
                                {"id": "W2", "lugares": [("Ciudad A1", None, "País A", "XA")]},
                                {"id": "W3", "lugares": [("Ciudad A2", None, "País A", "XA")]}])
        consulta = {"ubicaciones": [{"countryCode": "XA", "city": "Ciudad A1"}], "texto": "W1"}
        r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta)
        self.assertEqual(portal.listados, [{"location": [{"countryCode": "XA", "city": "Ciudad A1"}], "query": "W1"}])
        self.assertEqual(self.regiones(r), {"W1": "Dentro"})

    def test_una_consulta_mal_formada_sale_como_fallo(self):
        portal = WorkableFalso([{"id": "W1", "lugares": [("Ciudad A1", None, "País A", "XA")]}])
        for consulta in ({}, {"ubicaciones": ["Ciudad A1"]}, {"ubicaciones": [{"pais": "XA"}]}, {"texto": 5},
                         {"ubicaciones": [{}]}):
            with self.subTest(consulta=consulta):
                r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta,
                                   codigo_esperado=1)
                self.assertIn("consulta", r["error"])
                self.assertIn("06/CAT-PLATAFORMAS", r["error"])
        self.assertEqual(portal.listados, [])


class ComprobacionesDeWorkable(ConPortalFalso):
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A1"])])

    def test_vigencia_e_id_del_detalle_y_total_del_listado(self):
        portal = WorkableFalso([
            {"id": "W1", "lugares": [("Ciudad A1", None, "País A", "XA")], "estado": "closed"},
            {"id": "W2", "lugares": [("Ciudad A1", None, "País A", "XA")], "id_en_detalle": "OTRO"},
        ], extra_en_total=1)
        r, errores = self.buscar(self.BLOQUE, portal)
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        self.assertEqual(vacantes["W1"]["estado_vigencia"], "Revisar")
        self.assertIn("detalle no consultado", vacantes["W2"]["motivo"])
        self.assertIn("[INCOMPLETA] EMP-ACME: 2/3 únicos", errores)
        self.assertIn("revisar vigencia: W1 ", errores)

    def test_un_portal_que_no_es_de_workable_sale_como_fallo(self):
        self.escribir(modulo_04(self.BLOQUE), modulo_06({"EMP-ACME": ficha("EMP-ACME", {
            "plataforma": "workable", "portal": "https://empleos.acme.example/jobs", "consulta": None})}))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("[FALLO] EMP-ACME: ", r.stderr)
        self.assertIn("apply.workable.com/<cuenta>", r.stderr)


def publicacion(pid, lugar, **cambios):
    """Una publicación de SmartRecruitersFalso, con su ref en el listado y un detalle «Ciudad, Región, País»."""
    ciudad, _, pais = lugar.rpartition(", ")
    return {"id": pid, "lugar": lugar, "ref": f"R{pid}", "detalle": (ciudad, "Región X", pais), **cambios}


class AdaptadorDeSmartRecruiters(ConPortalFalso):
    def test_agrupado_por_ubicacion_completa_solo_los_grupos_que_pueden_ser_de_la_region(self):
        bloque = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])], zona_horaria="Etc/GMT+12")
        en_a1 = [publicacion(f"1{i:02}", "Ciudad A1, País A") for i in range(12)]
        en_a1[0].update(ref_detalle="REQ-100", detalle=("Ciudad A1", "Estado A", "País A"))
        en_a1[1].update(ref=None, publicada="2026-10-02T03:00:00.000Z")  # en UTC−12 todavía es el 1
        en_a1[2]["abierta"] = False
        portal = SmartRecruitersFalso(en_a1 + [
            # Grupos que solo nombran el país o una localidad no aceptada de un país de la región: decide su página
            publicacion("200", "País A", detalle=("Ciudad A7", "Estado A", "País A")),
            publicacion("300", "Ciudad A9, País A", detalle=("Ciudad A9", "Estado A", "País A")),
        ] + [publicacion(f"4{i:02}", "Ciudad C1, País C") for i in range(11)])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(portal.listados, [{}])
        # Solo el grupo de Ciudad A1 tiene más de las que muestra; el de Ciudad C1 no se completa
        self.assertEqual(portal.completados, ["Ciudad A1, País A, XX"])
        self.assertEqual(sorted(portal.detalles), sorted([p["id"] for p in en_a1] + ["200", "300"]))
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (14, 14, True))
        vacantes = {v["url_oficial"].rsplit("/", 1)[1].split("-")[0]: v for v in r["vacantes"]}
        self.assertEqual({p: v["region_relacionada"] for p, v in vacantes.items()},
                         {**{p["id"]: "Dentro" for p in en_a1}, "200": "Indeterminada", "300": "Indeterminada"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad C1, País C"])
        self.assertEqual({p: vacantes[p]["job_id"] for p in ("100", "101", "102")},
                         {"100": "REQ-100", "101": None, "102": "R102"})
        v = vacantes["100"]
        self.assertLessEqual(CAMPOS_DE_VACANTES_Y_OBSERVACIONES, set(v))
        url = SmartRecruitersFalso.PUBLICACIONES + "/Acme/100-puesto-100"
        self.assertEqual((v["url_oficial"], v["url_fuente"]), (url, url))
        self.assertEqual((v["ubicacion_literal"], v["modalidad_literal"]), ("Ciudad A1, Estado A, País A", "on_site"))
        self.assertEqual((v["departamento"], v["descripcion"]),
                         ("Ingeniería", "Descripción ficticia.\n\nRequisitos ficticios."))
        self.assertEqual({vacantes[p]["fecha_publicacion"] for p in ("100", "101")}, {"2026-10-01"})
        self.assertEqual({p: vacantes[p]["estado_vigencia"] for p in ("100", "102")},
                         {"100": "Confirmada abierta", "102": "Revisar"})
        self.assertIn("[OK] EMP-ACME: 14/14 únicos; 12 en la región", errores)
        self.assertIn("revisar ubicación: Ciudad A7, Estado A, País A (1 vacante: R200)", errores)
        self.assertIn("revisar vigencia: R102 ", errores)

    def test_un_grupo_que_no_nombra_un_pais_de_04_se_decide_por_la_pagina_de_su_primera_publicacion(self):
        # Como «Ciudad, Estado» en los sitios de algunos países: el nombre del grupo no dice el país
        en_z1 = [publicacion(f"1{i:02}", "Ciudad Z1, EZ", detalle=("Ciudad Z1", "EZ", "País A")) for i in range(11)]
        portal = SmartRecruitersFalso(en_z1 + [
            publicacion("200", "Ciudad Z2, EZ", detalle=("Ciudad Z2", "EZ", "País C")),
            publicacion("201", "Ciudad Z2, EZ", detalle=("Ciudad Z2", "EZ", "País C")),
            publicacion("300", "Ciudad C1, País C"),
        ])
        r, _ = self.buscar(preferencias([grupo("XA")]), portal)
        self.assertEqual(portal.completados, ["Ciudad Z1, EZ, XX"])
        # Una página por grupo sin país de 04, que no se vuelve a pedir; el grupo de País C no se lee
        self.assertEqual(sorted(portal.detalles), sorted([p["id"] for p in en_z1] + ["200"]))
        self.assertEqual(self.regiones(r), {p["ref"]: "Dentro" for p in en_z1})
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (11, 11, True))
        self.assertEqual(r["fuera_de_region"], ["Ciudad C1, País C", "Ciudad Z2, EZ"])

    def test_un_lugar_bajo_el_titulo_que_no_nombra_un_pais_de_04_se_decide_por_una_pagina_con_ese_lugar(self):
        portal = SmartRecruitersFalso([
            publicacion(f"1{i:02}", "Ciudad Z1, EZ", departamento="Ingeniería", detalle=("Ciudad Z1", "EZ", "País A"))
            for i in range(11)] + [
            publicacion("200", "Ciudad Z2, EZ", departamento="Ingeniería", detalle=("Ciudad Z2", "EZ", "País C")),
            publicacion("201", "Ciudad Z2, EZ", departamento="Finanzas", detalle=("Ciudad Z2", "EZ", "País C")),
        ], agrupar="department")
        r, _ = self.buscar(preferencias([grupo("XA")]), portal)
        # Una página por lugar sin país de 04: la de Ciudad Z1 se aprovecha; la de Ciudad Z2 decide que no
        self.assertEqual(sorted(portal.detalles), [f"1{i:02}" for i in range(11)] + ["201"])
        self.assertEqual(set(self.regiones(r).values()), {"Dentro"})
        self.assertEqual(len(r["vacantes"]), 11)
        self.assertEqual(r["fuera_de_region"], ["Ciudad Z2, EZ"])

    def test_una_requisicion_con_varias_publicaciones_da_una_sola_linea_revisar(self):
        portal = SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A", ref_detalle="REQ-1"),
                                       publicacion("2", "Ciudad A2, País A", ref_detalle="REQ-1"),
                                       publicacion("4", "Ciudad A3, País A", ref_detalle="REQ-1"),
                                       publicacion("3", "Ciudad A1, País A")])
        r, errores = self.buscar(preferencias([grupo("XA")]), portal)
        self.assertEqual(sorted(v["job_id"] for v in r["vacantes"]), ["R3", "REQ-1", "REQ-1", "REQ-1"])
        # El JSON conserva la nota en cada publicación; stderr la dice una vez, con las tres URL
        mismas = [v for v in r["vacantes"] if v["job_id"] == "REQ-1"]
        notas = {n for v in mismas for n in v["revisar"]}
        self.assertEqual(len(notas), 1)
        self.assertTrue(all(len(v["revisar"]) == 1 for v in mismas))
        self.assertEqual(errores.count("revisar: REQ-1 requisición"), 1)
        linea = next(linea for linea in errores.splitlines() if "revisar: REQ-1 requisición" in linea)
        self.assertIn("con 3 publicaciones", linea)
        for v in mismas:
            self.assertIn(v["url_oficial"], linea)
        self.assertNotIn("revisar: R3 requisición", errores)

    def test_agrupado_por_departamento_completa_todos_los_grupos_y_toma_el_lugar_de_cada_publicacion(self):
        ingenieria = [publicacion(f"1{i:02}", "Ciudad A1, País A" if i % 4 == 0 else "Ciudad C1, País C",
                                  departamento="Ingeniería") for i in range(12)]
        portal = SmartRecruitersFalso(ingenieria + [
            publicacion("201", "Ciudad A1, País A", departamento="Finanzas"),
            publicacion("202", "Ciudad D1, País D", departamento="Finanzas"),
        ], agrupar="department")
        r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal)
        self.assertEqual(portal.completados, ["1"])
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (14, 14, True))
        # 202 nombra un país que 04 no tiene: su página lo decide
        self.assertEqual(sorted(portal.detalles), ["100", "104", "108", "201", "202"])
        self.assertEqual(set(self.regiones(r).values()), {"Dentro"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad D1, País D", "Ciudad C1, País C"])

    def test_si_ningun_grupo_dice_como_agrupa_prueba_el_nombre_del_grupo_y_el_texto_de_la_publicacion(self):
        publicaciones = [publicacion("1", "Ciudad A1, País A", departamento="Ingeniería"),
                         publicacion("2", "Ciudad C1, País C", departamento="Ingeniería")]
        casos = {"location": "Ciudad C1, País C | Full-time", "department": "Ingeniería | Ciudad C1, País C"}
        for agrupar, fuera in casos.items():
            with self.subTest(agrupar):
                portal = SmartRecruitersFalso(publicaciones, agrupar=agrupar)
                r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal)
                self.assertEqual(self.regiones(r), {"R1": "Dentro"})
                self.assertEqual(portal.detalles, ["1"])
                self.assertEqual(r["fuera_de_region"], [fuera])

    def test_las_remotas_salen_del_filtro_locationtype_con_su_alcance(self):
        publicaciones = [
            publicacion("1", "Ciudad A1, País A"),
            publicacion("2", "Ciudad A2, País A", modalidad="remote"),
            publicacion("3", "Ciudad C1, País C", modalidad="remote"),
            # Un país que no reconocen 04 ni la tabla: puede estar en el alcance, y queda por revisar
            publicacion("4", "Ciudad D1, País D", modalidad="remote"),
            publicacion("5", "Ciudad B1, País B", modalidad="hybrid"),
        ]
        casos = {"paises": (["XA"], ["2", "4"], {"R2": "Fuera", "R4": "Fuera"},
                            ["Ciudad C1, País C | Full-time", "Ciudad A1, País A | Full-time"]),
                 "cualquiera": ([], ["2", "3", "4"], {"R2": "Fuera", "R3": "Fuera", "R4": "Fuera"},
                                ["Ciudad A1, País A | Full-time"])}
        for alcance, (paises_remoto, detalles, remotas, fuera) in casos.items():
            with self.subTest(alcance):
                portal = SmartRecruitersFalso(publicaciones)
                bloque = preferencias([grupo("XB", nombres=["Ciudad B1"])], alcance=alcance,
                                      paises_remoto=paises_remoto)
                r, errores = self.buscar(bloque, portal)
                # Las remotas primero: el listado de la región no dice la modalidad
                self.assertEqual(portal.listados, [{"locationType": ["REMOTE"]}, {}])
                self.assertEqual(sorted(portal.detalles), detalles + ["5"])
                self.assertEqual(self.regiones(r), {"R5": "Dentro"})
                self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), remotas)
                por_revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["remotas_fuera_de_region"]}
                self.assertEqual(por_revisar["R4"], ["Ciudad D1, Región X, País D"] if alcance == "paises" else [])
                self.assertEqual(r["fuera_de_region"], fuera)
                self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (5, 5, True))
                self.assertIn("locationType=REMOTE", r["remotas_revision"])

    def test_con_el_alcance_paises_una_remota_de_un_pais_reconocido_fuera_del_alcance_queda_fuera(self):
        portal = SmartRecruitersFalso([
            # Un país de la tabla, fuera del alcance: la página no se pide
            publicacion("1", "Ciudad Z, Country Z", modalidad="remote"),
            # Un lugar que contiene el nombre de un país de 04 no lo nombra
            publicacion("2", "Nuevo País A, Country Z", modalidad="remote"),
            # Sin país reconocido en el listado: decide el addressCountry de su página
            publicacion("3", "Ciudad Z, ZZ", modalidad="remote", detalle=("Ciudad Z", "ZZ", "Country Z")),
            publicacion("4", "Ciudad Y, ZZ", modalidad="remote", detalle=("Ciudad Y", "ZZ", "País A")),
            # Sin país en ninguna parte: puede estar en el alcance, y queda por revisar
            publicacion("5", "Ciudad Q, QQ", modalidad="remote", detalle=("Ciudad Q", "QQ", "")),
        ])
        bloque = preferencias([grupo("XB", nombres=["Ciudad B1"])], alcance="paises", paises_remoto=["XA"])
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(sorted(portal.detalles), ["3", "4", "5"])
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"R4": "Fuera", "R5": "Fuera"})
        revisar = {v["job_id"]: v["ubicaciones_por_revisar"] for v in r["remotas_fuera_de_region"]}
        self.assertEqual(revisar, {"R4": [], "R5": ["Ciudad Q, QQ"]})
        # Sin «Show more», el sitio no dice cómo agrupa: el lugar del listado lleva también el texto bajo el título
        self.assertEqual(sorted(r["fuera_de_region"]), ["Ciudad Z, Country Z | Full-time", "Ciudad Z, ZZ, Country Z",
                                                        "Nuevo País A, Country Z | Full-time"])
        self.assertIn("revisar ubicación: Ciudad Q, QQ (1 vacante: R5)", errores)
        self.assertNotIn("R4", "".join(linea for linea in errores.splitlines() if "revisar" in linea))

    def test_un_nombre_de_04_que_la_tabla_da_a_otro_pais_cuenta_para_el_pais_de_04(self):
        portal = SmartRecruitersFalso([publicacion("1", "Ciudad Q, Tierra Z", modalidad="remote"),
                                       publicacion("2", "Ciudad Q, Country Z", modalidad="remote")])
        bloque = preferencias([grupo("XB", nombres=["Ciudad B1"])], alcance="paises", paises_remoto=["XA"],
                              paises={**PAISES, "XA": ["País A", "Country A", "Tierra Z"]})
        r, errores = self.buscar(bloque, portal)
        self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), {"R1": "Fuera"})
        self.assertEqual(r["remotas_fuera_de_region"][0]["ubicaciones_por_revisar"], [])
        self.assertEqual(r["fuera_de_region"], ["Ciudad Q, Country Z | Full-time"])

    def test_la_consulta_de_la_ficha_elige_grupos_y_busca_texto(self):
        portal = SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A"), publicacion("2", "Ciudad A2, País A"),
                                       publicacion("3", "Ciudad A1, País A")])
        consulta = {"grupos": ["ciudad a1, pais a", "Ciudad Inexistente"], "texto": "puesto 1"}
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta)
        self.assertEqual(portal.listados, [{"search": ["puesto 1"]}])
        self.assertEqual(self.regiones(r), {"R1": "Dentro"})
        self.assertIn("revisar: el sitio no tiene el grupo «Ciudad Inexistente»", errores)

    def test_una_consulta_mal_formada_sale_como_fallo(self):
        portal = SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A")])
        for consulta in ({}, {"grupos": "Ciudad A1"}, {"grupos": []}, {"texto": 5}, {"facetas": {"x": ["y"]}}):
            with self.subTest(consulta=consulta):
                r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta,
                                   codigo_esperado=1)
                self.assertIn("consulta", r["error"])
                self.assertIn("06/CAT-PLATAFORMAS", r["error"])
        self.assertEqual(portal.listados, [])


class ComprobacionesDeSmartRecruiters(ConPortalFalso):
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A1"])])

    def test_si_un_grupo_trae_menos_publicaciones_que_su_conteo_la_busqueda_queda_incompleta(self):
        r, errores = self.buscar(self.BLOQUE, SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A")],
                                                                   extra_en_total=1))
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (2, 1, False))
        self.assertIn("[INCOMPLETA] EMP-ACME: 1/2 únicos", errores)

    def test_un_detalle_con_otro_id_deja_la_vacante_con_la_evidencia_del_listado(self):
        r, errores = self.buscar(self.BLOQUE, SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A",
                                                                                id_en_detalle="9")]))
        v = r["vacantes"][0]
        self.assertEqual((v["job_id"], v["estado_vigencia"]), ("R1", "Confirmada abierta"))
        self.assertIn("otro ID", v["motivo"])
        self.assertIn("revisar vigencia: R1 ", errores)

    def test_si_el_robots_txt_de_smartrecruiters_prohibe_la_empresa_no_se_usa(self):
        portal = SmartRecruitersFalso([publicacion("1", "Ciudad A1, País A")],
                                      robots_www="User-agent: *\nDisallow: /search/\nDisallow: /Acme/*\n")
        r, errores = self.buscar(self.BLOQUE, portal, codigo_esperado=1)
        self.assertIn("[FALLO] EMP-ACME: ", errores)
        self.assertIn("robots.txt", r["error"])
        self.assertEqual(portal.listados, [])

    def test_un_portal_que_no_es_de_smartrecruiters_sale_como_fallo(self):
        self.escribir(modulo_04(self.BLOQUE), modulo_06({"EMP-ACME": ficha("EMP-ACME", {
            "plataforma": "smartrecruiters", "portal": "https://api.smartrecruiters.com/v1/companies/Acme",
            "consulta": None})}))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("[FALLO] EMP-ACME: ", r.stderr)
        self.assertIn("careers.smartrecruiters.com/<empresa>", r.stderr)


class AdaptadorDeOracle(ConPortalFalso):
    def test_lista_cada_pais_de_la_region_con_el_primer_nombre_que_la_api_reconoce(self):
        bloque = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"]), grupo("XB", nombres=["Ciudad B1"])],
                              zona_horaria="Etc/GMT+12")
        en_a1 = [{"id": f"1{i:02}", "lugares": [("Ciudad A1, Estado A, País A", "XA")]} for i in range(27)]
        portal = OracleFalso(en_a1 + [
            # Publicada el 2 de octubre a las 03:00 UTC: en UTC−12 todavía es el 1
            {"id": "201", "lugares": [("Ciudad C1, País C", "XC"), ("Ciudad A1, Estado A, País A", "XA")],
             "publicada": "2026-10-02T03:00:00+00:00", "familia": "Ingeniería"},
            {"id": "202", "lugares": [("Ciudad A7, Estado A7, País A", "XA")]},
            {"id": "203", "lugares": [("Ciudad B1, País B", "XB")], "cierre": "2026-01-01T00:00:00+00:00"},
            {"id": "204", "lugares": [("Ciudad C2, País C", "XC")]},
        ], reconocidos={"Country A": "XA", "País B": "XB"})
        r, errores = self.buscar(bloque, portal)
        # La primera página sin filtros da las facetas; «País A» no lo reconoce, y entonces no filtra
        self.assertEqual(portal.listados,
                         [{}, {"location": "País A"}, {"location": "Country A"}, {"location": "País B"}])
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (30, 30, True))
        self.assertEqual(self.regiones(r), {**{a["id"]: "Dentro" for a in en_a1}, "201": "Incluye", "203": "Dentro"})
        self.assertEqual(r["fuera_de_region"], ["Ciudad A7, Estado A7, País A"])
        # Solo se lee el detalle de las que se entregan
        self.assertEqual(sorted(portal.detalles), sorted([f"1{i:02}" for i in range(27)] + ["201", "203"]))
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        v = vacantes["201"]
        self.assertLessEqual(CAMPOS_DE_VACANTES_Y_OBSERVACIONES, set(v))
        self.assertEqual(v["url_oficial"], OracleFalso.PORTAL + "/job/201")
        self.assertEqual(v["ubicacion_literal"], "Ciudad C1, País C | Ciudad A1, Estado A, País A")
        self.assertEqual((v["modalidad_literal"], v["departamento"]), ("Onsite", "Ingeniería"))
        self.assertEqual(v["descripcion"], "Descripción ficticia.\n\n- Responsabilidad ficticia.")
        self.assertIn("recruitingCEJobRequisitionDetails", v["url_fuente"])
        self.assertEqual({vacantes[j]["fecha_publicacion"] for j in ("100", "201")}, {"2026-10-01"})
        self.assertEqual({j: vacantes[j]["estado_vigencia"] for j in ("100", "203")},
                         {"100": "Confirmada abierta", "203": "Revisar"})
        self.assertIn("ExternalPostedEndDate", vacantes["203"]["motivo"])
        self.assertIn("[OK] EMP-ACME: 30/30 únicos; 29 en la región", errores)
        self.assertIn("revisar vigencia: 203 ", errores)

    def test_un_nombre_que_la_api_no_reconoce_no_filtra_aunque_su_faceta_lo_traiga_con_otros_acentos(self):
        # «Country Á» no lo reconoce y trae todo el sitio, cuya faceta de ubicaciones trae «Country A»
        bloque = preferencias([grupo("XA", nombres=["Ciudad A1"])], paises={"XA": ["Country Á", "Country A"]})
        portal = OracleFalso([{"id": "1", "lugares": [("Ciudad A1, País A", "XA")]},
                              {"id": "2", "lugares": [("Ciudad C1, País C", "XC")]}])
        r, _ = self.buscar(bloque, portal)
        self.assertEqual(portal.listados, [{}, {"location": "Country Á"}, {"location": "Country A"}])
        self.assertEqual((r["total_reportado"], r["unicos"]), (1, 1))
        self.assertEqual(r["fuera_de_region"], [])

    def test_avisa_si_la_api_no_reconoce_ningun_nombre_de_un_pais(self):
        portal = OracleFalso([{"id": "1", "lugares": [("Ciudad A1, País A", "XA")]}], reconocidos={})
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal)
        self.assertEqual(portal.listados, [{}, {"location": "País A"}, {"location": "Country A"}])
        self.assertEqual((r["total_reportado"], r["vacantes"]), (0, []))
        self.assertIn("revisar: la API no reconoce como país ningún nombre de XA", errores)

    def test_las_remotas_salen_de_la_faceta_de_modalidad_con_su_alcance_por_codigo_de_pais(self):
        requisiciones = [
            {"id": "1", "lugares": [("Ciudad A1, País A", "XA")]},
            {"id": "2", "lugares": [("Ciudad A2, País A", "XA")], "modalidad": "Remote"},
            # Remota de otro país con una ubicación secundaria en XA: la búsqueda por XA también la trae
            {"id": "3", "lugares": [("Ciudad D1, País D", "XD"), ("Ciudad A3, País A", "XA")], "modalidad": "Remote"},
            {"id": "4", "lugares": [("Ciudad C1, País C", "XC")], "modalidad": "Remote"},
            {"id": "5", "lugares": [("Ciudad A4, País A", "XA")], "modalidad": "Hybrid"},
        ]
        remoto = {"selectedWorkplaceTypesFacet": "ORA_REMOTE"}
        casos = {"paises": (["XA"], [{}, {"location": "País A", **remoto}, {"location": "Country A", **remoto}],
                            {"2": "Fuera", "3": "Fuera"}),
                 "cualquiera": ([], [{}, remoto], {"2": "Fuera", "3": "Fuera", "4": "Fuera"})}
        for alcance, (paises_remoto, listados, remotas) in casos.items():
            with self.subTest(alcance):
                portal = OracleFalso(requisiciones)
                r, _ = self.buscar(preferencias([], alcance=alcance, paises_remoto=paises_remoto), portal)
                self.assertEqual(portal.listados, listados)
                self.assertEqual(r["vacantes"], [])
                self.assertEqual(self.regiones(r, "remotas_fuera_de_region"), remotas)
                self.assertIn("selectedWorkplaceTypesFacet", r["remotas_revision"])

    def test_sin_valor_remoto_en_la_faceta_de_modalidad_avisa(self):
        portal = OracleFalso([{"id": "1", "lugares": [("Ciudad A1, País A", "XA")]}])
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="cualquiera"), portal)
        self.assertEqual(self.regiones(r), {"1": "Dentro"})
        self.assertIn("No disponible", r["remotas_revision"])
        self.assertIn("revisar: sin filtro de remoto en el portal", errores)

    def test_la_consulta_de_la_ficha_reemplaza_el_listado_por_paises(self):
        portal = OracleFalso([{"id": "1", "lugares": [("Ciudad A1, País A", "XA")], "familia": "Ingeniería"},
                              {"id": "2", "lugares": [("Ciudad A1, País A", "XA")], "familia": "Finanzas"},
                              {"id": "3", "lugares": [("Ciudad A1, País A", "XA")], "familia": "Ingeniería"}])
        consulta = {"facetas": {"CATEGORIES": ["ingenieria", "Inexistente"]}, "texto": "puesto 1"}
        r, errores = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta)
        self.assertEqual(portal.listados, [{}, {"selectedCategoriesFacet": "CAT-Ingeniería", "keyword": "puesto 1"}])
        self.assertEqual(self.regiones(r), {"1": "Dentro"})
        self.assertIn("revisar: la faceta CATEGORIES no ofrece «Inexistente»", errores)

    def test_una_consulta_mal_formada_sale_como_fallo(self):
        portal = OracleFalso([{"id": "1", "lugares": [("Ciudad A1, País A", "XA")]}])
        for consulta in ({}, {"facetas": {"CATEGORIES": "x"}}, {"facetas": {"OTRA": ["x"]}}, {"texto": 5},
                         {"ubicaciones": ["Ciudad A1"]}):
            with self.subTest(consulta=consulta):
                r, _ = self.buscar(preferencias([grupo("XA", nombres=["Ciudad A1"])]), portal, consulta=consulta,
                                   codigo_esperado=1)
                self.assertIn("consulta", r["error"])
                self.assertIn("06/CAT-PLATAFORMAS", r["error"])
        self.assertEqual(portal.listados, [])


class ComprobacionesDeOracle(ConPortalFalso):
    BLOQUE = preferencias([grupo("XA", nombres=["Ciudad A1"])])
    EN_XA = [{"id": "1", "lugares": [("Ciudad A1, País A", "XA")]}]

    def test_si_los_ids_unicos_no_igualan_el_total_la_busqueda_queda_incompleta(self):
        r, errores = self.buscar(self.BLOQUE, OracleFalso(self.EN_XA, extra_en_total=1))
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (2, 1, False))
        self.assertIn("[INCOMPLETA] EMP-ACME: 1/2 únicos", errores)

    def test_un_detalle_con_otro_id_deja_la_vacante_con_la_evidencia_del_listado(self):
        r, errores = self.buscar(self.BLOQUE, OracleFalso([{**self.EN_XA[0], "id_en_detalle": "9"}]))
        v = r["vacantes"][0]
        self.assertEqual(v["estado_vigencia"], "Confirmada abierta")
        self.assertIn("otro ID", v["motivo"])
        self.assertIn("revisar vigencia: 1 ", errores)

    def test_si_robots_txt_prohibe_la_api_no_se_usa(self):
        portal = OracleFalso(self.EN_XA, robots="User-agent: *\nDisallow: /hcmRestApi/\n")
        r, errores = self.buscar(self.BLOQUE, portal, codigo_esperado=1)
        self.assertIn("robots.txt", r["error"])
        self.assertEqual(portal.listados, [])

    def test_un_portal_que_no_es_de_oraclerecruitingcloud_sale_como_fallo(self):
        self.escribir(modulo_04(self.BLOQUE), modulo_06({"EMP-ACME": ficha("EMP-ACME", {
            "plataforma": "oraclerecruitingcloud", "portal": "https://empleos.acme.example/jobs", "consulta": None})}))
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("[FALLO] EMP-ACME: ", r.stderr)
        self.assertIn("/hcmUI/CandidateExperience/", r.stderr)


class OccFalso:
    """OCC Mundial ficticio a nivel de red: reemplaza urllib.request.urlopen, así que se ejercita el pedir() real.
    Sirve robots.txt y el listado en HTML.

    Cada anuncio es un dict con id, titulo, ubicacion, empresa, sueldo, clase (las clases extra de su tarjeta, como
    vacancy-card--recomendada) y en: las consultas que lo traen, como
    (término, lugar) con los slugs de la URL; lugar «remoto» es todo el país con el filtro tipo-home-office-remoto, y
    None, todo el país sin filtro. Como el sitio real: por_pagina tarjetas de la consulta por página y su total en
    data-total-offers del <h1>; si la consulta tiene más de una página, las fijas (anuncios que no son de la consulta
    ni cuentan en el total) se repiten al inicio de cada página; la página siguiente a la última llega sin tarjetas
    ni marcador. reto: toda página del listado es el reto «Just a moment…» de Cloudflare, servido con 200; con un
    conjunto de slugs de términos, solo las de esos términos.

    El detalle (/empleo/oferta/<id>) trae el JobPosting del anuncio en JSON-LD, con el «};» final que deja el sitio
    real, y su canonical. publicada: su DatePosted. detalle: lo que responde en su lugar: «404», «abuso» (HTTP 403 con
    el cuerpo «scraping abuse»), «reto» (el reto servido con 200), «reto 403» o «sin jobposting» (una página normal sin
    él) o «403» (un 403 sin señal en el cuerpo). robots None: su robots.txt responde 403 «scraping abuse». Anota en
    detalles los IDs pedidos y en cabeceras las de cada petición."""

    SITIO = "https://www.occ.com.mx"
    RETO = ('<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>'
            '<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script></body></html>')

    def __init__(self, anuncios, fijas=(), por_pagina=20, reto=False, robots="User-agent: *\nDisallow: /cuenta/\n"):
        self.anuncios, self.fijas, self.por_pagina = list(anuncios), list(fijas), por_pagina
        self.reto, self.robots = reto, robots
        self.pedidas, self.listados, self.detalles, self.cabeceras = [], [], [], []

    def tarjeta(self, a):
        return (f'<li class="vacancy-card {a.get("clase", "")}" data-id=\'{a["id"]}\' data-lc="ListOffers">'
                f'<h2 class="vacancy-card__title"><a href="/empleo/oferta/{a["id"]}-puesto">'
                f'{html.escape(a["titulo"])}</a></h2>'
                f'<p class="vacancy-card__company-text">{html.escape(a.get("empresa", "Empresa confidencial"))}</p>'
                f'<p class="vacancy-card__salary">{html.escape(a.get("sueldo", "Sueldo no mostrado"))}</p>'
                f'<p class="vacancy-card__location"><span>{html.escape(a["ubicacion"])}</span>'
                f'<span>{html.escape(a.get("cuando", "Hace 2 días"))}</span></p></li>\n')

    def jobposting(self, a):
        return {"@context": "http://schema.org", "@type": "JobPosting", "Title": a["titulo"],
                "Url": f"{self.SITIO}/empleo/oferta/{a['id']}-", "identifier": {"Value": a.get("id_detalle", a["id"])},
                "DatePosted": a.get("publicada", "2026-11-20"), "ValidThrough": "2027-01-19",
                "EmploymentType": "Tiempo completo",
                "HiringOrganization": {"Name": a.get("empresa", "Empresa confidencial")},
                "JobLocation": {"Address": {"AddressLocality": a.get("localidad", "Ciudad A1"),
                                            "AddressRegion": "Estado A", "AddressCountry": "XA"}},
                "BaseSalary": a.get("sueldo_detalle", {"Currency": "XTS", "Value": {"MinValue": 0, "MaxValue": 0,
                                                                                     "UnitText": "MONTH"}}),
                "Description": a.get("descripcion", "<p>Requisitos:</p><ul><li>SQL</li><li>Python</li></ul>")}

    def detalle(self, req, jid):
        self.detalles.append(jid)
        a = next((a for a in self.anuncios if a["id"] == jid), None)
        modo = a.get("detalle") if a else "404"
        url = req.full_url
        if modo == "404":
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"<html>No encontrada</html>"))
        if modo == "abuso":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"scraping abuse"))
        if modo == "403":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"<html>Forbidden</html>"))
        if modo == "reto 403":
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(self.RETO.encode()))
        if modo == "reto":
            return io.BytesIO(self.RETO.encode())
        jsonld = ("" if modo == "sin jobposting" else
                  f'<script type="application/ld+json">{json.dumps(self.jobposting(a), ensure_ascii=False)};</script>')
        return io.BytesIO((f'<html><head><link rel="canonical" href="{self.SITIO}/empleo/oferta/{jid}">'
                           f'<script type="application/ld+json">{{"@type": "Organization"}}</script>{jsonld}'
                           f'</head><body><h1>{html.escape(a["titulo"])}</h1></body></html>').encode())

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.pedidas.append(url)
        self.cabeceras.append({k.lower(): v for k, v in req.header_items()})
        u = urllib.parse.urlsplit(url)
        if f"{u.scheme}://{u.netloc}" != self.SITIO:
            raise AssertionError(f"petición inesperada: {url}")
        if u.path == "/robots.txt":
            if self.robots is None:
                raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"scraping abuse"))
            return io.BytesIO(self.robots.encode())
        m = re.fullmatch(r"/empleo/oferta/(\d+)", u.path)
        if m:
            return self.detalle(req, m.group(1))
        m = re.fullmatch(r"/empleos/de-([^/]+)/(?:en-([^/]+)/)?(tipo-home-office-remoto/)?", u.path)
        if not m:
            raise AssertionError(f"petición inesperada: {url}")
        q = urllib.parse.parse_qs(u.query)
        if q.get("sort") != ["2"]:
            raise AssertionError(f"el listado debe ir ordenado por fecha (sort=2): {url}")
        termino, lugar, pagina = m.group(1), "remoto" if m.group(3) else m.group(2), int(q.get("page", ["1"])[0])
        self.listados.append((termino, lugar, pagina))
        if self.reto is True or termino in (self.reto or ()):
            return io.BytesIO(self.RETO.encode())
        de_consulta = [a for a in self.anuncios if (termino, lugar) in a["en"]]
        paginas = max(1, -(-len(de_consulta) // self.por_pagina))
        if pagina > paginas:
            return io.BytesIO(b'<html><body><h1 class="title">0 empleos</h1><ul></ul></body></html>')
        tarjetas = (self.fijas if paginas > 1 else []) + de_consulta[(pagina - 1) * self.por_pagina:
                                                                       pagina * self.por_pagina]
        return io.BytesIO((f'<html><body><h1 class="title" data-total-offers="{len(de_consulta)}">{len(de_consulta)} '
                           f'empleos</h1><ul>{"".join(self.tarjeta(a) for a in tarjetas)}</ul></body></html>').encode())


def anuncio_occ(jid, ubicacion, *en, titulo="Analista de datos", **campos):
    return {"id": jid, "titulo": titulo, "ubicacion": ubicacion, "en": list(en), **campos}


class ConOccFalso(CopiaFicticia):
    BOLSA = ficha_bolsa("BOL-01", {"adaptador": "occ", "pais": "XA"})

    def buscar_bolsa(self, bloque_04, occ, bloque_05, *argumentos, empresas=None, bolsas=None, codigo_esperado=0,
                     nube=False):
        """Corre main() del script de la copia con OCC falso como red. empresas: {EMP-ID: portal falso} que se buscan
        junto a la bolsa, con su portal tras la misma red; bolsas: las fichas del catálogo de bolsas (por defecto,
        BOL-01 en OCC); nube: corre como Code en la nube (CLAUDE_CODE_REMOTE=true). Devuelve la salida JSON completa
        y stderr."""
        empresas = empresas or {}
        self.escribir(modulo_04(bloque_04),
                      modulo_06({eid: ficha(eid, {"plataforma": p.PLATAFORMA, "portal": p.PORTAL, "consulta": None})
                                 for eid, p in empresas.items()}, bolsas or {"BOL-01": self.BOLSA}),
                      None if bloque_05 is None else modulo_05(bloque_05))
        especificacion = importlib.util.spec_from_file_location("buscar_copia", self.dir / "herramientas" / "buscar.py")
        script = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(script)
        for p in empresas.values():
            p.script = script

        def red(req, timeout=None):
            if req.full_url.startswith(OccFalso.SITIO):
                return occ(req, timeout)
            portal = next(p for p in empresas.values() if req.full_url.startswith(getattr(p, "HOST", "-")))
            cuerpo = json.loads(req.data) if req.data else None
            respuesta = portal(req.full_url, cuerpo, como_json=req.get_header("Accept") == "application/json")
            return io.BytesIO((respuesta if isinstance(respuesta, str) else json.dumps(respuesta)).encode())

        self.esperas = []
        entorno = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
        if nube:
            entorno["CLAUDE_CODE_REMOTE"] = "true"
        salida, errores, codigo = io.StringIO(), io.StringIO(), 0
        with mock.patch.object(sys, "argv", ["buscar.py", *argumentos]), \
                mock.patch.object(script.urllib.request, "urlopen", red), \
                mock.patch.object(script.time, "sleep", self.esperas.append), \
                mock.patch.dict(os.environ, entorno, clear=True), \
                contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            try:
                script.main()
            except SystemExit as e:
                codigo = e.code
        self.assertEqual(codigo, codigo_esperado, errores.getvalue())
        self.assertNotIn("Traceback", errores.getvalue())
        return json.loads(salida.getvalue()), errores.getvalue()


class BolsaOcc(ConOccFalso):
    EN_A1 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])])
    TERMINOS = terminos(ROL_01=(["analista de datos"], ["analista de datos"]))

    def test_cada_vacante_sale_con_su_bolsa_y_los_campos_literales_de_su_tarjeta(self):
        occ = OccFalso([anuncio_occ("101", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"),
                                    empresa="Empresa confidencial", sueldo="$20,000 - $25,000 Mensual")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        self.assertEqual(salida["empresas"], [])
        r = salida["bolsas"][0]
        self.assertEqual(r["bolsa_id"], "BOL-01")
        v = r["vacantes"][0]
        self.assertEqual({k: v[k] for k in ("bolsa_id", "job_id", "titulo", "empresa_literal", "sueldo_literal",
                                            "ubicacion_literal", "region_relacionada", "modalidad_literal",
                                            "fecha_publicacion", "url_oficial", "estado_vigencia")},
                         {"bolsa_id": "BOL-01", "job_id": "101", "titulo": "Analista de datos",
                          "empresa_literal": "Empresa confidencial", "sueldo_literal": "$20,000 - $25,000 Mensual",
                          "ubicacion_literal": "Ciudad A1, Estado A", "region_relacionada": "Dentro",
                          "modalidad_literal": None, "fecha_publicacion": "2026-11-20",
                          "url_oficial": OccFalso.SITIO + "/empleo/oferta/101",
                          "estado_vigencia": "Confirmada abierta"})
        self.assertNotIn("empresa_id", v)
        # Con una sola página, la siguiente llega sin tarjetas y termina el recorrido; después, el detalle
        self.assertEqual(occ.listados, [("analista-de-datos", "ciudad-a1", 1), ("analista-de-datos", "ciudad-a1", 2)])
        self.assertEqual(occ.detalles, ["101"])
        self.assertIn("[OK] BOL-01: 1/1 únicos; 1 en la región", errores)
        self.assertNotIn("revisar", errores)

    def test_la_cobertura_cuadra_al_descontar_las_tarjetas_fijas_de_cada_pagina(self):
        consulta = ("analista-de-datos", "ciudad-a1")
        fijas = [anuncio_occ(f"9{i}", "Ciudad Z, Estado Z", titulo="Recomendada", clase="vacancy-card--recomendada")
                 for i in range(2)]
        de_consulta = [anuncio_occ(str(100 + i), "Ciudad A1, Estado A", consulta) for i in range(7)]
        occ = OccFalso(de_consulta, fijas=fijas, por_pagina=3)
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (7, 7, True))
        self.assertEqual(sorted(v["job_id"] for v in r["vacantes"]), [str(100 + i) for i in range(7)])
        self.assertEqual(r["fuera_de_region"], [])
        # Con las 7 reunidas en la página 3, no pide la 4
        self.assertEqual(occ.listados, [(*consulta, 1), (*consulta, 2), (*consulta, 3)])
        self.assertIn("[OK] BOL-01: 7/7 únicos", errores)
        # Una pausa antes de cada petición a OCC, salvo la primera (robots.txt): 3 páginas y 7 detalles
        self.assertEqual(self.esperas, [2] * 10)

    def test_con_una_sola_pagina_no_se_descarta_ninguna_tarjeta(self):
        # La primera puede llevar «Recomendada» y ser de la consulta: con una página no se distingue de una fija
        occ = OccFalso([anuncio_occ("101", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"),
                                    clase="vacancy-card--recomendada"),
                        anuncio_occ("102", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"))])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (2, 2, True))
        self.assertEqual([v["job_id"] for v in r["vacantes"]], ["101", "102"])

    def test_el_recorrido_termina_en_la_primera_pagina_sin_tarjetas_aunque_no_llegue_al_total(self):
        consulta = ("analista-de-datos", "ciudad-a1")

        class OccQueSeQuedaCorto(OccFalso):
            def __call__(self, req, timeout=None):
                respuesta = super().__call__(req, timeout)
                cuerpo = respuesta.read().decode()
                return io.BytesIO(cuerpo.replace('data-total-offers="4"', 'data-total-offers="5"').encode())

        occ = OccQueSeQuedaCorto([anuncio_occ(str(100 + i), "Ciudad A1, Estado A", consulta) for i in range(4)],
                                 por_pagina=2)
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (5, 4, False))
        self.assertEqual(occ.listados, [(*consulta, 1), (*consulta, 2), (*consulta, 3)])
        self.assertIn("[INCOMPLETA] BOL-01: 4/5 únicos", errores)

    def test_una_primera_pagina_sin_su_marcador_es_un_fallo_y_no_un_listado_vacio(self):
        class OccSinMarcador(OccFalso):
            def __call__(self, req, timeout=None):
                cuerpo = super().__call__(req, timeout).read().decode()
                return io.BytesIO(re.sub(r' data-total-offers="\d+"', "", cuerpo).encode())

        occ = OccSinMarcador([anuncio_occ("101", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"))])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1)
        r = salida["bolsas"][0]
        self.assertEqual(set(r), {"bolsa_id", "error"})
        self.assertIn("data-total-offers", r["error"])
        self.assertIn("[FALLO] BOL-01: ", errores)
        self.assertEqual(occ.listados, [("analista-de-datos", "ciudad-a1", 1)])

    def busquedas(self, bloque_04, bloque_05=None):
        """Las consultas (término, lugar) que pidió el script, en orden, con OCC sin vacantes."""
        occ = OccFalso([])
        self.buscar_bolsa(bloque_04, occ, bloque_05 or self.TERMINOS)
        return [(t, l) for t, l, _ in occ.listados]

    def test_hay_una_busqueda_por_cada_termino_y_lugar_y_las_remotas_van_primero(self):
        bloque_05 = terminos(ROL_01=(["Analista de datos", "power bi"], []),
                             ROL_02=(["Científico de datos", "analista  de  datos"], []))
        bloque_04 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1", "Municipio Á2"]),
                                  grupo("XB", nombres=["Ciudad B1"])], alcance="cualquiera")
        terminos_05 = ("analista-de-datos", "power-bi", "cientifico-de-datos")
        self.assertEqual(self.busquedas(bloque_04, bloque_05),
                         [(t, "remoto") for t in terminos_05]
                         + [(t, l) for t in terminos_05 for l in ("ciudad-a1", "municipio-a2")])

    def test_un_grupo_de_division_completa_busca_en_cada_division_y_uno_de_pais_completo_en_todo_el_pais(self):
        self.assertEqual(self.busquedas(preferencias([grupo("XA", ["Estado A", "Estado A2"])])),
                         [("analista-de-datos", "estado-a"), ("analista-de-datos", "estado-a2")])
        self.assertEqual(self.busquedas(preferencias([grupo("XA")])), [("analista-de-datos", None)])

    def test_sin_remoto_en_04_no_se_pide_ningun_listado_remoto(self):
        casos = {"ninguno": preferencias([grupo("XA", nombres=["Ciudad A1"])]),
                 "otros países": preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="paises",
                                              paises_remoto=["XB"])}
        for caso, bloque in casos.items():
            with self.subTest(caso):
                self.assertEqual(self.busquedas(bloque), [("analista-de-datos", "ciudad-a1")])

    def test_con_sin_remotas_no_se_pide_el_listado_remoto(self):
        occ = OccFalso([])
        salida, errores = self.buscar_bolsa(preferencias([grupo("XA", nombres=["Ciudad A1"])], alcance="cualquiera"),
                                            occ, self.TERMINOS, "--sin-remotas")
        self.assertEqual([(t, l) for t, l, _ in occ.listados], [("analista-de-datos", "ciudad-a1")])
        self.assertEqual(salida["bolsas"][0]["remotas_revision"], "Omitida (--sin-remotas)")

    def test_solo_remoto_en_el_pais_de_la_bolsa_busca_solo_el_listado_remoto(self):
        bloque = preferencias([], alcance="paises", paises_remoto=["XA"])
        self.assertEqual(self.busquedas(bloque), [("analista-de-datos", "remoto")])

    def test_si_04_no_busca_nada_en_el_pais_de_la_bolsa_la_bolsa_es_un_fallo(self):
        occ = OccFalso([])
        salida, errores = self.buscar_bolsa(preferencias([grupo("XB", nombres=["Ciudad B1"])]), occ, self.TERMINOS,
                                            codigo_esperado=1)
        self.assertIn("XA", salida["bolsas"][0]["error"])
        self.assertEqual(occ.pedidas, [])

    def test_una_vacante_que_aparece_con_varios_terminos_o_lugares_cuenta_una_vez(self):
        bloque_04 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1", "Ciudad A2"])], alcance="cualquiera")
        bloque_05 = terminos(ROL_01=(["analista de datos", "power bi"], []))
        todas = [("analista-de-datos", "remoto"), ("analista-de-datos", "ciudad-a1"), ("power-bi", "ciudad-a2")]
        occ = OccFalso([
            # La remota de la región también sale en los listados por lugar: la dice el filtro remoto
            anuncio_occ("101", "Ciudad A1, Estado A", *todas),
            anuncio_occ("102", "Ciudad A2, Estado A", ("power-bi", "ciudad-a2"), ("analista-de-datos", "ciudad-a1")),
            anuncio_occ("103", "Ciudad Z, Estado Z", ("analista-de-datos", "remoto"), ("power-bi", "remoto")),
            anuncio_occ("104", "Ciudad Y, Estado Y", ("power-bi", "ciudad-a2"))])
        salida, errores = self.buscar_bolsa(bloque_04, occ, bloque_05)
        r = salida["bolsas"][0]
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (4, 4, True))
        modalidades = {v["job_id"]: v["modalidad_literal"] for v in r["vacantes"] + r["remotas_fuera_de_region"]}
        self.assertEqual(modalidades, {"101": "Remoto (filtro tipo-home-office-remoto de OCC)", "102": None,
                                       "103": "Remoto (filtro tipo-home-office-remoto de OCC)"})
        self.assertEqual([v["job_id"] for v in r["remotas_fuera_de_region"]], ["103"])
        self.assertEqual(r["fuera_de_region"], ["Ciudad Y, Estado Y"])
        self.assertIn("[OK] BOL-01: 4/4 únicos; 2 en la región; remotas fuera de la región: 1", errores)

    def test_con_el_bloque_de_05_vacio_o_sin_llenar_falla_solo_la_bolsa_y_las_empresas_se_buscan_igual(self):
        en_xa = {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]}
        casos = {"vacío": {}, "sin términos": terminos(ROL_01=([], ["analista de datos"])),
                 "sin sección": "sin sección", "sin 05": None}
        for caso, bloque_05 in casos.items():
            with self.subTest(caso):
                (self.dir / "05_MAPA_HABILIDADES_Y_ROLES.md").unlink(missing_ok=True)
                occ = OccFalso([])
                if bloque_05 == "sin sección":
                    self.escribir(modulo_05_texto="# 05\n\n## HAB-ROLES\n\n- Familias.\n")
                    bloque_05 = None
                salida, errores = self.buscar_bolsa(self.EN_A1, occ, bloque_05,
                                                    empresas={"EMP-ACME": WorkdayFalso([en_xa])}, codigo_esperado=1)
                self.assertEqual(occ.pedidas, [])
                self.assertIn("05_MAPA_HABILIDADES_Y_ROLES.md", salida["bolsas"][0]["error"])
                self.assertIn("[FALLO] BOL-01: ", errores)
                if caso != "sin 05":
                    self.assertIn("HAB-TERMINOS", salida["bolsas"][0]["error"])
                    self.assertIn("/configurar", salida["bolsas"][0]["error"])
                self.assertIn("[OK] EMP-ACME: 1/1 únicos", errores)
                self.assertEqual([v["job_id"] for v in salida["empresas"][0]["vacantes"]], ["R-1"])

    def test_un_bloque_de_05_mal_formado_falla_solo_la_bolsa_con_un_mensaje_claro(self):
        casos = {"JSON inválido": '{"ROL-01": {},}', "lista": '["analista de datos"]',
                 "sin titulos": '{"ROL-01": {"terminos": ["analista"]}}',
                 "clave que no es ROL": '{"Analistas": {"terminos": ["analista"], "titulos": []}}'}
        for caso, texto in casos.items():
            with self.subTest(caso):
                salida, errores = self.buscar_bolsa(self.EN_A1, OccFalso([]), texto, codigo_esperado=1)
                self.assertIn("HAB-TERMINOS", salida["bolsas"][0]["error"])

    def test_los_ids_eligen_empresas_y_bolsas_y_sin_ellos_se_recorren_los_dos_catalogos(self):
        en_xa = {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]}
        for argumentos, empresas, bolsas in (((), ["EMP-ACME"], ["BOL-01"]), (("bol-01",), [], ["BOL-01"]),
                                             (("EMP-ACME",), ["EMP-ACME"], [])):
            with self.subTest(argumentos):
                salida, _ = self.buscar_bolsa(self.EN_A1, OccFalso([]), self.TERMINOS, *argumentos,
                                              empresas={"EMP-ACME": WorkdayFalso([en_xa])})
                self.assertEqual([r["empresa_id"] for r in salida["empresas"]], empresas)
                self.assertEqual([r["bolsa_id"] for r in salida["bolsas"]], bolsas)

    def test_un_id_desconocido_falla_y_nombra_las_empresas_y_las_bolsas_que_hay(self):
        self.escribir(modulo_04(self.EN_A1),
                      modulo_06({"EMP-ACME": ficha("EMP-ACME", {"plataforma": "workday", "portal": "https://x"})},
                                {"BOL-01": self.BOLSA}), modulo_05(self.TERMINOS))
        r = self.correr("BOL-02")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(r.stdout, "")
        for texto in ("BOL-02", "EMP-ACME", "BOL-01"):
            self.assertIn(texto, r.stderr)

    def test_una_ficha_de_bolsa_sin_configuracion_usable_sale_como_fallo(self):
        casos = {"sin adaptador": {"pais": "XA"}, "adaptador desconocido": {"adaptador": "otra", "pais": "XA"},
                 "país inválido": {"adaptador": "occ", "pais": "País A"}, "sin ficha": None}
        for caso, conf in casos.items():
            with self.subTest(caso):
                bolsas = {"BOL-01": "" if conf is None else ficha_bolsa("BOL-01", conf)}
                salida, errores = self.buscar_bolsa(self.EN_A1, OccFalso([]), self.TERMINOS, bolsas=bolsas,
                                                    codigo_esperado=1)
                self.assertIn("[FALLO] BOL-01: ", errores)
                self.assertIn("06", salida["bolsas"][0]["error"])

    def test_si_la_primera_pagina_llena_el_total_con_las_fijas_sigue_a_la_siguiente(self):
        # 2 fijas + 3 de la consulta en la página 1 suman el total de 5: sin la página 2 no se distinguen las fijas
        consulta = ("analista-de-datos", "ciudad-a1")
        fijas = [anuncio_occ(f"9{i}", "Ciudad Z, Estado Z", titulo="Recomendada") for i in range(2)]
        occ = OccFalso([anuncio_occ(str(100 + i), "Ciudad A1, Estado A", consulta) for i in range(5)], fijas=fijas,
                       por_pagina=3)
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (5, 5, True))
        self.assertEqual(sorted(v["job_id"] for v in r["vacantes"]), [str(100 + i) for i in range(5)])
        self.assertEqual(r["fuera_de_region"], [])

    def test_una_vacante_que_trae_el_filtro_remoto_de_otro_termino_sale_remota(self):
        bloque_04 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])], alcance="cualquiera")
        bloque_05 = terminos(ROL_01=(["analista de datos", "power bi"], []))
        occ = OccFalso([anuncio_occ("101", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"),
                                    ("power-bi", "remoto"))])
        salida, _ = self.buscar_bolsa(bloque_04, occ, bloque_05)
        v = salida["bolsas"][0]["vacantes"][0]
        self.assertEqual(v["modalidad_literal"], "Remoto (filtro tipo-home-office-remoto de OCC)")


class FiltroPorTitulo(ConOccFalso):
    EN_A1 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])])
    TERMINOS = terminos(ROL_01=(["analista de datos"], ["analista de datos", "analista bi"]),
                        ROL_02=(["power bi"], ["desarrollador power bi"]))

    def test_cada_vacante_se_clasifica_por_su_titulo_y_el_ruido_solo_se_cuenta(self):
        consulta = ("analista-de-datos", "ciudad-a1")
        titulos = {"101": "Analista de Datos Sr.", "102": "Desarrollador Power BI / Analista BI",
                   # Todas las palabras significativas del término, en otro orden o sin «de»: dudosas
                   "103": "Analista de Estrategia y Datos", "104": "Analista Comercial (Datos)",
                   # Le falta «datos»: ruido
                   "105": "Analista contable", "106": "Ejecutivo de ventas"}
        occ = OccFalso([anuncio_occ(j, "Ciudad A1, Estado A", consulta, titulo=t) for j, t in titulos.items()])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual({v["job_id"]: (v["clasificacion_titulo"], v["familias_rol"]) for v in r["vacantes"]},
                         {"101": ("encaja", ["ROL-01"]), "102": ("encaja", ["ROL-01", "ROL-02"]),
                          "103": ("dudosa", []), "104": ("dudosa", [])})
        self.assertEqual([v["job_id"] for v in r["vacantes"]], ["101", "102", "103", "104"])
        # El ruido cuenta en la cobertura, pero no se entrega ni deja su ubicación
        self.assertEqual((r["total_reportado"], r["unicos"], r["completa"]), (6, 6, True))
        self.assertEqual((r["remotas_fuera_de_region"], r["fuera_de_region"]), ([], []))
        self.assertEqual(r["clasificacion_titulos"], {"encajan": 2, "dudosas": 2, "ruido": 2})
        self.assertIn("[OK] BOL-01: 6/6 únicos; 4 en la región; remotas fuera de la región: 0 (No aplica: 04 no "
                      "acepta remoto); títulos: 2 encajan, 2 dudosas, 2 ruido", errores)
        lineas = [linea for linea in errores.splitlines() if "revisar título" in linea]
        self.assertEqual(len(lineas), 2, errores)
        self.assertIn("revisar título: 103 «Analista de Estrategia y Datos»", lineas[0])
        self.assertIn("«analista de datos»", lineas[0])
        self.assertIn("revisar título: 104 «Analista Comercial (Datos)»", lineas[1])
        for ruido in ("105", "106"):
            self.assertNotIn(ruido, errores)

    def test_el_rendimiento_por_termino_cuadra_con_lo_listado(self):
        bloque_04 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])], alcance="cualquiera")
        bloque_05 = terminos(ROL_01=(["Analista de datos", "analista  de  datos"], ["analista de datos"]),
                             ROL_02=(["power bi"], ["power bi"]))
        analista, power = ("analista-de-datos", "ciudad-a1"), ("power-bi", "ciudad-a1")
        occ = OccFalso([
            # Repetida entre los dos términos, encaja solo con ROL-01: cuenta en el rendimiento de los dos
            anuncio_occ("101", "Ciudad A1, Estado A", analista, power),
            anuncio_occ("102", "Ciudad A1, Estado A", analista, titulo="Analista de Estrategia y Datos"),
            # Encaja, pero fuera de la región: no es candidata
            anuncio_occ("103", "Ciudad Y, Estado Y", analista),
            anuncio_occ("104", "Ciudad A1, Estado A", power, titulo="Recepcionista"),
            # Remota fuera de la región, en el alcance: candidata
            anuncio_occ("105", "Ciudad Z, Estado Z", ("power-bi", "remoto"), titulo="Consultor Power BI"),
            # Dudosa fuera de la región: ni candidata ni línea «revisar título»
            anuncio_occ("106", "Ciudad Y, Estado Y", power, titulo="Especialista BI Power Platform")])
        salida, errores = self.buscar_bolsa(bloque_04, occ, bloque_05)
        r = salida["bolsas"][0]
        self.assertEqual(r["terminos"], ["Analista de datos", "power bi"])
        self.assertEqual(r["rendimiento"], {
            "Analista de datos": {"traidas": 3, "encajan": 2, "dudosas": 1, "candidatas": 2},
            "power bi": {"traidas": 4, "encajan": 2, "dudosas": 1, "candidatas": 2}})
        self.assertEqual(r["unicos"], 6)
        self.assertEqual(r["clasificacion_titulos"], {"encajan": 3, "dudosas": 2, "ruido": 1})
        candidatas = sorted(v["job_id"] for v in r["vacantes"] + r["remotas_fuera_de_region"])
        self.assertEqual(candidatas, ["101", "102", "105"])
        self.assertEqual(sorted(r["fuera_de_region"]), ["Ciudad Y, Estado Y"])
        self.assertIn("títulos: 3 encajan, 2 dudosas, 1 ruido", errores)
        self.assertIn("revisar título: 102 ", errores)
        self.assertNotIn("106", errores)

    def test_una_bolsa_sin_vacantes_reporta_cada_termino_en_cero(self):
        salida, errores = self.buscar_bolsa(self.EN_A1, OccFalso([]), self.TERMINOS)
        r = salida["bolsas"][0]
        cero = {"traidas": 0, "encajan": 0, "dudosas": 0, "candidatas": 0}
        self.assertEqual(r["rendimiento"], {"analista de datos": cero, "power bi": cero})
        self.assertIn("títulos: 0 encajan, 0 dudosas, 0 ruido", errores)


class DetalleHastaLaSenal(ConOccFalso):
    EN_A1 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1"])])
    TERMINOS = terminos(ROL_01=(["analista de datos"], ["analista de datos"]))
    CONSULTA = ("analista-de-datos", "ciudad-a1")

    def anuncio(self, jid, **campos):
        return anuncio_occ(jid, "Ciudad A1, Estado A", self.CONSULTA, **campos)

    def detalle_url(self, jid):
        return f"{OccFalso.SITIO}/empleo/oferta/{jid}"

    def test_el_detalle_de_la_candidata_da_descripcion_fecha_empresa_ubicacion_y_sueldo(self):
        occ = OccFalso([
            self.anuncio("101", empresa="Empresa Uno", publicada="2026-11-18", localidad="Ciudad A1",
                         sueldo_detalle={"Currency": "XTS", "Value": {"MinValue": 20000, "MaxValue": 25000,
                                                                       "UnitText": "MONTH"}}),
            # Ruido y una que encaja fuera de la región: no son candidatas y no se pide su detalle
            self.anuncio("102", titulo="Ejecutivo de ventas"),
            anuncio_occ("103", "Ciudad Y, Estado Y", self.CONSULTA)])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, ["101"])
        v = r["vacantes"][0]
        self.assertEqual({k: v[k] for k in ("titulo", "fecha_publicacion", "empresa_literal", "ubicacion_detalle",
                                            "sueldo_detalle", "tipo_empleo", "url_oficial", "estado_vigencia",
                                            "estado_detalle")},
                         {"titulo": "Analista de datos", "fecha_publicacion": "2026-11-18",
                          "empresa_literal": "Empresa Uno",
                          "ubicacion_detalle": {"localidad": "Ciudad A1", "division": "Estado A", "pais": "XA"},
                          "sueldo_detalle": "20,000 - 25,000 XTS (MONTH)", "tipo_empleo": "Tiempo completo",
                          "url_oficial": self.detalle_url("101"), "estado_vigencia": "Confirmada abierta",
                          "estado_detalle": "leido"})
        self.assertEqual(v["descripcion"], "Requisitos:\n- SQL\n- Python")
        self.assertIn("detalle leído", v["motivo"])
        # ValidThrough no es vigencia: no llega a la salida
        self.assertNotIn("2027-01-19", json.dumps(salida))
        self.assertEqual(r["detalle"], {"candidatas": 1, "anteriores": 0, "pedidos": 1, "leidos": 1, "bloqueo": None,
                                        "freno": None})
        self.assertIn("[OK] BOL-01: ", errores)

    def test_un_sueldo_0_0_en_el_detalle_es_no_publicado(self):
        occ = OccFalso([self.anuncio("101")])
        salida, _ = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        self.assertEqual(salida["bolsas"][0]["vacantes"][0]["sueldo_detalle"], "No publicado")

    def test_primero_las_que_encajan_y_despues_las_dudosas_cada_grupo_de_la_mas_nueva_a_la_mas_vieja(self):
        dudosa = "Analista de Estrategia y Datos"
        occ = OccFalso([self.anuncio("201", titulo=dudosa, cuando="Hoy"),
                        self.anuncio("202", cuando="Hace 2 semanas"),
                        self.anuncio("203", cuando="Ayer"),
                        self.anuncio("204", titulo=dudosa, cuando="Hace 3 días"),
                        self.anuncio("205", cuando="Hace 1 mes"),
                        self.anuncio("206", cuando="Hace 5 horas")])
        salida, _ = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        self.assertEqual(occ.detalles, ["206", "203", "202", "205", "201", "204"])
        # Con su pausa antes de cada petición: 2 páginas del listado y 6 detalles
        self.assertEqual(self.esperas, [2] * 8)
        self.assertEqual(salida["bolsas"][0]["detalle"]["leidos"], 6)

    def test_un_404_de_detalle_deja_la_vacante_no_verificable_y_sigue(self):
        occ = OccFalso([self.anuncio("301", cuando="Hoy", detalle="404"), self.anuncio("302", cuando="Ayer")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, ["301", "302"])
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        self.assertEqual(vacantes["301"]["estado_vigencia"], "No verificable")
        self.assertIn("404", vacantes["301"]["motivo"])
        self.assertEqual(vacantes["301"]["estado_detalle"], "no verificable")
        self.assertEqual(vacantes["302"]["estado_detalle"], "leido")
        self.assertEqual(r["detalle"], {"candidatas": 2, "anteriores": 0, "pedidos": 2, "leidos": 1, "bloqueo": None,
                                        "freno": None})
        self.assertIn("revisar vigencia: 301 ", errores)
        self.assertNotIn("[FALLO]", errores)

    def test_un_detalle_con_otro_id_o_sin_jobposting_no_detiene_la_bolsa(self):
        occ = OccFalso([self.anuncio("401", cuando="Hoy", id_detalle="499"),
                        self.anuncio("402", cuando="Ayer", detalle="sin jobposting"),
                        self.anuncio("403", cuando="Hace 2 días")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, ["401", "402", "403"])
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        self.assertEqual((vacantes["401"]["estado_vigencia"], vacantes["401"]["estado_detalle"]),
                         ("No verificable", "no verificable"))
        self.assertIn("devolvió otro ID", vacantes["401"]["motivo"])
        self.assertEqual((vacantes["402"]["estado_vigencia"], vacantes["402"]["estado_detalle"]),
                         ("Confirmada abierta", "pendiente"))
        self.assertIn("revisar: 402 ", errores)
        self.assertEqual(vacantes["403"]["estado_detalle"], "leido")
        self.assertEqual(r["detalle"]["bloqueo"], None)

    def test_scraping_abuse_en_la_segunda_peticion_detiene_la_bolsa_sin_pedir_la_tercera(self):
        occ = OccFalso([self.anuncio("501", cuando="Hoy"), self.anuncio("502", cuando="Ayer", detalle="abuso"),
                        self.anuncio("503", cuando="Hace 2 días")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, ["501", "502"])
        # Sin reintento: la petición bloqueada es la última que recibe OCC
        self.assertEqual(occ.pedidas[-1], self.detalle_url("502"))
        self.assertEqual(occ.pedidas.count(self.detalle_url("502")), 1)
        # Lo listado y lo leído se entregan
        self.assertEqual({v["job_id"]: v["estado_detalle"] for v in r["vacantes"]},
                         {"501": "leido", "502": "pendiente", "503": "pendiente"})
        self.assertEqual((r["unicos"], r["total_reportado"]), (3, 3))
        self.assertEqual(r["detalle"], {"candidatas": 3, "anteriores": 0, "pedidos": 2, "leidos": 1, "freno": None,
                                        "bloqueo": {"en": "detalle", "peticion": 2, "tipo": "scraping abuse, HTTP 403",
                                                    "url": self.detalle_url("502")}})
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] BOL-01: "))
        for texto in ("señal anti-bot", "scraping abuse", "en el detalle", "1 de 3 detalles", "no se reintenta"):
            self.assertIn(texto, fallo)
        self.assertNotIn("Code local", fallo)
        self.assertIn("3/3 únicos", errores)

    def test_un_reto_en_el_detalle_tambien_es_la_senal_con_200_o_con_403(self):
        for modo, tipo in (("reto", "reto de Cloudflare, HTTP 200"), ("reto 403", "reto de Cloudflare, HTTP 403")):
            with self.subTest(modo):
                occ = OccFalso([self.anuncio("601", cuando="Hoy", detalle=modo), self.anuncio("602", cuando="Ayer")])
                salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1)
                r = salida["bolsas"][0]
                self.assertEqual(occ.detalles, ["601"])
                self.assertEqual(r["detalle"]["bloqueo"], {"en": "detalle", "peticion": 1, "tipo": tipo,
                                                           "url": self.detalle_url("601")})
                self.assertIn("0 de 2 detalles", r["error"])

    def test_un_403_sin_senal_en_el_cuerpo_tambien_detiene_la_bolsa(self):
        occ = OccFalso([self.anuncio("651", cuando="Hoy", detalle="403"), self.anuncio("652", cuando="Ayer")])
        salida, _ = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1)
        self.assertEqual(occ.detalles, ["651"])
        self.assertEqual(salida["bolsas"][0]["detalle"]["bloqueo"]["tipo"],
                         "sin señal reconocible en el cuerpo, HTTP 403")

    def test_la_senal_en_el_robots_txt_es_un_bloqueo_en_el_listado(self):
        occ = OccFalso([self.anuncio("661")], robots=None)
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1, nube=True)
        r = salida["bolsas"][0]
        self.assertEqual(occ.pedidas, [OccFalso.SITIO + "/robots.txt"])
        self.assertEqual(r["detalle"]["bloqueo"]["en"], "listado")
        self.assertEqual(r["detalle"]["bloqueo"]["peticion"], 1)
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] BOL-01: "))
        self.assertIn("en el listado", fallo)
        self.assertIn("busca esta bolsa en Code local", fallo)

    def test_un_reto_en_el_listado_entrega_lo_listado_y_no_pide_detalles(self):
        bloque_05 = terminos(ROL_01=(["analista de datos", "power bi"], ["analista de datos"]))
        occ = OccFalso([self.anuncio("701")], reto={"power-bi"})
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, bloque_05, codigo_esperado=1)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, [])
        self.assertEqual(occ.listados[-1], ("power-bi", "ciudad-a1", 1))
        self.assertEqual([v["job_id"] for v in r["vacantes"]], ["701"])
        self.assertEqual(r["vacantes"][0]["estado_detalle"], "pendiente")
        self.assertFalse(r["completa"])
        self.assertEqual(r["detalle"]["bloqueo"]["en"], "listado")
        self.assertEqual(r["detalle"]["bloqueo"]["tipo"], "reto de Cloudflare, HTTP 200")
        self.assertEqual((r["detalle"]["pedidos"], r["detalle"]["leidos"]), (0, 0))
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] BOL-01: "))
        self.assertIn("en el listado", fallo)
        self.assertIn("0 de 1 detalles", fallo)

    def test_las_empresas_se_buscan_igual_con_la_bolsa_bloqueada(self):
        en_xa = {"id": "R-1", "pais": "País A", "ubicaciones": ["Ciudad A1, País A"]}
        occ = OccFalso([self.anuncio("801", detalle="abuso")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1,
                                            empresas={"EMP-ACME": WorkdayFalso([en_xa])})
        self.assertIn("[FALLO] BOL-01: ", errores)
        self.assertIn("[OK] EMP-ACME: 1/1 únicos", errores)
        self.assertEqual([v["job_id"] for v in salida["empresas"][0]["vacantes"]], ["R-1"])
        self.assertEqual([v["job_id"] for v in salida["bolsas"][0]["vacantes"]], ["801"])

    def test_en_code_en_la_nube_el_bloqueo_manda_a_buscar_la_bolsa_en_code_local(self):
        occ = OccFalso([self.anuncio("901", detalle="abuso")])
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, codigo_esperado=1, nube=True)
        fallo = next(linea for linea in errores.splitlines() if linea.startswith("[FALLO] BOL-01: "))
        self.assertIn("busca esta bolsa en Code local", fallo)
        self.assertEqual(occ.detalles, ["901"])

    def test_nunca_envia_cookies_ni_credenciales_a_la_bolsa(self):
        occ = OccFalso([self.anuncio("1001"), self.anuncio("1002", detalle="404")])
        self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        self.assertGreater(len(occ.cabeceras), 3)
        for cabeceras in occ.cabeceras:
            self.assertFalse({"cookie", "authorization", "proxy-authorization"} & set(cabeceras), cabeceras)


def estado_de_bolsas(copia, **bolsas):
    """El JSON de estado que da `registros.py estado-bolsas` para la copia: {BOL_ID: (con detalle o evaluación,
    pendientes, bloqueos seguidos)}."""
    return {"formato": "estado-bolsas", "version": 1, "copia": os.path.realpath(copia),
            "generado": "2026-11-22 10:00",
            "bolsas": {bid.replace("_", "-"): {"con_detalle_o_evaluacion": list(con), "pendientes": list(pendientes),
                                               "bloqueos_seguidos": bloqueos}
                       for bid, (con, pendientes, bloqueos) in bolsas.items()}}


class ReanudacionYFreno(ConOccFalso):
    """--estado: el detalle se retoma con las que siguen sin él, y el freno tras dos bloqueos seguidos (ADR 0010)."""

    EN_A1 = DetalleHastaLaSenal.EN_A1
    TERMINOS = DetalleHastaLaSenal.TERMINOS
    anuncio = DetalleHastaLaSenal.anuncio
    CONSULTA = DetalleHastaLaSenal.CONSULTA

    def anuncios(self):
        return [self.anuncio("101", cuando="Hoy"), self.anuncio("102", cuando="Ayer"),
                self.anuncio("103", cuando="Hace 2 días"), self.anuncio("104", titulo="Ejecutivo de ventas")]

    def con_estado(self, **bolsas):
        ruta = self.dir / "estado.json"
        ruta.write_text(json.dumps(estado_de_bolsas(self.dir, **bolsas), ensure_ascii=False), encoding="utf-8")
        return ruta

    def test_con_estado_solo_pide_el_detalle_de_las_que_siguen_sin_el(self):
        occ = OccFalso(self.anuncios())
        estado = self.con_estado(BOL_01=(["101", "999"], ["102", "103"], 0))
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, "--estado", str(estado))
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, ["102", "103"])
        vacantes = {v["job_id"]: v for v in r["vacantes"]}
        # La que ya tiene detalle se entrega con lo de su tarjeta, sin pedirlo
        self.assertEqual(vacantes["101"]["estado_detalle"], "anterior")
        self.assertIn("búsqueda anterior", vacantes["101"]["motivo"])
        self.assertIsNone(vacantes["101"]["descripcion"])
        self.assertEqual(r["detalle"], {"candidatas": 2, "anteriores": 1, "pedidos": 2, "leidos": 2, "bloqueo": None,
                                        "freno": None})
        # El rendimiento sigue contando lo listado
        self.assertEqual(r["rendimiento"]["analista de datos"]["candidatas"], 3)
        self.assertIn("detalle: 2 leídos de 2 candidatas (1 con detalle o evaluación de búsquedas anteriores)",
                      errores)
        self.assertNotIn("revisar vigencia: 101", errores)

    def test_sin_estado_pide_el_de_todas_las_candidatas(self):
        occ = OccFalso(self.anuncios())
        salida, _ = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS)
        self.assertEqual(occ.detalles, ["101", "102", "103"])
        self.assertEqual(salida["bolsas"][0]["detalle"]["anteriores"], 0)

    def test_con_dos_bloqueos_seguidos_no_pide_detalles_pero_lee_el_listado(self):
        occ = OccFalso(self.anuncios())
        estado = self.con_estado(BOL_01=(["101"], ["102", "103"], 2))
        salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, "--estado", str(estado))
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, [])
        self.assertEqual(occ.listados, [("analista-de-datos", "ciudad-a1", 1), ("analista-de-datos", "ciudad-a1", 2)])
        self.assertEqual((r["unicos"], r["total_reportado"]), (4, 4))
        self.assertEqual({v["job_id"]: v["estado_detalle"] for v in r["vacantes"]},
                         {"101": "anterior", "102": "pendiente", "103": "pendiente"})
        self.assertEqual((r["detalle"]["pedidos"], r["detalle"]["candidatas"]), (0, 2))
        self.assertIn("2 búsquedas seguidas", r["detalle"]["freno"])
        self.assertNotIn("error", r)
        linea = next(linea for linea in errores.splitlines() if linea.startswith("[OK] BOL-01: "))
        for texto in ("freno activo", "ninguno pedido de 2 pendientes", "2 búsquedas seguidas", "--sin-freno"):
            self.assertIn(texto, linea)

    def test_con_un_bloqueo_o_con_sin_freno_si_pide_los_pendientes(self):
        for bloqueos, argumentos in ((1, ()), (3, ("--sin-freno",))):
            with self.subTest(bloqueos=bloqueos):
                occ = OccFalso(self.anuncios())
                estado = self.con_estado(BOL_01=(["101"], ["102", "103"], bloqueos))
                salida, errores = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, "--estado", str(estado),
                                                    *argumentos)
                self.assertEqual(occ.detalles, ["102", "103"])
                self.assertIsNone(salida["bolsas"][0]["detalle"]["freno"])
                self.assertNotIn("freno activo", errores)

    def test_una_bolsa_que_el_estado_no_trae_pide_todas_sus_candidatas(self):
        occ = OccFalso(self.anuncios())
        estado = self.con_estado(BOL_02=(["101"], [], 2))
        salida, _ = self.buscar_bolsa(self.EN_A1, occ, self.TERMINOS, "--estado", str(estado))
        self.assertEqual(occ.detalles, ["101", "102", "103"])

    def test_un_estado_mal_formado_de_otra_copia_o_que_falta_falla_sin_buscar(self):
        self.escribir(modulo_04(self.EN_A1), modulo_06({}, {"BOL-01": self.BOLSA}), modulo_05(self.TERMINOS))
        bueno = estado_de_bolsas(self.dir, BOL_01=(["101"], [], 0))
        otra = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, otra)
        casos = {
            "no es JSON": ("{", "no es JSON válido"),
            "otro formato": ({"bolsas": {}}, "registros.py estado-bolsas"),
            "otra versión": (bueno | {"version": 2}, "versión"),
            "otra copia": (estado_de_bolsas(otra, BOL_01=([], [], 0)), "otra copia"),
            "bloqueos no numéricos": (bueno | {"bolsas": {"BOL-01": bueno["bolsas"]["BOL-01"]
                                                          | {"bloqueos_seguidos": "2"}}}, "BOL-01"),
            "IDs que no son texto": (bueno | {"bolsas": {"BOL-01": bueno["bolsas"]["BOL-01"]
                                                         | {"pendientes": [101]}}}, "BOL-01"),
        }
        for caso, (contenido, texto) in casos.items():
            with self.subTest(caso):
                ruta = self.dir / "estado.json"
                ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
                r = self.correr("--estado", str(ruta))
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("--estado", r.stderr)
                self.assertIn(texto, r.stderr)
                self.assertEqual(r.stdout, "")
        r = self.correr("--estado", str(self.dir / "no-existe.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no-existe.json", r.stderr)
        r = self.correr("--sin-freno")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--sin-freno", r.stderr)
        self.assertIn("--estado", r.stderr)


class ExploracionDeTerminos(ConOccFalso):
    """--explorar: lista términos nuevos en una bolsa, sin detalle, y solo reporta su rendimiento (07/BUS-BOLSAS)."""

    BLOQUE_04 = preferencias([grupo("XA", ["Estado A"], ["Ciudad A1", "Ciudad A2"])], alcance="cualquiera")
    TERMINOS = terminos(ROL_01=(["analista de datos"], ["analista de datos", "analista bi"]))

    def test_lista_solo_los_terminos_explorados_en_los_lugares_de_04_sin_pedir_detalles(self):
        bi, a2 = ("analista-bi", "ciudad-a1"), ("analista-bi", "ciudad-a2")
        occ = OccFalso([
            anuncio_occ("101", "Ciudad A1, Estado A", bi, titulo="Analista BI"),
            anuncio_occ("102", "Ciudad A2, Estado A", a2, ("analista-bi", "remoto"), titulo="Analista BI Sr."),
            anuncio_occ("103", "Ciudad A1, Estado A", bi, ("ciencia-de-datos", "ciudad-a1"),
                        titulo="Científico de datos"),
            anuncio_occ("104", "Ciudad Y, Estado Y", bi, titulo="Analista BI"),
            anuncio_occ("105", "Ciudad A1, Estado A", bi, titulo="Recepcionista"),
            # Del término de 05, que la exploración no lista
            anuncio_occ("106", "Ciudad A1, Estado A", ("analista-de-datos", "ciudad-a1"))])
        salida, errores = self.buscar_bolsa(self.BLOQUE_04, occ, self.TERMINOS, "BOL-01", "--explorar", "Analista BI",
                                            "ciencia de datos", "analista  bi")
        self.assertEqual(occ.detalles, [])
        self.assertEqual(sorted({(t, lugar) for t, lugar, _ in occ.listados}), [
            ("analista-bi", "ciudad-a1"), ("analista-bi", "ciudad-a2"), ("analista-bi", "remoto"),
            ("ciencia-de-datos", "ciudad-a1"), ("ciencia-de-datos", "ciudad-a2"), ("ciencia-de-datos", "remoto")])
        self.assertEqual(salida["exploracion"], {"bolsa_id": "BOL-01", "terminos": ["Analista BI", "ciencia de datos"]})
        r = salida["bolsas"][0]
        self.assertEqual(r["terminos"], ["Analista BI", "ciencia de datos"])
        # Las dos del término repetido cuentan una vez; «Científico de datos» no trae «ciencia»: ruido; 104 encaja
        # fuera de la región: no es candidata; 106 solo la trae el término de 05
        self.assertEqual(r["rendimiento"], {
            "Analista BI": {"traidas": 5, "encajan": 3, "dudosas": 0, "candidatas": 2},
            "ciencia de datos": {"traidas": 1, "encajan": 0, "dudosas": 0, "candidatas": 0}})
        self.assertIsNone(r["detalle"])
        self.assertNotIn("error", r)
        self.assertTrue(all(v["estado_detalle"] == "pendiente" for v in r["vacantes"] + r["remotas_fuera_de_region"]))
        self.assertIn("exploración", errores.lower())
        self.assertIn("«Analista BI»: 5 traídas, 3 encajan, 0 dudosas, 2 candidatas", errores)
        self.assertIn("«ciencia de datos»: 1 traídas, 0 encajan, 0 dudosas, 0 candidatas", errores)
        self.assertNotIn("revisar vigencia", errores)

    def test_una_senal_en_el_listado_detiene_la_exploracion_con_lo_listado(self):
        occ = OccFalso([anuncio_occ("101", "Ciudad A1, Estado A", ("analista-bi", "remoto"), titulo="Analista BI")],
                       reto={"ciencia-de-datos"})
        salida, errores = self.buscar_bolsa(self.BLOQUE_04, occ, self.TERMINOS, "BOL-01", "--explorar", "analista bi",
                                            "ciencia de datos", codigo_esperado=1)
        r = salida["bolsas"][0]
        self.assertEqual(occ.detalles, [])
        self.assertIn("en el listado", r["error"])
        self.assertNotIn("detalles", r["error"])
        self.assertFalse(r["completa"])
        self.assertEqual(r["rendimiento"]["analista bi"]["traidas"], 1)
        self.assertIn("exploracion", salida)
        self.assertIn("[FALLO] BOL-01", errores)

    def test_sin_exploracion_la_salida_no_lleva_el_marcador(self):
        salida, _ = self.buscar_bolsa(self.BLOQUE_04, OccFalso([]), self.TERMINOS)
        self.assertNotIn("exploracion", salida)

    def test_explorar_pide_un_solo_id_de_bolsa_y_no_vale_con_estado(self):
        self.escribir(modulo_04(self.BLOQUE_04), modulo_06({"EMP-01": ficha("EMP-01", {"plataforma": "workday"})},
                                                            {"BOL-01": self.BOLSA, "BOL-02": self.BOLSA}),
                      modulo_05(self.TERMINOS))
        casos = {"sin ID": ("--explorar", "x"), "una empresa": ("EMP-01", "--explorar", "x"),
                 "dos bolsas": ("BOL-01", "BOL-02", "--explorar", "x"),
                 "con estado": ("BOL-01", "--estado", "e.json", "--explorar", "x"),
                 "término vacío": ("BOL-01", "--explorar", " ")}
        for caso, argumentos in casos.items():
            with self.subTest(caso):
                r = self.correr(*argumentos)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("--explorar", r.stderr)
                self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
