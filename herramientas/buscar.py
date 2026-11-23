#!/usr/bin/env python3
"""ChambaKit: listado y detalle de vacantes por empresa y por bolsa de empleo (canal Code, 07/BUS-ACCESO-CODE).

Uso:
    python3 -I herramientas/buscar.py [EMP-ID | BOL-ID ...] [--salida archivo.json] [--sin-remotas] [--copia CARPETA]

Las empresas y las bolsas se nombran por su ID de 06; por defecto, todas las de sus catálogos (CAT-EMPRESAS y
CAT-BOLSAS). La región, el alcance del remoto y la zona horaria salen del bloque de 04/PREF-UBICACION; la plataforma,
el portal y la consulta de cada empresa, del bloque de «### Configuración» de su ficha en 06; el adaptador y el país
de cada bolsa, del de la suya, y sus términos de búsqueda, del bloque de 05/HAB-TERMINOS.

Si el bloque de 04 falta o no cumple sus reglas, los dos catálogos están vacíos, un ID no está en ellos o
--sin-remotas dejaría vacía la búsqueda de un titular que solo acepta remoto, termina con código 2 sin
buscar nada. Una empresa o una bolsa sin configuración usable, sin adaptador o cuyo sitio falla sale como [FALLO]
y las demás siguen; también una bolsa con el bloque de 05 sin llenar. Entonces termina con código 1.

Cada adaptador de empresa lista las vacantes de los países de la región, o las de la consulta de la ficha, y las
remotas con el filtro de su plataforma según el alcance del remoto; lee el detalle de cada una con comprobación de
ID. Cada adaptador de bolsa lista cada término de búsqueda en cada lugar de la región de su país y, si el alcance
del remoto lo incluye, en todo el país con su filtro remoto; clasifica cada vacante por su título como «encaja»,
«dudosa» (con su línea «revisar título») o «ruido», que no se entrega, y reporta el rendimiento de cada término
(05/HAB-TERMINOS, «Filtro por título»). Después pide el detalle solo de las candidatas, primero las que encajan,
hasta la primera señal anti-bot: ahí detiene la bolsa sin reintentar, la entrega con lo listado y lo leído
como [FALLO] y sigue con las demás (07/BUS-BOLSAS, ADR 0010). Solo se usan rutas que permite el robots.txt
del sitio, sin cookies ni credenciales. El JSON va a --salida o a stdout, con las empresas en «empresas» y
las bolsas en «bolsas»; el resumen y las líneas «revisar», a stderr. El script no evalúa ni escribe en los
registros: entrega los datos para los pasos 4-9 de 07/BUS-PASOS. Solo biblioteca estándar.
"""
import argparse
import collections
import datetime as dt
import html
import http.client
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

VERSION = "1.1"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def usar_copia(ruta):
    """La copia de la que se leen el 04 y el 06: la del script o, con --copia, otra, como la copia de prueba del
    mantenedor (CONTRIBUTING, «Titulares de prueba»)."""
    global RAIZ, MODULO_04, MODULO_05, MODULO_06
    RAIZ = os.path.abspath(ruta)
    MODULO_04 = os.path.join(RAIZ, "04_PREFERENCIAS_LABORALES.md")
    MODULO_05 = os.path.join(RAIZ, "05_MAPA_HABILIDADES_Y_ROLES.md")
    MODULO_06 = os.path.join(RAIZ, "06_EMPRESAS_OBJETIVO.md")


usar_copia(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # por defecto, la copia del script
# La tabla de países es de la plantilla: se lee junto al script, también con --copia (ADR 0009)
TABLA_DE_PAISES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paises.json")


class Fallo(Exception):
    """Lo que impide buscar en una empresa: su configuración o su portal. Sale como [FALLO] y las demás
    siguen. codigo: el estado HTTP, si lo hubo."""

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


class HostBloqueado(Fallo):
    """El proxy de Code en la nube no dejó salir la petición: el host no está en la lista de dominios del entorno
    (07/BUS-ACCESO-CODE). No se reintenta ni lo oculta el mensaje del robots.txt."""

    def __init__(self, host):
        super().__init__(f"el host no está en la lista de dominios del entorno de la nube; agrégalo en claude.ai/code "
                         f"(entorno → red → Custom) y vuelve a buscar: {host}")
        self.host = host


class IpBloqueada(Fallo):
    """En Code en la nube, el sitio responde HTTP 429 con el «error code: 1015» de Cloudflare o con un Retry-After de
    más de un minuto: bloquea las IP de la nube, como Workable (07/BUS-ACCESO-CODE). No se reintenta, porque esperar
    no lo resuelve: la empresa se busca en Code local."""

    def __init__(self, host, motivo):
        super().__init__(f"{host} bloquea las IP de Code en la nube (HTTP 429, {motivo}); "
                         "busca esta empresa en Code local", 429)
        self.host = host


class SenalAntiBot(Fallo):
    """El sitio respondió con una señal anti-bot: HTTP 403 con el cuerpo «scraping abuse», o el reto «Just a
    moment…» de Cloudflare (challenge-platform), con un error HTTP o servido con 200 sin el marcador que se esperaba.
    No se reintenta ni se le pide nada más al sitio en esa ejecución: retroceder ante la señal no es evadirla
    (ADR 0010). tipo: cuál fue y con qué estado HTTP; url: la petición que la recibió."""

    def __init__(self, url, senal, codigo):
        self.host, self.url, self.tipo = urllib.parse.urlsplit(url).hostname, url, f"{senal}, HTTP {codigo}"
        super().__init__(f"{self.host} respondió con una señal anti-bot ({self.tipo}) en {url}; no se reintenta "
                         "(ADR 0010)", codigo)


def senal_antibot(cuerpo):
    """La señal anti-bot que trae el cuerpo de una respuesta, o None (SenalAntiBot)."""
    if "scraping abuse" in cuerpo:
        return "scraping abuse"
    if "challenge-platform" in cuerpo or "Just a moment" in cuerpo:
        return "reto de Cloudflare"
    return None


def error(mensaje):
    """Configuración que falta o no sirve: termina con código 2 sin buscar nada."""
    print(mensaje, file=sys.stderr)
    sys.exit(2)


def leer(ruta, para, fallo=False):
    """El texto de un módulo. Si no se puede leer, termina con código 2 o, con fallo, levanta Fallo: lo que solo
    necesita una fuente, como los términos de una bolsa, no detiene las demás."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        mensaje = f"{ruta}: no se pudo leer el módulo, de donde salen {para} ({e.strerror})."
        if fallo:
            raise Fallo(mensaje) from e
        error(mensaje)


def seccion(md, titulo, nivel="##"):
    """Texto de la sección `<nivel> <titulo>` hasta la siguiente del mismo nivel o mayor."""
    m = re.search(rf"^{nivel} {re.escape(titulo)}(?![\w-]).*?(?=^#{{2,{len(nivel)}}} |\Z)", md, re.M | re.S)
    return m.group(0) if m else None


def bloque_json(texto):
    """Contenido del primer bloque ```json del texto, o None."""
    m = texto and re.search(r"^```json\n(.*?)^```", texto, re.M | re.S)
    return m.group(1) if m else None


def lista_de_textos(x):
    return isinstance(x, list) and all(isinstance(t, str) and t.strip() for t in x)


def leer_preferencias(ruta):
    """Bloque de 04/PREF-UBICACION, comprobado con sus «Reglas del bloque»."""
    bloque = bloque_json(seccion(leer(ruta, "la región, el remoto y la zona horaria"), "PREF-UBICACION"))
    if bloque is None:
        error(f"{ruta}: falta el bloque de configuración (```json) en la sección PREF-UBICACION.")
    try:
        p = json.loads(bloque)
    except ValueError as e:
        error(f"{ruta}: el bloque de PREF-UBICACION no es JSON válido ({e}).")

    def mal(mensaje):
        error(f"{ruta}, PREF-UBICACION: {mensaje}")

    if not isinstance(p, dict) or not isinstance(p.get("remoto"), dict):
        mal("el bloque debe ser un objeto con paises, localidades, remoto, zona_horaria y moneda.")
    remoto = p["remoto"]
    vacios = [c for c, v in (("remoto.alcance", remoto.get("alcance")), ("zona_horaria", p.get("zona_horaria")),
                              ("moneda", p.get("moneda"))) if v is None]
    if vacios:
        mal(f"el bloque está sin llenar ({', '.join(vacios)} en null); llénalo con `/configurar`, paso 4 "
            "(Preferencias).")
    paises = p.get("paises")
    if not isinstance(paises, dict) or not all(re.fullmatch(r"[A-Z]{2}", c) and lista_de_textos(n) and n
                                               for c, n in paises.items()):
        mal("paises debe ser un objeto: código ISO de dos letras mayúsculas → lista de nombres.")
    localidades = p.get("localidades")
    if not isinstance(localidades, list) or not all(
            isinstance(g, dict) and isinstance(g.get("pais"), str) and lista_de_textos(g.get("divisiones"))
            and lista_de_textos(g.get("nombres")) and isinstance(g.get("zona", None), (str, type(None)))
            for g in localidades):
        mal("localidades debe ser una lista de grupos con pais, divisiones, zona y nombres.")
    for g in localidades:
        g.setdefault("incluidas", [])
        if not lista_de_textos(g["incluidas"]):
            mal(f"incluidas del grupo de {g['pais']} debe ser una lista de textos.")
        if g["incluidas"] and (g["nombres"] or not g["divisiones"]):
            mal(f"incluidas solo va en un grupo de división completa (con divisiones y sin nombres); en el grupo "
                f"de {g['pais']}, las localidades que acepta van en nombres.")
    sin_pais = [g["pais"] for g in localidades if g["pais"] not in paises]
    if remoto["alcance"] not in ("ninguno", "paises", "cualquiera"):
        mal(f"remoto.alcance debe ser \"ninguno\", \"paises\" o \"cualquiera\"; dice {remoto['alcance']!r}.")
    if not lista_de_textos(remoto.get("paises")) or bool(remoto["paises"]) != (remoto["alcance"] == "paises"):
        mal("remoto.paises lleva los países del remoto solo con el alcance \"paises\"; con los otros, va vacía.")
    sin_pais += [c for c in remoto["paises"] if c not in paises]
    if sin_pais:
        mal(f"{', '.join(sin_pais)} no está en paises.")
    if not localidades and remoto["alcance"] == "ninguno":
        mal("localidades está vacía y el remoto es \"ninguno\": no habría nada que buscar.")
    try:
        p["tz"] = ZoneInfo(p["zona_horaria"])
    except (ValueError, KeyError, TypeError):
        mal(f"zona_horaria no es una zona IANA conocida: {p['zona_horaria']!r}. Si el nombre es correcto, al "
            "sistema le falta la base de zonas horarias (en Windows: `py -3 -m pip install tzdata`).")
    if not (isinstance(p["moneda"], str) and re.fullmatch(r"[A-Z]{3}", p["moneda"])):
        mal(f"moneda debe ser un código ISO 4217 de tres letras mayúsculas; dice {p['moneda']!r}.")
    return p


def leer_tabla_de_paises(ruta):
    """La tabla de países de la plantilla: código ISO 3166-1 alfa-2 → sus nombres (los de CLDR en inglés y en español
    que una ubicación puede escribir como una de sus partes, el alfa-3 y formas usuales de los portales)."""
    def mal(mensaje):
        error(f"{ruta}: {mensaje}; es un archivo de la plantilla, junto a buscar.py, y sin ella el script no reconoce "
              "los países que 04 no nombra.")

    try:
        with open(ruta, encoding="utf-8") as f:
            tabla = json.load(f)
    except OSError as e:
        mal(f"no se pudo leer la tabla de países ({e.strerror})")
    except ValueError as e:
        mal(f"la tabla de países no es JSON válido ({e})")
    if not isinstance(tabla, dict) or not all(re.fullmatch(r"[A-Z]{2}", c) and lista_de_textos(n) and n
                                              for c, n in tabla.items()):
        mal("la tabla de países debe ser un objeto: código ISO de dos letras mayúsculas → lista de nombres")
    return tabla


def paises_reconocidos(tabla, paises):
    """{código ISO: nombres normalizados como las partes de una ubicación} de los países que reconoce el script: los de
    la tabla, con los de paises de 04 sumados al país de su código. Si un nombre de 04 es de otro país en la tabla,
    gana 04 y ese nombre deja de contar para el otro."""
    de_04 = {c: {sin_generales(n) for n in nombres} - {""} for c, nombres in paises.items()}
    de_04_todos = set().union(*de_04.values())
    reconocidos = {c: {sin_generales(n) for n in nombres} - de_04_todos - {""} for c, nombres in tabla.items()}
    for c, nombres in de_04.items():
        reconocidos[c] = reconocidos.get(c, set()) | nombres
    return reconocidos


def leer_catalogos(ruta):
    """({EMP-ID: texto de su ficha, o None si falta}, {BOL-ID: ídem}) en el orden de CAT-EMPRESAS y de CAT-BOLSAS.
    Una copia anterior al catálogo de bolsas no tiene CAT-BOLSAS: no tiene bolsas."""
    md = leer(ruta, "las empresas y las bolsas de empleo")
    empresas = seccion(md, "CAT-EMPRESAS")
    if empresas is None:
        error(f"{ruta}: falta la sección CAT-EMPRESAS, el catálogo de empresas.")

    def fichas(catalogo, prefijo):
        ids = re.findall(rf"^\|\s*({prefijo}-[A-Z0-9]+(?:-[A-Z0-9]+)*)\s*\|", catalogo or "", re.M)
        return {i: seccion(md, i) for i in dict.fromkeys(ids)}

    catalogos = fichas(empresas, "EMP"), fichas(seccion(md, "CAT-BOLSAS"), "BOL")
    if not any(catalogos):
        error(f"{ruta}: el catálogo (CAT-EMPRESAS) no tiene empresas, ni CAT-BOLSAS bolsas de empleo; agrégalas con "
              "`/configurar`, paso 7 (Empresas).")
    return catalogos


def configuracion(fid, ficha, plantilla):
    """El bloque de «### Configuración» de una ficha de 06, como objeto. plantilla: la sección de 06 que lo describe.
    Sin él, la empresa o la bolsa sale como [FALLO]."""
    if ficha is None:
        raise Fallo(f"falta su ficha en 06, la sección «## {fid} — <nombre>»")
    bloque = bloque_json(seccion(ficha, "Configuración", "###"))
    if bloque is None:
        raise Fallo(f"su ficha no tiene el bloque ```json de «### Configuración» (06/{plantilla})")
    try:
        conf = json.loads(bloque)
    except ValueError as e:
        raise Fallo(f"el bloque de «### Configuración» de su ficha no es JSON válido ({e})") from e
    if not isinstance(conf, dict):
        raise Fallo(f"el bloque de «### Configuración» de su ficha debe ser un objeto (06/{plantilla})")
    return conf


def leer_ficha(eid, ficha):
    """Bloque de «### Configuración» de la ficha (06/FICHA-PLANTILLA). Sin él, la empresa sale como [FALLO]."""
    conf = configuracion(eid, ficha, "FICHA-PLANTILLA")
    if not isinstance(conf.get("plataforma"), str):
        raise Fallo("el bloque de «### Configuración» debe ser un objeto con plataforma, portal y consulta")
    if not (isinstance(conf.get("portal"), str) and re.match(r"https?://", conf["portal"])):
        raise Fallo(f"el portal de su ficha debe ser una URL http(s); dice {conf.get('portal')!r}")
    if conf.get("consulta") is not None and not isinstance(conf["consulta"], dict):
        raise Fallo("la consulta de su ficha debe ser null o un objeto (06/CAT-PLATAFORMAS)")
    return conf


# --- Acceso a los portales ---------------------------------------------------

def pedir(url, cuerpo=None, intentos=3, como_json=True, extra=None, antibot=False):
    """GET (o POST con cuerpo JSON) que devuelve JSON, o texto si como_json=False.
    extra: cabeceras adicionales que pida un adaptador. Sin cookies ni credenciales: urlopen no guarda las que da el
    sitio. Reintenta errores transitorios, también HTTP 429, salvo el bloqueo de las IP de la nube. antibot: el sitio
    es una bolsa de empleo (07/BUS-BOLSAS): todo 403 o 429, y un 503 con el reto en el cuerpo, son la señal
    anti-bot (SenalAntiBot), sin reintento."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    # Algunas plataformas responden JSON en lugar de la página solo si se pide application/json
    cabeceras = {"User-Agent": UA, "Accept": "application/json" if como_json else "text/html,application/xhtml+xml"}
    if datos is not None:
        cabeceras["Content-Type"] = "application/json"
    cabeceras.update(extra or {})
    for i in range(intentos):
        espera = 2 * (i + 1)
        try:
            req = urllib.request.Request(url, data=datos, headers=cabeceras,
                                         method="POST" if datos is not None else "GET")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r) if como_json else r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            pedida = (e.headers.get("Retry-After") if e.headers else None) or ""
            try:
                inicio = e.read(100_000)
            except (OSError, http.client.HTTPException):
                inicio = b""
            if antibot:
                # Ante la duda se retrocede: un 403 o un 429 de una bolsa la detiene aunque no traiga la señal
                senal = senal_antibot(inicio.decode("utf-8", "replace"))
                if e.code in (403, 429) or (e.code == 503 and senal):
                    raise SenalAntiBot(url, senal or "sin señal reconocible en el cuerpo", e.code) from e
            if e.code == 429 and os.environ.get("CLAUDE_CODE_REMOTE") == "true":
                # Workable responde así a las IP de la nube: con su propia página de error y un Retry-After de horas
                # si se le pide como navegador, o con el «error code: 1015» de Cloudflare si no
                if b"error code: 1015" in inicio:
                    raise IpBloqueada(urllib.parse.urlsplit(url).hostname, "«error code: 1015» de Cloudflare") from e
                if pedida.isdigit() and int(pedida) > 60:
                    segundos = int(pedida)
                    plazo = f"{round(segundos / 3600, 1):g} h" if segundos >= 3600 else f"{round(segundos / 60)} min"
                    raise IpBloqueada(urllib.parse.urlsplit(url).hostname, f"pide esperar {plazo}") from e
            if (e.code < 500 and e.code != 429) or i == intentos - 1:
                raise Fallo(f"HTTP {e.code} en {url}", e.code) from e
            if e.code == 429:
                # El sitio pide bajar el ritmo: se espera lo que diga Retry-After, hasta un minuto
                espera = min(int(pedida), 60) if pedida.isdigit() else 5 * espera
        # OSError: también el timeout de lectura, que en Python 3.9 todavía no es TimeoutError
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:
            # El proxy de la nube responde 403 al CONNECT de un host fuera de la lista; urllib lo da como URLError
            if isinstance(e, urllib.error.URLError) and "Tunnel connection failed: 403" in str(e.reason):
                raise HostBloqueado(urllib.parse.urlsplit(url).hostname) from e
            if i == intentos - 1:
                raise Fallo(f"{type(e).__name__}: {e} en {url}") from e
        time.sleep(espera)


def robots_permite(reglas, url):
    """Si el robots.txt (su texto) permite la URL a este script, según RFC 9309: se aplican las reglas del grupo de su
    agente, o las de «*», y gana la que coincide con más caracteres de la ruta; en empate, Allow. Se evalúa aquí y
    no con urllib.robotparser porque, hasta Python 3.12, ese aplica la primera regla que coincide, y así un
    «Disallow: /» antes de un «Allow: /api/» lo prohíbe todo."""
    grupos, nuevo = [], True
    for linea in reglas.splitlines():
        clave, _, valor = linea.split("#", 1)[0].partition(":")
        clave, valor = clave.strip().lower(), valor.strip()
        if clave == "user-agent":
            if nuevo:  # varias líneas User-agent seguidas comparten grupo
                grupos.append((set(), []))
                nuevo = False
            grupos[-1][0].add(valor.lower())
        elif clave:
            nuevo = True
            if clave in ("allow", "disallow") and grupos and valor:  # «Disallow:» vacío no prohíbe nada
                grupos[-1][1].append((valor, clave == "allow"))
    agente = UA.split("/")[0].lower()
    aplican = [g for g in grupos if agente in g[0]] or [g for g in grupos if "*" in g[0]]
    u = urllib.parse.urlsplit(url)
    ruta = (u.path or "/") + (f"?{u.query}" if u.query else "")
    largo, permite = -1, True
    for _, reglas_grupo in aplican:
        for patron, allow in reglas_grupo:
            # «*» es cualquier texto y un «$» final ancla el fin de la ruta
            regex = ".*".join(map(re.escape, patron.rstrip("$").split("*"))) + ("$" if patron.endswith("$") else "")
            if re.match(regex, ruta) and (len(patron) > largo or (len(patron) == largo and allow)):
                largo, permite = len(patron), allow
    return permite


def comprobar_robots(sitio, urls, antibot=False):
    """Falla si el robots.txt del sitio prohíbe alguna de las URL que usa el adaptador (07/BUS-CANALES). Las URL
    llevan una consulta (?…) si el adaptador la usa, porque hay sitios que prohíben las rutas con consulta."""
    url = f"{sitio}/robots.txt"
    try:
        # Solo una bolsa pasa antibot: los portales falsos de las pruebas de empresas reemplazan pedir() sin él
        reglas = pedir(url, como_json=False, antibot=True) if antibot else pedir(url, como_json=False)
    except (HostBloqueado, IpBloqueada, SenalAntiBot):
        raise
    except Fallo as e:
        if e.codigo in (404, 410):
            return  # sin robots.txt, el sitio no prohíbe nada
        raise Fallo(f"no se pudo leer {url} ({e}); sin él no se sabe qué rutas permite") from e
    prohibidas = [u for u in urls if not robots_permite(reglas, u)]
    if prohibidas:
        raise Fallo(f"{url} prohíbe {', '.join(prohibidas)}: no se usa; busca otra ruta del sitio oficial "
                    "(07/BUS-CANALES)")


def campo(d, *ruta):
    """Lee un campo obligatorio; si la API cambió de forma, falla con un mensaje claro."""
    for k in ruta:
        if not isinstance(d, dict) or k not in d:
            raise Fallo(f"Falta el campo {'.'.join(ruta)}: la API pudo haber cambiado")
        d = d[k]
    return d


def texto(h):
    """HTML a texto plano conservando párrafos y viñetas."""
    if not h:
        return ""
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</h\d>|</ul>|</ol>", "\n", h)
    h = re.sub(r"(?i)<li[^>]*>", "\n- ", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h).replace("\xa0", " ")
    lineas = [" ".join(l.split()) for l in h.splitlines()]
    return "\n".join(l for l in lineas if l)


def atributos(etiqueta):
    """{nombre: valor} de los atributos de una etiqueta HTML."""
    return {k: html.unescape(v) for k, v in re.findall(r'([\w:-]+)="([^"]*)"', etiqueta)}


# --- Región de 04 -------------------------------------------------------------

# Palabras que no nombran un lugar. Una ubicación hecha solo de ellas y de los países de la región
# es demasiado general, como «Remote» o «Multiple Locations» (11, «Indeterminada»).
GENERALES = frozenset("""remote remoto remota teletrabajo hybrid hibrido hibrida home office anywhere virtual
multiple locations location ubicaciones ubicacion varias various in en de from desde and y or o""".split())


def normalizar(s):
    """Minúsculas, sin acentos y con un solo espacio, para comparar lugares (04, «Cómo se lee un grupo»)."""
    s = unicodedata.normalize("NFKD", s.casefold())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def palabra(nombre):
    """Patrón del nombre normalizado como palabra o frase completa."""
    return rf"(?<![^\W_]){re.escape(normalizar(nombre))}(?![^\W_])"


def nombra(s, nombres):
    """El texto normalizado s, una ubicación o un título, contiene alguno de los nombres como palabra o frase
    completa."""
    return any(re.search(palabra(n), s) for n in nombres if n.strip())


def sin_generales(texto):
    return " ".join(p for p in normalizar(texto).split() if p not in GENERALES)


def partes_ubicacion(literal):
    """Las partes de una ubicación, en orden, separadas por comas, guiones con espacios, paréntesis, barra, «|»
    o un punto entre palabras: «Ciudad, País», «País - Ciudad», «Remote - País», «MEX.Ciudad». El punto de una
    abreviatura («U.S.A.», «Edo. A») no separa. Cada parte va normalizada y sin las palabras generales, y las que
    quedan vacías no cuentan: «País A (Remote)» tiene una sola parte, «pais a»."""
    partes = re.split(r"\s+[-–]\s+|[,|/()]|(?<=[^\W\d_]{2})\.(?=[^\W\d_]{2})", literal)
    return [p for p in map(sin_generales, partes) if p]


def nombres_de_paises(pref):
    """Los nombres de todos los países que reconoce el script (paises_reconocidos)."""
    return set().union(*pref["reconocidos"].values())


def nombra_pais(literal, nombres):
    """La ubicación nombra uno de esos países como una de sus partes. Así otro lugar que contiene el nombre del
    país («Nuevo País A») no lo nombra."""
    buscados = {sin_generales(n) for n in nombres}
    return any(parte in buscados for parte in partes_ubicacion(literal))


def parte_localidad(literal, pref):
    """La primera parte de la ubicación que no es un país reconocido: «ciudad a» en «Ciudad A, Estado A, País A», en
    «XAA.Ciudad A» y en «Country Z, Ciudad Z». None si no hay, como en «País A» o «Remote - País A»."""
    paises = nombres_de_paises(pref)
    return next((p for p in partes_ubicacion(literal) if p not in paises), None)


def paises_nombrados(literal, pref):
    """Los códigos de los países reconocidos que la ubicación nombra como una de sus partes."""
    partes = set(partes_ubicacion(literal))
    return {c for c, nombres in pref["reconocidos"].items() if nombres & partes}


def paises_region(pref):
    """Los países de localidades, en su orden."""
    return list(dict.fromkeys(g["pais"] for g in pref["localidades"]))


def demasiado_general(s, pref):
    """La ubicación normalizada s no nombra ningún lugar fuera de los países de la región: puede estar dentro."""
    for c in paises_region(pref):
        for n in sorted(pref["reconocidos"][c], key=len, reverse=True):
            s = re.sub(palabra(n), " ", s)
    return all(p in GENERALES for p in re.findall(r"[^\W\d_]+", s))


def entre_localidad_y_pais(literal, pref):
    """Las partes de la ubicación entre la de la localidad y la siguiente que es un país (o el final), sin las que
    son solo un número, como un código postal: «estado z» en «Localidad Z, Estado Z, País A»; ninguna en «Localidad A3,
    País A (Edificio 1)» ni en «XAA.Localidad A4»."""
    nombres_pais = nombres_de_paises(pref)
    partes = partes_ubicacion(literal)
    i = next((i for i, p in enumerate(partes) if p not in nombres_pais), len(partes))
    entre = []
    for p in partes[i + 1:]:
        if p in nombres_pais:
            break
        if not re.fullmatch(r"[\d\s-]+", p):
            entre.append(p)
    return entre


def clasificar_ubicacion(literal, pref, codigos=None):
    """«dentro», «revisar» o «fuera»: una ubicación literal contra los grupos de 04/PREF-UBICACION. codigos: los
    códigos ISO de país de la vacante, si la plataforma los publica; sitúan en su país una ubicación que no nombra
    ninguno."""
    s = normalizar(literal)
    revisar = demasiado_general(s, pref)
    # Una ubicación que nombra otro país de 04, y no el del grupo, no es de ese grupo: hay ciudades y
    # divisiones homónimas entre países
    nombrados = paises_nombrados(literal, pref)
    situada = nombrados or set(codigos or ())
    localidad = parte_localidad(literal, pref)
    for g in pref["localidades"]:
        if nombrados and g["pais"] not in nombrados:
            continue
        if g["nombres"]:
            # Una ciudad homónima de su división cuenta como localidad solo en el lugar de la localidad;
            # en otro lugar nombra la división
            divisiones = {normalizar(d) for d in g["divisiones"]}
            homonimas = {sin_generales(n) for n in g["nombres"] if normalizar(n) in divisiones}
            otras = [n for n in g["nombres"] if normalizar(n) not in divisiones]
            if nombra(s, otras) or localidad in homonimas:
                return "dentro"
            # Nombra su división sin una localidad aceptada: puede estar dentro
            revisar = revisar or nombra(s, g["divisiones"])
        elif g["divisiones"]:
            if nombra(s, g["divisiones"]) or nombra(s, g["incluidas"]):
                return "dentro"
            # Red de seguridad: en su país, una ubicación con solo la localidad («Localidad, País», «XAA.Localidad»)
            # puede ser de la división si el portal no la escribe; una parte entre la localidad y el país es otra
            # división
            if g["pais"] in situada and localidad is not None:
                revisar = revisar or not entre_localidad_y_pais(literal, pref)
        elif g["pais"] in nombrados:
            return "dentro"
    return "revisar" if revisar else "fuera"


def region(literales, pref, codigos=None):
    """region_relacionada de 11 y las ubicaciones que pueden estar dentro sin nombrar una localidad aceptada.
    codigos: los códigos ISO de país de la vacante, si la plataforma los publica (clasificar_ubicacion)."""
    if not literales:
        return "Indeterminada", []
    clases = [clasificar_ubicacion(l, pref, codigos) for l in literales]
    revisar = [l for l, c in zip(literales, clases) if c == "revisar"]
    if all(c == "dentro" for c in clases):
        return "Dentro", revisar
    if "dentro" in clases:
        return "Incluye", revisar
    if revisar:
        return "Indeterminada", revisar
    return "Fuera", revisar


def es_remota(texto):
    """Una modalidad o una ubicación que dice remoto («Remote», «Remoto», «Teletrabajo»)."""
    return bool(texto) and re.search(r"(?<![^\W_])(?:remot[eoa]s?|teletrabajo)(?![^\W_])",
                                     normalizar(texto)) is not None


def alcance_remoto(literal, pref, paises=None):
    """«dentro», «revisar» o «fuera»: una remota contra el alcance del remoto de 04. Con el alcance "paises", deciden
    los códigos ISO de sus ubicaciones (paises), si la plataforma los publica; si no, los países reconocidos que nombra:
    alguno del alcance, dentro; otros, fuera; ninguno, puede estar y queda por revisar (ADR 0009)."""
    alcance = pref["remoto"]["alcance"]
    if alcance != "paises":
        return "dentro" if alcance == "cualquiera" else "fuera"
    nombrados = set(paises or ()) or paises_nombrados(literal or "", pref)
    if not nombrados:
        return "revisar"
    return "dentro" if nombrados & set(pref["remoto"]["paises"]) else "fuera"


def sin_remotas(pref, remotas):
    """Por qué no se listan remotas en esta búsqueda, o None si sí se listan."""
    if pref["remoto"]["alcance"] == "ninguno":
        return "No aplica: 04 no acepta remoto"
    if not remotas:
        return "Omitida (--sin-remotas)"
    return None


def aviso_sin_filtro_de_remoto(r):
    """La línea «revisar» de un portal sin filtro de remoto: sus remotas solo salen del listado de la región."""
    r["revisar"].append("sin filtro de remoto en el portal: solo se revisaron las remotas del listado de la región; "
                        "anotarlo en no_revisado_pendientes")


# --- Resultado de cada empresa -------------------------------------------------

def vigencia(indicador, valor, abiertos):
    """Estado sugerido según 07/BUS-VIGENCIA. Solo los valores positivos observados (abiertos) se mapean.
    El motivo lleva el prefijo «Detalle oficial: », como se registra."""
    motivo = f"Detalle oficial: {indicador}: {json.dumps(valor, ensure_ascii=False)}"
    if valor in abiertos:
        return "Confirmada abierta", motivo
    return "Revisar", motivo + " (valor no observado antes: decidir con 07/BUS-VIGENCIA)"


def fecha(instante, pref):
    """fecha_publicacion de un instante con zona (07/BUS-FECHAS): a las 00:00 UTC es una fecha sin hora y queda como
    fecha UTC; con hora real, pasa a la zona horaria de 04."""
    utc = instante.astimezone(dt.timezone.utc)
    return (utc if utc.time() == dt.time() else instante.astimezone(pref["tz"])).date().isoformat()


def instante_iso(s):
    """Una marca de tiempo ISO 8601 de una API («…Z» incluida) como datetime con zona (UTC si no trae), o None."""
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def fecha_iso(s, pref):
    """fecha() de una marca de tiempo ISO 8601, o None si no lo es."""
    t = instante_iso(s)
    return fecha(t, pref) if t else None


def vacante(pref, empresa_id, job_id, titulo, url_oficial, ubicaciones, modalidad, fecha_pub,
            estado, motivo, url_fuente, departamento, descripcion, codigos=None):
    """Los campos de `vacantes` y `observaciones` (11), con la región de 04. codigos: los códigos ISO de país de la
    vacante, si la plataforma los publica."""
    ubicaciones = [u for u in ubicaciones if u]
    reg, revisar = region(ubicaciones, pref, codigos)
    return {
        "empresa_id": empresa_id,
        "job_id": job_id,
        "titulo": titulo,
        "url_oficial": url_oficial,
        "ubicacion_literal": " | ".join(ubicaciones) if ubicaciones else None,
        "modalidad_literal": modalidad,
        "region_relacionada": reg,
        "ubicaciones_por_revisar": revisar,
        "fecha_publicacion": fecha_pub,
        "estado_vigencia": estado,
        "motivo": motivo,
        "url_fuente": url_fuente,
        "departamento": departamento,
        "descripcion": descripcion,
    }


def sin_detalle(base, fallo):
    """Vacante del listado cuyo detalle falló: 07 admite el listado como evidencia."""
    base["estado_vigencia"] = "Confirmada abierta"
    base["motivo"] = f"En listado oficial; detalle no consultado ({fallo})"
    base["descripcion"] = None
    return base


def resultado(eid, acceso):
    """Lo que entrega cada adaptador; lo llenan listado() y repartir()."""
    return {"empresa_id": eid, "acceso": acceso, "consultas": [], "total_reportado": 0, "unicos": 0,
            "completa": True, "vacantes": [], "remotas_fuera_de_region": [], "fuera_de_region": [],
            "remotas_revision": None, "revisar": []}


def listado(r, consulta, total, ids, vistas=frozenset()):
    """Suma un listado al resultado, con sus IDs únicos contra el total que reporta (07/BUS-COBERTURA).
    total = None: la fuente no lo publica. Las vacantes que ya trajo un listado anterior (vistas) se
    descuentan de los únicos y del total, para que el resultado cuente vacantes distintas."""
    r["consultas"].append(f"{consulta} ({len(ids)} únicos de {total})" if total is not None
                          else f"{consulta} ({len(ids)} únicos, sin total publicado)")
    repetidas = len(ids & vistas)
    r["unicos"] += len(ids) - repetidas
    if total is None or r["total_reportado"] is None:
        r["total_reportado"] = r["completa"] = None
    else:
        r["total_reportado"] += total - repetidas
        r["completa"] = r["completa"] and len(ids) == total


def modalidad_remota(v):
    """(remota, contradicción): si la vacante es remota por su modalidad o, si la plataforma no la publica, por su
    ubicación («País (Remote)»). Si la modalidad publicada dice otra cosa y la ubicación dice remoto, gana la
    modalidad, y la contradicción es la nota «revisar» con las dos; si no, None (ADR 0009, «Ante la duda»)."""
    modalidad, ubicacion = v["modalidad_literal"], v["ubicacion_literal"]
    if modalidad in (None, "", "No publicado"):
        return es_remota(ubicacion), None
    if not es_remota(modalidad) and es_remota(ubicacion):
        return False, (f"la modalidad publicada («{modalidad}») contradice la ubicación («{ubicacion}»): cuenta como "
                       f"«{modalidad}»; confirmar la modalidad en el anuncio")
    return es_remota(modalidad), None


def repartir(r, v, pref, de_remotas=False, paises=None, remota=None):
    """Las de la región van a vacantes; las remotas de fuera, si las trajo un filtro de remoto ya acotado al alcance
    de 04 (de_remotas) o pueden estar en ese alcance, a remotas_fuera_de_region, y las que pueden estar llevan su
    ubicación en ubicaciones_por_revisar; las demás solo dejan su ubicación en fuera_de_region. Una remota de la
    región en el alcance no lleva ubicaciones por revisar: ya se acepta como remota. paises: los códigos
    ISO de sus ubicaciones, si la plataforma los publica (alcance_remoto). remota: si es remota, cuando la plataforma
    lo dice fuera de su modalidad; si no, modalidad_remota. Devuelve si la vacante se entrega, para leer el detalle
    solo de esas."""
    if remota is None:
        remota, contradiccion = modalidad_remota(v)
        if contradiccion:
            v.setdefault("revisar", []).append(contradiccion)
    if v["region_relacionada"] != "Fuera":
        if remota and (de_remotas or alcance_remoto(v["ubicacion_literal"], pref, paises) == "dentro"):
            v["ubicaciones_por_revisar"] = []
        r["vacantes"].append(v)
        return True
    if not de_remotas:
        alcance = alcance_remoto(v["ubicacion_literal"], pref, paises) if remota else "fuera"
        if alcance == "fuera":
            anotar_fuera(r, v["ubicacion_literal"])
            return False
        if alcance == "revisar":
            v["ubicaciones_por_revisar"].append(v["ubicacion_literal"])
    r["remotas_fuera_de_region"].append(v)
    return True


def por_desplazamiento(pagina, total_de, filas_de, id_de, primera=None):
    """(filas sin repetir, total) de un listado que pagina por desplazamiento: pagina(inicio) pide la página que
    empieza en inicio, y primera es la de inicio 0, si ya se pidió. Termina al llegar al total o con una página sin
    filas nuevas."""
    d = primera or pagina(0)
    filas, ids, inicio, total = [], set(), 0, total_de(d)
    while True:
        lista = filas_de(d)
        nuevas = [f for f in lista if id_de(f) not in ids]
        if not nuevas:
            return filas, total
        ids.update(id_de(f) for f in nuevas)
        filas += nuevas
        inicio += len(lista)
        if inicio >= total:
            return filas, total
        d = pagina(inicio)


def anotar_fuera(r, ubicacion):
    """Anota una vez en fuera_de_region la ubicación de una vacante que no se entrega."""
    if (ubicacion or "") not in r["fuera_de_region"]:
        r["fuera_de_region"].append(ubicacion or "")


# --- Consulta de la ficha ---------------------------------------------------------

def es_texto(x):
    return isinstance(x, str)


def listas_por_nombre(x):
    """Un objeto: nombre → lista no vacía de textos, como las facetas o los filtros de una consulta."""
    return isinstance(x, dict) and all(lista_de_textos(v) and v for v in x.values())


def leer_consulta(conf, campos, forma):
    """La consulta de la ficha, comprobada antes de pedir nada, o None si no trae. campos: {campo: comprobación}
    de su plataforma, y forma, cómo se escribe (06/CAT-PLATAFORMAS). Debe traer al menos un campo no vacío, para
    no listar todo el portal."""
    consulta = conf.get("consulta")
    if consulta is None:
        return None
    if (set(consulta) - set(campos) or not all(campos[k](v) for k, v in consulta.items())
            or not any(v.strip() if isinstance(v, str) else v for v in consulta.values())):
        raise Fallo(f"la consulta de su ficha debe ser {forma}, con al menos uno de sus campos (06/CAT-PLATAFORMAS)")
    return consulta


def resolver(pedidas, ofrecidos, r, parametro):
    """{parámetro: [valores]} con los de la consulta que el portal ofrece hoy, buscados por su nombre sin mayúsculas
    ni acentos (ofrecidos: {parámetro: {nombre normalizado: valor}}); None si a algún parámetro no le queda ninguno,
    porque el listado saldría vacío. parametro: cómo llama la plataforma a los suyos («la faceta»), para el aviso."""
    aplicados = {}
    for p, nombres in pedidas.items():
        hay = ofrecidos.get(p, {})
        for n in nombres:
            if normalizar(n) not in hay:
                r["revisar"].append(f"{parametro} {p} no ofrece «{n}»: no hay vacantes con ese valor hoy, o el nombre "
                                    "cambió (consulta de la ficha)")
        aplicados[p] = [hay[normalizar(n)] for n in nombres if normalizar(n) in hay]
    return None if any(not v for v in aplicados.values()) else aplicados


# --- Workday --------------------------------------------------------------------
# Portal: https://<empresa>.wd<N>.myworkdayjobs.com/<sitio>. API: POST para listar, GET para el detalle.

WD_POR_PAGINA = 20  # máximo que acepta la API


def wd_api(portal):
    """(sitio, base de la API) desde la URL del portal de la ficha."""
    u = urllib.parse.urlsplit(portal)
    host = u.hostname or ""
    partes = [p for p in u.path.split("/") if p]
    if partes and re.fullmatch(r"[a-z]{2}(?:-[A-Za-z]{2})?", partes[0]):
        partes = partes[1:]  # idioma de la página, como /en-US/
    if u.scheme != "https" or not host.endswith(".myworkdayjobs.com") or not partes:
        raise Fallo(f"el portal {portal} no es de Workday: debe ser https://<empresa>.wd<N>.myworkdayjobs.com/<sitio> "
                    "(06/CAT-PLATAFORMAS)")
    return f"https://{host}", f"https://{host}/wday/cxs/{host.split('.')[0]}/{partes[0]}"


def wd_listar(base, facetas, busqueda=""):
    filas, inicio, total = [], 0, None
    while total is None or inicio < total:
        d = pedir(f"{base}/jobs", {"appliedFacets": facetas, "limit": WD_POR_PAGINA, "offset": inicio,
                                   "searchText": busqueda})
        if total is None:
            total = campo(d, "total")  # las páginas siguientes pueden traer 0
        pagina = campo(d, "jobPostings")
        if not pagina:
            break
        filas += pagina
        inicio += WD_POR_PAGINA
    return filas, total


def wd_facetas(base):
    """(parámetro, nombre, id) de cada valor de faceta, también de las anidadas (locationMainGroup → locations).
    Un valor solo aparece si alguna vacante lo tiene."""
    d = pedir(f"{base}/jobs", {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    valores = []

    def recorrer(facetas):
        for f in facetas:
            for v in f.get("values", []):
                if "facetParameter" in v:
                    recorrer([v])
                else:
                    valores.append((f.get("facetParameter"), v.get("descriptor") or "", v.get("id")))

    recorrer(campo(d, "facets"))
    return valores


def wd_elegir(facetas, es_parametro, es_valor):
    """(parámetro, [(nombre, id)]) del parámetro que más valores aceptados ofrece, o None. Se aplica uno solo
    porque Workday combina parámetros distintos con «y»."""
    por_parametro = {}
    for p, nombre, i in facetas:
        if p and es_parametro(p) and es_valor(nombre):
            por_parametro.setdefault(p, []).append((nombre, i))
    if not por_parametro:
        return None
    p = max(por_parametro, key=lambda k: len(por_parametro[k]))
    return p, por_parametro[p]


def wd_es_pais(p):
    return "country" in p.lower()


def wd_es_ubicacion(p):
    return "location" in p.lower() and not wd_es_pais(p)


def wd_paises(facetas, pref, codigos, con_localidades):
    """(faceta, códigos sin valor): la faceta que acota el listado a esos países y los que no ofrece. Es la
    de país, si el portal la tiene; si no, las ubicaciones que nombran uno de ellos o, con con_localidades,
    una localidad aceptada de 04. Un valor solo existe si alguna vacante lo tiene."""
    def de_pais(c):
        iguales = {normalizar(n) for n in pref["paises"][c]}
        return lambda d: normalizar(d) in iguales

    def de_ubicacion(c):
        del_pais = {**pref, "localidades": [g for g in pref["localidades"] if g["pais"] == c]}
        return lambda d: nombra_pais(d, pref["paises"][c]) or (
            con_localidades and clasificar_ubicacion(d, del_pais) == "dentro")

    if any(wd_es_pais(p) for p, _, _ in facetas if p):
        es_parametro, prueba = wd_es_pais, de_pais
    else:
        es_parametro, prueba = wd_es_ubicacion, de_ubicacion
    pruebas = {c: prueba(c) for c in codigos}
    elegida = wd_elegir(facetas, es_parametro, lambda d: any(ofrece(d) for ofrece in pruebas.values()))
    faltan = [c for c, ofrece in pruebas.items() if not elegida or not any(ofrece(n) for n, _ in elegida[1])]
    return elegida, faltan


def wd_aviso_pais(r, codigos):
    for c in codigos:
        r["revisar"].append(f"el portal no ofrece {c} en su faceta de país ni en la de ubicación: la empresa no "
                            "tiene vacantes ahí hoy, o el portal escribe el país de otra forma (paises de 04)")


def wd_vacante(pref, eid, base, f):
    """Detalle de una vacante del listado, con comprobación de ID por la ruta."""
    url_det = base + f["externalPath"]
    v = vacante(pref, eid, None, f["title"], None, [f.get("locationsText")], None, None, None, None, url_det,
                None, None)
    try:
        det = campo(pedir(url_det), "jobPostingInfo")
        ubic = [campo(det, "location")] + list(det.get("additionalLocations") or [])
        v = vacante(pref, eid, campo(det, "jobReqId"), campo(det, "title"), det.get("externalUrl"), ubic,
                    det.get("remoteType"), det.get("startDate"), *vigencia("canApply", det.get("canApply"), (True,)),
                    url_det, det.get("jobFamily") or None, texto(det.get("jobDescription")))
        # La ruta termina en _<jobReqId>, a veces con un sufijo -1 (republicación)
        if not re.search(rf"_{re.escape(v['job_id'])}(-\d+)?$", f["externalPath"]):
            raise Fallo(f"devolvió otro ID ({v['job_id']})")
    except Fallo as e:
        sin_detalle(v, e)
    return v


WD_CONSULTA = ({"facetas": listas_por_nombre, "texto": es_texto},
               '{"facetas": {"<parámetro>": ["<nombre visible>"]}, "texto": "<búsqueda>"}')


def wd_recorrer(r, pref, eid, base, aplicadas, nombre, vistas, de_remotas=False, busqueda=""):
    """Lista con las facetas elegidas ({parámetro: [(nombre, id)]}) y el texto, lee el detalle de cada vacante
    que no se había visto y la reparte. Devuelve la descripción del listado."""
    filas, total = wd_listar(base, {p: [i for _, i in valores] for p, valores in aplicadas.items()}, busqueda)
    ids = {f["externalPath"] for f in filas}
    filtro = "; ".join([f"{p} = {', '.join(n for n, _ in valores)}" for p, valores in aplicadas.items()]
                       + ([f"searchText = {busqueda}"] if busqueda else []))
    listado(r, f"{nombre}: POST {base}/jobs, {filtro}", total, ids, vistas)
    for f in filas:
        if f["externalPath"] not in vistas:
            vistas.add(f["externalPath"])
            repartir(r, wd_vacante(pref, eid, base, f), pref, de_remotas)
    return f"{filtro}: {len(ids)} únicos de {total}"


def wd_remotas(r, pref, eid, base, facetas, vistas):
    """Las remotas, con el filtro de remoto del portal según el alcance de 04: la faceta de remoto (acotada a los
    países del remoto) o, si no la tiene, sus ubicaciones «Remote …». Devuelve cómo se revisaron."""
    alcance, codigos = pref["remoto"]["alcance"], pref["remoto"]["paises"]
    remoto = wd_elegir(facetas, lambda p: "remote" in p.lower(), es_remota)
    if remoto:
        aplicadas = dict([remoto])
        if alcance == "paises":
            pais, faltan = wd_paises(facetas, pref, codigos, False)
            wd_aviso_pais(r, faltan)
            if not pais:
                return f"Faceta {remoto[0]}, sin listado: el portal no ofrece {', '.join(codigos)}"
            aplicadas[pais[0]] = pais[1]
    else:
        nombres = [n for c in codigos for n in pref["paises"][c]]
        ubicaciones = wd_elegir(facetas, wd_es_ubicacion, lambda d: es_remota(d) and (
            alcance == "cualquiera" or nombra_pais(d, nombres)))
        if not ubicaciones:
            aviso_sin_filtro_de_remoto(r)
            return "No disponible: el portal no tiene faceta de remoto ni ubicaciones «Remote»"
        aplicadas = dict([ubicaciones])
    return "Filtro de remoto del portal, " + wd_recorrer(r, pref, eid, base, aplicadas, "Remotas", vistas,
                                                         de_remotas=True)


def workday(eid, conf, pref, remotas):
    """Adaptador de Workday (06/CAT-PLATAFORMAS)."""
    sitio, base = wd_api(conf["portal"])
    consulta = leer_consulta(conf, *WD_CONSULTA)
    comprobar_robots(sitio, [f"{base}/jobs", f"{base}/job/"])
    facetas = wd_facetas(base)
    r = resultado(eid, "API de Workday (POST para listar, GET para el detalle)")
    vistas = set()
    if consulta:
        ofrecidos = {}
        for p, nombre, i in facetas:
            ofrecidos.setdefault(p, {})[normalizar(nombre)] = (nombre, i)
        aplicadas = resolver(consulta.get("facetas", {}), ofrecidos, r, "la faceta")
        if aplicadas is not None:
            wd_recorrer(r, pref, eid, base, aplicadas, "Consulta de la ficha", vistas,
                        busqueda=consulta.get("texto", ""))
    elif pref["localidades"]:
        faceta, faltan = wd_paises(facetas, pref, paises_region(pref), True)
        wd_aviso_pais(r, faltan)
        if faceta:
            wd_recorrer(r, pref, eid, base, dict([faceta]), "Países de la región", vistas)
    r["remotas_revision"] = sin_remotas(pref, remotas) or wd_remotas(r, pref, eid, base, facetas, vistas)
    return r


# --- Eightfold ------------------------------------------------------------------
# Portal: https://<sitio>/careers?domain=<dominio>, en <empresa>.eightfold.ai o en un dominio de la empresa. API pcsx
# del buscador: GET para listar, 10 por página, y GET para el detalle.

EF_ABIERTOS = ("allowed", "log_in")  # applyAction.status: postulación directa o tras iniciar sesión
EF_CONSULTA = ({"ubicaciones": lista_de_textos, "filtros": listas_por_nombre, "texto": es_texto},
               '{"ubicaciones": ["<lugar>"], "filtros": {"<filtro>": ["<nombre visible>"]}, "texto": "<búsqueda>"}')


def ef_api(portal):
    """(sitio, dominio) desde la URL del portal de la ficha."""
    u = urllib.parse.urlsplit(portal)
    dominio = urllib.parse.parse_qs(u.query).get("domain", [""])[0].strip()
    if u.scheme != "https" or not u.hostname or not dominio:
        raise Fallo(f"el portal {portal} no sirve para Eightfold: debe ser https://<sitio>/careers?domain=<dominio> "
                    "(06/CAT-PLATAFORMAS)")
    return f"https://{u.hostname}", dominio


def ef_pagina(sitio, dominio, parametros):
    """Una página del listado (start va en parametros), en el único orden estable: con el de por defecto, por
    distancia, las páginas se traslapan."""
    consulta = urllib.parse.urlencode({"domain": dominio, "sort_by": "timestamp", **parametros}, doseq=True)
    d = campo(pedir(f"{sitio}/api/pcsx/search?{consulta}"), "data")
    if campo(d, "sortBy") != "timestamp":
        raise Fallo(f"la página start={parametros['start']} no vino ordenada por timestamp")
    return d


def ef_filtros(sitio, dominio):
    """{filterName: [opciones]} de los filtros del buscador, desde su primera página sin filtros. Un sitio con el
    buscador anterior de Eightfold, sin la API pcsx, responde HTTP 403."""
    try:
        d = ef_pagina(sitio, dominio, {"start": 0})
    except Fallo as e:
        if e.codigo == 403:
            raise Fallo(f"{sitio} respondió HTTP 403 a la API pcsx: puede usar el buscador anterior de Eightfold, que "
                        "este adaptador no lee, o bloquear el acceso (06/CAT-PLATAFORMAS)") from e
        raise
    return {f.get("filterName"): f.get("options") or [] for f in (d.get("filterDef") or {}).get("allFilters") or []
            if isinstance(f, dict)}


def ef_ofrecidos(filtros):
    """{filtro: {nombre normalizado: valor}} de sus opciones, por su valor o por su nombre visible (resolver)."""
    ofrecidos = {}
    for nombre, opciones in filtros.items():
        for o in opciones:
            if isinstance(o, dict) and isinstance(o.get("value"), str):
                for k in ("value", "label"):
                    if isinstance(o.get(k), str):
                        ofrecidos.setdefault(nombre, {})[normalizar(o[k])] = o["value"]
    return ofrecidos


def ef_listar(sitio, dominio, parametros, primera=None):
    """(posiciones sin repetir, total) de todas las páginas. primera: la página start=0, si ya se pidió."""
    return por_desplazamiento(lambda inicio: ef_pagina(sitio, dominio, {**parametros, "start": inicio}),
                              lambda d: campo(d, "count"), lambda d: campo(d, "positions"),
                              lambda p: campo(p, "id"), primera)


def ef_pais(sitio, dominio, parametros, pref, c):
    """(nombre, página start=0) del primer nombre de c en 04 que el buscador busca como país; (None, None) si
    ninguno. A una ciudad, o a un lugar que no reconoce, le aplica un radio (distance en appliedFilters)."""
    for nombre in pref["paises"][c]:
        d = ef_pagina(sitio, dominio, {**parametros, "location": nombre, "start": 0})
        if "distance" not in campo(d, "appliedFilters"):
            return nombre, d
    return None, None


def ef_aviso_pais(r, c):
    r["revisar"].append(f"el buscador no reconoce como país ningún nombre de {c} en 04 (le aplica un radio): agrega "
                        "a paises de 04 el nombre que usa el portal")


def ef_codigos(p):
    """Los códigos ISO de país de sus ubicaciones normalizadas: «Ciudad, ST, XA», «ST,XA» o «XA»."""
    finales = (s.rsplit(",", 1)[-1].strip() for s in p.get("standardizedLocations") or [] if isinstance(s, str))
    return {c for c in finales if re.fullmatch(r"[A-Z]{2}", c)}


def ef_vacante(pref, eid, sitio, dominio, p):
    """Vacante desde el listado, que ya trae ubicaciones, modalidad y fecha; el detalle se lee aparte."""
    try:
        publicada = fecha(dt.datetime.fromtimestamp(p.get("postedTs"), dt.timezone.utc), pref)
    except (TypeError, ValueError, OverflowError, OSError):  # sin fecha, o no en segundos
        publicada = None
    modalidad = " | ".join(str(m) for m in (p.get("workLocationOption"), p.get("locationFlexibility")) if m) or None
    url_det = f"{sitio}/api/pcsx/position_details?" + urllib.parse.urlencode(
        {"position_id": p["id"], "domain": dominio, "hl": "en"})
    return vacante(pref, eid, p.get("displayJobId"), p.get("name"),
                   sitio + p["positionUrl"] if p.get("positionUrl") else None, p.get("locations") or [], modalidad,
                   publicada, None, None, url_det, p.get("department"), None, ef_codigos(p))


def ef_detalle(v, pid):
    """Vigencia y descripción desde el detalle, con comprobación de ID."""
    try:
        det = campo(pedir(v["url_fuente"]), "data")
        if det.get("id") != pid:
            raise Fallo(f"devolvió otro ID ({det.get('id')})")
        v["estado_vigencia"], v["motivo"] = vigencia(
            "applyAction.status", campo(det, "positionUserActions", "applyAction", "status"), EF_ABIERTOS)
        v["descripcion"] = texto(det.get("jobDescription"))
    except Fallo as e:
        sin_detalle(v, e)


def ef_recorrer(r, pref, eid, sitio, dominio, parametros, nombre, vistas, de_remotas=False, primera=None):
    """Lista con esos parámetros, reparte las vacantes que no se habían visto y lee el detalle de las que se
    entregan. Devuelve la descripción del listado."""
    filas, total = ef_listar(sitio, dominio, parametros, primera)
    ids = {p["id"] for p in filas}
    filtro = "; ".join(f"{k} = {', '.join(v) if isinstance(v, list) else v}" for k, v in parametros.items())
    listado(r, f"{nombre}: GET {sitio}/api/pcsx/search, {filtro}", total, ids, vistas)
    for p in filas:
        if p["id"] not in vistas:
            vistas.add(p["id"])
            v = ef_vacante(pref, eid, sitio, dominio, p)
            if repartir(r, v, pref, de_remotas, ef_codigos(p)):
                ef_detalle(v, p["id"])
    return f"{filtro}: {len(ids)} únicos de {total}"


def ef_remotas(r, pref, eid, sitio, dominio, filtros, vistas):
    """Las remotas según el alcance de 04: con el filtro de modalidad del buscador (work_location_option), por país
    si el alcance es "paises", o, si no lo tiene, con su búsqueda «Remote», que trae las de todos los países. Como
    la búsqueda por país también puede traer remotas abiertas a otros países, con el alcance "paises" lo decide el
    código de país de cada vacante. Devuelve cómo se revisaron."""
    alcance, codigos = pref["remoto"]["alcance"], pref["remoto"]["paises"]
    remotos = [o["value"] for o in filtros.get("work_location_option", []) if isinstance(o, dict)
               and isinstance(o.get("value"), str) and (es_remota(o["value"]) or es_remota(o.get("label")))]
    if remotos:
        parametros = {"filter_work_location_option": remotos}
        if alcance == "cualquiera":
            return "Filtro de remoto del portal, " + ef_recorrer(r, pref, eid, sitio, dominio, parametros, "Remotas",
                                                                 vistas, de_remotas=True)
        revisadas = []
        for c in codigos:
            nombre, primera = ef_pais(sitio, dominio, parametros, pref, c)
            if nombre:
                revisadas.append(ef_recorrer(r, pref, eid, sitio, dominio, {"location": nombre, **parametros},
                                             "Remotas", vistas, primera=primera))
            else:
                ef_aviso_pais(r, c)
        return "Filtro de remoto del portal, " + ("; ".join(revisadas) or f"sin listado: el buscador no reconoce "
                                                                          f"{', '.join(codigos)} como país")
    d = ef_pagina(sitio, dominio, {"location": "Remote", "start": 0})
    if campo(d, "appliedFilters").get("includeRemote") != ["1"]:
        aviso_sin_filtro_de_remoto(r)
        return "No disponible: el buscador no tiene filtro de modalidad ni búsqueda «Remote»"
    return "Búsqueda «Remote» del portal, " + ef_recorrer(r, pref, eid, sitio, dominio, {"location": "Remote"},
                                                          "Remotas", vistas, alcance == "cualquiera", d)


def eightfold(eid, conf, pref, remotas):
    """Adaptador de Eightfold, para los buscadores con la API pcsx (06/CAT-PLATAFORMAS)."""
    sitio, dominio = ef_api(conf["portal"])
    consulta = leer_consulta(conf, *EF_CONSULTA)
    # Con todos los parámetros que se mandan, por si el robots.txt prohíbe alguno
    busqueda = urllib.parse.urlencode({"domain": dominio, "sort_by": "timestamp", "location": "x", "query": "x",
                                       "filter_work_location_option": "x", "start": 0})
    detalle = urllib.parse.urlencode({"position_id": 0, "domain": dominio, "hl": "en"})
    comprobar_robots(sitio, [f"{sitio}/api/pcsx/search?{busqueda}", f"{sitio}/api/pcsx/position_details?{detalle}"])
    filtros = ef_filtros(sitio, dominio)
    r = resultado(eid, "API pcsx de Eightfold (GET para listar y para el detalle)")
    vistas = set()
    if consulta:
        aplicados = resolver(consulta.get("filtros", {}), ef_ofrecidos(filtros), r, "el filtro")
        if aplicados is not None:
            parametros = {f"filter_{k}": v for k, v in aplicados.items()}
            if consulta.get("texto", "").strip():
                parametros["query"] = consulta["texto"]
            for lugar in consulta.get("ubicaciones") or [None]:
                ef_recorrer(r, pref, eid, sitio, dominio, {**({"location": lugar} if lugar else {}), **parametros},
                            "Consulta de la ficha", vistas)
    elif pref["localidades"]:
        for c in paises_region(pref):
            nombre, primera = ef_pais(sitio, dominio, {}, pref, c)
            if nombre:
                ef_recorrer(r, pref, eid, sitio, dominio, {"location": nombre}, "Países de la región", vistas,
                            primera=primera)
            else:
                ef_aviso_pais(r, c)
    r["remotas_revision"] = sin_remotas(pref, remotas) or ef_remotas(r, pref, eid, sitio, dominio, filtros, vistas)
    return r


# --- Workable -------------------------------------------------------------------
# Portal: https://apply.workable.com/<cuenta>/. API: POST para listar (v3, 10 por página, con token) y GET para el
# detalle (v2).

WK_SITIO = "https://apply.workable.com"


def wk_ubicaciones(u):
    """Las ubicaciones de una consulta: objetos con countryCode, region o city, como las da el listado."""
    return isinstance(u, list) and all(isinstance(l, dict) and l and set(l) <= {"countryCode", "region", "city"}
                                       and all(isinstance(x, str) and x.strip() for x in l.values()) for l in u)


WK_CONSULTA = ({"ubicaciones": wk_ubicaciones, "texto": es_texto},
               '{"ubicaciones": [{"countryCode": "<código>", "region": "<región>", "city": "<ciudad>"}], '
               '"texto": "<búsqueda>"}')


def wk_cuenta(portal):
    """La cuenta de la empresa desde la URL del portal de la ficha."""
    u = urllib.parse.urlsplit(portal)
    partes = [p for p in u.path.split("/") if p]
    if u.scheme != "https" or u.hostname != "apply.workable.com" or not partes or partes[0] in ("j", "api"):
        raise Fallo(f"el portal {portal} no es de Workable: debe ser {WK_SITIO}/<cuenta>/ (06/CAT-PLATAFORMAS)")
    return partes[0]


def wk_listar(base, filtros):
    """(vacantes sin repetir, total) de todas las páginas, con esos campos del cuerpo. Una página llena trae
    nextPage aunque la siguiente salga vacía."""
    cuerpo = {"query": "", "location": [], "department": [], "worktype": [], "remote": [], **filtros}
    filas, ids, total = [], set(), None
    while True:
        d = pedir(f"{base}/jobs", cuerpo)
        if total is None:
            total = campo(d, "total")
        nuevas = [f for f in campo(d, "results") if campo(f, "shortcode") not in ids]
        ids.update(f["shortcode"] for f in nuevas)
        filas += nuevas
        if not nuevas or not d.get("nextPage"):
            return filas, total
        cuerpo = {**cuerpo, "token": d["nextPage"]}


def wk_vacante(pref, eid, cuenta, f):
    """Vacante desde el listado, que ya trae ubicaciones, modalidad y fecha; el detalle se lee aparte."""
    sc = f["shortcode"]
    lugares = [", ".join(x for x in (l.get("city"), l.get("region"), l.get("country")) if x)
               for l in f.get("locations") or []]
    return vacante(pref, eid, sc, f.get("title"), f"{WK_SITIO}/{cuenta}/j/{sc}/", lugares, f.get("workplace"),
                   fecha_iso(f.get("published"), pref), None, None, f"{WK_SITIO}/api/v2/accounts/{cuenta}/jobs/{sc}",
                   None, None, wk_codigos(f))


def wk_codigos(f):
    """Los códigos ISO de país de sus ubicaciones."""
    return {l.get("countryCode") for l in f.get("locations") or []} - {None, ""}


def wk_detalle(v, sc):
    """Vigencia, departamento y descripción desde el detalle, con comprobación de ID."""
    try:
        det = pedir(v["url_fuente"])
        if campo(det, "shortcode") != sc:
            raise Fallo(f"devolvió otro ID ({det['shortcode']})")
        v["estado_vigencia"], v["motivo"] = vigencia("state", det.get("state"), ("published",))
        departamento = det.get("department")
        v["departamento"] = (" / ".join(departamento) if isinstance(departamento, list) else departamento) or None
        secciones = (texto(det.get(k)) for k in ("description", "requirements", "benefits"))
        v["descripcion"] = "\n\n".join(s for s in secciones if s)
    except Fallo as e:
        sin_detalle(v, e)


def wk_recorrer(r, pref, eid, cuenta, filtros, nombre, vistas, de_remotas=False):
    """Lista con esos campos del cuerpo, reparte las vacantes que no se habían visto y lee el detalle de las que se
    entregan. Una vacante es remota por workplace o por el booleano remote, aunque workplace diga otra cosa.
    Devuelve la descripción del listado."""
    base = f"{WK_SITIO}/api/v3/accounts/{cuenta}"
    filas, total = wk_listar(base, filtros)
    ids = {f["shortcode"] for f in filas}
    filtro = "; ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in filtros.items())
    listado(r, f"{nombre}: POST {base}/jobs, {filtro}", total, ids, vistas)
    for f in filas:
        if f["shortcode"] not in vistas:
            vistas.add(f["shortcode"])
            v = wk_vacante(pref, eid, cuenta, f)
            codigos = wk_codigos(f)
            if repartir(r, v, pref, de_remotas, codigos, remota=True if f.get("remote") is True else None):
                wk_detalle(v, f["shortcode"])
    return f"{filtro}: {len(ids)} únicos de {total}"


def wk_remotas(r, pref, eid, cuenta, vistas):
    """Las remotas, con el filtro de remoto de la API, acotado a los países del remoto si el alcance es "paises".
    Ese filtro de país también trae las remotas abiertas a cualquier país, así que ahí el alcance se decide por los
    códigos de país de cada vacante. Devuelve cómo se revisaron."""
    filtros = {"remote": [True]}
    if pref["remoto"]["alcance"] == "paises":
        filtros["location"] = [{"countryCode": c} for c in pref["remoto"]["paises"]]
    return "Filtro de remoto del portal, " + wk_recorrer(r, pref, eid, cuenta, filtros, "Remotas", vistas,
                                                         de_remotas=pref["remoto"]["alcance"] == "cualquiera")


def workable(eid, conf, pref, remotas):
    """Adaptador de Workable (06/CAT-PLATAFORMAS)."""
    cuenta = wk_cuenta(conf["portal"])
    consulta = leer_consulta(conf, *WK_CONSULTA)
    comprobar_robots(WK_SITIO, [f"{WK_SITIO}/api/v3/accounts/{cuenta}/jobs",
                                f"{WK_SITIO}/api/v2/accounts/{cuenta}/jobs/"])
    r = resultado(eid, "API de Workable: listado v3 (POST) y detalle v2 (GET)")
    vistas = set()
    if consulta:
        filtros = {"location": consulta.get("ubicaciones"), "query": consulta.get("texto", "").strip()}
        wk_recorrer(r, pref, eid, cuenta, {k: v for k, v in filtros.items() if v}, "Consulta de la ficha", vistas)
    elif pref["localidades"]:
        wk_recorrer(r, pref, eid, cuenta, {"location": [{"countryCode": c} for c in paises_region(pref)]},
                    "Países de la región", vistas)
    r["remotas_revision"] = sin_remotas(pref, remotas) or wk_remotas(r, pref, eid, cuenta, vistas)
    return r


# --- SmartRecruiters ------------------------------------------------------------
# Portal: el sitio de carreras, https://careers.smartrecruiters.com/<empresa>. Listado agrupado en HTML (GET), con el
# «Show more» de cada grupo, y página de cada publicación en jobs.smartrecruiters.com (GET, HTML). La API de
# api.smartrecruiters.com no se usa: su robots.txt la prohíbe.

SR_CARRERAS = "https://careers.smartrecruiters.com"
SR_PUBLICACIONES = "https://jobs.smartrecruiters.com"
SR_WWW = "https://www.smartrecruiters.com"
SR_PAGINAS = 200  # tope de páginas de grupos; si se alcanza, la paginación cambió
SR_POR_PAGINA = 10  # publicaciones por página del «Show more» de un grupo
SR_SECCIONES = ("jobDescription", "qualifications", "additionalInformation")
SR_CONSULTA = ({"grupos": lista_de_textos, "texto": es_texto},
               '{"grupos": ["<nombre visible del grupo>"], "texto": "<búsqueda>"}')


def sr_empresa(portal):
    """El identificador de la empresa desde la URL del portal de la ficha."""
    u = urllib.parse.urlsplit(portal)
    partes = [p for p in u.path.split("/") if p]
    if (u.scheme != "https" or u.hostname not in ("careers.smartrecruiters.com", "jobs.smartrecruiters.com")
            or not partes or partes[0] == "sr-jobs"):
        raise Fallo(f"el portal {portal} no es de SmartRecruiters: debe ser {SR_CARRERAS}/<empresa> "
                    "(06/CAT-PLATAFORMAS)")
    return partes[0]


def sr_url(empresa, recurso, filtros, **parametros):
    """URL del listado del sitio de carreras: «groups» (los grupos) o «more» (el «Show more» de uno)."""
    return f"{SR_CARRERAS}/{empresa}/api/{recurso}?" + urllib.parse.urlencode({**filtros, **parametros},
                                                                               quote_via=urllib.parse.quote)


def sr_publicaciones(h):
    """Las publicaciones de un fragmento del listado: id, url, título, ref (o None) y los textos bajo el título."""
    pubs = []
    for enlace, cuerpo in re.findall(r"<a\s([^>]*\bjs-job-ad-link\b[^>]*)>(.*?)</a>", h, re.S):
        a = atributos(enlace)
        url = a.get("href", "").split("?")[0]
        m = re.match(rf"{re.escape(SR_PUBLICACIONES)}/[^/]+/(\d+)", url)
        titulo = re.search(r"<h4[^>]*>(.*?)</h4>", cuerpo, re.S)
        if not (m and titulo):
            raise Fallo("el listado del sitio de carreras cambió de forma (una publicación sin ID o sin título)")
        # aria-label: «<título> - <ref>»; sin ref, «undefined»
        aria = a.get("aria-label", "")
        ref = aria.rpartition(" - ")[2].strip() if " - " in aria else ""
        desc = re.search(r'<p class="details-desc job-desc">(.*?)</p>', cuerpo, re.S)
        textos = [texto(s) for s in re.findall(r"<span[^>]*>(.*?)</span>", desc.group(1), re.S)] if desc else []
        pubs.append({"id": m.group(1), "url": url, "titulo": texto(titulo.group(1)),
                     "ref": None if ref in ("", "undefined") else ref, "textos": [t for t in textos if t]})
    return pubs


def sr_grupos_de_pagina(h):
    """Los grupos de una página: nombre, total (data-qty), las publicaciones que muestra y su «Show more»."""
    grupos = []
    for total, s in re.findall(r'<section data-qty="(\d+)"[^>]*>(.*?)</section>', h, re.S):
        nombre = re.search(r"<h3[^>]*>(.*?)</h3>", s, re.S)
        mas = re.search(r"<a\s([^>]*\bjs-more\b[^>]*)>", s)
        a = atributos(mas.group(1)) if mas else {}
        if not nombre or (mas and not (a.get("data-type") and a.get("data-value"))):
            raise Fallo("el listado del sitio de carreras cambió de forma (un grupo sin nombre o con otro «Show more»)")
        grupos.append({"nombre": texto(nombre.group(1)), "total": int(total), "publicaciones": sr_publicaciones(s),
                       "mas": (a["data-type"], urllib.parse.unquote(a["data-value"])) if mas else None})
    if len(re.findall(r"\bjs-job-ad-link\b", h)) != sum(len(g["publicaciones"]) for g in grupos):
        raise Fallo("el listado del sitio de carreras cambió de forma (publicaciones fuera de un grupo)")
    return grupos


def sr_grupos(empresa, filtros):
    """Los grupos de todas las páginas del listado. Sin filtros, el sitio los reparte en páginas; con un filtro, los
    repite todos en cada una: se para en la primera página que no trae un grupo nuevo."""
    grupos, vistos = [], set()
    for p in range(SR_PAGINAS):
        nuevos = []
        for g in sr_grupos_de_pagina(pedir(sr_url(empresa, "groups", filtros, page=p), como_json=False)):
            clave = (g["nombre"], g["total"], tuple(x["id"] for x in g["publicaciones"]))
            if clave not in vistos:
                vistos.add(clave)
                nuevos.append(g)
        if not nuevos:
            return grupos
        grupos += nuevos
    raise Fallo("el listado de grupos no termina: la paginación del sitio pudo haber cambiado")


def sr_completar(empresa, filtros, g):
    """Las publicaciones del grupo, también las que esconde su «Show more»: sus páginas, hasta una vacía. La página 0
    repite las que muestra el grupo."""
    pubs = {x["id"]: x for x in g["publicaciones"]}
    if g["mas"]:
        tipo, valor = g["mas"]
        for k in range(g["total"] // SR_POR_PAGINA + 2):  # más la página 0 y la vacía del final
            pagina = sr_publicaciones(pedir(sr_url(empresa, "more", filtros, type=tipo, value=valor, page=k),
                                            como_json=False))
            if not pagina:
                break
            for x in pagina:
                pubs.setdefault(x["id"], x)
    return list(pubs.values())


def sr_pagina(x):
    """Los campos de la página de una publicación, con comprobación de ID."""
    h = pedir(x["url"], como_json=False)
    canonica = re.search(r'<link\s[^>]*\brel="canonical"[^>]*>', h)
    devuelto = re.search(r"/(\d+)[^/]*$", atributos(canonica.group(0)).get("href", "")) if canonica else None
    if not devuelto:
        raise Fallo("la página no trae su ID (link canonical)")
    if devuelto.group(1) != x["id"]:
        raise Fallo(f"devolvió otro ID ({devuelto.group(1)})")
    micro = dict(re.findall(r'itemprop="(address(?:Locality|Region|Country))"[^>]*\bcontent="([^"]*)"', h))
    partes = [html.unescape(micro[k]).strip() for k in ("addressLocality", "addressRegion", "addressCountry")
              if micro.get(k, "").strip()]
    ubicacion = re.search(r"<spl-job-location\s[^>]*>", h)
    a = atributos(ubicacion.group(0)) if ubicacion else {}
    publicada = re.search(r'itemprop="datePosted"[^>]*\bcontent="([^"]*)"', h)
    ref = re.search(r"'jobRefCode': '([^']+)'", h)
    departamento = re.search(r'<li class="job-detail">\s*Department:\s*(.*?)</li>', h, re.S)
    secciones = dict(re.findall(r'<section class="job-section" id="st-(\w+)"[^>]*>(.*?)</section>', h, re.S))
    return {"lugar": ", ".join({normalizar(p): p for p in partes}.values()),  # sin partes repetidas («Canada, CANADA»)
            "modalidad": " | ".join(m for m in (a.get("workplaceType"), a.get("workplaceDescription")) if m) or None,
            "publicada": publicada.group(1) if publicada else None, "ref": ref.group(1) if ref else None,
            "departamento": (texto(departamento.group(1)) or None) if departamento else None,
            "abierta": 'data-sr-track="apply"' in h,
            "descripcion": "\n\n".join(texto(secciones[k]) for k in SR_SECCIONES if k in secciones)}


def sr_vacante(pref, eid, x, lugares, modalidad, pagina=None):
    """Vacante de una publicación con su página (pagina: la ya leída); si la página falla, queda con lo del listado.
    modalidad: la del filtro que la trajo, si la dice."""
    v = vacante(pref, eid, x["ref"], x["titulo"], x["url"], lugares, modalidad, None, None, None, x["url"], None, None)
    try:
        p = pagina or sr_pagina(x)
    except Fallo as e:
        return sin_detalle(v, e)
    return vacante(pref, eid, p["ref"] or x["ref"], x["titulo"], x["url"], [p["lugar"]] if p["lugar"] else lugares,
                   p["modalidad"] or modalidad, fecha_iso(p["publicada"], pref),
                   *vigencia('botón de postulación (data-sr-track="apply")', p["abierta"], (True,)), x["url"],
                   p["departamento"], p["descripcion"])


def sr_recorrer(r, pref, eid, empresa, filtros, nombre, vistas, puede_estar, de_remotas=False, modalidad=None,
                elegidos=None):
    """Lista los grupos con esos filtros, completa los que pueden traer vacantes buscadas, lee la página de cada
    publicación que puede serlo (puede_estar: si puede serlo, por sus lugares del listado) y la reparte. elegidos:
    los grupos de la consulta. Devuelve la descripción del listado.

    Un sitio agrupa por ubicación o por otro campo, como el departamento, y el «Show more» de un grupo grande dice
    cuál. Por ubicación, el lugar de una publicación es el nombre de su grupo, y un grupo que no puede estar no se
    completa; por otro campo, es el texto bajo su título; si ningún grupo lo dice, se prueban los dos. Un lugar que no
    nombra un país de 04, como «Ciudad, Estado», lo decide la página de la primera publicación con ese lugar."""
    grupos = sr_grupos(empresa, filtros)
    tipos = {g["mas"][0] for g in grupos if g["mas"]}
    por_ubicacion = "location" in tipos
    leidas, decididos = {}, {}  # páginas ya leídas, que no se vuelven a pedir, y lo que decidieron por lugar

    def lugares_de(g, x):
        return [g["nombre"]] if por_ubicacion else x["textos"] if tipos else [g["nombre"], *x["textos"]]

    def se_lee(lugares, x):
        if not lugares or puede_estar(lugares):
            return True
        clave = " | ".join(lugares)
        if paises_nombrados(clave, pref):
            return False
        if clave not in decididos:
            try:
                leidas[x["id"]] = sr_pagina(x)
                decididos[clave] = puede_estar([leidas[x["id"]]["lugar"] or clave])
            except Fallo:
                decididos[clave] = True  # sin la página no se sabe: se leen, y quedan con lo del listado
        return decididos[clave]

    if elegidos is not None:
        pedidos = {normalizar(n) for n in elegidos}
        hay = {normalizar(g["nombre"]) for g in grupos}
        for n in elegidos:
            if normalizar(n) not in hay:
                r["revisar"].append(f"el sitio no tiene el grupo «{n}»: no hay vacantes en él hoy, o el nombre cambió "
                                    "(consulta de la ficha)")
        grupos = [g for g in grupos if normalizar(g["nombre"]) in pedidos]
    completos, total = [], 0
    for g in grupos:
        if (elegidos is None and por_ubicacion and g["publicaciones"]
                and not se_lee([g["nombre"]], g["publicaciones"][0])):
            if any(x["id"] not in vistas for x in g["publicaciones"]) or len(g["publicaciones"]) < g["total"]:
                anotar_fuera(r, g["nombre"])
            continue
        completos.append((g, sr_completar(empresa, filtros, g)))
        total += g["total"]
    ids = {x["id"] for _, pubs in completos for x in pubs}
    filtro = "; ".join(f"{k} = {v}" for k, v in filtros.items()) or "sin filtros"
    listado(r, f"{nombre}: GET {SR_CARRERAS}/{empresa}/api/groups y api/more, {filtro}", total, ids, vistas)
    for g, pubs in completos:
        for x in pubs:
            if x["id"] not in vistas:
                vistas.add(x["id"])
                lugares = lugares_de(g, x)
                if se_lee(lugares, x):
                    repartir(r, sr_vacante(pref, eid, x, lugares, modalidad, leidas.get(x["id"])), pref, de_remotas)
                else:
                    anotar_fuera(r, " | ".join(lugares))
    return f"{filtro}: {len(completos)} de {len(grupos)} grupos, {len(ids)} únicos de {total}"


def sr_en_la_region(lugares, pref):
    """Una publicación puede estar en la región por sus lugares del listado: alguno puede estarlo según 04, o nombran
    uno de sus países, y entonces su página dice la localidad."""
    return (any(clasificar_ubicacion(l, pref) != "fuera" for l in lugares)
            or bool(paises_nombrados(" | ".join(lugares), pref) & set(paises_region(pref))))


def sr_remotas(r, pref, eid, empresa, vistas):
    """Las remotas, con el filtro locationType=REMOTE del sitio, que trae las de todos los países: con el alcance
    "paises", lo decide el lugar de cada una. Devuelve cómo se revisaron."""
    def puede_estar(lugares):
        # El alcance, con los lugares juntos: si el sitio no dice cómo agrupa, uno puede no ser un lugar («Full-time»)
        return sr_en_la_region(lugares, pref) or alcance_remoto(" | ".join(lugares), pref) != "fuera"

    return "Filtro locationType=REMOTE del sitio, " + sr_recorrer(
        r, pref, eid, empresa, {"locationType": "REMOTE"}, "Remotas", vistas, puede_estar,
        de_remotas=pref["remoto"]["alcance"] == "cualquiera", modalidad="REMOTE")


def sr_requisiciones(r):
    """Señala las publicaciones entregadas que comparten requisición (job_id): son una sola vacante."""
    por_id = {}
    for v in r["vacantes"] + r["remotas_fuera_de_region"]:
        if v["job_id"]:
            por_id.setdefault(v["job_id"], []).append(v)
    for mismas in por_id.values():
        if len(mismas) > 1:
            urls = ", ".join(v["url_oficial"] for v in mismas)
            for v in mismas:
                v.setdefault("revisar", []).append(
                    f"requisición con {len(mismas)} publicaciones en esta búsqueda ({urls}): es una sola vacante, con "
                    "todas sus ubicaciones y la relación regional de todas (11/REG-IDENTIDAD)")


def smartrecruiters(eid, conf, pref, remotas):
    """Adaptador del sitio de carreras de SmartRecruiters (06/CAT-PLATAFORMAS)."""
    empresa = sr_empresa(conf["portal"])
    consulta = leer_consulta(conf, *SR_CONSULTA)
    filtros = {"locationType": "REMOTE", "search": "x"}
    comprobar_robots(SR_CARRERAS, [sr_url(empresa, "groups", filtros, page=0),
                                   sr_url(empresa, "more", filtros, type="location", value="x", page=0)])
    comprobar_robots(SR_PUBLICACIONES, [f"{SR_PUBLICACIONES}/{empresa}/0"])
    # El robots.txt de www.smartrecruiters.com prohíbe las páginas de algunas empresas: esas no se leen en ningún host
    comprobar_robots(SR_WWW, [f"{SR_WWW}/{empresa}/"])
    r = resultado(eid, "Sitio de carreras de SmartRecruiters (GET, HTML): listado agrupado, «Show more» de cada "
                       "grupo y página de cada publicación")
    vistas = set()
    # Las remotas van primero: el listado no dice la modalidad, y una remota de fuera de la región que ya trajo el
    # listado de la región no se volvería a ver
    revision = sin_remotas(pref, remotas) or sr_remotas(r, pref, eid, empresa, vistas)
    if consulta:
        busqueda = consulta.get("texto", "").strip()
        sr_recorrer(r, pref, eid, empresa, {"search": busqueda} if busqueda else {}, "Consulta de la ficha", vistas,
                    lambda lugares: sr_en_la_region(lugares, pref), elegidos=consulta.get("grupos") or None)
    elif pref["localidades"]:
        sr_recorrer(r, pref, eid, empresa, {}, "Grupos de la región", vistas,
                    lambda lugares: sr_en_la_region(lugares, pref))
    r["remotas_revision"] = revision
    sr_requisiciones(r)
    return r


# --- Oracle Recruiting Cloud ----------------------------------------------------
# Portal: https://<host>/hcmUI/CandidateExperience/<idioma>/sites/<sitio>. API REST del mismo host: GET para listar
# (finder findReqs, 25 por página) y GET para el detalle (finder ById).

OR_POR_PAGINA = 25
# Las facetas: su nombre en facetsList → (su lista en la respuesta, el parámetro que filtra por ella)
OR_FACETAS = {"LOCATIONS": ("locationsFacet", "selectedLocationsFacet"),
              "WORKPLACE_TYPES": ("workplaceTypesFacet", "selectedWorkplaceTypesFacet"),
              "CATEGORIES": ("categoriesFacet", "selectedCategoriesFacet"),
              "ORGANIZATIONS": ("organizationsFacet", "selectedOrganizationsFacet"),
              "TITLES": ("titlesFacet", "selectedTitlesFacet")}
OR_CONSULTA = ({"facetas": lambda x: listas_por_nombre(x) and set(x) <= set(OR_FACETAS), "texto": es_texto},
               '{"facetas": {"<faceta>": ["<nombre visible>"]}, "texto": "<búsqueda>"}')
OR_DESCRIPCION = ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr")


def or_api(portal):
    """(sitio, portal, base de la API, número de sitio) desde la URL del portal de la ficha."""
    u = urllib.parse.urlsplit(portal)
    m = re.fullmatch(r"(/hcmUI/CandidateExperience/[^/]+/sites/([^/]+))(?:/requisitions)?/?", u.path)
    if u.scheme != "https" or not u.hostname or not m:
        raise Fallo(f"el portal {portal} no es de Oracle Recruiting Cloud: debe ser "
                    "https://<host>/hcmUI/CandidateExperience/<idioma>/sites/<sitio> (06/CAT-PLATAFORMAS)")
    sitio = f"https://{u.hostname}"
    return sitio, sitio + m.group(1), f"{sitio}/hcmRestApi/resources/latest", m.group(2)


def or_finder(nombre, parametros):
    """El parámetro finder de la API, «finder=<nombre>;k=v,k=v», con cada valor codificado."""
    return f"finder={nombre};" + ",".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in parametros.items())


def or_url(api, numero, parametros, inicio):
    """URL de una página del listado, de la publicación más reciente a la más antigua."""
    return (f"{api}/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&"
            + or_finder("findReqs", {"siteNumber": numero, "facetsList": ";".join(OR_FACETAS), "limit": OR_POR_PAGINA,
                                     "offset": inicio, "sortBy": "POSTING_DATES_DESC", **parametros}))


def or_pagina(api, numero, parametros, inicio):
    """items[0] de una página del listado: total, requisiciones y facetas."""
    items = campo(pedir(or_url(api, numero, parametros, inicio)), "items")
    if not (isinstance(items, list) and items):
        raise Fallo("el listado no trajo items: la API pudo haber cambiado")
    return items[0]


def or_listar(api, numero, parametros, primera=None):
    """(requisiciones sin repetir, total) de todas las páginas. primera: la página offset=0, si ya se pidió."""
    return por_desplazamiento(lambda inicio: or_pagina(api, numero, parametros, inicio),
                              lambda it: campo(it, "TotalJobsCount"), lambda it: campo(it, "requisitionList"),
                              lambda x: str(campo(x, "Id")), primera)


def or_pais(api, numero, parametros, pref, c):
    """(nombre, página offset=0) del primer nombre de c en 04 que la API reconoce; (None, None) si ninguno. Con un
    nombre que no reconoce, location no filtra y trae todo el sitio. Lo reconoce si no hay ninguna requisición o si
    su faceta de ubicaciones trae ese nombre con el total del resultado: la del sitio completo también puede traer
    el país con otro conteo, y con otros acentos («Canadá» frente a «Canada»)."""
    for nombre in pref["paises"][c]:
        it = or_pagina(api, numero, {**parametros, "location": nombre}, 0)
        total = campo(it, "TotalJobsCount")
        if total == 0 or any(isinstance(f, dict) and normalizar(str(f.get("Name"))) == normalizar(nombre)
                             and f.get("TotalCount") == total for f in it.get("locationsFacet") or []):
            return nombre, it
    return None, None


def or_aviso_pais(r, c):
    r["revisar"].append(f"la API no reconoce como país ningún nombre de {c} en 04: agrega a paises de 04 el nombre que "
                        "usa la faceta de ubicaciones del portal, en su idioma")


def or_codigos(x):
    """Los códigos ISO de país de sus ubicaciones, la principal y las secundarias."""
    return ({x.get("PrimaryLocationCountry")} | {s.get("CountryCode") for s in x.get("secondaryLocations") or []
                                                 if isinstance(s, dict)}) - {None, ""}


def or_vacante(pref, eid, portal, api, numero, x):
    """Vacante desde el listado, que ya trae ubicaciones, modalidad y fecha; el detalle se lee aparte."""
    rid = str(x["Id"])
    lugares = [x.get("PrimaryLocation")] + [s.get("Name") for s in x.get("secondaryLocations") or []
                                            if isinstance(s, dict)]
    url_det = (f"{api}/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&"
               + or_finder("ById", {"Id": f'"{rid}"', "siteNumber": numero}))
    return vacante(pref, eid, rid, x.get("Title"), f"{portal}/job/{rid}", lugares, x.get("WorkplaceType") or None,
                   x.get("PostedDate"), None, None, url_det, x.get("JobFunction"), None, or_codigos(x))


def or_detalle(v, rid, pref):
    """Vigencia, fecha, modalidad, función y descripción desde el detalle, con comprobación de ID. La API no trae un
    indicador de postulación: la vacante está en el listado y vale mientras su fecha de cierre no haya pasado."""
    try:
        items = campo(pedir(v["url_fuente"]), "items")
        det = items[0] if isinstance(items, list) and items else None
        if str(campo(det, "Id")) != rid:
            raise Fallo(f"devolvió otro ID ({det['Id']})")
        fin = det.get("ExternalPostedEndDate")
        cierre = instante_iso(fin)
        vigente = fin is None or (cierre is not None and cierre > dt.datetime.now(dt.timezone.utc))
        v["estado_vigencia"] = "Confirmada abierta" if vigente else "Revisar"
        v["motivo"] = f"En listado oficial; ExternalPostedEndDate: {json.dumps(fin)}" + (
            "" if vigente else " (fecha de cierre pasada o ilegible: decidir con 07/BUS-VIGENCIA)")
        v["fecha_publicacion"] = fecha_iso(det.get("ExternalPostedStartDate"), pref) or v["fecha_publicacion"]
        v["modalidad_literal"] = det.get("WorkplaceType") or v["modalidad_literal"]
        v["departamento"] = det.get("JobFunction") or det.get("Category") or v["departamento"]
        v["descripcion"] = "\n\n".join(texto(det[k]) for k in OR_DESCRIPCION if det.get(k))
    except Fallo as e:
        sin_detalle(v, e)


def or_recorrer(r, pref, eid, portal, api, numero, parametros, nombre, vistas, de_remotas=False, primera=None):
    """Lista con esos parámetros del finder, reparte las requisiciones que no se habían visto y lee el detalle de las
    que se entregan. Devuelve la descripción del listado."""
    filas, total = or_listar(api, numero, parametros, primera)
    ids = {str(x["Id"]) for x in filas}
    filtro = "; ".join(f"{k} = {v}" for k, v in parametros.items())
    listado(r, f"{nombre}: GET {api}/recruitingCEJobRequisitions, {filtro}", total, ids, vistas)
    for x in filas:
        rid = str(x["Id"])
        if rid not in vistas:
            vistas.add(rid)
            v = or_vacante(pref, eid, portal, api, numero, x)
            if repartir(r, v, pref, de_remotas, or_codigos(x)):
                or_detalle(v, rid, pref)
    return f"{filtro}: {len(ids)} únicos de {total}"


def or_remotas(r, pref, eid, portal, api, numero, facetas, vistas):
    """Las remotas, con el valor remoto de la faceta de modalidad, un listado por país del remoto si el alcance es
    "paises". Una búsqueda por país también trae las requisiciones que lo tienen como ubicación secundaria: el alcance
    lo deciden los códigos de país de cada una. Devuelve cómo se revisaron."""
    alcance, codigos = pref["remoto"]["alcance"], pref["remoto"]["paises"]
    remotos = [str(f["Id"]) for f in facetas.get("workplaceTypesFacet") or [] if isinstance(f, dict)
               and f.get("Id") is not None and (es_remota(str(f.get("Name"))) or es_remota(str(f["Id"])))]
    if not remotos:
        aviso_sin_filtro_de_remoto(r)
        return "No disponible: la faceta de modalidad del sitio no ofrece un valor remoto"
    parametros = {"selectedWorkplaceTypesFacet": ";".join(remotos)}
    if alcance == "cualquiera":
        return "Faceta de modalidad del sitio, " + or_recorrer(r, pref, eid, portal, api, numero, parametros, "Remotas",
                                                               vistas, de_remotas=True)
    revisadas = []
    for c in codigos:
        nombre, primera = or_pais(api, numero, parametros, pref, c)
        if nombre:
            revisadas.append(or_recorrer(r, pref, eid, portal, api, numero, {"location": nombre, **parametros},
                                         "Remotas", vistas, primera=primera))
        else:
            or_aviso_pais(r, c)
    return "Faceta de modalidad del sitio, " + ("; ".join(revisadas) or f"sin listado: la API no reconoce "
                                                                        f"{', '.join(codigos)} como país")


def oraclerecruitingcloud(eid, conf, pref, remotas):
    """Adaptador de Oracle Recruiting Cloud (06/CAT-PLATAFORMAS)."""
    sitio, portal, api, numero = or_api(conf["portal"])
    consulta = leer_consulta(conf, *OR_CONSULTA)
    # Con todos los parámetros que se mandan, por si el robots.txt prohíbe alguno
    todos = {"location": "x", "keyword": "x", **{p: "x" for _, p in OR_FACETAS.values()}}
    comprobar_robots(sitio, [or_url(api, numero, todos, 0), f"{api}/recruitingCEJobRequisitionDetails?expand=all&"
                             f"onlyData=true&" + or_finder("ById", {"Id": '"0"', "siteNumber": numero})])
    facetas = or_pagina(api, numero, {}, 0)
    r = resultado(eid, "API REST de Oracle Recruiting Cloud (GET para listar y para el detalle)")
    vistas = set()
    if consulta:
        ofrecidos = {nombre: {normalizar(str(f.get("Name"))): str(f["Id"]) for f in facetas.get(clave) or []
                              if isinstance(f, dict) and f.get("Id") is not None}
                     for nombre, (clave, _) in OR_FACETAS.items()}
        aplicadas = resolver(consulta.get("facetas", {}), ofrecidos, r, "la faceta")
        if aplicadas is not None:
            parametros = {OR_FACETAS[k][1]: ";".join(v) for k, v in aplicadas.items()}
            if consulta.get("texto", "").strip():
                parametros["keyword"] = consulta["texto"].strip()
            or_recorrer(r, pref, eid, portal, api, numero, parametros, "Consulta de la ficha", vistas)
    elif pref["localidades"]:
        for c in paises_region(pref):
            nombre, primera = or_pais(api, numero, {}, pref, c)
            if nombre:
                or_recorrer(r, pref, eid, portal, api, numero, {"location": nombre}, "Países de la región", vistas,
                            primera=primera)
            else:
                or_aviso_pais(r, c)
    r["remotas_revision"] = sin_remotas(pref, remotas) or or_remotas(r, pref, eid, portal, api, numero, facetas, vistas)
    return r


# --- Bolsas de empleo ------------------------------------------------------------
# Una bolsa se busca por término de búsqueda (05/HAB-TERMINOS) y lugar (04/PREF-UBICACION), no por empresa. Su
# ficha en 06 (CAT-BOLSAS) solo dice su adaptador y su país.

def leer_terminos(ruta):
    """{ROL-ID: {"terminos": [...], "titulos": [...]}} del bloque de 05/HAB-TERMINOS. Si falta o está sin llenar,
    falla la bolsa y no la búsqueda: las empresas no lo usan."""
    llenar = "llénalo con `/configurar`, paso 5 (Habilidades y roles)"
    bloque = bloque_json(seccion(leer(ruta, "los términos de búsqueda", fallo=True), "HAB-TERMINOS"))
    if bloque is None:
        raise Fallo(f"{ruta}: falta el bloque de términos de búsqueda (```json) en la sección HAB-TERMINOS; {llenar}")
    try:
        familias = json.loads(bloque)
    except ValueError as e:
        raise Fallo(f"{ruta}: el bloque de HAB-TERMINOS no es JSON válido ({e})") from e
    if not isinstance(familias, dict) or not all(
            re.fullmatch(r"ROL-\d+", rol) and isinstance(f, dict) and lista_de_textos(f.get("terminos"))
            and lista_de_textos(f.get("titulos")) for rol, f in familias.items()):
        raise Fallo(f'{ruta}, HAB-TERMINOS: el bloque debe ser un objeto: ROL-ID → {{"terminos": [...], '
                    '"titulos": [...]}, con listas de textos')
    if not any(f["terminos"] for f in familias.values()):
        raise Fallo(f"{ruta}, HAB-TERMINOS: el bloque está sin llenar (no tiene ningún término de búsqueda); {llenar}")
    return familias


def leer_ficha_bolsa(bid, ficha):
    """Bloque de «### Configuración» de la ficha de una bolsa (06/CAT-BOLSAS): su adaptador y su país."""
    conf = configuracion(bid, ficha, "CAT-BOLSAS")
    if not isinstance(conf.get("adaptador"), str):
        raise Fallo("el bloque de «### Configuración» debe ser un objeto con adaptador y pais (06/CAT-BOLSAS)")
    if not (isinstance(conf.get("pais"), str) and re.fullmatch(r"[A-Z]{2}", conf["pais"])):
        raise Fallo(f"el pais de su ficha debe ser un código ISO de dos letras mayúsculas (06/CAT-BOLSAS); dice "
                    f"{conf.get('pais')!r}")
    return conf


def slug(texto_libre):
    """Un término o un lugar como lo escribe una URL: minúsculas, sin acentos y con guiones: «municipio-a2» de
    «Municipio Á2»."""
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto_libre)).strip("-")


def lugares_de_bolsa(pref, pais):
    """Los lugares de la región de 04 en el país de la bolsa, como slugs: cada nombre de un grupo con nombres, cada
    división de uno de división completa, y None (todo el país) por un grupo de país completo."""
    lugares = []
    for g in pref["localidades"]:
        if g["pais"] == pais:
            for n in g["nombres"] or g["divisiones"] or [None]:
                lugar = slug(n) if n else None
                if lugar not in lugares:
                    lugares.append(lugar)
    return lugares


def resultado_bolsa(bid, acceso, terminos):
    """resultado() de una bolsa: con bolsa_id en lugar de empresa_id y los términos usados; su rendimiento y la
    clasificación de los títulos los agrega contar_rendimiento()."""
    r = resultado(bid, acceso)
    del r["empresa_id"]
    return {"bolsa_id": bid, **r, "terminos": terminos}


def terminos_de_bolsa(familias):
    """{slug: término} de 05, cada término una vez: el primero que se escribió de cada slug, porque dos términos
    con el mismo slug son la misma búsqueda (05/HAB-TERMINOS, «Reglas»)."""
    terminos = {}
    for f in familias.values():
        for t in f["terminos"]:
            terminos.setdefault(slug(t), " ".join(t.split()))
    return terminos


# Palabras que no cuentan para que un título traiga las de un término: «analista de datos» pide «analista» y «datos»
VACIAS = frozenset("a al con de del e el en la las lo los o para por u un una y".split())


def clasificar_titulo(titulo, familias, terminos):
    """(clase, familias ROL, término) de una vacante de bolsa por su título (05/HAB-TERMINOS, «Filtro por título»):
    «encaja» si contiene una frase de titulos de alguna familia, con esas familias; «dudosa» si no, pero trae todas las
    palabras significativas de un término de búsqueda, en cualquier orden, con ese término; y «ruido» en otro caso."""
    s = normalizar(titulo)
    roles = [rol for rol, f in familias.items() if nombra(s, f["titulos"])]
    if roles:
        return "encaja", roles, None
    for t in terminos:
        palabras = [p for p in re.findall(r"[^\W_]+", normalizar(t)) if p not in VACIAS]
        if palabras and all(nombra(s, [p]) for p in palabras):
            return "dudosa", [], t
    return "ruido", [], None


def contar_rendimiento(r, ids_por_termino, clases, candidatas):
    """El rendimiento de cada término: las vacantes distintas que trajo, cuántas encajan, cuántas son dudosas y
    cuántas son candidatas (encajan o dudosas, y se entregan por su región o el alcance del remoto). Una vacante
    traída por varios términos cuenta en cada uno, con su única clase."""
    def por_clase(ids):
        cuenta = collections.Counter(clases[i] for i in ids)
        return {"encajan": cuenta["encaja"], "dudosas": cuenta["dudosa"], "ruido": cuenta["ruido"]}

    r["rendimiento"] = {}
    for t, ids in ids_por_termino.items():
        c = por_clase(ids)
        r["rendimiento"][t] = {"traidas": len(ids), "encajan": c["encajan"], "dudosas": c["dudosas"],
                               "candidatas": len(ids & candidatas)}
    r["clasificacion_titulos"] = por_clase(clases)


# --- OCC Mundial ------------------------------------------------------------------
# Listado: GET https://www.occ.com.mx/empleos/de-<término>/[en-<lugar>/][tipo-home-office-remoto/]?page=<n>&sort=2,
# en HTML. Detalle: GET https://www.occ.com.mx/empleo/oferta/<id>, con el JobPosting en JSON-LD, solo de las
# candidatas y hasta la primera señal anti-bot. Sin login ni cookies; con pausas entre peticiones (ADR 0010).

OCC_SITIO = "https://www.occ.com.mx"
OCC_REMOTO = "tipo-home-office-remoto"
OCC_PAGINAS = 100  # tope de páginas de un listado; si se alcanza, la paginación cambió
OCC_PAUSA = 2  # segundos entre peticiones a OCC, como en la investigación del sitio


def occ_url(termino, lugar, remoto, pagina=1):
    """URL de una página del listado, de la más nueva a la más vieja (sort=2). lugar None: todo el país."""
    ruta = f"/empleos/de-{termino}/" + (f"en-{lugar}/" if lugar else "") + (f"{OCC_REMOTO}/" if remoto else "")
    return f"{OCC_SITIO}{ruta}?" + (f"page={pagina}&" if pagina > 1 else "") + "sort=2"


def occ_tarjetas(h):
    """Las tarjetas de una página del listado: id (data-id), título, empresa, sueldo y ubicación literales, y la
    fecha relativa (cuando), como «Hace 2 días»."""
    tarjetas = []
    for t in re.split(r'<li class="vacancy-card', h)[1:]:
        jid = re.search(r"""data-id=['"](\d+)['"]""", t)
        titulo = re.search(r"vacancy-card__title[^>]*>(.*?)</h2>", t, re.S)
        if not (jid and titulo):
            raise Fallo("el listado de OCC cambió de forma (una tarjeta sin data-id o sin título)")

        def parrafo(clase):
            m = re.search(rf'{clase}"[^>]*>(.*?)</p>', t, re.S)
            return (texto(m.group(1)) or None) if m else None

        lugar = re.search(r'vacancy-card__location"[^>]*>(.*?)</p>', t, re.S)
        partes = [texto(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", lugar.group(1), re.S)] if lugar else []
        tarjetas.append({"id": jid.group(1), "titulo": texto(titulo.group(1)),
                         "empresa": parrafo("vacancy-card__company-text"), "sueldo": parrafo("vacancy-card__salary"),
                         "ubicacion": partes[0] if partes else None, "cuando": partes[-1] if len(partes) > 1 else None})
    return tarjetas


def occ_pedir(url, peticiones, tipo):
    """pedir() de una página de OCC, con una pausa antes, para no cargar el sitio: la primera petición a OCC siempre
    es su robots.txt. peticiones: la cuenta de las de cada tipo («listado» o «detalle») en esta ejecución."""
    time.sleep(OCC_PAUSA)
    peticiones[tipo] += 1
    return pedir(url, como_json=False, antibot=True)


def occ_si_es_reto(url, h):
    """Una página de OCC servida con 200 sin el marcador que se esperaba: si es un reto, la señal anti-bot."""
    senal = senal_antibot(h)
    if senal:
        raise SenalAntiBot(url, senal, 200)


def occ_listar(termino, lugar, remoto, peticiones):
    """(tarjetas sin repetir ni fijas, total publicado) de un listado. Las fijas son las tarjetas que se repiten al
    inicio de cada página y no cuentan en el total; con una sola página no se distinguen y no se descarta ninguna.
    Termina en la primera página sin tarjetas nuevas o, desde la segunda, al reunir el total: en la primera, las fijas
    pueden completarlo. Una primera página sin data-total-offers no es un listado vacío: es la señal anti-bot si es
    un reto servido con 200 y, si no, un fallo."""
    paginas, total = [], None
    for p in range(1, OCC_PAGINAS + 1):
        url = occ_url(termino, lugar, remoto, p)
        h = occ_pedir(url, peticiones, "listado")
        if total is None:
            m = re.search(r'data-total-offers="(\d+)"', h)
            if not m:
                occ_si_es_reto(url, h)
                raise Fallo(f"{url} no trae data-total-offers en su primera página: no es un listado vacío, puede "
                            "ser un cambio del sitio")
            total = int(m.group(1))
        tarjetas = occ_tarjetas(h)
        antes = len(occ_sin_fijas(paginas))
        paginas.append(tarjetas)
        unicas = occ_sin_fijas(paginas)
        if not tarjetas or len(unicas) == antes or (p > 1 and len(unicas) == total):
            return unicas, total
    raise Fallo("el listado de OCC no termina: la paginación del sitio pudo haber cambiado")


def occ_sin_fijas(paginas):
    """Las tarjetas de las páginas, sin repetir y sin las fijas: el prefijo de IDs que comparten todas las páginas
    con tarjetas, si son varias."""
    llenas = [[t["id"] for t in p] for p in paginas if p]
    fijas = 0
    if len(llenas) > 1:
        while all(len(p) > fijas and p[fijas] == llenas[0][fijas] for p in llenas):
            fijas += 1
    unicas = {}
    for p in paginas:
        for t in p[fijas:]:
            unicas.setdefault(t["id"], t)
    return list(unicas.values())


def occ_vacante(pref, bid, pais, t, remoto, url):
    """Vacante desde su tarjeta. La fecha de la tarjeta es relativa («Hace 2 días») y no llena fecha_publicacion; la
    modalidad es la del filtro con que se listó."""
    v = vacante(pref, None, t["id"], t["titulo"], f"{OCC_SITIO}/empleo/oferta/{t['id']}", [t["ubicacion"]],
                f"Remoto (filtro {OCC_REMOTO} de OCC)" if remoto else None, None, "Confirmada abierta",
                "En el listado oficial de la bolsa (07/BUS-VIGENCIA); detalle sin leer", url, None, None, {pais})
    del v["empresa_id"]
    return {"bolsa_id": bid, **v, "empresa_literal": t["empresa"], "sueldo_literal": t["sueldo"],
            "estado_detalle": "pendiente"}


def occ_dias(cuando):
    """Los días aproximados de una fecha relativa de tarjeta («Hoy», «Ayer», «Hace 5 horas», «Hace 2 semanas»,
    «Hace 1 mes»), solo para ordenar las candidatas; una que no se entiende va al final."""
    s = normalizar(cuando or "")
    if s in ("hoy", "recien publicada") or re.search(r"\b(minuto|hora)s?\b", s):
        return 0
    if s == "ayer":
        return 1
    m = re.search(r"(\d+)\s*(dia|semana|mes|meses|ano)s?\b", s)
    if not m:
        return float("inf")
    return int(m.group(1)) * {"dia": 1, "semana": 7, "mes": 30, "meses": 30, "ano": 365}[m.group(2)]


def occ_clave(d, k):
    """Una clave del JobPosting de OCC, que las escribe con mayúscula inicial, o la de schema.org en minúscula."""
    return d.get(k, d.get(k[0].lower() + k[1:])) if isinstance(d, dict) else None


def occ_jobposting(h):
    """El JobPosting del detalle, o None. Se lee con raw_decode desde la primera «{», porque el bloque del sitio
    termina en «};»."""
    for bloque in re.findall(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", h, re.S):
        if "JobPosting" in bloque and "{" in bloque:
            try:
                jp = json.JSONDecoder().raw_decode(bloque[bloque.index("{"):])[0]
            except ValueError:
                continue
            if isinstance(jp, dict) and occ_clave(jp, "@type") == "JobPosting":
                return jp
    return None


def occ_sueldo(base):
    """El sueldo del detalle como texto: «No publicado» si BaseSalary es 0/0; «20,000 - 25,000 <moneda> (<unidad>)»
    si trae mínimo y máximo; y, con otra forma, su JSON tal cual, para no perderlo."""
    if base in (None, "", {}):
        return None
    if isinstance(base, str):
        return "No publicado" if re.fullmatch(r"[\s0/.,$-]*", base) else base
    valor = occ_clave(base, "Value")
    montos = [occ_clave(valor, "MinValue"), occ_clave(valor, "MaxValue")] if isinstance(valor, dict) else [valor]
    if all(isinstance(x, (int, float)) for x in montos):
        if not any(montos):
            return "No publicado"
        unidad = occ_clave(valor, "UnitText") if isinstance(valor, dict) else None
        moneda = occ_clave(base, "Currency")
        return (" - ".join(f"{x:,.0f}" for x in dict.fromkeys(montos)) + (f" {moneda}" if moneda else "")
                + (f" ({unidad})" if unidad else ""))
    return json.dumps(base, ensure_ascii=False)


def occ_leer_detalle(v, h, url):
    """Aplica a la vacante su detalle: título, descripción, DatePosted en fecha_publicacion, empresa, ubicación
    estructurada, sueldo y tipo de empleo; la canonical es la url_oficial. ValidThrough es DatePosted + 60 días, un
    plazo fijo, y no se usa como vigencia: la vigencia sigue siendo la del listado (07/BUS-VIGENCIA). Una página sin
    JobPosting es la señal anti-bot si es un reto; si no, la vacante queda con su detalle pendiente y una nota
    «revisar». Un JobPosting de otro ID deja la vacante «No verificable». Devuelve si se leyó."""
    jp = occ_jobposting(h)
    if jp is None:
        occ_si_es_reto(url, h)
        v.setdefault("revisar", []).append(f"el detalle ({url}) no trae el JobPosting: ¿vacante cerrada o cambio "
                                           "del sitio? Confirmarlo en el anuncio")
        return False
    jid = occ_clave(occ_clave(jp, "identifier"), "Value")
    if jid is not None and str(jid) != v["job_id"]:
        v.update(estado_vigencia="No verificable", estado_detalle="no verificable",
                 motivo=f"Detalle de la bolsa: devolvió otro ID ({jid}) en {url}")
        return False
    lugar = occ_clave(occ_clave(jp, "JobLocation"), "Address")
    canonical = next((a["href"] for a in map(atributos, re.findall(r"<link[^>]*>", h))
                      if a.get("rel") == "canonical" and a.get("href")), None)
    publicada = occ_clave(jp, "DatePosted")
    v.update({
        "titulo": texto(occ_clave(jp, "Title")) or v["titulo"],
        "descripcion": texto(occ_clave(jp, "Description")) or None,
        "fecha_publicacion": publicada[:10] if isinstance(publicada, str)
        and re.match(r"\d{4}-\d{2}-\d{2}", publicada) else None,
        "empresa_literal": texto(occ_clave(occ_clave(jp, "HiringOrganization"), "Name")) or v["empresa_literal"],
        "ubicacion_detalle": {"localidad": occ_clave(lugar, "AddressLocality") or None,
                              "division": occ_clave(lugar, "AddressRegion") or None,
                              "pais": occ_clave(lugar, "AddressCountry") or None} if isinstance(lugar, dict) else None,
        "sueldo_detalle": occ_sueldo(occ_clave(jp, "BaseSalary")),
        "tipo_empleo": occ_clave(jp, "EmploymentType") or None,
        "url_oficial": canonical or v["url_oficial"],
        "motivo": "En el listado oficial de la bolsa (07/BUS-VIGENCIA); detalle leído",
        "estado_detalle": "leido"})
    return True


def occ_detalles(r, candidatas, peticiones):
    """Pide el detalle de las candidatas, en su orden, hasta la primera señal anti-bot, que se deja subir. Un 404 deja
    la vacante «No verificable» y sigue; también otro fallo de una sola vacante, que la deja pendiente."""
    d = r["detalle"]
    for v in candidatas:
        url = f"{OCC_SITIO}/empleo/oferta/{v['job_id']}"
        d["pedidos"] += 1
        try:
            h = occ_pedir(url, peticiones, "detalle")
        except SenalAntiBot:
            raise
        except Fallo as e:
            if e.codigo == 404:
                v.update(estado_vigencia="No verificable", estado_detalle="no verificable",
                         motivo=f"Detalle de la bolsa: error 404 en {url}, aunque el listado la traía")
            else:
                v.setdefault("revisar", []).append(f"no se pudo leer el detalle ({e}); queda pendiente")
            continue
        d["leidos"] += occ_leer_detalle(v, h, url)


def occ_bloqueo(r, e, en, peticiones):
    """Anota en la bolsa la señal anti-bot que la detuvo: en qué petición y de qué tipo, y el [FALLO], que dice si
    fue en el listado o en el detalle y cuántos detalles se leyeron. En Code en la nube, la bolsa se busca en Code
    local, como con IpBloqueada (07/BUS-CANALES)."""
    d = r["detalle"]
    d["bloqueo"] = {"en": en, "peticion": peticiones[en], "tipo": e.tipo, "url": e.url}
    r["error"] = (f"{e.host} respondió con una señal anti-bot ({e.tipo}) en el {en}, petición {peticiones[en]} "
                  f"({e.url}); se leyeron {d['leidos']} de {d['candidatas']} detalles; no se reintenta ni se le pide "
                  "nada más en esta ejecución (07/BUS-BOLSAS, ADR 0010)")
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        r["error"] += "; en Code en la nube la bolsa recibe más bloqueos: busca esta bolsa en Code local"


def occ(bid, conf, pref, familias, remotas):
    """Adaptador de OCC Mundial (06/CAT-BOLSAS): un listado por cada término de búsqueda de 05 y cada lugar de la
    región de 04 en el país de la bolsa, más todo el país con el filtro remoto si el alcance del remoto lo incluye."""
    pais = conf["pais"]
    terminos = terminos_de_bolsa(familias)
    lugares = lugares_de_bolsa(pref, pais)
    alcance = pref["remoto"]["alcance"]
    sin_remoto = sin_remotas(pref, remotas) or (
        None if alcance == "cualquiera" or pais in pref["remoto"]["paises"]
        else f"No aplica: el alcance del remoto de 04 no incluye {pais}")
    if not lugares and sin_remoto:
        raise Fallo(f"ni la región ni el alcance del remoto de 04 incluyen {pais}, el país de la bolsa: no hay nada "
                    "que buscar en ella")
    r = resultado_bolsa(bid, "Listado de OCC Mundial (GET, HTML), por término de búsqueda y lugar, y detalle de las "
                             "candidatas hasta la primera señal anti-bot", list(terminos.values()))
    r["detalle"] = {"candidatas": 0, "pedidos": 0, "leidos": 0, "bloqueo": None}
    peticiones = collections.Counter()
    # clases: la clase de cada vacante ya vista, por su ID; sus claves son las vistas de listado()
    clases, candidatas = {}, set()
    ids_por_termino = {t: set() for t in terminos.values()}
    revisadas = []
    # Los listados remotos, de todos los términos, van primero: el listado sin filtro no dice la modalidad, y una
    # vacante ya vista no se vuelve a ver
    consultas = ([] if sin_remoto else [(termino, None, True) for termino in terminos]) + [
        (termino, lugar, False) for termino in terminos for lugar in lugares]
    try:
        # Una URL de muestra por cada forma del listado, con lugar y con el filtro remoto, y con toda su consulta, y
        # una del detalle. El robots.txt es la primera petición del listado
        peticiones["listado"] += 1
        comprobar_robots(OCC_SITIO, [occ_url("x", "x", False, 2), occ_url("x", None, True, 2),
                                     f"{OCC_SITIO}/empleo/oferta/1"], antibot=True)
        occ_listados(r, pref, bid, pais, familias, terminos, consultas, clases, candidatas, ids_por_termino,
                     revisadas, peticiones)
    except SenalAntiBot as e:
        # Lo listado se entrega; las consultas que faltaron dejan la cobertura incompleta
        r["completa"] = False
        r["detalle"]["candidatas"] = len(candidatas)
        occ_bloqueo(r, e, "listado", peticiones)
    contar_rendimiento(r, ids_por_termino, clases, candidatas)
    r["remotas_revision"] = sin_remoto or f"Filtro {OCC_REMOTO} en todo {pais}, " + "; ".join(revisadas)
    if r["detalle"]["bloqueo"] is None:
        # Primero las que encajan y después las dudosas; en cada grupo, de la más nueva a la más vieja (el orden
        # del listado desempata)
        orden = sorted((v for v in r["vacantes"] + r["remotas_fuera_de_region"] if v["job_id"] in candidatas),
                       key=lambda v: (v["clasificacion_titulo"] != "encaja", occ_dias(v["_cuando"])))
        r["detalle"]["candidatas"] = len(orden)
        try:
            occ_detalles(r, orden, peticiones)
        except SenalAntiBot as e:
            occ_bloqueo(r, e, "detalle", peticiones)
    for v in r["vacantes"] + r["remotas_fuera_de_region"]:
        v.pop("_cuando", None)
    return r


def occ_listados(r, pref, bid, pais, familias, terminos, consultas, clases, candidatas, ids_por_termino, revisadas,
                 peticiones):
    """Recorre los listados de la bolsa: suma cada uno al resultado y clasifica sus vacantes por título. Llena
    clases, candidatas, ids_por_termino y revisadas, que quedan con lo listado si una señal anti-bot lo corta."""
    for termino, lugar, remoto in consultas:
        tarjetas, total = occ_listar(termino, lugar, remoto, peticiones)
        url = occ_url(termino, lugar, remoto)
        ids = {t["id"] for t in tarjetas}
        ids_por_termino[terminos[termino]] |= ids
        donde = f"todo {pais}, remoto" if remoto else f"en {lugar}" if lugar else f"todo {pais}"
        listado(r, f"«{termino}», {donde}: GET {url}", total, ids, clases.keys())
        if remoto:
            revisadas.append(f"«{termino}»: {len(ids)} únicos de {total}")
        for t in tarjetas:
            if t["id"] in clases:
                continue
            clase, roles, en_titulo = clasificar_titulo(t["titulo"], familias, terminos.values())
            clases[t["id"]] = clase
            # El ruido solo se cuenta: no se entrega ni deja su ubicación en fuera_de_region
            if clase == "ruido":
                continue
            v = {**occ_vacante(pref, bid, pais, t, remoto, url), "clasificacion_titulo": clase, "familias_rol": roles,
                 "_cuando": t["cuando"]}
            if en_titulo:
                v["termino_en_titulo"] = en_titulo
            if repartir(r, v, pref, de_remotas=remoto):
                candidatas.add(t["id"])


# --- Principal --------------------------------------------------------------

# Un adaptador por plataforma de reclutamiento (06/CAT-PLATAFORMAS). Uno nuevo es una función
# (eid, conf, pref, remotas) que devuelve resultado(), llenado con listado(), repartir() y anotar_fuera(), y que
# antes de pedir nada pasa por comprobar_robots(); se registra aquí con el nombre que lleva la ficha en «plataforma».
ADAPTADORES = {"workday": workday, "eightfold": eightfold, "workable": workable, "smartrecruiters": smartrecruiters,
               "oraclerecruitingcloud": oraclerecruitingcloud}
# Un adaptador por bolsa de empleo (06/CAT-BOLSAS): una función (bid, conf, pref, familias, remotas), con las familias
# de 05/HAB-TERMINOS, que devuelve resultado_bolsa(); se registra con el nombre que lleva la ficha en «adaptador».
BOLSAS = {"occ": occ}


def imprimir_revisar(vacantes):
    """Las líneas «revisar» de las vacantes de una empresa, agrupadas para que se lean en un portal grande: una
    «revisar ubicación» por ubicación literal por revisar, con los IDs que la comparten; las de vigencia, una por
    vacante, y cada nota una vez por ID, porque las publicaciones de una requisición repiten la suya
    (sr_requisiciones). Una vacante sin ubicación publicada sale como tal; una remota en el alcance ya no lleva
    ubicaciones por revisar (repartir). El JSON de cada vacante no cambia."""
    por_ubicacion = {}
    for v in vacantes:
        if v["ubicaciones_por_revisar"] or not v["ubicacion_literal"]:
            for u in v["ubicaciones_por_revisar"] or [v["ubicacion_literal"] or "sin ubicación publicada"]:
                ids = por_ubicacion.setdefault(u, [])
                if nombre_en_revisar(v) not in ids:
                    ids.append(nombre_en_revisar(v))
    for u, ids in por_ubicacion.items():
        cuantas = "1 vacante" if len(ids) == 1 else f"{len(ids)} vacantes"
        print(f"    revisar ubicación: {u} ({cuantas}: {', '.join(ids)})", file=sys.stderr)
    dichas = set()
    for v in vacantes:
        nombre = nombre_en_revisar(v)
        if v.get("clasificacion_titulo") == "dudosa":
            print(f"    revisar título: {nombre} «{v['titulo']}»: trae las palabras de «{v['termino_en_titulo']}», "
                  "pero ninguna frase de titulos de 05/HAB-TERMINOS", file=sys.stderr)
        if v["estado_vigencia"] != "Confirmada abierta" or "detalle no consultado" in (v["motivo"] or ""):
            print(f"    revisar vigencia: {nombre} {v['motivo']}", file=sys.stderr)
        for nota in v.get("revisar", []):
            if (nombre, nota) not in dichas:
                dichas.add((nombre, nota))
                print(f"    revisar: {nombre} {nota}", file=sys.stderr)


def nombre_en_revisar(v):
    """Cómo se nombra una vacante en sus líneas «revisar»: sin Job ID publicado (11/REG-IDENTIDAD), por su URL."""
    return v["job_id"] if v["job_id"] not in (None, "No publicado") else v["url_oficial"] or v["url_fuente"]


def informar(fid, r):
    """La línea de una empresa o una bolsa en stderr, con su cobertura y sus líneas «revisar». Una bolsa detenida por
    una señal anti-bot sale como [FALLO] y, debajo, lo que se entrega."""
    if "error" in r:
        print(f"[FALLO] {fid}: {r['error']}", file=sys.stderr)
        if "vacantes" not in r:
            return
    en_region = sum(v["region_relacionada"] in ("Dentro", "Incluye") for v in r["vacantes"])
    # completa = None: la fuente no publica total (07/BUS-COBERTURA); se declara con su verificación
    estado = "OK" if r["completa"] else "SIN TOTAL" if r["completa"] is None else "INCOMPLETA"
    cuenta = (f"{r['unicos']}/{r['total_reportado']}" if r["total_reportado"] is not None
              else f"{r['unicos']} (sin total publicado)")
    titulos = ""
    if "clasificacion_titulos" in r:
        c = r["clasificacion_titulos"]
        titulos = (f"; títulos: {c['encajan']} encaja{'' if c['encajan'] == 1 else 'n'}, {c['dudosas']} "
                   f"dudosa{'' if c['dudosas'] == 1 else 's'}, {c['ruido']} ruido")
    detalle = ""
    if r.get("detalle"):
        d = r["detalle"]
        detalle = f"; detalle: {d['leidos']} leídos de {d['candidatas']} candidatas"
    inicio = f"    entregado, {estado.lower()}:" if "error" in r else f"[{estado}] {fid}:"
    print(f"{inicio} {cuenta} únicos; {en_region} en la región; remotas fuera de la región: "
          f"{len(r['remotas_fuera_de_region'])} ({r['remotas_revision']}){titulos}{detalle}", file=sys.stderr)
    if r.get("verificacion_cobertura"):
        print(f"    cobertura: {r['verificacion_cobertura']}", file=sys.stderr)
    for nota in r["revisar"]:
        print(f"    revisar: {nota}", file=sys.stderr)
    imprimir_revisar(r["vacantes"] + r["remotas_fuera_de_region"])


def buscar_empresa(eid, ficha, pref, remotas):
    """El resultado de una empresa, con el adaptador de su plataforma."""
    conf = leer_ficha(eid, ficha)
    adaptador = ADAPTADORES.get(conf["plataforma"].strip().lower())
    if adaptador is None:
        raise Fallo(f"la plataforma {conf['plataforma']!r} no tiene adaptador en el script (hay: "
                    f"{', '.join(ADAPTADORES)}); para agregar uno, 06/CAT-REGLAS")
    return adaptador(eid, conf, pref, remotas)


def buscar_bolsa(bid, ficha, pref, remotas):
    """El resultado de una bolsa, con su adaptador y los términos de 05."""
    conf = leer_ficha_bolsa(bid, ficha)
    adaptador = BOLSAS.get(conf["adaptador"].strip().lower())
    if adaptador is None:
        raise Fallo(f"el adaptador {conf['adaptador']!r} no existe en el script (hay: {', '.join(BOLSAS)}; "
                    "06/CAT-BOLSAS)")
    return adaptador(bid, conf, pref, leer_terminos(MODULO_05), remotas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=f"Plataformas con adaptador: {', '.join(ADAPTADORES)}. Bolsas de empleo con "
                                        f"adaptador: {', '.join(BOLSAS)}.")
    ap.add_argument("ids", nargs="*", metavar="ID", help="IDs EMP- y BOL- de 06 (por defecto, los dos catálogos)")
    ap.add_argument("--salida", help="archivo JSON de salida (por defecto, stdout)")
    ap.add_argument("--sin-remotas", action="store_true", help="omitir el listado de vacantes remotas")
    ap.add_argument("--copia", metavar="CARPETA",
                    help="leer el 04, el 05 y el 06 de otra copia (por defecto, la del script)")
    a = ap.parse_args()
    if a.copia is not None:
        if not os.path.isdir(a.copia):
            ap.error(f"--copia: {a.copia!r} no existe o no es una carpeta")
        usar_copia(a.copia)
    pref = leer_preferencias(MODULO_04)
    pref["reconocidos"] = paises_reconocidos(leer_tabla_de_paises(TABLA_DE_PAISES), pref["paises"])
    empresas, bolsas = leer_catalogos(MODULO_06)
    pedidas = [i.upper() for i in a.ids] or [*empresas, *bolsas]
    desconocidas = [i for i in pedidas if i not in empresas and i not in bolsas]
    if desconocidas:
        ap.error(f"{', '.join(desconocidas)} no está en los catálogos de 06; opciones: "
                 f"{', '.join([*empresas, *bolsas])}")
    if a.sin_remotas and not pref["localidades"]:
        ap.error("04 solo acepta remoto (localidades vacía): con --sin-remotas no habría nada que buscar")
    ahora = dt.datetime.now(pref["tz"])
    res = {"script": f"herramientas/buscar.py v{VERSION}", "fecha_hora": ahora.strftime("%Y-%m-%d %H:%M"),
           "zona_horaria": pref["zona_horaria"], "empresas": [], "bolsas": []}
    fallos = 0
    # Las empresas primero y después las bolsas, cada una en su lista de la salida
    for fid in sorted(pedidas, key=lambda i: i in bolsas):
        es_bolsa = fid in bolsas
        try:
            r = (buscar_bolsa(fid, bolsas[fid], pref, not a.sin_remotas) if es_bolsa
                 else buscar_empresa(fid, empresas[fid], pref, not a.sin_remotas))
        except Fallo as e:
            r = {"bolsa_id" if es_bolsa else "empresa_id": fid, "error": str(e)}
        # Una bolsa detenida por una señal anti-bot entrega su resultado con el error
        fallos += "error" in r
        res["bolsas" if es_bolsa else "empresas"].append(r)
        informar(fid, r)
    salida = json.dumps(res, ensure_ascii=False, indent=1)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8") as f:
            f.write(salida + "\n")
    else:
        print(salida)
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
