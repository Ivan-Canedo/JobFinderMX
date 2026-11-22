# El encaje es un número calculado desde los núcleos

El nivel de encaje de 08 se decidía por el peor núcleo: un solo núcleo insuficiente mandaba la vacante a ★☆☆☆☆ aunque los demás fueran directos, y la escala no separaba «me falta un tema puntual» de «tengo poco que ver con el puesto». En la copia de un titular, 36 de 64 evaluaciones quedaban en ★☆☆☆☆. Ahora cada núcleo vale unas estrellas según su categoría (directa 5, transferible 3, académica/formativa 1.5, insuficiente 0), el encaje exacto es el promedio de sus núcleos y las estrellas son su redondeo, con los empates en .5 hacia abajo y al menos ★☆☆☆☆ si algún núcleo tiene evidencia. Los pesos viven en una línea de 08/EVAL-ACUERDOS, como valores por defecto que el titular cambia con una decisión `EVAL-U##`. La cuenta la hace la herramienta de registros desde `nucleos` y esa línea, no el agente; en Web, el agente la hace con la misma línea.

Esto revierte la regla de 08 «sin puntaje sumado ni ponderaciones». Sus razones no se sostienen con esta fórmula: los requisitos menores no la diluyen porque solo entran los núcleos, las alertas siguen diciendo qué falta, y los pesos son arbitrarios pero quedan escritos en 08 y se pueden recalibrar con evaluaciones reales.

## Considered Options

- **Ajustar las filas de la escala por peor núcleo:** igualaba un núcleo académico con uno insuficiente o seguía amontonando vacantes en pocos niveles.
- **Penalizar aparte cada núcleo insuficiente:** llevaba a ☆☆☆☆☆ vacantes con evidencia en algún núcleo.
- **Incluir la cobertura de obligatorios en el número:** volvía a esconder qué falta; la cobertura se reporta aparte, como `X/Y`.
- **Un subagente que asigne las estrellas con reglas abstractas:** daba resultados distintos para los mismos núcleos y no permitía recalcular evaluaciones guardadas.

## Consequences

- El agente sigue decidiendo la categoría de cada núcleo; la aritmética es determinista y se prueba con `unittest`.
- Las evaluaciones guardadas se recalculan desde `nucleos` sin volver a leer el anuncio.
- ☆☆☆☆☆ queda solo para vacantes con todos los núcleos insuficientes.
