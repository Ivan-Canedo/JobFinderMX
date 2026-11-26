# Guion de prueba en Windows

Recorrido manual de la guía de inicio (CONTRIBUTING, «Guía de inicio») en una laptop con Windows 11, tal como lo vive el titular principiante: Antigravity, una cuenta estándar sin permisos de administrador y la versión publicada, bajada con el botón de la guía. Se hace desde cero, en una sola pasada, y deja tomadas las capturas de la guía. Se repite completo cada vez que la guía se vuelve a probar.

**Cómo usarlo:** no marques las casillas en este archivo. Cópialo al clon de la cuenta de administrador como `.scratch/guia-de-inicio/prueba-<AAAA-MM-DD>.md`, que queda fuera de git, y marca ahí. Una casilla que no se cumple lleva debajo su problema anotado: qué pasó, el texto exacto en pantalla y la captura, si la hay. Los ajustes a `/configurar`, `AGENTS.md`, el README o la guía se hacen después, con esas notas, para la versión siguiente; la versión probada no se cambia.

## Antes de empezar

- **Dos cuentas de Windows:** la de administrador, con VS Code y Claude Code, para preparar y para correr las pruebas automáticas; y una cuenta estándar sin permisos de administrador, que hace de titular principiante.
- **Nombre de la cuenta estándar:** uno que no identifique a nadie, como `titular`, porque las rutas de Windows lo muestran en las capturas (`C:\Users\titular`).
- **Cuenta de Google nueva:** créala para la prueba, con un nombre que no identifique a nadie, porque Antigravity saluda con él («Hey `<nombre>`») en casi todas sus pantallas. Con ella inicias sesión en Antigravity y abres el CV en Google Docs. Una cuenta nueva también mide la cuota desde cero.
- **Titular de prueba:** la `FICHA.md` de un titular de prueba (CONTRIBUTING, «Titulares de prueba») cuyos lugares incluyan una zona metropolitana que esté en la tabla de metrópolis de la plantilla, para probarla en el paso 4. Contesta la entrevista de `/configurar` solo con ella, como al generar un titular de prueba. Su paso 7 nombra la empresa real de la búsqueda.
- **Tiempo y cuota:** el nivel 1 (pasos 1 a 6) puede usar casi toda la cuota semanal del plan gratuito. Si se agota, toma la captura `07-cuota-agotada` y retoma cuando se renueve: la prueba sigue en la misma casilla.

## 1. Preparación en la cuenta de administrador

- [ ] **Python y VS Code solo para esta cuenta.** En PowerShell, sin abrirlo como administrador. Si se instalan para todo el equipo, la cuenta estándar los encuentra y `/configurar` no prueba su instalación. Si winget no responde en un Windows recién instalado, actualiza «Instalador de aplicaciones» en la Microsoft Store.

  ```powershell
  winget install -e --id Python.Python.3.13 --scope user
  winget install -e --id Microsoft.VisualStudioCode --scope user
  ```

- [ ] **git con PortableGit.** No uses winget para git en esta cuenta: en una cuenta de administrador, `winget install -e --id Git.Git --scope user` instala para todo el equipo en `C:\Program Files\Git`, aunque pida el modo por usuario. Si ya quedó así, desinstálalo con `C:\Program Files\Git\unins000.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES`, con elevación (`winget uninstall` da «Acceso denegado»). Después, en PowerShell sin elevación:
  1. Baja `PortableGit-<versión>-64-bit.7z.exe` del último release de Git for Windows en GitHub. Comprueba que su SHA-256 (`Get-FileHash`) sea el del release y que su firma (`Get-AuthenticodeSignature`) sea válida, con el mismo firmante que los releases anteriores de Git for Windows.
  2. Descomprímelo en el perfil. En la prueba del 24-nov-2026 se corrió la forma de cmd, `-o"%LOCALAPPDATA%\Programs\Git" -y`; esta es su equivalente en PowerShell:

     ```powershell
     & "$env:USERPROFILE\Downloads\PortableGit-<versión>-64-bit.7z.exe" -o"$env:LOCALAPPDATA\Programs\Git" -y
     ```

  3. Corre su `post-install.bat` con la ruta completa y desde su carpeta; se borra solo al terminar. Desde `git-cmd.exe --command=post-install.bat` falla.

     ```powershell
     Start-Process -Wait -FilePath "$env:LOCALAPPDATA\Programs\Git\post-install.bat" -WorkingDirectory "$env:LOCALAPPDATA\Programs\Git"
     ```

  4. Agrega su carpeta `cmd` al PATH del usuario:

     ```powershell
     [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ";$env:LOCALAPPDATA\Programs\Git\cmd", 'User')
     ```

  Al final, el PATH del equipo no tiene git y no existe `HKLM\SOFTWARE\GitForWindows`.
- [ ] **Claude Code.** Instala la extensión Claude Code en VS Code e inicia sesión. Cierra VS Code por completo y vuelve a abrirlo, para que encuentre git, Python y la Git Bash de PortableGit: sin eso, PowerShell no encuentra `git` y Git Bash no encuentra `py`.
- [ ] **Repositorio en la laptop.** Clónalo de GitHub y pon la marca: `git config --local plantilla.mantenedor true`. Lleva a la laptop la `FICHA.md`, que vive fuera de git.
- [ ] **Versión probada.** Anota la última versión publicada: la del Release que baja el enlace fijo (CONTRIBUTING, «Versión de la plantilla»). Antes, copia este guion desde `main` a `.scratch/` (ver «Cómo usarlo»). Después deja el clon en la etiqueta, para que las pruebas automáticas corran sobre lo mismo que baja el titular: `git switch --detach vX.Y`.
- [ ] **VS Code y Claude Code** abren el clon, y el agente trabaja como mantenedor.
- [ ] **Pruebas automáticas en Windows.** En Git Bash, desde el clon:

  ```sh
  py -3 -m venv .venv && .venv/Scripts/python -m pip install openpyxl tzdata fpdf2 python-docx pypdf pypdfium2
  .venv/Scripts/python -I -B -m unittest discover -s herramientas/pruebas
  ```

  Anota cuántas pasan, fallan y se saltan, y la razón de cada una que falla o se salta.
- [ ] **FICHA y CV.** Copia la `FICHA.md` a `C:\Users\Public\Documents`. Guarda también ahí el CV de su paso 3 como documento de Word o PDF, porque la guía le pide al titular su CV en ese formato.
- [ ] **Cuenta estándar** creada sin permisos de administrador, con el nombre de «Antes de empezar». Comprueba en «Configuración» → «Cuentas» → «Otros usuarios» que diga «Usuario estándar».
- [ ] **Cuenta estándar desde cero.** Inicia sesión en ella:
  - `py -3 --version` y `git --version` en PowerShell no dan una versión (`py` puede ofrecer instalarse desde la Store: no aceptes). Si alguno la da, desinstálalo: de esta cuenta si quedó de una prueba anterior, o desde la de administrador si quedó para todo el equipo.
  - No tiene Antigravity, ni una copia o un `JobFinderMX.zip` en Descargas. Si quedaron de una prueba anterior, bórralos como en «Limpieza».

## 2. Recorrido en la cuenta estándar

Inicia sesión en la cuenta estándar y sigue la guía publicada (<https://ivan-canedo.github.io/JobFinderMX/>) tal cual, sin saltarte pasos ni usar lo que sabes como mantenedor. Toma cada captura en su momento con Win+Mayús+S, recortada a la ventana, y nómbrala como su marcador (ver «Capturas»).

**Cuota:** al terminar cada paso de `/configurar`, y al terminar la búsqueda, anota el % de cuota usado que muestra Antigravity, en «Versiones y fecha». La primera vez, anota dónde se ve.

### Descargar y descomprimir (sección 3)

- [ ] El botón «Descargar JobFinderMX» de la guía baja `JobFinderMX.zip`. Anota cualquier aviso del navegador o de Windows.
- [ ] Clic derecho → «Extraer todo…» → «Extraer», sin cambiar la carpeta propuesta. Capturas `03-extraer-todo` y `03-carpeta-propuesta`.
- [ ] Queda la carpeta doble (`JobFinderMX` dentro de `JobFinderMX`), y la de adentro tiene `README.md` y `01_MAPA_DEL_PROYECTO.md`. Anota la ruta exacta. Captura `03-carpeta-de-adentro`.
- [ ] El 01 de la carpeta de adentro dice la versión probada de la preparación.

### Instalar Antigravity e iniciar sesión (sección 4)

- [ ] En <https://antigravity.google/download>, anota los nombres del botón («Descargar para x64» en la prueba anterior) y del archivo que baja. Captura `04-descarga`, sin el avatar del navegador.
- [ ] El instalador termina sin pedir permisos de administrador. Anota cada pantalla y su texto. Capturas `04-instalador` (una por pantalla, numeradas `04-instalador-1`, `04-instalador-2`…).
- [ ] «Continue with Google» abre el navegador; inicia sesión con la cuenta de Google nueva y, tras aceptar, Antigravity queda con la sesión iniciada. Captura `04-iniciar-sesion`.
- [ ] Pantalla del rol («What best describes your work?»): anota todas las opciones, la que elegiste y si después se puede cambiar. Captura `04-rol`.
- [ ] **Razonamiento en «Medium».** Anota el modelo y el nivel de razonamiento con que arranca Antigravity, y cámbialo a «Medium» como dice la guía. Anota dónde se cambia y si el cambio se conserva en una conversación nueva. Captura `04-razonamiento`.
- [ ] Anota la versión de Antigravity (en su menú de ayuda, «About»), para el pie de la guía.

### Abrir tu carpeta (sección 5)

- [ ] «Create New Project» (el ícono de carpeta con «+» junto a «Projects») → en el diálogo «Open workspace», la carpeta de adentro → «Seleccionar carpeta». Anota si algún nombre cambió. Captura `05-abrir-carpeta`.
- [ ] Anota si Antigravity pregunta entre «Local mode» y «New worktree mode». Si pregunta, elige «Local mode», como dice la guía.
- [ ] Escribe «configura mi copia». El agente ofrece la configuración. Captura `05-configura-mi-copia`.

### Conversación técnica (pasos 1 y 2)

- [ ] **Aviso de ubicación.** El agente dice en dos frases que la copia está en Descargas y que no la borre ni la mueva al limpiarla, sin ofrecer moverla y sin intentar moverla. Anota el texto exacto.
- [ ] **Python por usuario.** Se instala con winget sin ninguna ventana que pida permisos de administrador, y el agente lo usa enseguida por su ruta, sin pedirte cerrar Antigravity.
- [ ] **git opcional.** El agente lo ofrece con palabras sencillas. Acepta. Anota si se instaló con winget por usuario sin pedir permisos o si hizo falta MinGit, y el error de winget, si lo hubo. La copia queda como repositorio con su primer commit.
- [ ] **Guardar versiones.** El agente pregunta una sola vez si guarda una versión al terminar cada paso. Contesta que sí.
- [ ] **Bibliotecas y esqueleto del CV.** Las bibliotecas se instalan en el `.venv` de la copia sin pedir permisos de administrador, y la prueba del esqueleto del CV dice «sí» en fuentes, en Carlito y en el texto del PDF y del DOCX.
- [ ] **La revisión encuentra Python y git** sin reiniciar y sin que digas que ya están, en esta conversación y en cada una de las siguientes. Anota cada vez que el agente dijo que faltaba un programa ya instalado o propuso instalarlo otra vez.
- [ ] Al terminar, el agente te recomienda seguir en una conversación nueva.

### Entrevista hasta el primer CV (pasos 3 a 6)

- [ ] **Una conversación por paso.** Para cada paso, abre una conversación nueva en el proyecto y escribe «configura mi copia». Contesta con la FICHA. En el paso 3, dale el CV de `C:\Users\Public\Documents`. Al terminar cada paso, el agente recomienda una conversación nueva. Anota cuántas conversaciones hicieron falta.
- [ ] **Una conversación nueva no repite revisiones ni avisos:** ni el aviso de ubicación, ni la oferta de git, ni el paso 2, ni la pregunta de guardar versiones. La revisión de privacidad no dice nada, porque la copia no tiene remoto. Anota lo que se repitió.
- [ ] **Resúmenes sin IDs, fuentes ni JSON.** Ningún mensaje muestra IDs (como `F01`, `U02`, `EXP-01`, `PREF-U01`, `HAB-01`, `ROL-01` o `P01`), fuentes, números de sección, nombres de bloque, JSON ni nombres de archivo de los módulos. El bloque de ubicación se confirma en palabras. Anota cada caso, con su captura.
- [ ] **Zona metropolitana desde la tabla** (paso 4). Al nombrar la zona metropolitana de la FICHA, el agente muestra su lista completa de municipios, agrupada por estado, y cita la fuente que trae la tabla (SEDATU, CONAPO e INEGI). Solo te pide quitar lo que no quieras. Compara la lista con la tabla de la plantilla.
- [ ] **Datos inventados.** Compara el perfil (02) y el CV base (03) con la FICHA: anota cada dato, fecha, cifra o habilidad que la FICHA no da. Pide la corrección de uno de ellos como dice la sección 8 de la guía. Captura `08-pedir-correccion`.
- [ ] **Lenguaje sencillo.** Anota cada mensaje del agente con jerga que un principiante no entendería.
- [ ] **Pausa del nivel 1.** Al terminar el paso 6, el agente cierra el nivel 1: dice que ya tienes tu perfil y tu CV, que revises lo que pide la guía y que la búsqueda es el siguiente nivel, para cuando quieras o cuando se renueve tu cuota. No empieza el paso 7 por su cuenta.

### CV generado

- [ ] El paso 6 genera el CV sin instalar nada: las bibliotecas ya estaban en el `.venv`.
- [ ] El CV queda en PDF y DOCX en `muestras_cv/`, y el informe del generador pasa sus controles.
- [ ] El PDF se ve con la fuente Carlito, el color de acento y las viñetas de dos niveles.
- [ ] El DOCX abre bien en Word para la web: fuente, negritas, viñetas y colores. Súbelo a OneDrive desde el navegador.
- [ ] El DOCX abre bien en Google Docs, con los mismos puntos. Súbelo a Google Drive con la cuenta de Google nueva.

### Nivel 2: empresas, registros y búsqueda (sección 9)

- [ ] **Pasos 7 y 8**, cada uno en una conversación nueva con «configura mi copia». Todas las filas de ESTADO quedan «Configurado», y el agente propone la primera búsqueda en una conversación nueva.
- [ ] En una conversación nueva, pide «busca vacantes en mis empresas». La empresa de la FICHA responde y la búsqueda queda en el archivo de registros. Captura `09-tabla-de-vacantes`.
- [ ] Anota cada línea «revisar» o `[FALLO]` y lo que hizo el agente con ella.
- [ ] Anota si el sandbox cortó la red y si el agente explicó cómo cambiar a «Request Review».

### Aprobaciones y cuota (secciones 6 y 7)

- [ ] Antes de cada aprobación, el agente explicó el comando en español. Anota los que pidió aprobar sin explicarlos.
- [ ] Anota los botones del aviso para aprobar un comando y su traducción, para la tabla de la guía. Captura `06-aprobar-comando`.
- [ ] Anota dónde se cambia el modo de permisos y los nombres de los modos que aparecen. Captura `06-modo-de-permisos`, con «Request Review» elegido.
- [ ] Anota si aprobaste cada comando o si algunos corrieron solos en el sandbox, junto con la versión de Windows (ver «Versiones y fecha»).
- [ ] Si se agotó la cuota: anota el mensaje exacto, si dice cuándo se renueva y si `/configurar` retomó en el paso correcto. Captura `07-cuota-agotada`. Si no se agotó, anótalo y deja el marcador para la siguiente prueba.
- [ ] El agente avisó antes de una tarea que gastara mucha cuota, como la búsqueda.

### Reportar (sección 10)

- [ ] La página de Issues muestra «New issue». Captura `10-nuevo-reporte`, sin sesión de GitHub o con el usuario tapado.

## 3. Datos sin confirmar

Los datos que las pruebas anteriores no confirmaron. Cada uno se resuelve con lo que viste en el recorrido.

- [ ] **Shell del agente.** Qué terminal usa el agente de Antigravity en Windows: PowerShell, cmd o Git Bash. Se ve en lo que da `uname -s` en el paso 2 de `/configurar` (sin `uname`, es PowerShell o cmd). Anota los comandos de las skills que fallaron por el shell.
- [ ] **MinGit.** Si winget instaló git, anota si MinGit también funciona (opcional: desinstala git y pídele al agente la alternativa).
- [ ] **OneDrive y Descargas.** Si OneDrive respalda Descargas en esta versión de Windows: en OneDrive, «Configuración» → «Sincronizar y hacer copia de seguridad» → «Administrar copia de seguridad» (anota los nombres reales del menú si no coinciden). Si la cuenta estándar no tiene OneDrive con sesión, anótalo como no comprobado.
- [ ] **Rol.** Qué rol conviene en el primer arranque y qué cambia al elegirlo (por ejemplo, si con él aparece la pregunta de «Local mode»).
- [ ] **«Por confirmar en la prueba» de la guía.** Para cada uno que siga en la guía publicada, anota lo que viste.

## 4. Capturas

Una por marcador de la guía, con el nombre exacto del marcador. Van en `capturas/<nombre>.png` de `gh-pages`, donde reemplazan su cita.

- [ ] `03-extraer-todo`
- [ ] `03-carpeta-propuesta`
- [ ] `03-carpeta-de-adentro`
- [ ] `04-descarga`
- [ ] `04-instalador` (una o varias, numeradas)
- [ ] `04-iniciar-sesion`
- [ ] `04-rol`
- [ ] `04-razonamiento`
- [ ] `05-abrir-carpeta`
- [ ] `05-configura-mi-copia`
- [ ] `06-aprobar-comando`
- [ ] `06-modo-de-permisos`
- [ ] `07-cuota-agotada`
- [ ] `08-pedir-correccion`
- [ ] `09-tabla-de-vacantes`
- [ ] `10-nuevo-reporte`

Antes de usarlas, revisa cada una: sin correo, nombre o foto de una persona real, con la cuenta de Google nueva y el usuario de Windows de la cuenta de prueba. Llévalas a `C:\Users\Public\Pictures` para pasarlas a la cuenta de administrador. Al agregarlas a `gh-pages`, aplica «Privacidad» de CONTRIBUTING (auditoría de términos y metadatos).

## 5. Versiones y fecha

Para el pie de la guía («Probada con Antigravity X.Y en Windows N, el fecha») y para medir la cuota:

- Versión de Antigravity:
- Windows (`winver`): edición, versión (por ejemplo, 24H2) y compilación:
- Fecha de la prueba:
- Versión de la plantilla probada (de la preparación):
- Modelo y nivel de razonamiento con que arrancó Antigravity:
- Modelo y nivel de razonamiento usados en la prueba:

% de cuota usado al terminar cada tramo, con el número de conversación en que terminó:

- Pasos 1 y 2:
- Paso 3:
- Paso 4:
- Paso 5:
- Paso 6:
- Paso 7:
- Paso 8:
- Búsqueda:

## 6. Limpieza en la cuenta estándar

Al terminar, borra lo que dejó la prueba, para que la siguiente empiece desde cero:

- [ ] La copia y `JobFinderMX.zip` en Descargas.
- [ ] El CV subido a OneDrive y a Google Drive, y su papelera.
- [ ] Antigravity, con sus conversaciones y proyectos.
- [ ] Python y git, desinstalados de la cuenta estándar.
- [ ] Las capturas de `Imágenes\Capturas de pantalla`, una vez copiadas.
- [ ] En las carpetas públicas: la `FICHA.md`, el CV y las capturas.
- [ ] La cuenta de Google nueva, si no se va a volver a usar.

La cuenta estándar se queda, para la siguiente prueba.
