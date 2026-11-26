# Paso 1: Copia privada

Los módulos van a guardar datos personales del titular, así que su copia debe ser privada o no tener remoto. En Windows, además, conviene que sepa qué cuidar si su copia está en una carpeta que se suele limpiar o que se sincroniza sola.

En la conversación técnica (índice, «Cómo avanzar») haz el paso completo. Después, haz solo los puntos 1 a 4, en silencio: no digas la línea del punto 1 y solo habla si un remoto es público o apunta a la plantilla.

1. Lista los remotos con `git remote -v`. Si la carpeta no es un repositorio de git o no tiene remotos, dilo en una línea y salta los puntos 2 a 4.
2. Si un remoto apunta a la plantilla pública (`github.com/Ivan-Canedo/JobFinderMX`, por HTTPS o SSH), el titular clonó la plantilla en lugar de crear su copia. Ofrécele dos caminos, en este orden:
   - **Solo en su equipo:** con su permiso, quita ese remoto (`git remote remove <nombre>`). Dile en una línea que su copia queda solo en su equipo y que en el paso 8 le explicas su respaldo. Sigue con el punto 3.
   - **Copia en GitHub:** en la página de la plantilla, «Use this template» → «Create a new repository» con visibilidad **Private**; después clona ese repositorio y ábrelo con su agente. Detén la configuración hasta que trabaje en esa copia: al configurarla, este paso revisa su visibilidad.
3. Revisa la visibilidad de cada remoto restante:
   - **GitHub:** `gh repo view <dueño>/<repo> --json visibility --jq .visibility`, si `gh` está instalado y con sesión. Si no, `curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/<dueño>/<repo>`: `200` es público; `404`, privado; `000`, que el comando no llegó a la red («Comandos sin red» (`comandos-sin-red.md`)).
   - **Otro servicio:** pídele al titular que confirme la visibilidad en la configuración del repositorio.
4. Si alguno es público, avísale que todo lo que llene quedará publicado en cuanto haga push, y recomiéndale volverlo privado antes de seguir (en GitHub: «Settings» → «General» → «Danger Zone» → «Change visibility»).
5. **Ubicación, solo en Windows y en la conversación técnica** (la revisión del paso 1 que piden AGENTS.md y `/actualizar` termina en el punto 4): el sistema se detecta como en el paso 2 (`paso-2-herramientas.md`), punto 1. Revisa la ruta de la copia, que es tu carpeta de trabajo. Está en un lugar de riesgo si queda dentro de `%USERPROFILE%\Downloads` (el Explorador la llama «Descargas») o si algún tramo de la ruta empieza con `OneDrive` (`OneDrive`, `OneDrive - <organización>`). En OneDrive caen también Documentos y el Escritorio cuando OneDrive los respalda. Si no está en ninguno, no digas nada.
   1. **Aviso:** no ofrezcas moverla ni la muevas: su agente tiene la carpeta abierta y Windows no deja mover una carpeta abierta. Dale un aviso de dos frases, como este en Descargas: «Tu copia está en Descargas. Es una carpeta que mucha gente limpia, así que no la borres ni la muevas al limpiarla. Si un día quieres cambiarla de lugar, pídemelo y te digo cómo.» En OneDrive, nombra la carpeta donde está y suma una frase: OneDrive va a subir sus archivos y, si un día no se puede guardar el archivo de registros, que espere a que termine de sincronizar y lo vuelva a pedir.
   2. **Si pide cambiarla de lugar,** en esta conversación o en otra, dale los pasos para que lo haga él:
      1. Cerrar el proyecto en su agente.
      2. Mover la carpeta con el Explorador de archivos a una carpeta de su usuario fuera de Descargas y de OneDrive, como `C:\Users\<usuario>\JobFinderMX`; dile la ruta completa, con su nombre de usuario.
      3. Abrirla de nuevo: en Antigravity, con «Create New Project» → «Seleccionar carpeta»; en un editor como VS Code, con «File» → «Open Folder…».
      4. Abrir una conversación nueva y escribir «configura mi copia». Lo que ya hizo viaja con la carpeta, y la configuración retoma donde quedó.

El paso termina cuando cada remoto es privado, o el titular, ya avisado, decide seguir, y en Windows, si la copia está en Descargas o en OneDrive, cuando el titular recibió el aviso del punto 5.1.
