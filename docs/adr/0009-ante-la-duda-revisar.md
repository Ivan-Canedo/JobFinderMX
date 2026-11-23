# Ante la duda, revisar: ninguna ubicación se descarta en silencio

Al probar `buscar.py` con los titulares de prueba, la clasificación de ubicaciones fallaba en las dos direcciones. Unas vacantes de la región salían como fuera sin aviso: una localidad de un grupo de división completa escrita sin su división, como «Localidad A3, País A». Otras entraban sin serlo: una ciudad homónima de su división aceptaba toda la división, y las remotas de países que 04 no nombra («Country Z») entraban al alcance del remoto porque el script no sabía que eran países. Arreglar solo los falsos positivos con reglas más estrictas habría aumentado las pérdidas silenciosas.

La regla es que una ubicación que puede estar en la región o en el alcance del remoto, y que el script no puede decidir, es una ubicación por revisar: sale en una línea «revisar» y se entrega. Solo queda fuera lo que el script sabe que está fuera: otra división escrita en el lugar de la división, un país que reconoce y que no está en el alcance. El ruido que esto produce se paga de dos formas: con datos (una tabla de países en la plantilla y el campo `incluidas` del grupo de localidades, que llena el titular) y con agrupamiento (una línea «revisar» por ubicación literal y por requisición, no por publicación).

## Considered Options

- **Solo con datos del titular** (`incluidas`, sin la regla de revisar): lo que el titular no anotó se seguía perdiendo en silencio.
- **Solo con la regla de revisar**, sin `incluidas`: el titular revisaba cada vez las mismas localidades.
- **Una remota que no nombra un país del alcance queda fuera**, sin tabla de países: descartaba a ciegas las de países que 04 escribe de otra forma.
- **Una remota que no nombra un país del alcance queda por revisar**, sin tabla de países: cientos de líneas «revisar» en un portal grande, lo que vuelve ilegible la salida.
- **Revisar también en los grupos con `nombres`** las localidades que no están en la lista: en esos grupos el titular ya dijo qué acepta, y cada «Ciudad, País» del país sería una línea «revisar».

## Consequences

- `herramientas/paises.json` (nombres en inglés y en español de CLDR, código alfa-3 y formas usuales de los portales) vive en la plantilla y se lee junto al script, también con `--copia`. Los nombres de `paises` de 04 mandan sobre ella.
- `localidades[].incluidas` es opcional y solo vale en un grupo de división completa; una copia sin el campo sigue siendo válida, y `/actualizar` lo pregunta con el titular.
- Una ciudad homónima de su división cuenta como localidad solo en el lugar de la localidad (la primera parte de la ubicación, sin contar el país).
- Una ubicación con «Remote» decide la modalidad solo si la plataforma no la publica; si las dos se contradicen, gana la modalidad y sale una línea «revisar».
- Un portal cuyas ubicaciones nunca escriben la división da más líneas «revisar»; la ficha de esa empresa en 06 lo documenta y el titular lo reduce con `incluidas`.
