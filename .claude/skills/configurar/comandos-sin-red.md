# Comandos sin red

Algunos agentes corren los comandos en un entorno aislado sin internet, como Antigravity en su preset «Default» en Linux, macOS y Windows 11 24H2 o posterior con las actualizaciones de agosto de 2026. Entonces fallan todos los que salen a la red (`buscar.py`, `git ls-remote` y `git fetch` de `/actualizar`, `pip`, `npm`, `curl`), aunque el script esté bien. En los demás Windows, Antigravity no tiene ese entorno aislado: aun con «Default», los comandos tienen red y el titular aprueba cada uno.

1. **Cómo se reconoce:** el error no viene de ningún servidor. O no se resuelve el nombre (`Temporary failure in name resolution`, `Name or service not known`, `nodename nor servname`, `getaddrinfo`, `Could not resolve host`), o se niega la conexión (`Connection refused`, `Network is unreachable`, `Operation not permitted`, `Failed to connect`); `curl` da el código `000`.
2. **No es falta de red:** un `[FALLO]` de `buscar.py` con un código HTTP (`HTTP 403`, `HTTP 404`…), un `robots.txt` que prohíbe una ruta o un error de la configuración de la ficha: ahí el portal respondió, o el problema es de la ficha, y se corrige como dice el paso 7. Tampoco lo es si en la misma búsqueda otra empresa dio `[OK]` o `[SIN TOTAL]`.
3. **Confirmación:** si no está claro, prueba la red con un sitio que siempre responde (en Windows, con `py -3`):

   ```sh
   python3 -I -c "import urllib.request; urllib.request.urlopen('https://github.com', timeout=20); print('con red')"
   ```

   Si imprime `con red`, el comando sí tiene red y el fallo es de otra cosa.
4. **Qué decirle al titular:** en palabras simples, que su agente corre los comandos sin acceso a internet, así que no llegan a los portales ni a la plantilla; que no es un error de su copia, y que hay que darle red a su agente:
   - **Antigravity,** en cualquier sistema: en su configuración («Settings» → «General» → «Global Permissions» → «Permission Preset»), que cambie el preset de permisos a «Request Review». Con él los comandos tienen red y el agente le pide aprobar cada uno antes de correrlo. Que no use «Turbo»: corre los comandos sin preguntarle, así que ninguno pasa por su revisión.
   - **Otro agente:** que busque en su configuración cómo dejar que los comandos usen la red, de preferencia con la opción que pide aprobar cada comando antes que con la que los corre todos sin preguntar.
5. **Después:** cuando diga que ya cambió el ajuste, repite la confirmación del punto 3 y luego el comando que falló. Si no quiere darle red, dile que las búsquedas, las instalaciones y `/actualizar` no van a funcionar hasta que la tenga, y detén el paso donde estás.
