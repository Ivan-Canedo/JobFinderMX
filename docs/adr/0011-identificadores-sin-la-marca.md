# Identificadores sin la marca

La plantilla pasa a llamarse JobFinderMX en v3.0. «ChambaKit» sonaba informal y no apareció un nombre en español que estuviera libre y gustara, así que se eligió JobFinderMX. «MX» dice que la plantilla está probada con perfiles de México, sin estar limitada a ese país. Se eligió «MX» y no «ES» para que nadie lo lea como España.

El nombre era también parte de identificadores que viven en cada copia o en los clones del mantenedor. Desde v3.0 no llevan la marca:

- **Archivo de registros:** `Registros.xlsx`, no `ChambaKit_Registros.xlsx`. Su nombre sale del bloque de 11/REG-ESQUEMA. `/actualizar` lo renombra en la copia con `git mv`, dentro de su commit, y conserva su historial.
- **Marca de mantenedor:** la clave local de git `plantilla.mantenedor`, no `chambakit.mantenedor`. No se acepta la vieja durante una transición: solo existía en los clones del mantenedor, que la cambia en el mismo trabajo.
- **Estado de las bolsas:** el JSON que da `registros.py estado-bolsas` y lee `buscar.py --estado` declara el formato `estado-bolsas`. Se regenera antes de cada búsqueda en el directorio temporal, así que un estado con el formato viejo solo se rechaza y se genera de nuevo.

## Considered Options

- **Dejar los identificadores con el nombre viejo:** evitaba migrar las copias, pero el nombre retirado seguiría a la vista del titular en su archivo y en cada módulo que lo nombra.
- **Pasarlos a `JobFinderMX`:** costaba la misma migración que quitar la marca, y un renombre futuro obligaría a migrar las copias otra vez.

## Consequences

- Un renombre futuro de la plantilla solo cambia texto: ninguna copia tiene que migrar nada.
- Las secciones de CAMBIOS anteriores a v3.0 siguen nombrando `ChambaKit_Registros.xlsx`, porque `/actualizar` las ejecuta al saltar versiones, antes de la acción de v3.0 que renombra el archivo. Los ADR anteriores conservan su texto, salvo el nombre del archivo en el ADR 0006.
- Las copias con la URL anterior en 01 siguen actualizando por la redirección de GitHub, que se mantiene mientras nadie cree otro repositorio con el nombre viejo en la misma cuenta.
