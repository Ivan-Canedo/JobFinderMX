"""Pruebas de los archivos de paso de /configurar, sin red.

Uso:
    python3 -I -B -m unittest discover -s herramientas/pruebas

La skill /configurar es un índice (.claude/skills/configurar/SKILL.md) con las reglas comunes y una
línea por paso que nombra el archivo del paso, como `paso-3-perfil-maestro.md`, junto al índice. El
agente lee solo el archivo del paso que toca. Como la prueba de los punteros, esta no llama a un
script: lee la estructura del repo, para que el índice y los archivos no se desincronicen en silencio.
"""
import pathlib
import re
import unittest

CARPETA = pathlib.Path(__file__).resolve().parents[2] / ".claude" / "skills" / "configurar"
NOMBRE = re.compile(r"paso-(\d+)-[a-z0-9-]+\.md")


def indice():
    return (CARPETA / "SKILL.md").read_text(encoding="utf-8")


def nombrados():
    """Archivos de paso que nombra el índice, en el orden en que aparecen."""
    return [m.group(0) for m in NOMBRE.finditer(indice())]


def archivos():
    """Archivos de paso que hay en la carpeta de la skill."""
    return sorted(a.name for a in CARPETA.glob("paso-*.md"))


class PasosDeConfigurar(unittest.TestCase):
    def test_el_indice_nombra_los_pasos_del_1_al_9_en_orden(self):
        numeros = [int(NOMBRE.fullmatch(n).group(1)) for n in nombrados()]
        self.assertEqual(numeros, list(range(1, 10)))

    def test_cada_paso_nombrado_tiene_su_archivo(self):
        faltan = sorted(set(nombrados()) - set(archivos()))
        self.assertEqual(faltan, [], "pasos que nombra el índice sin su archivo")

    def test_ningun_archivo_de_paso_queda_sin_nombrar(self):
        sobran = sorted(set(archivos()) - set(nombrados()))
        self.assertEqual(sobran, [], "archivos de paso que el índice no nombra")

    def test_existe_comandos_sin_red_que_nombra_el_indice(self):
        self.assertIn("comandos-sin-red.md", indice())
        self.assertTrue((CARPETA / "comandos-sin-red.md").is_file())

    def test_cada_archivo_de_paso_abre_con_su_titulo(self):
        for nombre in archivos():
            with self.subTest(archivo=nombre):
                numero = NOMBRE.fullmatch(nombre).group(1)
                primera = (CARPETA / nombre).read_text(encoding="utf-8").splitlines()[0]
                self.assertTrue(primera.startswith(f"# Paso {numero}: "), primera)


if __name__ == "__main__":
    unittest.main()
