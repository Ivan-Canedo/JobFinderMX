# Paso 7: Empresas

Llena `06_EMPRESAS_OBJETIVO.md` con las empresas donde el titular quiere buscar, cada una con su ficha y la configuración de su plataforma de reclutamiento, y con las bolsas de empleo de su país que quiera usar. Con 06 lleno, 07 queda listo para buscar.

1. **Lista:** pregúntale en qué empresas quiere buscar vacantes. Puede dar varias, una o ninguna; no le sugieras nombres. Si no sabe cuáles o te pide ideas, ofrécele descubrirlas.
2. **Descubrir, solo si lo pide:** busca empresas desde 02, 04 y 05 según 07/BUS-REGLAS («Empresas nuevas»): que contraten en sus familias de roles (05) y en su región o con su alcance de remoto (04); compartir sector no basta. Muéstrale una lista corta, cada empresa con el motivo en una línea y su fuente. Solo entran las que acepte.
3. **Cada empresa, una a la vez:**
   1. **Portal:** encuentra la página oficial de empleo desde el sitio de la empresa y, desde ahí, su buscador de vacantes. Identifica la plataforma por la URL del buscador (06/CAT-PLATAFORMAS).
   2. **Plataforma con adaptador** (las que lista `python3 -I herramientas/buscar.py --help`): escribe la configuración con la forma de CAT-PLATAFORMAS, con `consulta` en `null`.
   3. **Plataforma sin adaptador o sitio propio:** sigue CAT-REGLAS («Plataforma»): lee el `robots.txt` antes de pedirle nada al portal. El adaptador nuevo va en `herramientas/buscar.py` con la interfaz de los que ya tiene (el comentario sobre `ADAPTADORES`). Si ninguna ruta está permitida, díselo al titular.
   4. **Ficha:** asígnale un ID y escribe su fila de CAT-EMPRESAS y su ficha según CAT-REGLAS y FICHA-PLANTILLA, con el bloque de «### Configuración». Lo que no hayas comprobado queda pendiente.
   5. **Búsqueda de prueba:** corre el script solo con esa empresa y guarda la salida en `<directorio temporal>`:

      ```sh
      python3 -I herramientas/buscar.py EMP-<ID> --salida <directorio temporal>/prueba.json
      ```

      Debe salir `[OK]`, o `[SIN TOTAL]` con la comprobación de su ficha. Si el `[FALLO]` dice que no se resolvió el nombre o que se negó la conexión, sigue «Comandos sin red» (`comandos-sin-red.md`) antes de tocar la ficha. Con otro `[FALLO]`, corrige la configuración o el adaptador y repítela. Revisa las líneas «revisar ubicación»: si una nombra de otra forma un lugar que el titular ya aceptó, como una abreviatura o su nombre en inglés, propónle agregar esa forma al bloque de 04 (paso 4, «Cómo se escriben»); si es otro lugar, no lo propongas. Si el listado trae miles de vacantes, ofrécele una `consulta` más estrecha. Completa la ficha con lo que comprobaste (ubicaciones, remotas, cobertura) y anota el resultado en su primera línea. La búsqueda de prueba no se registra.
4. **Bolsas de empleo (06/CAT-BOLSAS):** una bolsa lista por término de búsqueda las vacantes de muchas empresas, también las de empresas que el titular no conoce o que publican como «Empresa confidencial». Este punto también lo retoma una actualización con una copia ya configurada (`CAMBIOS.md`); si 06 ya tiene la bolsa, salta al subpaso 3.
   1. **Catálogo:** las bolsas con adaptador son las que lista `python3 -I herramientas/buscar.py --help`, cada una con su sección en CAT-BOLSAS, que da su `pais`. Elige las de un país de su región o del alcance de su remoto (el bloque de 04/PREF-UBICACION). Si no hay ninguna, díselo en una línea y sigue con el punto 5. Si hay, ofrécelas, cada una con lo que gana y su límite en dos frases: vacantes que no están en los portales de su catálogo; a cambio, la bolsa tolera pocas lecturas de detalle, así que el encaje de sus vacantes puede tardar varias búsquedas en completarse (07/BUS-BOLSAS), y la búsqueda nunca usa su cuenta en la bolsa. Solo entran las que acepte.
   2. **Ficha:** asígnale el siguiente `BOL-##` y escribe su fila y su ficha según CAT-BOLSAS, con el `adaptador` y el `pais` de su sección.
   3. **Términos (05/HAB-TERMINOS):** si el bloque ya tiene términos, muéstraselos y pregúntale si los conserva. Si no, propónselos desde las familias de HAB-ROLES, en una tabla con una fila por familia:
      - `terminos`: cómo se busca la familia en la bolsa, en el idioma de sus anuncios: el nombre de la familia o su título más común. Pocos por familia, porque cada término es una búsqueda en cada lugar de su región (06/CAT-BOLSAS, «Búsquedas»).
      - `titulos`: las frases que, en el título de una vacante, indican la familia, desde su nombre y su base en HAB-ROLES y desde HAB-VOCABULARIO. Nada que no salga de sus familias.

      Dile que puede quitar, cambiar o agregar, como el nombre de una herramienta que los anuncios ponen en el título, y que una familia que no quiera buscar en bolsas queda con `terminos` vacío. Solo entra lo que apruebe. Escribe el bloque, comprueba que sea JSON válido con una clave por familia de HAB-ROLES, y anota su respuesta como `HAB-U##` en HAB-FUENTES, con la fecha. 05 sube de versión y su fila de ESTADO toma la versión nueva, sin cambiar su estado ni su siguiente paso.
   4. **Comprobación:** una exploración de términos con los términos recién escritos en el bloque (06/CAT-BOLSAS, «Comprobación»):

      ```sh
      python3 -I herramientas/buscar.py BOL-<##> --explorar "<término>" "<término>" --salida <directorio temporal>/prueba.json
      ```

      La bolsa no debe salir como `[FALLO]`. Si el `[FALLO]` es una señal anti-bot, no la repitas: la bolsa queda dada de alta y se prueba en la primera búsqueda. Si dice que no se resolvió el nombre o que se negó la conexión, sigue «Comandos sin red» (`comandos-sin-red.md`). Muéstrale el rendimiento de cada término, para que sepa cuánto ruido trae cada uno; los cambios a los términos se proponen después, con el rendimiento de sus búsquedas (07/BUS-BOLSAS). Anota la fecha en la primera línea de la ficha.
   5. **Code en la nube:** dale en una línea el host de la bolsa (su sección en CAT-BOLSAS, «Hosts»), que va en la lista de dominios del entorno de la nube, como en «Empresa nueva» de 07/BUS-CANALES.
5. **Revisión:** muéstrale el catálogo, con la plataforma de cada empresa, las bolsas y lo que quedó pendiente.
6. **Cierre:** llena la línea **Estado** de 06 y súbelo de versión. Las filas de 06 y 07 en ESTADO quedan «Configurado», con los siguientes pasos «Agregar o retirar empresas según CAT-REGLAS» para 06 y «Buscar vacantes (BUS-PASOS)» para 07. Si no dio ninguna empresa ni aceptó ninguna bolsa, los catálogos quedan vacíos y las dos filas quedan «Configurado» con esos mismos siguientes pasos; dile que el script no tiene dónde buscar hasta que agregue una, con este paso o cuando quiera.
