"""Pruebas del generador de CV, por su línea de comandos y sin red.

Uso, con el Python del entorno virtual de la copia, que tiene las bibliotecas del CV (CONTRIBUTING, «Pruebas»):
    .venv/bin/python -I -B -m unittest discover -s herramientas/pruebas

Las que generan el CV se saltan si faltan fpdf2, python-docx, pypdf o pypdfium2. Las que revisan los
errores de 09 no las necesitan: el script lee 09 antes de cargarlas.
"""
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "herramientas" / "generar_cv.py"
FUENTES = RAIZ / "herramientas" / "fuentes"
BIBLIOTECAS_CV = ("fpdf", "docx", "pypdf", "pypdfium2")
FALTAN_BIBLIOTECAS = any(importlib.util.find_spec(m) is None for m in BIBLIOTECAS_CV)
SALTO = "faltan las bibliotecas del CV: corre las pruebas con el Python del entorno virtual"

CV_MINIMO = """### Encabezado

**Nombre Apellido**
**Título descriptivo**
Ciudad, País · <nombre@example.com>

### Experiencia profesional

**Empresa — Cargo**
Ciudad, País · 2020–actualidad

- Responsabilidad con su resultado.
"""

CV_CON_SUBVINETAS = """### Encabezado

**Nombre Apellido**
**Título descriptivo**
Ciudad, País · <nombre@example.com>

### Experiencia profesional

**Empresa — Cargo**
Ciudad, País · 2020–actualidad

- **Logro destacado:** redujo el tiempo de respuesta con Python/SQL.
  - Detalle subordinado con **otra negrita** en medio.
- Viñeta de primer nivel después de la subviñeta.

### Habilidades

- **Grupo:** herramientas y prácticas.
"""


def modulo_09(bloque):
    return f"# 09 — Generación de CV\n\n## CV-PLANTILLA — Presentación\n\nDiseño.\n\n{bloque}\n"


def palabras(texto):
    return re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ’'+.#/-]+", texto)


class GeneradorDeCV(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def copia(self, contenido_09, cv=CV_MINIMO):
        """Una copia ficticia con el script, sus fuentes, un CV y, si hay contenido, un 09 con él."""
        (self.dir / "herramientas").mkdir(exist_ok=True)
        shutil.copy(SCRIPT, self.dir / "herramientas")
        if not (self.dir / "herramientas" / "fuentes").exists():
            shutil.copytree(FUENTES, self.dir / "herramientas" / "fuentes")
        if contenido_09 is not None:
            (self.dir / "09_GENERACION_DE_CV.md").write_text(contenido_09, encoding="utf-8")
        (self.dir / "cv.md").write_text(cv, encoding="utf-8")

    def generar_en_la_copia(self):
        return self.generar(self.dir / "herramientas" / "generar_cv.py", self.dir / "cv.md")

    def generar(self, script, entrada, idioma="es"):
        return subprocess.run(
            [sys.executable, "-I", "-B", str(script), str(entrada), "--idioma", idioma,
             "--salida", str(self.dir / "salida" / f"cv_{idioma}")],
            capture_output=True, text=True, timeout=300,
        )

    def salida(self, extension, idioma="es"):
        return self.dir / "salida" / f"cv_{idioma}.{extension}"

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_el_esqueleto_de_03_genera_pdf_docx_png_y_txt_y_pasa_los_controles(self):
        for idioma in ("es", "en"):
            with self.subTest(idioma=idioma):
                r = self.generar(SCRIPT, RAIZ / "03_CV_BASE.md", idioma)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("Fuentes incrustadas: sí", r.stdout)
                self.assertIn("Carlito incrustada: sí", r.stdout)
                self.assertIn("Texto extraído = contenido, en el mismo orden: sí", r.stdout)
                self.assertIn("Texto del DOCX = contenido, en el mismo orden: sí", r.stdout)
                for extension in ("pdf", "docx", "txt"):
                    self.assertTrue(self.salida(extension, idioma).is_file(), extension)
                self.assertTrue((self.dir / "salida" / f"cv_{idioma}_p-1.png").is_file())
                self.assertFalse(self.salida("fodt", idioma).exists())

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_el_cv_usa_el_color_de_09(self):
        self.copia(modulo_09('```json\n{\n  "color_acento": "#123456"\n}\n```'))
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        estilos = zipfile.ZipFile(self.salida("docx")).read("word/styles.xml").decode()
        colores = re.findall(r'w:color(?: w:val)?="(\w{6})"', estilos)
        # El acento va en dos lugares: los títulos de sección y la línea bajo el contacto.
        self.assertEqual(colores.count("123456"), 2, colores)

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_el_docx_dice_lo_mismo_que_el_contenido_y_nombra_carlito(self):
        import docx
        self.copia(modulo_09('```json\n{"color_acento": "#3B4A5A"}\n```'))
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        documento = docx.Document(str(self.salida("docx")))
        texto = "\n".join(p.text for p in documento.paragraphs)
        esperado = ("Nombre Apellido Título descriptivo Ciudad, País · nombre@example.com "
                    "Experiencia profesional Empresa — Cargo Ciudad, País · 2020–actualidad "
                    "Responsabilidad con su resultado.")
        self.assertEqual([w.lower() for w in palabras(texto)], [w.lower() for w in palabras(esperado)])
        estilos = zipfile.ZipFile(self.salida("docx")).read("word/styles.xml").decode()
        self.assertIn('w:ascii="Carlito"', estilos)
        self.assertNotIn("asciiTheme", estilos.split("</w:docDefaults>")[0])
        self.assertIn("Texto del DOCX = contenido, en el mismo orden: sí", r.stdout)

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_el_pdf_lleva_carlito_incrustada(self):
        import pypdf
        self.copia(modulo_09('```json\n{"color_acento": "#3B4A5A"}\n```'), CV_CON_SUBVINETAS)
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Fuentes incrustadas: sí", r.stdout)
        self.assertIn("Carlito incrustada: sí", r.stdout)
        fuentes = {}
        for pagina in pypdf.PdfReader(str(self.salida("pdf"))).pages:
            for fuente in pagina["/Resources"]["/Font"].values():
                fuente = fuente.get_object()
                descriptor = (fuente["/DescendantFonts"][0].get_object() if "/DescendantFonts" in fuente
                              else fuente)["/FontDescriptor"].get_object()
                fuentes[str(fuente["/BaseFont"])] = any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3"))
        self.assertTrue(fuentes)
        self.assertTrue(all("Carlito" in nombre for nombre in fuentes), fuentes)
        self.assertTrue(all(fuentes.values()), fuentes)
        self.assertTrue(any("Bold" in nombre for nombre in fuentes), fuentes)

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_hay_un_png_por_pagina_y_no_quedan_los_de_una_version_anterior(self):
        largo = CV_MINIMO + "".join(f"- Viñeta número {n} con texto suficiente para ocupar una línea completa "
                                    f"del cuerpo del CV y forzar la segunda página.\n" for n in range(60))
        self.copia(modulo_09('```json\n{"color_acento": "#3B4A5A"}\n```'), largo)
        (self.dir / "salida").mkdir()
        viejo = self.dir / "salida" / "cv_es_p-9.png"
        viejo.write_bytes(b"de una version anterior")
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        paginas = int(re.search(r"cv_es: (\d+) página", r.stdout).group(1))
        self.assertGreaterEqual(paginas, 2)
        pngs = sorted((self.dir / "salida").glob("cv_es_p-*.png"))
        self.assertEqual([p.name for p in pngs], sorted(f"cv_es_p-{n}.png" for n in range(1, paginas + 1)))
        for png in pngs:
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", png.name)

    @unittest.skipIf(FALTAN_BIBLIOTECAS, SALTO)
    def test_subvinetas_y_negritas_en_linea_salen_en_el_pdf_y_en_el_docx(self):
        import docx
        self.copia(modulo_09('```json\n{"color_acento": "#3B4A5A"}\n```'), CV_CON_SUBVINETAS)
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Texto extraído = contenido, en el mismo orden: sí", r.stdout)
        self.assertIn("Texto del DOCX = contenido, en el mismo orden: sí", r.stdout)
        texto_pdf = self.salida("txt").read_text(encoding="utf-8")
        self.assertIn("•", texto_pdf)
        self.assertIn("–", texto_pdf)
        documento = docx.Document(str(self.salida("docx")))
        por_texto = {p.text: p for p in documento.paragraphs}
        sub = por_texto["Detalle subordinado con otra negrita en medio."]
        primero = por_texto["Logro destacado: redujo el tiempo de respuesta con Python/SQL."]
        nivel = lambda p: p._p.pPr.numPr.ilvl.val
        self.assertEqual(nivel(primero), 0)
        self.assertEqual(nivel(sub), 1)
        self.assertEqual([run.text for run in sub.runs if run.bold], ["otra negrita"])
        self.assertEqual([run.text for run in primero.runs if run.bold], ["Logro destacado:"])

    def test_sin_las_bibliotecas_falla_con_un_mensaje_claro_y_no_genera_nada(self):
        self.copia(modulo_09('```json\n{"color_acento": "#3B4A5A"}\n```'))
        # -S deja fuera site-packages, donde pip instala las bibliotecas, como el Python del sistema.
        r = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(self.dir / "herramientas" / "generar_cv.py"),
             str(self.dir / "cv.md"), "--idioma", "es", "--salida", str(self.dir / "salida" / "cv_es")],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn(".venv", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse((self.dir / "salida").exists())

    def test_sin_el_bloque_de_09_falla_con_un_mensaje_claro_y_no_genera_nada(self):
        self.copia(modulo_09("El titular todavía no elige color."))
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("09_GENERACION_DE_CV.md", r.stderr)
        self.assertIn("CV-PLANTILLA", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertFalse((self.dir / "salida").exists())

    def test_sin_09_falla_con_un_mensaje_claro(self):
        self.copia(None)
        r = self.generar_en_la_copia()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("09_GENERACION_DE_CV.md", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_un_color_que_no_es_rrggbb_falla_con_un_mensaje_claro(self):
        for bloque in ('{"color_acento": "rojo"}', '{"color": "#123456"}', '["#123456"]',
                       '{"color_acento": "#123456",}'):
            with self.subTest(bloque=bloque):
                self.copia(modulo_09(f"```json\n{bloque}\n```"))
                r = self.generar_en_la_copia()
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("CV-PLANTILLA", r.stderr)
                self.assertIn("color_acento", r.stderr)
                self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
