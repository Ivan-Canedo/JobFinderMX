---
name: configurar
description: Configura paso a paso la copia de JobFinderMX del titular y retoma donde quedó según la tabla ESTADO de 01. Úsala cuando el titular acepte configurar su copia o pida retomar la configuración.
---

# Configurar una copia de JobFinderMX

Lleva al titular de una copia recién creada a una copia lista para usar, un paso corto y revisable a la vez. La configuración puede repartirse en varias sesiones: el avance vive en la tabla ESTADO de `01_MAPA_DEL_PROYECTO.md`, donde «Sin llenar» marca lo pendiente y el «Siguiente paso sugerido» de cada fila nombra el paso de esta skill que la atiende.

Si `git config --local --get plantilla.mantenedor` da `true`, esta carpeta es la plantilla: detente y dile al mantenedor que pruebe en un clon temporal (`CONTRIBUTING.md`).

Cualquier agente con terminal configura la copia completa. No anotes qué agente usa el titular: puede cambiarlo. En los comandos, `<directorio temporal>` es el directorio temporal de la sesión o, si no tienes uno, el del sistema; nunca esta carpeta.

Este archivo es el índice: lleva cómo avanzar, las reglas que valen en todos los pasos y la lista de pasos. Cada paso vive en su propio archivo, en esta misma carpeta (`.claude/skills/configurar/`). Lee solo el archivo del paso que toca. Si un paso remite a otro paso, lee también el archivo de ese otro paso.

## Cómo avanzar

1. **Conversación técnica:** mientras ninguna fila de ESTADO diga «Configurado», empieza por los pasos 1 y 2 completos, antes de cualquier pregunta sobre el titular. Dejan listo todo lo que se instala, y el paso 2 termina cuando el esqueleto del CV sale bien. Si el paso 2 no terminó, la configuración retoma en él.
   - **Después,** con alguna fila «Configurado», no corras el paso 2 ni repitas el aviso de ubicación ni la oferta de git. Del paso 1 haz solo la revisión de privacidad (sus puntos 1 a 4), en silencio salvo que un remoto sea público o apunte a la plantilla.
   - **Al fallar:** si un comando falla por el `.venv` o por git, sigue «Diagnóstico al fallar» de AGENTS.md, que repara con el paso 2.
2. Sigue con el primer paso, en el orden de esta skill, que nombre una fila «Sin llenar» de ESTADO. Si no queda ninguna, la configuración está completa: ofrece el paso 9, que no tiene fila en ESTADO.
3. Haz un paso por vez. Al terminarlo, marca «Configurado», con su siguiente paso de uso, cada fila de ESTADO que lo nombra: la de cada módulo que el paso escribió y también la de cada módulo de método que solo deja listo, sin editarlo. Cada módulo escrito pasa markdownlint sin advertencias, si está instalado, y se versiona según AGENTS.md («Al cerrar»). El paso termina cuando ninguna fila que lo nombra sigue «Sin llenar». Si el titular dio en el paso 2 el permiso para guardar versiones, guarda una al terminar el paso y avísalo en una línea (paso 2, «Guardar versiones»).
4. Al terminar un paso, di cuál sigue y pregunta si continuar ahora o en otra sesión.
5. **Agente que no es Claude Code:** valen sus reglas de AGENTS.md, como explicar cada comando antes de que el titular lo apruebe. Además, como el plan del titular puede tener una cuota limitada, propón un solo paso por sesión, con los pasos 1 y 2 como uno solo: al terminarlo, en lugar de la pregunta del punto 4, recomiéndale seguir en una conversación nueva y escribir otra vez «configura mi copia», que retoma donde quedó. Si la cuota se acaba a la mitad de un paso, la configuración retoma en ese paso.
6. **Fin de la configuración:** cuando ya no queda ninguna fila «Sin llenar» y el titular terminó o declinó lo que se ofrece en el punto 2, cierra en este orden:
   1. Un resumen corto: una línea por paso configurado.
   2. Si esta sesión creó el archivo de registros, ofrece en una línea el commit de 11/REG-LOCAL («Historial y respaldo»), sin que sea la pregunta final.
   3. Como último mensaje, el siguiente paso: la primera búsqueda (07/BUS-PASOS). Recomiéndale abrir una conversación nueva en esta carpeta (en Claude Code, `/clear`) y pedir «busca vacantes en mis empresas»: la de la configuración ya trae mucho contexto que la búsqueda no necesita. Si 06 no tiene empresas ni bolsas, el siguiente paso es agregar una con el paso 7.

## Reglas de todos los pasos

- **No inventes datos:** todo lo que entra a un módulo sale de los documentos del titular, de sus respuestas o de otro módulo. No propongas valores, cifras, lugares ni habilidades que él no haya dicho; lo que no sepa o no quiera responder queda pendiente, como pide cada módulo.
- **Preguntas en bloques:** pregunta en bloques de dos a cuatro preguntas cortas sobre un mismo tema, y espera la respuesta antes del siguiente bloque. No sugieras respuestas.
- **Lenguaje de lo que le dices al titular,** sobre todo en los resúmenes que le pides confirmar. Esta regla manda sobre lo que diga un paso:
  1. Nunca le muestres IDs ni fuentes (de documentos, de respuestas, de experiencias, de preferencias, de habilidades, de familias ni de pendientes), números de sección, nombres de bloque, JSON ni nombres de archivo de los módulos. Todo eso se sigue escribiendo en el módulo.
  2. Nombra los módulos por lo que son («tu perfil», «tus preferencias», «tu CV»). El nombre del archivo, solo si el titular pregunta dónde está.
  3. Los resúmenes para confirmar llevan solo hechos, en las palabras del titular. Los términos de su profesión, solo si él los usó. Los pendientes se dicen como preguntas abiertas.
  4. El bloque de ubicación se confirma en palabras: lugares, modalidad, países del remoto y una línea sobre cómo suelen escribir esos lugares los anuncios, con un ejemplo. El bloque se valida igual, sin mostrarlo.
  5. Traduce tus términos técnicos («guardar una versión», «bajar de internet», «una carpeta de herramientas dentro de tu copia»). La excepción son los comandos que el titular aprueba: se muestran, con su explicación en español antes.

## Pasos

Cada línea da el paso, lo que hace y el archivo que hay que leer para hacerlo.

1. **Paso 1: Copia privada.** Remotos privados y, en Windows, el aviso si la copia está en Descargas o en OneDrive. Archivo: `paso-1-copia-privada.md`.
2. **Paso 2: Herramientas básicas.** Python, git si el titular lo acepta, el entorno de Python con las bibliotecas del CV y de los registros, y la prueba del esqueleto del CV. Archivo: `paso-2-herramientas.md`.
3. **Paso 3: Perfil maestro.** Llena 02 desde los documentos del titular y una entrevista. Archivo: `paso-3-perfil-maestro.md`.
4. **Paso 4: Preferencias.** Llena 04 con sus respuestas. Archivo: `paso-4-preferencias.md`.
5. **Paso 5: Habilidades y roles.** Llena 05 desde 02 y 04, y deja listo 08. Archivo: `paso-5-habilidades-y-roles.md`.
6. **Paso 6: CV base.** Redacta 03 y genera el primer CV. Archivo: `paso-6-cv-base.md`.
7. **Paso 7: Empresas.** Llena 06 con empresas y bolsas de empleo, y deja listo 07. Archivo: `paso-7-empresas.md`.
8. **Paso 8: Registros.** Crea el archivo de registros. Archivo: `paso-8-registros.md`.
9. **Paso 9: Otros canales (opcional).** Ofrece Code en la nube y el canal Web; no tiene fila en ESTADO. Archivo: `paso-9-otros-canales.md`.

**Comandos sin red:** si un comando que sale a la red falla porque no se resuelve el nombre o se niega la conexión, lee `comandos-sin-red.md`, en cualquier paso.
