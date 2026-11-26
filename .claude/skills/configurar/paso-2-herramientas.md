# Paso 2: Herramientas básicas

Este paso deja listo todo lo que se instala, antes de cualquier pregunta sobre el titular, así que los pasos siguientes no instalan nada: Python; git, opcional pero recomendado, que guarda las versiones de la copia; el entorno virtual con las bibliotecas de Python del CV y del archivo de registros, y la prueba del esqueleto del CV.

Corre en la conversación técnica (índice, «Cómo avanzar»). En cualquier otra conversación, solo repara lo que falló (AGENTS.md, «Diagnóstico al fallar»): haz la parte de este paso que toca y su comprobación, sin el aviso, la oferta de git ni la pregunta de «Guardar versiones».

**Code en la nube:** si `CLAUDE_CODE_REMOTE` vale `true`, la sesión corre en la nube y el hook de la copia (`herramientas/preparar_nube.sh`) ya instaló al abrirla markdownlint-cli2 y creó `.venv` con las bibliotecas de Python; Python y Node vienen con la máquina de la nube. Salta los puntos 1, 2 y 4, la oferta de git y «Guardar versiones», porque la copia en la nube siempre es un repositorio y su configuración local no dura más que la sesión: corre solo las comprobaciones de Python y del entorno virtual (la de Linux), sin mostrar los comandos de instalación, y la prueba del CV. Si una comprobación falla, no le pidas al titular comandos de instalación: dile que el hook de la nube falló y qué aviso dio al abrir la sesión (empieza con «Hook de la nube de JobFinderMX»). Si no ves el aviso, repítelo con `CLAUDE_CODE_REMOTE=true bash herramientas/preparar_nube.sh`, que solo instala lo que falta.

1. **Sistema:** detecta el sistema operativo con `uname -s`: `Linux`; `Darwin` es macOS; `MINGW…`, `MSYS…` o un `uname` inexistente (PowerShell) es Windows. En Linux, lee `ID` e `ID_LIKE` en `/etc/os-release`: `dnf` sirve a Fedora y derivados; `apt`, a Debian, Ubuntu y derivados. En macOS el gestor es Homebrew (`brew`) y en Windows, `winget`.
2. **Aviso:** solo en macOS, dile al titular que JobFinderMX solo se ha probado en Linux y Windows, así que un fallo puede venir de ahí.
3. **Revisión:** corre la comprobación de cada herramienta que toca revisar: Python, git si el titular lo acepta (ver «git») y, solo si el titular los pidió, los opcionales. La que ya cumple no se toca. En Windows, la comprobación de Python y de git es «Búsqueda en Windows».
4. **Instalación:** muéstrale al titular el comando de cada herramienta que falta y pide su permiso antes de instalar. Un comando con `sudo` pide contraseña: pídele que lo corra él en una terminal y que te avise al terminar. Si su sistema no tiene ninguno de estos gestores, dale el sitio oficial de descarga de la herramienta. En Windows, ninguna instalación de este paso pide permisos de administrador (ver «Windows sin administrador»).
5. **Comprobación:** vuelve a correr la comprobación de cada herramienta instalada; en Windows, para Python y git, «Búsqueda en Windows» de inmediato, sin reiniciar el agente, porque ya prueba la ruta donde instala cada comando de la tabla. Si dice que el programa no existe justo después de instalarlo, no lo reinstales: sigue el tropiezo «Programa recién instalado». Con Python listo, sigue con «git», «Guardar versiones», «Entorno virtual» y «Prueba del CV», en ese orden.

**Fin del paso:** termina cuando la prueba del CV sale bien y, si la copia es un repositorio, porque ya lo era o porque el titular aceptó git, cuando tiene su primer commit y él contestó la pregunta de «Guardar versiones». Un opcional que no quedó instalado no lo detiene, y git tampoco: si no se pudo instalar, sigue como si lo hubiera rechazado («git», punto 4).

| Herramienta | Comprobación | dnf / apt | brew | winget |
| --- | --- | --- | --- | --- |
| Python 3.9 o mayor | `python3 --version`; en Windows, «Búsqueda en Windows» | `sudo dnf install python3` / `sudo apt install python3` | `brew install python` | `winget install -e --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements` |
| git (opcional, recomendado) | `git --version` | `sudo dnf install git` / `sudo apt install git` | `brew install git` | `winget install -e --id Git.Git --scope user --location "%LOCALAPPDATA%\Programs\Git" --silent --accept-package-agreements --accept-source-agreements` (en PowerShell, `"$env:LOCALAPPDATA\Programs\Git"`) |

**Búsqueda en Windows:** la terminal del agente puede no ver un programa que sí está, porque conserva el `PATH` (la lista de carpetas donde la terminal busca los programas) de cuando se abrió el agente. Por eso, en Windows, nunca le digas al titular que falta Python o git ni le propongas instalarlo sin haber corrido antes este bloque de PowerShell. Prueba en orden las ubicaciones de cada programa y se queda con la primera que da una versión: para Python, `py` en el `PATH`, el lanzador de la instalación por usuario y el del equipo; para git, `git` en el `PATH`, la ubicación de winget por usuario, la de MinGit y la de la instalación para el equipo.

```powershell
function Find-Programa($Candidatos, $Argumentos, $Patron) {
  foreach ($c in $Candidatos) {
    if (-not $c -or -not (Test-Path -LiteralPath $c)) { continue }
    try { $v = @($null | & $c @Argumentos 2>$null)[0] } catch { continue }
    if ("$v" -match $Patron) { return "$c | $v" }
  }
  'no encontrado'
}
$enPath = { param($n) (Get-Command $n -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source }
'Python: ' + (Find-Programa @((& $enPath py), "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe", "$env:WINDIR\py.exe") @('-3', '--version') '^Python 3\.(9|[1-9]\d)\b')
'git: ' + (Find-Programa @((& $enPath git), "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe", "$env:LOCALAPPDATA\Programs\MinGit\cmd\git.exe", "$env:ProgramFiles\Git\cmd\git.exe") @('--version') '^git version')
```

- **Cómo correrlo:** pégalo tal cual en PowerShell. Si tu terminal no es PowerShell, guárdalo como `buscar.ps1` en el directorio temporal y córrelo con `powershell -NoProfile -ExecutionPolicy Bypass -File <directorio temporal>\buscar.ps1`.
- **Qué imprime:** una línea por programa, con la ruta y su versión, o `no encontrado`. Python cumple con 3.9 o mayor; un Python más viejo sale como `no encontrado`.
- **La ruta se usa toda la conversación:** escribe la ruta que imprimió en cada comando de ese programa, en PowerShell con `&` delante, como `& "<ruta de git>" status`. Vale también para los commits del cierre de la sesión (AGENTS.md, «Al cerrar una sesión…»).
- **Python solo crea el entorno virtual,** con el lanzador `py -3` o su ruta («Entorno virtual»). Después, todo comando de Python usa el del `.venv` (`.venv\Scripts\python.exe`), no el lanzador ni `python`.
- **Si dice `no encontrado`:** ese programa falta de verdad; sigue con la instalación (punto 4). Si sale así justo después de instalarlo, sigue el tropiezo «Programa recién instalado».

**git:** si `git rev-parse --is-inside-work-tree` da `true`, la copia ya es un repositorio: no hay nada que ofrecer. Si no, ofrécelo una vez por conversación; si ya lo rechazó en esta, no insistas.

1. **Oferta:** explícaselo sin jerga, más o menos así: «git guarda versiones de tus archivos: si algo sale mal, puedes volver a una versión anterior, y te deja recibir las mejoras de JobFinderMX con `/actualizar`. Es opcional: sin él tu copia funciona igual, pero sin ese respaldo ni las mejoras.» Pregúntale si lo quiere.
2. **Instalación:** si lo acepta y la comprobación de git falla, instálalo con los puntos 4 y 5. Si no queda instalado, ni con la alternativa de «Windows sin administrador», díselo en una línea y sigue con el punto 4 de esta lista.
3. **Repositorio:** con git instalado y su permiso, convierte la carpeta en repositorio:
   1. `git init -b main`.
   2. Si `git config user.name` o `git config user.email` no dan nada, pregúntale qué nombre y qué correo quiere que firmen sus versiones, y guárdalos solo en la copia con `git config user.name "<nombre>"` y `git config user.email "<correo>"`. Dile que esos datos solo viajan si un día sube su copia a un repositorio privado; si prefiere no dar un correo, el que elija sirve aunque no exista, como el de GitHub sin respuesta (`<usuario>@users.noreply.github.com`) si tiene cuenta.
   3. `git add -A` y `git commit -m "Copia de JobFinderMX"`.
4. **Si lo rechaza o no se pudo instalar:** sigue sin git; el aviso del paso 8 le dice lo que deja de tener. Si después cambia de opinión y lo pide, en cualquier conversación, haz con él esta sección y «Guardar versiones».

**Guardar versiones:** si la copia es un repositorio, porque ya lo era o porque lo creó «git», y `git config --local --get configurar.guardarversiones` no da nada, pregúntale una sola vez si quiere que guardes una versión de su copia al terminar cada paso de la configuración, sin preguntarle cada vez. Dile que subirla a internet, si un día tiene su copia en GitHub, te lo seguirá preguntando cada vez.

- **Su respuesta:** guárdala con `git config --local configurar.guardarversiones true`, o `false` si dice que no. Vive solo en la configuración de git de esta carpeta, que no viaja con la copia.
- **Con un sí:** al terminar cada paso de `/configurar`, guarda la versión con `git add -A` y `git commit -m "Configura el paso <número>: <nombre del paso>"` y avísale en una línea, como «Guardé una versión de tu copia.» (AGENTS.md, «Al cerrar una sesión…», «Excepción de `/configurar`»). Fuera de la configuración, como en una búsqueda, la versión se ofrece y se pide su permiso como siempre.
- **Con un no:** al terminar cada sesión que cambie su copia le vas a ofrecer guardar una versión, como pide AGENTS.md. Díselo en una línea.

**Entorno virtual:** la herramienta de registros usa `openpyxl`, y el generador de CV, fpdf2, python-docx, pypdf y pypdfium2. Todas van en un entorno virtual dentro de la copia (`.venv/`, una carpeta de herramientas que git ignora), no en el Python del sistema, y ninguna pide permisos de administrador. Si la comprobación ya imprime «listo», no hay nada que instalar. Si no, muéstrale los comandos de su sistema y pide su permiso antes de correrlos. Si `.venv/` ya existe y su Python corre, no lo crees de nuevo: basta la instalación. Si existe pero su Python no corre, como cuando la copia viene de otra computadora, créalo de nuevo con `--clear` al final del comando de crear.

| Sistema | Crear el entorno | Instalar las bibliotecas | Comprobación |
| --- | --- | --- | --- |
| Linux y macOS | `python3 -m venv .venv` | `.venv/bin/python -m pip install openpyxl fpdf2 python-docx pypdf pypdfium2` | `.venv/bin/python -I -c "import openpyxl, fpdf, docx, pypdf, pypdfium2; print('listo')"` |
| Windows | `py -3 -m venv .venv`, o con la ruta del lanzador que dio «Búsqueda en Windows» (`& "<ruta de py>" -3 -m venv .venv`) | `.venv\Scripts\python.exe -m pip install openpyxl tzdata fpdf2 python-docx pypdf pypdfium2` (Windows no trae la base de zonas horarias, `tzdata`) | `.venv\Scripts\python.exe -I -c "import openpyxl, fpdf, docx, pypdf, pypdfium2; print('listo')"` |

En Debian y Ubuntu, si crear el entorno falla por `ensurepip`, falta el paquete del sistema: `sudo apt install python3-venv`, que corre el titular (punto 4). El entorno queda listo cuando la comprobación imprime «listo».

**Prueba del CV:** genera el esqueleto de 03 en `<directorio temporal>`, no en la copia (en Windows, con `.venv\Scripts\python.exe`). La fuente Carlito viaja con la copia (`herramientas/fuentes/`): no se instala.

```sh
.venv/bin/python -I herramientas/generar_cv.py 03_CV_BASE.md --idioma es --salida <directorio temporal>/esqueleto
```

El informe debe decir «sí» en fuentes, en Carlito y en el texto del PDF y del DOCX. Así se sabe, antes de entrevistar al titular, que su CV va a salir. Si dice que falta una biblioteca, vuelve a «Entorno virtual». Si falla por otra causa, explícale el error en palabras simples y no sigas al paso 3.

**Windows sin administrador:** el titular puede no tener permisos de administrador, y no sabe qué contestar si Windows se los pide. Las instalaciones con `winget` de la tabla son solo para su usuario (`--scope user`) y no preguntan nada (`--silent` y los `--accept-…`). Si aun así aparece la ventana de Windows que pide permiso para hacer cambios en el equipo, dile que elija «No». Con esa ventana, o si `winget` falla por otra causa que no sea la red (por ejemplo, que no encuentra un instalador para su usuario), sigue con la alternativa de esa herramienta:

- **Python:** el instalador de <https://www.python.org/downloads/windows/>, con «Use admin privileges when installing py.exe» sin marcar.
- **git:** MinGit, la versión mínima de git para Windows, que se descomprime en su perfil sin instalador. Con su permiso, en PowerShell:

  ```powershell
  $ProgressPreference = 'SilentlyContinue'
  $r = Invoke-RestMethod -UseBasicParsing https://api.github.com/repos/git-for-windows/git/releases/latest
  $a = $r.assets | Where-Object name -Match '^MinGit-[\d.]+-64-bit\.zip$' | Select-Object -First 1
  $zip = Join-Path $env:TEMP $a.name
  Invoke-WebRequest -UseBasicParsing $a.browser_download_url -OutFile $zip
  $dir = "$env:LOCALAPPDATA\Programs\MinGit"
  Expand-Archive $zip -DestinationPath $dir -Force
  $p = [Environment]::GetEnvironmentVariable('Path', 'User')
  if (-not (($p -split ';') -contains "$dir\cmd")) {
    [Environment]::SetEnvironmentVariable('Path', ((@($p -split ';') + "$dir\cmd") | Where-Object { $_ }) -join ';', 'User')
  }
  ```

  El bloque `if` agrega git al `PATH` de su usuario una sola vez, que se lee al reiniciar el agente. Mientras tanto, «Búsqueda en Windows» lo encuentra en la ubicación de MinGit y la conversación usa esa ruta.

**Opcionales:** Node y markdownlint-cli2 solo revisan el formato de los `.md` que edita el agente (AGENTS.md, «Formato Markdown»); la copia funciona sin ellos. No los revises, ofrezcas ni instales salvo que el titular los pida. Si los pide, sigue con ellos los puntos 3 a 5 con esta tabla:

| Herramienta | Comprobación | dnf / apt | brew | winget |
| --- | --- | --- | --- | --- |
| Node | `node --version`, con la versión mayor que pide `npm view markdownlint-cli2 engines.node` | `sudo dnf install nodejs npm` / `sudo apt install nodejs npm` | `brew install node` | `winget install -e --id OpenJS.NodeJS.LTS` |
| markdownlint-cli2 | `markdownlint-cli2 --help` (la primera línea da la versión; sale con código 2 aunque esté instalado) | `npm install -g --prefix ~/.local markdownlint-cli2` | `brew install markdownlint-cli2` | `npm install -g markdownlint-cli2` |

**Tropiezos conocidos:**

- **Python en Windows:** donde la documentación diga `python3`, usa el Python del `.venv` (`.venv\Scripts\python.exe`; ver «Búsqueda en Windows»).
- **Programa recién instalado:** si la comprobación no lo encuentra justo después de instalarlo, la terminal todavía no ve el `PATH` nuevo; pasa sobre todo en Windows. Ahí, antes de decir que falta, corre «Búsqueda en Windows», que prueba las rutas donde lo instala este paso, y usa en la conversación la ruta que dé una versión. En Linux y macOS, búscalo con `command -v` después de abrir una terminal nueva. Reiniciar el agente es el último recurso: solo si la búsqueda tampoco lo encuentra, pídele al titular que lo cierre por completo y lo vuelva a abrir, y que te vuelva a pedir «configura mi copia»: la configuración retoma en este paso. Cerrar la ventana no basta, porque el programa puede seguir abierto con el `PATH` viejo. En Antigravity, dile que cierre todas sus ventanas con «File» → «Exit» y que, antes de abrirlo de nuevo, revise en el Administrador de tareas (Ctrl+Shift+Esc) que no quede «Antigravity» en la lista; si queda, que lo seleccione y pulse «Finalizar tarea». Si él instaló el programa en una terminal, basta con cerrar esa terminal y abrir otra.
- **Sin red:** si una instalación falla porque no se resuelve un nombre o se niega la conexión, sigue «Comandos sin red» (`comandos-sin-red.md`).
- **Node viejo:** si el gestor instala un Node más viejo que el que pide markdownlint-cli2 (pasa con `apt` en versiones anteriores de Debian y Ubuntu), ofrece la versión LTS con las instrucciones de <https://nodejs.org> para su distribución.
- **markdownlint-cli2 ya instalado:** cumple si la primera línea de `--help` da la versión, aunque el código de salida no sea 0. No lo busques con `npm list -g`: no ve lo que se instaló con `--prefix ~/.local`.
- **`PATH` de markdownlint-cli2:** si no aparece después de instalarlo con `--prefix ~/.local`, falta `~/.local/bin` en el `PATH`; explícale al titular cómo agregarlo en su shell.
