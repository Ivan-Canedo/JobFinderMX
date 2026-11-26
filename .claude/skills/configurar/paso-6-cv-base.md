# Paso 6: CV base

Redacta el CV base de `03_CV_BASE.md` en español e inglés desde 02, con las reglas de 03 (CV-REGLAS y los acuerdos por defecto de CV-DECISIONES) y de 09 (CV-SINTESIS y CV-PLANTILLA), y genera el primero con el color que elija el titular.

1. **Sin instalaciones:** el paso 2 ya dejó las bibliotecas del CV en el entorno virtual de la copia y probó el esqueleto, así que este paso no instala nada. Si el generador dice que falta una biblioteca o el entorno, repáralo con el paso 2 (`paso-2-herramientas.md`, «Entorno virtual») y sigue.
2. **Enfoque:** con sus familias de roles (05) y sus objetivos (04), proponle en pocas líneas qué perfil presenta la base y en qué orden van los hechos de su empleo principal. Pregúntale también si cambia algún acuerdo por defecto de CV-DECISIONES, dicho en palabras, como el orden de las secciones o cómo van las fechas. Lo que decida se anota ahí como `CV-U##`.
3. **Redacción:** reemplaza el esqueleto de CV-ES y CV-EN con el CV redactado desde 02, en el formato literal de 09/CV-HERRAMIENTAS, y borra de CV-USO el párrafo del esqueleto. Cada línea o viñeta lleva su `[CV-E##]`, con su fila en CV-TRAZABILIDAD. Escribe la síntesis general al final, según CV-SINTESIS. Lo pertinente que no cabe va a CV-OPCIONALES. Si a 02 le falta un dato que el CV necesita, pregúntalo (entra a 02 como `U##`) o déjalo fuera y anótalo como `CV-P##`. La versión en inglés lleva los mismos hechos.
4. **Revisión:** muéstrale el CV por bloques (encabezado y perfil, experiencia, el resto), como se leerá, sin las marcas `[CV-E##]`, y aplica sus correcciones en los dos idiomas. Un hecho nuevo o corregido entra primero a 02, con su `U##`.
5. **Color:** pregúntale qué color quiere para los títulos de sección y la línea bajo el contacto, y ofrécele el de la plantilla, que es neutro. Si pregunta cuál conviene, dile que no hay evidencia sólida de un color que mejore las candidaturas; lo que sí hay, cuéntaselo en palabras desde 09/CV-PLANTILLA. Pasa su elección a `#RRGGBB` y revisa el contraste que recomienda CV-PLANTILLA; si no lo alcanza, díselo y ofrécele un tono más oscuro del mismo color, pero la decisión es suya. Escribe el color en el bloque de configuración de CV-PLANTILLA.
6. **Primer CV:** genera la base en los dos idiomas, en `muestras_cv/` y con el nombre de 09/CV-HERRAMIENTAS:

   ```sh
   .venv/bin/python -I herramientas/generar_cv.py 03_CV_BASE.md --idioma es --salida muestras_cv/CV_<Nombre>_<Apellido>_ES_base_<fecha>_v01
   .venv/bin/python -I herramientas/generar_cv.py 03_CV_BASE.md --idioma en --salida muestras_cv/CV_<Nombre>_<Apellido>_EN_base_<fecha>_v01
   ```

   El informe debe decir «sí» en fuentes, Carlito y texto, y cada línea «revisar» se corrige en 03. Revisa las vistas PNG de cada página según 09/CV-CONTROLES y dile al titular dónde quedaron los PDF y los DOCX. Si quiere otro color, cambia el bloque y vuelve a generar.
7. **Cierre:** en 03, actualiza la línea **Estado** para describir su CV base y anota la versión de 02 que usaste como fuente de trayectoria; súbelo de versión. Sube también la de 09 si el color cambió. Las filas de 03 y 09 en ESTADO quedan «Configurado», con el siguiente paso «Adaptar a cada vacante con 09; actualizar si cambia 02» para 03 y «Adaptar y exportar CV para vacantes (CV-FLUJO)» para 09.
