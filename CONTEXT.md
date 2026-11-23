# JobFinderMX

Plantilla de instrucciones, módulos y herramientas para que un agente de IA apoye la búsqueda laboral de una persona: perfil, CV, búsqueda, evaluación de vacantes y tendencias. «MX» dice que está probada con perfiles de México, no que esté limitada a ese país.

## Personas y repositorios

**Titular**:
La persona que busca trabajo y usa su copia de JobFinderMX con sus propios datos.
_Avoid_: usuario, candidato

**Mantenedor**:
Quien desarrolla y publica la plantilla.
_Avoid_: usuario, autor

**Plantilla**:
El repositorio público de JobFinderMX, sin datos de ningún titular.
_Avoid_: template, repo base

**Copia**:
El repositorio privado de un titular, creado desde la plantilla y llenado con sus datos.
_Avoid_: fork, clon

**Titular de prueba**:
Un titular inventado, con datos sintéticos y marcados como tales, que el mantenedor usa para probar las herramientas en portales reales con un perfil siempre igual. Puede haber varios; cada uno se nombra por su perfil, como «el titular de datos».
_Avoid_: usuario de prueba, usuario falso, titular falso

**Copia de prueba**:
Los módulos llenos y el archivo de registros del titular de prueba, guardados fuera de git en el equipo del mantenedor. Tiene la forma de una copia, pero no es un repositorio ni se publica.
_Avoid_: clon de prueba (ese es temporal y nace sin llenar), fixture

**Versión de la plantilla**:
Una publicación numerada de la plantilla (1.0, 1.1…). Cada copia anota de cuál salió o a cuál se actualizó por última vez.
_Avoid_: release, versión del módulo

**Actualización**:
Llevar a una copia los cambios de una versión más nueva de la plantilla, conservando lo que escribió el titular.
_Avoid_: migración, sincronización, merge

## Uso

**Canal**:
Dónde se usa JobFinderMX: Code (un agente con terminal sobre la copia, sea Claude Code, Antigravity u otro, en el equipo del titular o en la nube) o Web (un proyecto de claude.ai). Los separa si se llega a los portales y a los scripts, no qué agente se usa ni dónde corre. Solo Code hace búsquedas y escribe los registros; Web consulta y hace comprobaciones puntuales.
_Avoid_: modo, entorno, Local, canal Nube

**Code local**:
El canal Code en el equipo del titular, sobre su carpeta de la copia.
_Avoid_: modo local

**Code en la nube**:
El canal Code en una sesión de Claude Code en la nube (claude.ai/code o la pestaña Code de la app), sobre un clon nuevo del repositorio privado de la copia. Solo llega a los portales que estén en la lista de dominios del entorno.
_Avoid_: canal Nube, Claude Code web, remoto

**Entorno de la nube**:
La configuración en claude.ai/code con la que arranca cada sesión de Code en la nube: la lista de dominios y el script de instalación. Vive en la cuenta del titular, no en la copia.
_Avoid_: entorno, sandbox, VM

**Agente**:
El asistente de IA que trabaja con el titular. En el canal Code puede ser cualquiera con terminal; en el canal Web, solo Claude.
_Avoid_: Claude, cuando se habla del canal Code

## Registros

**Archivo de registros**:
El archivo de la copia donde viven las búsquedas, vacantes, observaciones, evaluaciones y documentos del titular. Es la única fuente de verdad, y solo lo escribe el canal Code.
_Avoid_: modo local, hoja de registros, base de datos

**Instantánea**:
La copia en texto del archivo de registros que lee el canal Web. Se regenera completa desde el archivo y nunca se edita a mano.
_Avoid_: export, réplica, snapshot, hoja

**Nota para Code**:
Lo que deja un chat del canal Web cuando algo debe cambiar en un módulo o en los registros, para que el canal Code lo aplique en la copia.
_Avoid_: pendiente, parche

## Búsqueda

**Plataforma de reclutamiento**:
El sistema que aloja el portal de empleo de una empresa, como Workday, Eightfold o SmartRecruiters.
_Avoid_: ATS, portal

**Adaptador**:
La parte del script de búsqueda que sabe leer una plataforma de reclutamiento; cada empresa que la usa solo aporta su configuración.
_Avoid_: adaptador por empresa, scraper

**Bolsa de empleo**:
Un sitio donde los empleadores publican sus vacantes y se postula ahí mismo, como OCC Mundial o Computrabajo. Para una vacante publicada en ella, su anuncio en la bolsa es el oficial, aunque la empresa sea confidencial.
_Avoid_: portal de empleo, job board, agregador

**Agregador**:
Un sitio que copia vacantes publicadas en otros lados y redirige a ellos para postular, como Jooble o Talent.com. Nunca es la fuente oficial de una vacante.
_Avoid_: bolsa de empleo, buscador de empleo

**Término de búsqueda**:
Una palabra o frase que se le da a una bolsa de empleo para listar sus vacantes, como «analista de datos» o «power bi». Sale de las familias de roles del titular y de los términos que él agregue; el lugar no es parte del término.
_Avoid_: consulta, keyword, palabra clave

**Exploración de términos**:
Una corrida que prueba términos de búsqueda nuevos en una bolsa de empleo y solo reporta cuánto rinden. No registra vacantes ni cuenta para comparar una búsqueda con la anterior.
_Avoid_: búsqueda de prueba

**Búsqueda**:
Recorrer el listado de vacantes de una o varias empresas en sus portales, o de una bolsa de empleo, filtrarlas, evaluarlas y registrarlas. Solo se hace en el canal Code.
_Avoid_: comprobación, consulta

**Comprobación puntual**:
Leer el anuncio oficial de una vacante, o de unas pocas que el titular nombra, sin recorrer ningún listado. Se hace en cualquier canal; desde Web, lo que se quiera conservar va en una nota para Code.
_Avoid_: búsqueda, verificación

## Región

**Región**:
Los lugares de `localidades` en el bloque de 04/PREF-UBICACION donde el titular acepta trabajo presencial o híbrido.
_Avoid_: zona (esa es la zona metropolitana de un grupo de localidades), área

**Grupo de localidades**:
Un elemento de `localidades`: de división completa (con `divisiones` y sin `nombres`), con `nombres` (solo esas localidades) o de país completo (sin ninguno de los dos).
_Avoid_: localidad (esa es una sola ciudad, municipio o comuna)

**Alcance del remoto**:
Desde qué países acepta el titular vacantes remotas: ninguno, los de `remoto.paises` o cualquiera.
_Avoid_: región remota

**Ubicación por revisar**:
Una ubicación que puede estar en la región o en el alcance del remoto sin que el script pueda decidirlo. Sale en una línea «revisar» y nunca se descarta.
_Avoid_: ubicación dudosa, indeterminada (ese es un valor de `region_relacionada` en 11)

## Evaluación

**Núcleo**:
Una de las dos o tres necesidades centrales de una vacante, elegida entre sus requisitos obligatorios, ambiguos o en funciones. Recibe la categoría de su mejor evidencia en el perfil del titular.
_Avoid_: requisito clave, requisito principal

**Encaje**:
Qué tanto respalda el perfil del titular los núcleos de una vacante. Se calcula desde la categoría de cada núcleo y se muestra en estrellas; la cobertura de requisitos obligatorios se reporta aparte.
_Avoid_: fit, puntaje, match
