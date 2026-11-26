# Paso 1: Copia privada

Los módulos van a guardar datos personales del titular, así que su copia debe ser privada o no tener remoto. En Windows, además, debe estar en una carpeta que no se borre ni se sincronice sola.

1. Lista los remotos con `git remote -v`. Si la carpeta no es un repositorio de git o no tiene remotos, dilo en una línea y salta los puntos 2 a 4.
2. Si un remoto apunta a la plantilla pública (`github.com/Ivan-Canedo/JobFinderMX`, por HTTPS o SSH), el titular clonó la plantilla en lugar de crear su copia. Ofrécele dos caminos, en este orden:
   - **Solo en su equipo:** con su permiso, quita ese remoto (`git remote remove <nombre>`). Dile en una línea que su copia queda solo en su equipo y que en el paso 8 le explicas su respaldo. Sigue con el punto 3.
   - **Copia en GitHub:** en la página de la plantilla, «Use this template» → «Create a new repository» con visibilidad **Private**; después clona ese repositorio y ábrelo con su agente. Detén la configuración hasta que trabaje en esa copia: al configurarla, este paso revisa su visibilidad.
3. Revisa la visibilidad de cada remoto restante:
   - **GitHub:** `gh repo view <dueño>/<repo> --json visibility --jq .visibility`, si `gh` está instalado y con sesión. Si no, `curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/<dueño>/<repo>`: `200` es público; `404`, privado; `000`, que el comando no llegó a la red («Comandos sin red» (`comandos-sin-red.md`)).
   - **Otro servicio:** pídele al titular que confirme la visibilidad en la configuración del repositorio.
4. Si alguno es público, avísale que todo lo que llene quedará publicado en cuanto haga push, y recomiéndale volverlo privado antes de seguir (en GitHub: «Settings» → «General» → «Danger Zone» → «Change visibility»).
5. **Ubicación, solo en Windows y dentro de esta skill** (la revisión del paso 1 que piden AGENTS.md y `/actualizar` termina en el punto 4): el sistema se detecta como en el paso 2 (`paso-2-herramientas.md`), punto 1. Revisa la ruta de la copia, que es tu carpeta de trabajo. Está en un lugar de riesgo si queda dentro de `%USERPROFILE%\Downloads` (el Explorador la llama «Descargas») o si algún tramo de la ruta empieza con `OneDrive` (`OneDrive`, `OneDrive - <organización>`). En OneDrive caen también Documentos y el Escritorio cuando OneDrive los respalda. Si no está en ninguno, no digas nada.
   1. **Oferta:** explícale en dos frases sin jerga por qué conviene moverla. Descargas es una carpeta que se suele limpiar. OneDrive sube a internet cada archivo que cambia, también los miles que agrega la configuración, y mientras sube el archivo de registros puede no dejar guardarlo. Ofrécele moverla a `%USERPROFILE%\JobFinderMX`, una carpeta de su usuario fuera de las dos; dile la ruta completa, con su nombre de usuario.
   2. **Mover:** si acepta, comprueba que `%USERPROFILE%\JobFinderMX` no exista. Si existe, no la toques: pregúntale qué es y sigue con el subpunto 4. Si no existe, muévela con su permiso (en PowerShell; desde otra terminal, dentro de `powershell -NoProfile -Command "…"`):

      ```powershell
      Move-Item -LiteralPath "<ruta actual>" -Destination "$env:USERPROFILE\JobFinderMX"
      ```

   3. **Volver a abrirla:** si se movió, detén la configuración: esta conversación quedó en la ruta vieja. Dile cómo volver, paso por paso: que abra `C:\Users\<usuario>\JobFinderMX` en su agente como abrió la carpeta la primera vez (en los editores como VS Code, «File» → «Open Folder…»), abre una conversación nueva y escribe «configura mi copia». Lo que ya hizo viaja con la carpeta, y la configuración retoma donde quedó.
   4. **Si no se puede mover** (Windows no deja mover una carpeta abierta y responde, por ejemplo, que la usa otro proceso o que el acceso se denegó), o si el titular no quiere: la copia se queda donde está. No intentes otro comando. Pídele que no la borre ni la mueva al limpiar Descargas. Si está en OneDrive, dile además que OneDrive va a subir sus archivos y que, si un día no se puede guardar el archivo de registros, espere a que termine de sincronizar y lo vuelva a pedir.

El paso termina cuando cada remoto es privado, o el titular, ya avisado, decide seguir, y en Windows la copia quedó fuera de Descargas y de OneDrive o el titular recibió el aviso del punto 5.4.
