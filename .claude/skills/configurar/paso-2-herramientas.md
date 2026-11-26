# Paso 2: Herramientas básicas

Python sirve a todos los pasos siguientes. git es opcional pero recomendado: guarda las versiones de la copia. Las bibliotecas de Python del CV y del archivo de registros se instalan cuando hacen falta, en el paso 6 o el 8, el que llegue primero.

**Code en la nube:** si `CLAUDE_CODE_REMOTE` vale `true`, la sesión corre en la nube y el hook de la copia (`herramientas/preparar_nube.sh`) ya instaló al abrirla markdownlint-cli2 y creó `.venv` con las bibliotecas de Python; Python y Node vienen con la máquina de la nube. Salta los puntos 1, 2 y 4 y la oferta de git, porque la copia en la nube siempre es un repositorio: corre solo la comprobación de Python. Si falla, no le pidas al titular comandos de instalación: dile que el hook de la nube falló y qué aviso dio al abrir la sesión (empieza con «Hook de la nube de JobFinderMX»). Si no ves el aviso, repítelo con `CLAUDE_CODE_REMOTE=true bash herramientas/preparar_nube.sh`, que solo instala lo que falta.

1. **Sistema:** detecta el sistema operativo con `uname -s`: `Linux`; `Darwin` es macOS; `MINGW…`, `MSYS…` o un `uname` inexistente (PowerShell) es Windows. En Linux, lee `ID` e `ID_LIKE` en `/etc/os-release`: `dnf` sirve a Fedora y derivados; `apt`, a Debian, Ubuntu y derivados. En macOS el gestor es Homebrew (`brew`) y en Windows, `winget`.
2. **Aviso:** si el sistema no es Linux, dile al titular que JobFinderMX solo se ha probado en Linux, así que un fallo puede venir de ahí.
3. **Revisión:** corre la comprobación de cada herramienta que toca revisar: Python, git si el titular lo acepta (ver «git») y, solo si el titular los pidió, los opcionales. La que ya cumple no se toca.
4. **Instalación:** muéstrale al titular el comando de cada herramienta que falta y pide su permiso antes de instalar. Un comando con `sudo` pide contraseña: pídele que lo corra él en una terminal y que te avise al terminar. Si su sistema no tiene ninguno de estos gestores, dale el sitio oficial de descarga de la herramienta. En Windows, ninguna instalación de este paso pide permisos de administrador (ver «Windows sin administrador»).
5. **Comprobación:** vuelve a correr la comprobación de cada herramienta instalada. Si dice que el programa no existe justo después de instalarlo, no lo reinstales: sigue el tropiezo «Programa recién instalado». El paso termina cuando Python da una versión que cumple y, si el titular aceptó git, cuando la copia es un repositorio con su primer commit. Un opcional que no quedó instalado no lo detiene, y git tampoco: si no se pudo instalar, sigue como si lo hubiera rechazado («git», punto 4).

| Herramienta | Comprobación | dnf / apt | brew | winget |
| --- | --- | --- | --- | --- |
| Python 3.9 o mayor | `python3 --version`; en Windows, `py -3 --version` | `sudo dnf install python3` / `sudo apt install python3` | `brew install python` | `winget install -e --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements` |
| git (opcional, recomendado) | `git --version` | `sudo dnf install git` / `sudo apt install git` | `brew install git` | `winget install -e --id Git.Git --scope user --location "%LOCALAPPDATA%\Programs\Git" --silent --accept-package-agreements --accept-source-agreements` (en PowerShell, `"$env:LOCALAPPDATA\Programs\Git"`) |

**git:** si `git rev-parse --is-inside-work-tree` da `true`, la copia ya es un repositorio: no hay nada que ofrecer. Si no, ofrécelo una vez por conversación; si ya lo rechazó en esta, no insistas.

1. **Oferta:** explícaselo sin jerga, más o menos así: «git guarda versiones de tus archivos: si algo sale mal, puedes volver a una versión anterior, y te deja recibir las mejoras de JobFinderMX con `/actualizar`. Es opcional: sin él tu copia funciona igual, pero sin ese respaldo ni las mejoras.» Pregúntale si lo quiere.
2. **Instalación:** si lo acepta y la comprobación de git falla, instálalo con los puntos 4 y 5. Si no queda instalado, ni con la alternativa de «Windows sin administrador», díselo en una línea y sigue con el punto 4 de esta lista.
3. **Repositorio:** con git instalado y su permiso, convierte la carpeta en repositorio:
   1. `git init -b main`.
   2. Si `git config user.name` o `git config user.email` no dan nada, pregúntale qué nombre y qué correo quiere que firmen sus versiones, y guárdalos solo en la copia con `git config user.name "<nombre>"` y `git config user.email "<correo>"`. Dile que esos datos solo viajan si un día sube su copia a un repositorio privado; si prefiere no dar un correo, el que elija sirve aunque no exista, como el de GitHub sin respuesta (`<usuario>@users.noreply.github.com`) si tiene cuenta.
   3. `git add -A` y `git commit -m "Copia de JobFinderMX"`.

   Dile en una línea que, desde ahora, al terminar cada sesión que cambie su copia le vas a ofrecer guardar una versión (AGENTS.md, «Al cerrar una sesión…»).
4. **Si lo rechaza o no se pudo instalar:** sigue sin git; el aviso del paso 8 le dice lo que deja de tener.

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

  El bloque `if` agrega git al `PATH` de su usuario una sola vez, que se lee al reiniciar el agente (tropiezo «Programa recién instalado»).

**Opcionales:** Node y markdownlint-cli2 solo revisan el formato de los `.md` que edita el agente (AGENTS.md, «Formato Markdown»); la copia funciona sin ellos. No los revises, ofrezcas ni instales salvo que el titular los pida. Si los pide, sigue con ellos los puntos 3 a 5 con esta tabla:

| Herramienta | Comprobación | dnf / apt | brew | winget |
| --- | --- | --- | --- | --- |
| Node | `node --version`, con la versión mayor que pide `npm view markdownlint-cli2 engines.node` | `sudo dnf install nodejs npm` / `sudo apt install nodejs npm` | `brew install node` | `winget install -e --id OpenJS.NodeJS.LTS` |
| markdownlint-cli2 | `markdownlint-cli2 --help` (la primera línea da la versión; sale con código 2 aunque esté instalado) | `npm install -g --prefix ~/.local markdownlint-cli2` | `brew install markdownlint-cli2` | `npm install -g markdownlint-cli2` |

**Tropiezos conocidos:**

- **Python en Windows:** donde la documentación diga `python3`, usa `py -3`.
- **Programa recién instalado:** si la comprobación no lo encuentra justo después de instalarlo, la terminal todavía no ve el `PATH` nuevo; pasa sobre todo en Windows. Dile al titular que cierre y vuelva a abrir su agente (o la terminal, si instaló él el programa) y te vuelva a pedir «configura mi copia»: la configuración retoma en este paso.
- **Sin red:** si una instalación falla porque no se resuelve un nombre o se niega la conexión, sigue «Comandos sin red» (`comandos-sin-red.md`).
- **Node viejo:** si el gestor instala un Node más viejo que el que pide markdownlint-cli2 (pasa con `apt` en versiones anteriores de Debian y Ubuntu), ofrece la versión LTS con las instrucciones de <https://nodejs.org> para su distribución.
- **markdownlint-cli2 ya instalado:** cumple si la primera línea de `--help` da la versión, aunque el código de salida no sea 0. No lo busques con `npm list -g`: no ve lo que se instaló con `--prefix ~/.local`.
- **`PATH` de markdownlint-cli2:** si no aparece después de instalarlo con `--prefix ~/.local`, falta `~/.local/bin` en el `PATH`; explícale al titular cómo agregarlo en su shell.
