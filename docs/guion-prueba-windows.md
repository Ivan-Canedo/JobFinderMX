# Guion de prueba en Windows

Recorrido manual de la guía de inicio (CONTRIBUTING, «Guía de inicio») en una laptop con Windows 11, tal como lo vive el titular principiante: Antigravity, una cuenta estándar sin permisos de administrador y una copia salida del ZIP. Se hace en una sola pasada y deja tomadas las capturas de la guía. Se repite completo cada vez que la guía se vuelve a probar.

**Cómo usarlo:** no marques las casillas en este archivo. Cópialo al clon de la cuenta de administrador como `.scratch/guia-de-inicio/prueba-<AAAA-MM-DD>.md`, que queda fuera de git, y marca ahí. Una casilla que no se cumple lleva debajo su problema anotado: qué pasó, el texto exacto en pantalla y la captura, si la hay. Los ajustes a `/configurar`, `AGENTS.md`, el README o la guía se hacen después, con esas notas, no a mitad de la prueba.

## Antes de empezar

- **Dos cuentas de Windows:** la de administrador, con VS Code y Claude Code, para preparar y para correr las pruebas automáticas; y una cuenta estándar sin permisos de administrador, que hace de titular principiante.
- **Nombre de la cuenta estándar:** uno que no identifique a nadie, como `titular`, porque las rutas de Windows lo muestran en las capturas (`C:\Users\titular`).
- **Cuenta de Google de prueba:** para iniciar sesión en Antigravity y abrir el CV en Google Docs. Si usas una cuenta propia, tapa su correo en cada captura donde aparezca.
- **Titular de prueba:** la `FICHA.md` de un titular de prueba (CONTRIBUTING, «Titulares de prueba»). Contesta la entrevista de `/configurar` solo con ella, como al generar un titular de prueba. Su paso 7 nombra la empresa real de la búsqueda.
- **Tiempo y cuota:** `/configurar` completo con el plan gratuito puede agotar la cuota semanal. Si se agota, toma la captura `07-cuota-agotada` y retoma cuando se renueve: la prueba sigue en la misma casilla.

## 1. Preparación en la cuenta de administrador

- [ ] **Repositorio en la laptop.** Si `main` ya tiene push, clónalo de GitHub. Si no, en la máquina de desarrollo crea un paquete con `git bundle create JobFinderMX.bundle main gh-pages`, llévalo a la laptop junto con la `FICHA.md` y clónalo con `git clone -b main JobFinderMX.bundle JobFinderMX`. En el clon, pon la marca: `git config --local plantilla.mantenedor true`.
- [ ] **Commit probado.** Anota el hash de `git rev-parse --short HEAD` y la versión de la plantilla que dice la tabla ESTADO de 01.
- [ ] **VS Code y Claude Code** abren el clon, y el agente trabaja como mantenedor.
- [ ] **Pruebas automáticas en Windows.** En Git Bash, desde el clon, con Python 3 instalado:

  ```sh
  py -3 -m venv .venv && .venv/Scripts/python -m pip install openpyxl tzdata fpdf2 python-docx pypdf pypdfium2
  .venv/Scripts/python -I -B -m unittest discover -s herramientas/pruebas
  ```

  Anota cuántas pasan, fallan y se saltan, y la razón de cada una que falla o se salta.
- [ ] **ZIP local.** Arma el mismo ZIP del Release (CONTRIBUTING, «Probar el ZIP sin publicar») en la carpeta pública de descargas, que la cuenta estándar puede leer:

  ```sh
  git archive --format=zip --prefix=JobFinderMX/ -o /c/Users/Public/Downloads/JobFinderMX.zip HEAD
  ```

- [ ] **FICHA y CV.** Copia la `FICHA.md` a `C:\Users\Public\Documents`. Guarda también ahí el CV de su paso 3 como documento de Word o PDF, porque la guía le pide al titular su CV en ese formato.
- [ ] **Cuenta estándar** creada sin permisos de administrador, con el nombre de «Antes de empezar». Comprueba en «Configuración» → «Cuentas» → «Otros usuarios» que diga «Usuario estándar».

## 2. Recorrido en la cuenta estándar

Inicia sesión en la cuenta estándar y sigue la guía publicada (<https://ivan-canedo.github.io/JobFinderMX/>) tal cual, sin saltarte pasos ni usar lo que sabes como mantenedor. Toma cada captura en su momento con Win+Mayús+S, recortada a la ventana, y nómbrala como su marcador (ver «Capturas»).

### Descargar y descomprimir (sección 3)

- [ ] El botón «Descargar JobFinderMX» de la guía baja `JobFinderMX.zip`. Descomprímelo con «Extraer todo» para comprobar que Windows no bloquea un ZIP bajado de internet, y anota cualquier aviso. Después borra el ZIP y su carpeta: son la última versión publicada, no la que se prueba.
- [ ] Copia `C:\Users\Public\Downloads\JobFinderMX.zip` a tu carpeta Descargas. Desde aquí, el recorrido usa este ZIP.
- [ ] Clic derecho → «Extraer todo…» → «Extraer», sin cambiar la carpeta propuesta. Capturas `03-extraer-todo` y `03-carpeta-propuesta`.
- [ ] Queda la carpeta doble (`JobFinderMX` dentro de `JobFinderMX`), y la de adentro tiene `README.md` y `01_MAPA_DEL_PROYECTO.md`. Anota la ruta exacta. Captura `03-carpeta-de-adentro`.

### Instalar Antigravity e iniciar sesión (sección 4)

- [ ] En <https://antigravity.google/download>, anota los nombres del botón y del archivo que baja. Captura `04-descarga`.
- [ ] El instalador termina sin pedir permisos de administrador. Anota cada pantalla, su texto en inglés y el botón que pulsaste. Capturas `04-instalador` (una por pantalla, numeradas `04-instalador-1`, `04-instalador-2`…).
- [ ] «Sign in» abre el navegador y, tras aceptar, Antigravity queda con la sesión iniciada. Captura `04-iniciar-sesion`.
- [ ] Pantalla del rol: anota todas las opciones, la que elegiste y si después se puede cambiar. Captura `04-rol`.
- [ ] Aviso «Terms & Data Use»: anota el nombre del botón que lo acepta. Captura `04-terminos`.
- [ ] Anota la versión de Antigravity (en su menú de ayuda, «About»), para el pie de la guía.

### Abrir la carpeta y mover la copia (sección 5)

- [ ] «New Project» → «Add Folder» → la carpeta de adentro → «Create». Anota los nombres reales del ícono y de cada botón. Captura `05-abrir-carpeta`.
- [ ] Anota si Antigravity pregunta entre «Local mode» y «New worktree mode». Si pregunta, elige «Local mode», como dice la guía.
- [ ] Escribe «configura mi copia». El agente ofrece la configuración. Captura `05-configura-mi-copia`.
- [ ] El agente detecta que la copia está en Descargas y ofrece moverla a `C:\Users\titular\JobFinderMX`, explicando por qué en palabras sencillas. Captura `05-mover-carpeta`.
- [ ] Acepta. Anota si el movimiento funcionó o el error exacto de Windows. Si falló, comprueba que el agente siga el plan B: la copia se queda en Descargas, con el aviso de no borrarla.
- [ ] Anota cómo te dice el agente que vuelvas a abrir la carpeta y si coincide con la guía («New Project» → «Add Folder»).
- [ ] Si se movió, ábrela de nuevo siguiendo la guía («New Project» → «Add Folder»), en una conversación nueva, y escribe «configura mi copia». La configuración retoma donde quedó.

### `/configurar` completo con la FICHA

- [ ] **Python por usuario.** Se instala con winget sin ninguna ventana que pida permisos de administrador, y `py -3 --version` da la versión. Anota si hubo que cerrar y volver a abrir Antigravity para que apareciera.
- [ ] **git opcional.** El agente lo ofrece con palabras sencillas. Acepta. Anota si se instaló con winget por usuario sin pedir permisos o si hizo falta MinGit, y el error de winget, si lo hubo. La copia queda como repositorio con su primer commit.
- [ ] **Pasos 3 a 8.** Contesta con la FICHA, un paso por conversación cuando el agente lo proponga. En el paso 3, dale el CV de `C:\Users\Public\Documents`. Anota cuántas conversaciones hicieron falta.
- [ ] **Datos inventados.** Compara el perfil (02) y el CV base (03) con la FICHA: anota cada dato, fecha, cifra o habilidad que la FICHA no da. Pide la corrección de uno de ellos como dice la sección 8 de la guía. Captura `08-pedir-correccion`.
- [ ] **Lenguaje sencillo.** Anota cada mensaje del agente con jerga que un principiante no entendería.
- [ ] **Fin.** Todas las filas de ESTADO quedan «Configurado» y el agente propone la primera búsqueda en una conversación nueva.

### CV generado

- [ ] Las bibliotecas del CV se instalan en el `.venv` de la copia sin pedir permisos de administrador.
- [ ] El CV queda en PDF y DOCX en `muestras_cv/`, y el informe del generador pasa sus controles.
- [ ] El PDF se ve con la fuente Carlito, el color de acento y las viñetas de dos niveles.
- [ ] El DOCX abre bien en Word para la web: fuente, negritas, viñetas y colores. Súbelo a OneDrive desde el navegador.
- [ ] El DOCX abre bien en Google Docs, con los mismos puntos. Súbelo a Google Drive con la cuenta de prueba.

### Búsqueda con una empresa real (sección 9)

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

Los datos que la investigación previa a la guía no confirmó. Cada uno se resuelve con lo que viste en el recorrido.

- [ ] **Shell del agente.** Qué terminal usa el agente de Antigravity en Windows: PowerShell, cmd o Git Bash. Se ve en lo que da `uname -s` en el paso 2 de `/configurar` (sin `uname`, es PowerShell o cmd). Anota los comandos de las skills que fallaron por el shell.
- [ ] **git sin administrador.** Si `winget install -e --id Git.Git --scope user …` instala git en silencio sin pedir permisos, o si hace falta MinGit. Si winget funcionó, anota si MinGit también funciona (opcional: desinstala git y pídele al agente la alternativa).
- [ ] **Mover la carpeta.** Si el agente puede mover su propia carpeta de trabajo con Antigravity abierto. Si no, se aplica el plan B de `/configurar` (paso 1, punto 5.4): la copia se queda donde está, con el aviso.
- [ ] **OneDrive y Descargas.** Si OneDrive respalda Descargas en esta versión de Windows: en OneDrive, «Configuración» → «Sincronizar y hacer copia de seguridad» → «Administrar copia de seguridad» (anota los nombres reales del menú si no coinciden). Si la cuenta estándar no tiene OneDrive con sesión, anótalo como no comprobado.
- [ ] **Rol.** Qué rol conviene en el primer arranque y qué cambia al elegirlo (por ejemplo, si con él aparece la pregunta de «Local mode»).

Además, los «Por confirmar en la prueba» de la guía, que no están en esa lista:

- [ ] Todo el recorrido funcionó sin permisos de administrador (sección 2 de la guía).
- [ ] La ruta exacta tras «Extraer todo» (sección 3).
- [ ] Los nombres del botón y del archivo de la descarga de Antigravity, y las pantallas del instalador (sección 4).
- [ ] El botón que acepta «Terms & Data Use» (sección 4).
- [ ] Los nombres «New Project», «Add Folder» y «Create», y la pregunta de «Local mode» (sección 5).
- [ ] Los botones del aviso de aprobación y los nombres de los cuatro modos de permisos (sección 6).
- [ ] El mensaje de cuota agotada (sección 7).

## 4. Capturas

Una por marcador de la guía, con el nombre exacto del marcador. Van en `capturas/<nombre>.png` de `gh-pages`, donde reemplazan su cita.

- [ ] `03-extraer-todo`
- [ ] `03-carpeta-propuesta`
- [ ] `03-carpeta-de-adentro`
- [ ] `04-descarga`
- [ ] `04-instalador` (una o varias, numeradas)
- [ ] `04-iniciar-sesion`
- [ ] `04-rol`
- [ ] `04-terminos`
- [ ] `05-abrir-carpeta`
- [ ] `05-configura-mi-copia`
- [ ] `05-mover-carpeta`
- [ ] `06-aprobar-comando`
- [ ] `06-modo-de-permisos`
- [ ] `07-cuota-agotada`
- [ ] `08-pedir-correccion`
- [ ] `09-tabla-de-vacantes`
- [ ] `10-nuevo-reporte`

Antes de usarlas, revisa cada una: sin correo, nombre o foto de una persona real, y con el usuario de Windows de la cuenta de prueba. Llévalas a `C:\Users\Public\Pictures` para pasarlas a la cuenta de administrador. Al agregarlas a `gh-pages`, aplica «Privacidad» de CONTRIBUTING (auditoría de términos y metadatos).

## 5. Versiones y fecha

Para el pie de la guía («Probada con Antigravity X.Y en Windows N, el fecha»):

- Versión de Antigravity:
- Windows (`winver`): edición, versión (por ejemplo, 24H2) y compilación:
- Fecha de la prueba:
- Commit y versión de la plantilla probados (de la preparación):

## 6. Limpieza en la cuenta estándar

Al terminar, borra los datos sintéticos que dejó la prueba:

- [ ] La copia (`C:\Users\titular\JobFinderMX` o la que quedó en Descargas), los restos de la descompresión y `JobFinderMX.zip` en Descargas.
- [ ] El CV subido a OneDrive y a Google Drive, y su papelera.
- [ ] Las conversaciones y proyectos de Antigravity, o Antigravity completo si no se va a volver a usar en esa cuenta.
- [ ] Las capturas de `Imágenes\Capturas de pantalla`, una vez copiadas.
- [ ] En las carpetas públicas: `JobFinderMX.zip`, la `FICHA.md`, el CV y las capturas.

Python y git pueden quedarse: no llevan datos del titular de prueba. La cuenta estándar también se queda, para la siguiente prueba.
