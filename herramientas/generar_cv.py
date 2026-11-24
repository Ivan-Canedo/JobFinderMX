#!/usr/bin/env python3
"""Genera un CV (PDF, DOCX, PNG por página y TXT) a partir del Markdown de 03 o de una adaptación.

Uso, con el Python del entorno virtual de la copia (en Windows, .venv\\Scripts\\python.exe):
  .venv/bin/python -I herramientas/generar_cv.py ENTRADA.md --idioma es|en --salida DIR/NOMBRE [--borrador]

ENTRADA puede ser 03_CV_BASE.md (se toma la sección CV-ES o CV-EN) o un archivo con
solo el CV adaptado, con el mismo formato: ### por sección, **negritas**, viñetas «- ».
Los marcadores [CV-E##] y los <> de correos y URL se retiran.

El PDF sale de fpdf2 y el DOCX de python-docx, cada uno con el diseño de 09/CV-PLANTILLA y sin
archivo intermedio; el PDF se revisa con pypdf (páginas, fuentes incrustadas, texto y su orden) y
pypdfium2 (vistas PNG). Las cuatro bibliotecas van en el entorno virtual de la copia, junto con
openpyxl. La fuente Carlito viaja en herramientas/fuentes/, con su licencia (OFL.txt).

El color de acento sale del primer bloque ```json de la sección CV-PLANTILLA de
09_GENERACION_DE_CV.md, en la raíz de la copia: {"color_acento": "#RRGGBB"}. Si 09 no se puede
leer, no tiene el bloque o el color no es #RRGGBB, o si a este Python le falta alguna biblioteca,
termina con código 2 sin generar nada. Si el texto extraído del PDF o el del DOCX no coincide con
el contenido, termina con código 1.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

HERRAMIENTAS = os.path.dirname(os.path.abspath(__file__))
MODULO_09 = os.path.join(os.path.dirname(HERRAMIENTAS), "09_GENERACION_DE_CV.md")
FUENTES = os.path.join(HERRAMIENTAS, "fuentes")
TEXTO = "#1A1A1A"
GRIS = "#4D4D4D"
FUENTE = "Carlito"
BIBLIOTECAS = {"fpdf": "fpdf2", "docx": "python-docx", "pypdf": "pypdf", "pypdfium2": "pypdfium2"}

ENCABEZADO = {"encabezado", "header"}
EXPERIENCIA = {"experiencia profesional", "professional experience"}

CM = 72 / 2.54  # puntos por centímetro
VINETAS = ("•", "–")
SANGRIA = (0.42 * CM, 0.84 * CM)  # donde empieza el texto de cada nivel de viñeta
COLGANTE = 0.38 * CM  # cuánto sobresale la viñeta a la izquierda del texto
LINEA_CONTACTO = (0.75, 5)  # grosor de la línea bajo el contacto y su separación del texto, en puntos
DPI_VISTAS = 80
# Altura natural de una línea de Carlito, en tamaños de letra: (ascendente + descendente) / unidades por em
# de su tabla OS/2. Word y LibreOffice miden el interlineado sobre ella, así que el PDF también.
LINEA_CARLITO = 2500 / 2048


def error(mensaje):
    print(mensaje, file=sys.stderr)
    sys.exit(2)


def leer_acento(ruta):
    """Color de acento del primer bloque JSON de la sección CV-PLANTILLA de 09."""
    try:
        with open(ruta, encoding="utf-8") as f:
            md = f.read()
    except OSError as e:
        error(f"{ruta}: no se pudo leer el módulo 09, de donde sale el color del CV ({e.strerror}).")
    seccion = re.search(r"^## CV-PLANTILLA\b.*?(?=^## |\Z)", md, re.M | re.S)
    bloque = seccion and re.search(r"^```json\n(.*?)^```", seccion.group(0), re.M | re.S)
    if not bloque:
        error(f"{ruta}: falta el bloque de configuración (```json) en la sección CV-PLANTILLA.")
    try:
        config = json.loads(bloque.group(1))
    except ValueError as e:
        error(f"{ruta}: el bloque de CV-PLANTILLA no es JSON válido ({e}); debe ser un objeto con color_acento.")
    acento = config.get("color_acento") if isinstance(config, dict) else None
    if not isinstance(acento, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", acento):
        error(f"{ruta}: color_acento, en el bloque de CV-PLANTILLA, debe ser un color #RRGGBB; dice {acento!r}.")
    return acento


def comprobar_bibliotecas():
    """Termina con código 2 si a este Python le falta alguna biblioteca del CV."""
    import importlib.util
    faltan = [paquete for modulo, paquete in BIBLIOTECAS.items() if importlib.util.find_spec(modulo) is None]
    if faltan:
        error(f"Faltan {', '.join(faltan)}. Corre el script con el Python del entorno virtual de la copia "
              "(.venv/bin/python; en Windows, .venv\\Scripts\\python.exe). Si no existe o no las tiene, "
              "las instala el paso del CV de /configurar (09/CV-HERRAMIENTAS).")


def extraer_cv(md, idioma):
    """Devuelve las líneas del CV: la sección CV-ES/CV-EN de 03 o el archivo completo."""
    marca = f"## CV-{idioma.upper()}"
    if marca in md:
        inicio = md.index(marca)
        md = md[md.index("\n", inicio) + 1:]
        fin = re.search(r"^## ", md, re.M)
        md = md[: fin.start()] if fin else md
    return md.splitlines()


def limpiar(texto):
    texto = re.sub(r"<((?:https?://|mailto:)[^<>\s]+|[^<>\s@]+@[^<>\s]+)>", r"\1", texto)
    return re.sub(r"\s*\[CV-E[^\]]*\]", "", texto).rstrip()


def segmentos(texto):
    """Markdown en línea a [(texto, negrita)], sin los asteriscos."""
    return [(p[2:-2], True) if p.startswith("**") and p.endswith("**") and len(p) > 4 else (p, False)
            for p in re.split(r"(\*\*.+?\*\*)", texto) if p]


def bloques(lineas):
    """Convierte las líneas en una lista de (estilo, texto) y viñetas (nivel, texto)."""
    salida, seccion, i = [], None, 0
    while i < len(lineas):
        crudo = lineas[i]
        linea = limpiar(crudo)
        i += 1
        if not linea.strip():
            continue
        if linea.startswith("### "):
            seccion = linea[4:].strip()
            if seccion.lower() not in ENCABEZADO:
                salida.append(("Seccion", seccion))
            continue
        m = re.match(r"^(\s*)- (.*)$", linea)
        if m:
            salida.append(("Vineta", (1 if len(m.group(1)) >= 2 else 0, m.group(2))))
            continue
        texto = linea.strip()
        solo_negrita = re.fullmatch(r"\*\*[^*]+\*\*", texto)
        if seccion and seccion.lower() in ENCABEZADO:
            n = sum(1 for e in salida if e[0] in ("Nombre", "Titulo"))
            estilo = ("Nombre", "Titulo")[n] if solo_negrita and n < 2 else "Contacto"
            salida.append((estilo, texto.strip("*") if solo_negrita else texto))
        elif seccion and seccion.lower() in EXPERIENCIA and solo_negrita:
            salida.append(("Puesto", texto.strip("*")))
        elif salida and salida[-1][0] == "Puesto":
            salida.append(("PuestoDatos", texto))
        else:
            salida.append(("Cuerpo", texto))
    return salida


def estilos(tam, acento):
    """El diseño de 09/CV-PLANTILLA, el mismo para el PDF y el DOCX. Tamaños y espacios en puntos."""
    def e(**cambios):
        return {"tam": tam, "negrita": False, "color": TEXTO, "antes": 0, "despues": 0, "interlineado": 1.13,
                "junto": False, "mayusculas": False, "espaciado": 0, **cambios}
    return {
        "Nombre": e(tam=tam + 9, negrita=True, despues=1, interlineado=1.0),
        "Titulo": e(tam=tam + 1, negrita=True, color=GRIS, despues=2),
        "Contacto": e(tam=tam - 0.5, color=GRIS, despues=2),
        "Seccion": e(negrita=True, color=acento, antes=9, despues=3, junto=True, mayusculas=True,
                     espaciado=0.02 * CM),
        "Cuerpo": e(despues=3),
        "Puesto": e(tam=tam + 0.5, negrita=True, junto=True),
        "PuestoDatos": e(tam=tam - 0.5, color=GRIS, despues=3, junto=True),
        "Vineta": e(despues=2.5),
        "Borrador": e(tam=tam - 2, color=GRIS, despues=4),
    }


def con_borrador(bl, borrador):
    return [("Borrador", borrador)] + bl if borrador else bl


def alto_de_linea(s):
    return s["tam"] * LINEA_CARLITO * s["interlineado"]


def rgb(color):
    return tuple(int(color[k:k + 2], 16) for k in (1, 3, 5))


# --- PDF (fpdf2) ---

def generar_pdf(bl, tam, margen, borrador, acento, ruta):
    import logging
    from fpdf import FPDF
    # fontTools, con que fpdf2 lee la TTF, avisa que la fecha de creación de Carlito «parece muy baja»;
    # no afecta al PDF y confundiría al titular.
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    est = estilos(tam, acento)
    pdf = FPDF(unit="pt", format="letter")
    vertical, horizontal = margen[0] * CM, margen[1] * CM
    pdf.set_margins(horizontal, vertical, horizontal)
    pdf.set_auto_page_break(True, vertical)
    for estilo, archivo in (("", "Regular"), ("B", "Bold"), ("I", "Italic"), ("BI", "BoldItalic")):
        pdf.add_font(FUENTE, estilo, os.path.join(FUENTES, f"{FUENTE}-{archivo}.ttf"))
    pdf.set_creator("JobFinderMX")
    pdf.add_page()

    lista = con_borrador(bl, borrador)
    for k, (nombre, contenido) in enumerate(lista):
        s = est[nombre]
        nivel, texto = contenido if nombre == "Vineta" else (None, contenido)
        alto = alto_de_linea(s)
        pdf.set_y(pdf.get_y() + s["antes"])
        # Los títulos, los puestos y sus datos no quedan solos al pie: piden lugar para la primera línea
        # de cada párrafo que les sigue, hasta el primero que no es de los que van juntos.
        reserva, j = alto, k
        while j + 1 < len(lista) and est[lista[j][0]]["junto"]:
            anterior, siguiente = est[lista[j][0]], est[lista[j + 1][0]]
            reserva += anterior["despues"] + siguiente["antes"] + alto_de_linea(siguiente)
            j += 1
        if pdf.get_y() + reserva > pdf.page_break_trigger:
            pdf.add_page()

        izquierda = horizontal
        if nivel is not None:
            pdf.set_font(FUENTE, "", s["tam"])
            pdf.set_text_color(*rgb(GRIS))
            pdf.set_x(horizontal + SANGRIA[nivel] - COLGANTE)
            pdf.write(alto, VINETAS[nivel])
            izquierda = horizontal + SANGRIA[nivel]
        pdf.set_left_margin(izquierda)
        pdf.set_x(izquierda)
        pdf.set_char_spacing(s["espaciado"])
        pdf.set_text_color(*rgb(s["color"]))
        for trozo, negrita in segmentos(texto):
            pdf.set_font(FUENTE, "B" if negrita or s["negrita"] else "", s["tam"])
            pdf.write(alto, trozo.upper() if s["mayusculas"] else trozo)
        pdf.set_char_spacing(0)
        pdf.set_left_margin(horizontal)
        pdf.ln(alto)

        if nombre == "Contacto" and (k + 1 == len(lista) or lista[k + 1][0] != "Contacto"):
            grosor, separacion = LINEA_CONTACTO
            y = pdf.get_y() + separacion
            pdf.set_draw_color(*rgb(acento))
            pdf.set_line_width(grosor)
            pdf.line(horizontal, y, pdf.w - horizontal, y)
            pdf.set_y(y + grosor)
        pdf.set_y(pdf.get_y() + s["despues"])
    pdf.output(ruta)


def revisar_pdf(ruta):
    """(páginas, texto por página, {fuente: incrustada}) del PDF."""
    import pypdf
    lector = pypdf.PdfReader(ruta)
    fuentes = {}
    for pagina in lector.pages:
        recursos = pagina.get("/Resources")
        recursos = recursos.get_object() if recursos else {}
        for fuente in (recursos.get("/Font") or {}).values():
            fuente = fuente.get_object()
            descendiente = fuente.get("/DescendantFonts")
            base = descendiente[0].get_object() if descendiente else fuente
            descriptor = base.get("/FontDescriptor")
            descriptor = descriptor.get_object() if descriptor else {}
            nombre = str(fuente.get("/BaseFont", "?")).lstrip("/")
            fuentes[nombre] = any(k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3"))
    return len(lector.pages), [p.extract_text() or "" for p in lector.pages], fuentes


def vistas_png(ruta, destino):
    """Una vista PNG por página, destino_p-N.png; borra antes las de una versión anterior."""
    import pypdfium2
    for viejo in glob.glob(glob.escape(destino) + "_p-*.png"):
        os.remove(viejo)
    documento = pypdfium2.PdfDocument(ruta)
    try:
        for n, pagina in enumerate(documento, 1):
            pagina.render(scale=DPI_VISTAS / 72).to_pil().save(f"{destino}_p-{n}.png")
    finally:
        documento.close()


# --- DOCX (python-docx) ---

# Orden de los hijos de w:pPr y w:rPr en el esquema de Word: un elemento fuera de orden lo vuelve inválido.
ORDEN_PPR = ("pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
             "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
             "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
             "sectPr", "pPrChange")
ORDEN_RPR = ("rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline",
             "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
             "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText",
             "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath")


def poner(padre, xml, orden):
    """Agrega a padre el elemento de xml en su lugar del esquema, en lugar del que ya hubiera."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    elemento = parse_xml(re.sub(r"^<([\w:]+)", rf"<\1 {nsdecls('w')}", xml, count=1))
    nombre = elemento.tag.split("}")[1]
    for viejo in padre.findall(qn(f"w:{nombre}")):
        padre.remove(viejo)
    padre.insert_element_before(elemento, *(f"w:{t}" for t in orden[orden.index(nombre) + 1:]))


def generar_docx(bl, tam, margen, borrador, acento, idioma, ruta):
    import docx
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn
    from docx.shared import Cm, Pt, RGBColor

    est = estilos(tam, acento)
    d = docx.Document()
    seccion = d.sections[0]
    seccion.page_width, seccion.page_height = Cm(21.59), Cm(27.94)
    seccion.top_margin = seccion.bottom_margin = Cm(margen[0])
    seccion.left_margin = seccion.right_margin = Cm(margen[1])

    # La fuente y el idioma por omisión del documento, sin las del tema (Calibri/Cambria) de la plantilla.
    por_omision = d.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    familia = f'w:ascii="{FUENTE}" w:hAnsi="{FUENTE}" w:eastAsia="{FUENTE}" w:cs="{FUENTE}"'
    poner(por_omision, f"<w:rFonts {familia}/>", ORDEN_RPR)
    poner(por_omision, f'<w:lang w:val="{idioma}"/>', ORDEN_RPR)

    normal = d.styles["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(tam)
    normal.font.color.rgb = RGBColor(*rgb(TEXTO))
    normal.paragraph_format.widow_control = True
    poner(normal.element.get_or_add_pPr(), "<w:suppressAutoHyphens/>", ORDEN_PPR)

    for nombre, s in est.items():
        estilo = d.styles.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
        estilo.base_style = normal
        estilo.font.size = Pt(s["tam"])
        estilo.font.bold = s["negrita"]
        estilo.font.color.rgb = RGBColor(*rgb(s["color"]))
        estilo.font.all_caps = s["mayusculas"]
        formato = estilo.paragraph_format
        formato.space_before, formato.space_after = Pt(s["antes"]), Pt(s["despues"])
        formato.line_spacing = s["interlineado"]
        formato.keep_with_next = s["junto"]
        if s["espaciado"]:
            poner(estilo.element.get_or_add_rPr(), f'<w:spacing w:val="{round(s["espaciado"] * 20)}"/>', ORDEN_RPR)
    # La línea bajo el contacto: Word une los bordes de párrafos seguidos con el mismo borde, así que
    # queda una sola bajo el último.
    grosor, separacion = LINEA_CONTACTO
    poner(d.styles["Contacto"].element.get_or_add_pPr(),
          f'<w:pBdr><w:bottom w:val="single" w:sz="{round(grosor * 8)}" w:space="{separacion}" '
          f'w:color="{acento[1:].upper()}"/></w:pBdr>', ORDEN_PPR)

    # Viñetas reales: «•» y «–» en gris, con sangría francesa.
    numeracion = d.part.numbering_part.element
    abstracto = 1 + max((int(a.get(qn("w:abstractNumId"))) for a in numeracion.findall(qn("w:abstractNum"))), default=-1)
    lista = 1 + max((int(n.get(qn("w:numId"))) for n in numeracion.findall(qn("w:num"))), default=0)
    twips = lambda puntos: round(puntos * 20)
    niveles = "".join(
        f'<w:lvl w:ilvl="{n}"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="{VINETAS[n]}"/>'
        f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{twips(SANGRIA[n])}" w:hanging="{twips(COLGANTE)}"/></w:pPr>'
        f'<w:rPr><w:rFonts {familia}/><w:color w:val="{GRIS[1:]}"/></w:rPr></w:lvl>' for n in range(2))
    nuevo = parse_xml(f'<w:abstractNum {nsdecls("w")} w:abstractNumId="{abstracto}">'
                      f'<w:multiLevelType w:val="hybridMultilevel"/>{niveles}</w:abstractNum>')
    primero = numeracion.find(qn("w:num"))
    if primero is None:
        numeracion.append(nuevo)
    else:
        primero.addprevious(nuevo)
    numeracion.append(parse_xml(f'<w:num {nsdecls("w")} w:numId="{lista}"><w:abstractNumId w:val="{abstracto}"/></w:num>'))

    for nombre, contenido in con_borrador(bl, borrador):
        nivel, texto = contenido if nombre == "Vineta" else (None, contenido)
        p = d.add_paragraph(style=nombre)
        if nivel is not None:
            num = p._p.get_or_add_pPr().get_or_add_numPr()
            num.get_or_add_ilvl().val = nivel
            num.get_or_add_numId().val = lista
        for trozo, negrita in segmentos(texto):
            run = p.add_run(trozo)
            if negrita:
                run.bold = True

    propiedades = d.core_properties
    ahora = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    propiedades.author = propiedades.last_modified_by = propiedades.title = propiedades.subject = ""
    propiedades.comments = propiedades.keywords = propiedades.category = ""
    propiedades.created = propiedades.modified = ahora
    propiedades.revision = 1
    d.save(ruta)


def texto_docx(ruta):
    import docx
    return "\n".join(p.text for p in docx.Document(ruta).paragraphs)


# --- Revisión del texto ---

def palabras(texto):
    return re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ’'+.#/-]+", texto)


def texto_plano(bl):
    out = []
    for estilo, c in bl:
        t = c[1] if estilo == "Vineta" else c
        out.append(t.replace("**", ""))
    return "\n".join(out)


def comparar(esperado, obtenido, borrador):
    """Lista de diferencias (vacía si el texto obtenido dice lo mismo, en el mismo orden)."""
    obtenido = palabras(obtenido)
    if borrador:
        obtenido = obtenido[len(palabras(borrador)):]
    if [w.lower() for w in esperado] == [w.lower() for w in obtenido]:
        return []
    for k, (x, y) in enumerate(zip(esperado, obtenido)):
        if x.lower() != y.lower():
            return [f"  primera diferencia en la palabra {k}: esperado {x!r}, extraído {y!r}"]
    return [f"  longitudes distintas: {len(esperado)} frente a {len(obtenido)}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("--idioma", choices=["es", "en"], required=True)
    ap.add_argument("--salida", required=True, help="ruta sin extensión")
    ap.add_argument("--tam", type=float, default=10.5)
    ap.add_argument("--margen", type=float, nargs=2, default=[1.4, 1.7], metavar=("VERT", "HORIZ"))
    ap.add_argument("--borrador", default="", help="línea de aviso al inicio (muestras)")
    a = ap.parse_args()

    acento = leer_acento(MODULO_09)
    comprobar_bibliotecas()
    with open(a.entrada, encoding="utf-8") as f:
        bl = bloques(extraer_cv(f.read(), a.idioma))
    destino = os.path.abspath(a.salida)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    base = os.path.basename(destino)

    generar_pdf(bl, a.tam, a.margen, a.borrador, acento, destino + ".pdf")
    generar_docx(bl, a.tam, a.margen, a.borrador, acento, a.idioma, destino + ".docx")
    vistas_png(destino + ".pdf", destino)
    paginas, textos, fuentes = revisar_pdf(destino + ".pdf")
    crudo = "\n".join(textos)
    with open(destino + ".txt", "w", encoding="utf-8") as f:
        f.write("\f".join(textos))

    # Un compuesto partido al final de línea («state-of-» / «the-art») puede unirse sin guion al extraerlo.
    partidos = re.findall(r"(\S+-)\n(\S+)", crudo)
    crudo = re.sub(r"(\S-)\n", r"\1", crudo)
    esperado = palabras(texto_plano(bl))
    dif_pdf = comparar(esperado, crudo, a.borrador)
    dif_docx = comparar(esperado, texto_docx(destino + ".docx"), a.borrador)
    carlito = bool(fuentes) and all(FUENTE in nombre and incrustada for nombre, incrustada in fuentes.items())
    print(f"{base}: {paginas} página(s), {len(esperado)} palabras")
    print("Fuentes incrustadas:", "sí" if fuentes and all(fuentes.values()) else "revisar")
    print("Carlito incrustada:", "sí" if carlito else f"NO (fuentes: {', '.join(fuentes) or 'ninguna'})")
    print("Texto extraído = contenido, en el mismo orden:", "NO" if dif_pdf else "sí")
    for antes, despues in partidos:
        print(f"  revisar: compuesto partido al final de línea «{antes} {despues}»")
    for linea in dif_pdf:
        print(linea)
    print("Texto del DOCX = contenido, en el mismo orden:", "NO" if dif_docx else "sí")
    for linea in dif_docx:
        print(linea)
    if dif_pdf or dif_docx:
        sys.exit(1)


if __name__ == "__main__":
    main()
