# El detalle de una bolsa se pide hasta la señal anti-bot y se retoma después

El encaje necesita la descripción de la vacante, y en una bolsa de empleo la descripción solo está en el detalle. En OCC Mundial, el listado nunca se bloqueó, pero 6 de ~24 peticiones de detalle recibieron `403 scraping abuse` o el reto «Just a moment…» de Cloudflare, aun con pausas de 2 s. Sus términos de uso no prohíben leer vacantes para uso personal (§6), pero dejan a OCC como el único intérprete del uso aceptable (§4). Por eso el script pide el detalle solo de las candidatas que pasaron la tarjeta del listado, con pausas, y se detiene en la primera señal anti-bot, sin reintentar en esa ejecución. Una ejecución posterior retoma solo las que siguen sin detalle. Si dos ejecuciones seguidas se bloquean en su primera petición de detalle, el script deja de pedir detalles de esa bolsa y avisa: la IP que se arriesga es la de la casa del titular, que también la usa para navegar.

Retroceder ante la señal no es evadirla. Reintentar de inmediato, cambiar de IP o de huella, usar la sesión del titular o resolver un reto sí lo son, y no se hacen.

## Considered Options

- **Solo el listado, con el detalle por comprobación puntual:** dejaba el encaje en manos del titular, que tendría que guardar o pegar cada anuncio. El encaje es una función central y no puede depender de eso.
- **Navegador headless en `buscar.py`:** el `403 scraping abuse` le llega igual a un headless, y solo serviría para pasar el reto, que es evasión. Además costaba ~300 MB de Chromium y su instalación en el entorno de la nube. Se reabre solo si el uso real muestra que el detalle no alcanza.
- **Usar el login del titular:** OCC prohíbe usar la contraseña «para cualquier fin no autorizado» (§7.3.4), un bloqueo caería sobre la cuenta con la que el titular postula, y nada indicaba que la sesión quitara el bloqueo.

## Consequences

- El volumen de detalle es pequeño porque la tarjeta filtra antes: en la simulación, 86 vacantes dieron 5 candidatas.
- Una vacante de bolsa se registra al verse en el listado, sin evaluación; la siguiente ejecución completa su detalle. Las vacantes sin evaluación son la lista de pendientes, sin estado aparte.
- En Code en la nube, un bloqueo de detalle o de listado sigue el patrón de `IpBloqueada`: la bolsa queda como no revisada y se busca en Code local.
