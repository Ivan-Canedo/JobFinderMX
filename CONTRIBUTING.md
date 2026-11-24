# Contribuir a JobFinderMX

Guía para quien mantiene la plantilla o le propone cambios. El titular de una copia no la necesita: sus instrucciones están en `AGENTS.md`.

## Plantilla o copia

Un clon de la plantilla se ve igual para el mantenedor que para un titular que la clonó en lugar de crear su copia. Los distingue una marca que vive solo en la configuración local de git (`.git/config`), que no se publica ni viaja en un clon. Ponla en cada clon donde trabajes la plantilla:

```sh
git config --local plantilla.mantenedor true
```

Con la marca, el agente trabaja como mantenedor (`AGENTS.md`, «Al iniciar»); sin ella, como en la copia de un titular.

## Reglas para el agente del mantenedor

Valen las reglas de `AGENTS.md`, con estos cambios:

- **Los módulos son plantilla:** estructura, instrucciones breves y marcadores «pendiente», sin datos de ninguna persona ni nombres de empresas, ni siquiera de ejemplo. Sus filas de ESTADO siguen en «Sin llenar».
- **Remoto público a propósito:** la revisión de «Copia privada» de `AGENTS.md` no aplica a la plantilla.
- **Sin registros ni búsquedas reales:** la plantilla no tiene archivo de registros, instantánea ni proyecto web. Los scripts se prueban con datos ficticios, en un clon de prueba (ver «Probar como titular»). La excepción son los titulares de prueba, cuyas copias viven fuera de git en `.scratch/` y sí buscan en portales reales (ver «Titulares de prueba»).
- **Versión de la plantilla:** vive en la tabla ESTADO de 01, junto a la URL de la plantilla; es la que anota cada copia nueva y de la que parte `/actualizar` (ADR 0004). Ver «Versión de la plantilla».

## Agent skills

El mantenedor trabaja con las skills de ingeniería de `mattpocock-skills`: planifica con `grill-with-docs`, resume el plan en un spec con `to-spec`, lo divide con `to-tickets` e implementa un ticket por conversación con `implement`.

### Issue tracker

Los tickets son archivos Markdown en `.scratch/`, fuera de git porque el repo es público. Ver `docs/agents/issue-tracker.md`.

### Triage labels

Los cinco roles canónicos con sus nombres por defecto. Ver `docs/agents/triage-labels.md`.

### Domain docs

Un solo contexto: `CONTEXT.md` (glosario) y `docs/adr/` (decisiones) en la raíz. Ver `docs/agents/domain.md`.

## Privacidad

La plantilla es pública: ningún archivo puede llevar datos de una persona real. Antes de cada commit:

1. **Auditoría de términos:** la lista de términos que identifican al mantenedor vive en `.scratch/convertir-en-plantilla/terminos.txt`, fuera de git. Toda la carpeta debe dar cero coincidencias (agrega `--excluir .venv` si existe):

   ```sh
   python3 -I herramientas/auditar_terminos.py .scratch/convertir-en-plantilla/terminos.txt . --excluir .scratch
   ```

   El formato de la lista, las excepciones (`!frase`), cómo busca y sus códigos de salida están en el docstring del script. Quien contribuya sin esa lista puede auditar con una propia.
2. **Binarios:** la auditoría no los lee; los avisa en stderr. Revisa aparte sus metadatos (autor, rutas de la máquina) antes de publicarlos.
3. **Formato:** `markdownlint-cli2` sin argumentos revisa todo el repo según `.markdownlint-cli2.jsonc` y debe dar cero advertencias.
4. **Correo:** los commits usan el correo noreply de GitHub, configurado en `user.email` local. Revísalo antes de un push con `git log --format='%an <%ae> | %cn <%ce>'`.

## Pruebas

Las pruebas automáticas usan `unittest`, sin red, y llaman a cada script por su línea de comandos con entradas ficticias. La excepción es la búsqueda en un portal: la prueba importa `buscar.py` desde una copia ficticia, cambia `pedir()`, su única función de red, por un portal falso y corre `main()`. Para probar lo que detecta el propio `pedir()`, como un host bloqueado por el proxy o el 429 de Workable en la nube, cambia en su lugar `urllib.request.urlopen` por una red falsa. Una bolsa de empleo se prueba siempre así, con `OccFalso`, porque sus señales anti-bot las distingue `pedir()`. Otra es `TablaDePaises`, que lee `herramientas/paises.json` y solo revisa su formato: las demás pruebas usan una tabla ficticia que `CopiaFicticia` escribe junto al script copiado. La otra es `test_punteros_skills.py`, que no llama a ningún script: lee las skills del repo y comprueba que cada una de `.claude/skills/` tenga en `.agents/skills/` su puntero, con el mismo `name` y la misma `description`. Y `test_preparar_nube.py` lee el comando del hook de `.claude/settings.json` y lo corre con `bash` en una copia ficticia: sin `CLAUDE_CODE_REMOTE` debe salir con 0, sin imprimir ni crear nada; con la variable, cambia `npm`, `markdownlint-cli2`, `python3` e `id` por comandos falsos al inicio del `PATH`, porque la instalación real necesita root y red, y comprueba que `apt-get` y `dpkg` no se llamen. Con `-B` no quedan cachés:

```sh
python3 -I -B -m unittest discover -s herramientas/pruebas
```

Las que generan un CV se saltan si faltan fpdf2, python-docx, pypdf o pypdfium2; las de la herramienta de registros, si falta `openpyxl`, y la que revisa el formato de la instantánea, si falta `markdownlint-cli2`. Para correrlas, usa el Python de un entorno virtual con esas bibliotecas, el mismo que crea `/configurar` en el paso 6 (CV base) o el 8 (Registros):

```sh
python3 -m venv .venv && .venv/bin/python -m pip install openpyxl fpdf2 python-docx pypdf pypdfium2
.venv/bin/python -I -B -m unittest discover -s herramientas/pruebas
```

### Probar como titular

Para ver la plantilla como la ve un titular nuevo, trabaja en un clon de prueba temporal, que nace sin la marca:

```sh
git clone . "$(mktemp -d)/clon"
```

El clon de prueba solo lleva lo que ya tiene commit. Para probar cambios sin commit, duplica la carpeta y quítale la marca al duplicado con `git -C <clon> config --local --unset plantilla.mantenedor`.

Al abrir el clon de prueba en VS Code con Claude Code, el agente debe ofrecer `/configurar`. Marca como sintéticos los datos de prueba y bórralos al terminar, incluidos el archivo de registros, la instantánea y cualquier proyecto web o repositorio de prueba.

### Titulares de prueba

Para probar herramientas nuevas contra portales reales con perfiles que no cambian de una prueba a otra, el mantenedor tiene titulares de prueba: titulares inventados, con datos sintéticos marcados como tales (nombre «Titular» más su perfil, como «Titular Datos», correo `@example.com`). Cada uno se nombra por su perfil, como «el titular de datos», y cubre casos distintos de región, remoto y plataforma. Su perfil está en su `FICHA.md`, el CV ficticio y las respuestas a cada paso de `/configurar` con que se generó, no aquí, porque la plantilla es pública.

- **Dónde viven:** cada copia de prueba está en `.scratch/titulares-de-prueba/<perfil>/`, fuera de git: los módulos 00–11 llenos, el archivo de registros y su instantánea en la raíz, como en una copia real, más `FICHA.md` y `VERSION.md`, con la versión de la plantilla de la que salió y las correcciones a mano. Su 06 lleva una sola empresa real. `ls .scratch/titulares-de-prueba` da los perfiles que hay.
- **Cómo se usan:** los scripts leen una copia con `--copia`, sin copiar código a ella. Cuando el mantenedor pide «prueba X para el titular de marketing», el agente corre la herramienta de la plantilla con `--copia .scratch/titulares-de-prueba/marketing`. Si no nombra un perfil, el agente pregunta cuál, o si son todos. Por ejemplo:

  ```sh
  python3 -I herramientas/buscar.py --copia .scratch/titulares-de-prueba/<perfil> --salida "$(mktemp -d)/salida.json"
  .venv/bin/python -I herramientas/registros.py --copia .scratch/titulares-de-prueba/<perfil> leer busquedas
  ```

  La salida JSON va al directorio temporal, como en cualquier copia (`AGENTS.md`).
- **Cómo se genera uno:** se escribe su `FICHA.md` y se corre `/configurar` completo en un clon de prueba (ver «Probar como titular»), contestando con ella; luego se copian a `.scratch/titulares-de-prueba/<perfil>/` los módulos, el archivo de registros, la instantánea y los CV de `muestras_cv/`, se anota en `VERSION.md` la versión de la plantilla del clon y se borra el clon.
- **Cambiar un perfil:** se edita primero su `FICHA.md` y el cambio se aplica a los módulos como en la copia de un titular real (un `U##` o `PREF-U##` nuevo, con el antecedente en 02 §12), anotándolo en `VERSION.md`. Así también se prueba actualizar una copia llena.
- **Mantenimiento:** `/actualizar` no sirve, porque la carpeta no tiene git. Si un script rechaza un módulo tras un cambio de la plantilla, se corrige a mano ese módulo y se anota en `VERSION.md`. Si los cambios se acumulan, se regenera completo desde `FICHA.md`.
- **Solo local:** `.scratch/` no viaja a la nube; para probar ahí, ver «Probar en la nube».

### Probar en la nube

Code en la nube (ADR 0007) no se prueba sobre la plantilla: una sesión trabaja sobre un clon de un repositorio de GitHub, sin `.scratch/` ni la marca de mantenedor, y necesita una copia configurada. Para probarlo:

1. **Repositorio privado de prueba:** créalo en tu cuenta de GitHub y sube a su `main` un clon de prueba (ver «Probar como titular») configurado con datos sintéticos, marcados como tales. Ese repositorio sí puede llevar empresas reales en 06, una por adaptador, porque no es la plantilla. Ni su 06 ni lo que se pruebe solo en la nube (un script de comprobación, sus resultados) entra en la plantilla.
2. **Entorno de la nube:** créalo con `/conectar-nube`, corrida en el clon de prueba en Code local, que también comprueba el repositorio y arma la lista de dominios desde su 06. Para probar el `[FALLO]` de host bloqueado, deja fuera de la lista el host de una de esas empresas.
3. **Sesión:** abre una en claude.ai/code sobre el repositorio de prueba. Revisa lo que las pruebas automáticas no ven: que el hook prepare la sesión sin preguntar por `.venv`, los `[FALLO]` de host bloqueado y de Workable con la red real, el push a `main` al cerrar y, si cambió `/actualizar`, el `git fetch` de una etiqueta de la plantilla.
4. **Para un cambio nuevo de la plantilla,** lleva al `main` del repositorio de prueba el diff entre la versión de la que salió y la nueva, y abre una sesión nueva.
5. **Al terminar,** borra el repositorio de prueba, su entorno de la nube en claude.ai/code y el clon de prueba.

## Versión de la plantilla

Cada versión publicada es una etiqueta `vX.Y` sobre su commit. `/actualizar` fusiona cada archivo de la copia en tres vías, con la etiqueta que anota su 01 como base, así que una etiqueta publicada no se mueve ni se borra. Para publicar una versión:

1. Sube la versión en la línea **Versión de la plantilla** de 01. Los módulos de la plantilla no cambian de versión por esto: la copia lleva la suya.
2. Agrega a `CAMBIOS.md` la sección `## vX.Y — fecha`, arriba de las anteriores, con dos subsecciones:
   - `### Qué cambió`: en pocas líneas, para el titular.
   - `### En la copia`: una lista numerada de lo que la fusión no ve, como columnas nuevas en los registros o datos que hay que preguntarle al titular. Cada acción va marcada **automática** o **con el titular** y, si toca un módulo que en la copia puede estar «Configurado», dice qué paso retomar en su fila de ESTADO. Si no hay acciones, «Sin acciones».
3. Commit, etiqueta y push de los dos:

   ```sh
   git tag vX.Y
   git push origin main vX.Y
   ```

4. **Release:** el push de la etiqueta activa `.github/workflows/release.yml`, que arma `JobFinderMX.zip` con el repositorio completo en una carpeta `JobFinderMX/` y crea el Release de la etiqueta, con las notas de su sección de `CAMBIOS.md` y el ZIP adjunto. Usa solo el token del repositorio y no corre en las copias. Cuando termine, descarga el enlace fijo, <https://github.com/Ivan-Canedo/JobFinderMX/releases/latest/download/JobFinderMX.zip>, y comprueba que sea la versión nueva: el ZIP trae la carpeta `JobFinderMX/`, el 01 de esa carpeta dice la versión que publicaste y, abierta con el agente, la copia ofrece `/configurar`.

`v1.0` es el commit que trae `/actualizar` y `CAMBIOS.md`.

### Probar el ZIP sin publicar

El mismo ZIP del Release se arma en local con `git archive`, que toma lo que tiene commit en la referencia dada (`HEAD` o una etiqueta) y deja fuera `.git` y lo que no tiene commit, como `.scratch/`:

```sh
git archive --format=zip --prefix=JobFinderMX/ -o "$(mktemp -d)/JobFinderMX.zip" HEAD
```

Una copia salida del ZIP le sirve a `/actualizar` cuando la convierte en repositorio el paso 2 de `/configurar` (`git init` y un primer commit con todo): sus archivos son idénticos a los de la etiqueta que anota su 01, que es la base de la fusión.
