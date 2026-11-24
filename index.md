---
layout: page
title: Guía de inicio de JobFinderMX
---

Esta guía te lleva paso a paso, desde descargar JobFinderMX hasta tener tu perfil y tu CV listos. Está pensada para Windows y para alguien que nunca ha usado un agente de IA. No necesitas pagar ninguna suscripción.

Tiene dos niveles. El **nivel 1** (pasos 1 a 8) deja listos tu perfil y tu CV, lo más útil y con menos riesgo. El **nivel 2** (paso 9) te lleva a buscar vacantes, cuando ya domines lo básico.

## 1. Qué es y qué no hace

JobFinderMX es una carpeta con instrucciones para un **agente de IA**: un asistente como los chats que ya conoces, pero que además puede trabajar con los archivos de tu computadora. Con esas instrucciones, el agente:

- Te entrevista y arma tu **perfil**: tu experiencia, tus estudios y tus habilidades, sin inventar nada.
- Escribe tu **CV** en español e inglés, en PDF y en Word.
- Cuando estés listo, **busca vacantes** en las empresas que elijas y te dice cuáles encajan contigo.

Lo que **no** hace:

- No postula a ninguna vacante ni contacta a nadie por ti. Eso lo decides y lo haces tú.
- No es una aplicación ni una página web: todo pasa en una carpeta de tu computadora.

Tus archivos se guardan en tu computadora. El agente trabaja con un servicio de Google, así que lo que lee de tu carpeta pasa por ese servicio. Lo explica el aviso de uso de datos que aceptas en el paso 4.

## 2. Qué necesitas

- Una computadora con **Windows 10 u 11**.
- Una **cuenta de Google**, como la de Gmail.
- **Tener 18 años o más.**
- **Tu CV actual**, en PDF o Word, si lo tienes. Sin CV también se puede: el agente te entrevista.
- Conexión a internet.

No necesitas pagar ninguna suscripción: el agente se usa con el plan gratuito de Google.

> **Por confirmar en la prueba:** que todo el recorrido funcione en una cuenta de Windows sin permisos de administrador, incluida la instalación de Antigravity. Si es así, agregar aquí: «Tampoco necesitas permisos de administrador».

## 3. Descargar y descomprimir

Pulsa el botón. Baja un solo archivo, `JobFinderMX.zip`, siempre con la versión más reciente.

[Descargar JobFinderMX](https://github.com/Ivan-Canedo/JobFinderMX/releases/latest/download/JobFinderMX.zip){: .boton}

Un archivo `.zip` es una carpeta comprimida: antes de usarla hay que **descomprimirla**, es decir, sacar su contenido.

1. Abre tu carpeta **Descargas**. Ahí está `JobFinderMX.zip`.
2. Haz clic derecho sobre el archivo y elige **«Extraer todo…»**.

   > **Captura pendiente `03-extraer-todo`:** el menú del clic derecho sobre `JobFinderMX.zip`, con «Extraer todo…» resaltado.

3. Windows te propone una carpeta. **No la cambies:** pulsa **«Extraer»**.

   > **Captura pendiente `03-carpeta-propuesta`:** la ventana «Extraer carpetas comprimidas» con la carpeta que propone Windows y el botón «Extraer».

4. Se abre una carpeta `JobFinderMX`, y dentro hay otra `JobFinderMX`. **Tu copia es la de adentro**: la que tiene muchos archivos, como `README.md` y `01_MAPA_DEL_PROYECTO.md`. Recuerda dónde quedó: la vas a abrir en el paso 5.

   > **Captura pendiente `03-carpeta-de-adentro`:** el Explorador dentro de la segunda carpeta `JobFinderMX`, con la lista de archivos y la ruta visible arriba.
   >
   > **Por confirmar en la prueba:** la ruta exacta que queda (por ejemplo, `Descargas\JobFinderMX\JobFinderMX`).

No abras el `.zip` con doble clic para trabajar desde ahí: así solo ves su contenido, sin sacarlo, y el agente no puede trabajar con él.

## 4. Instalar Antigravity e iniciar sesión

**Antigravity** es el programa de Google donde vive el agente. Está en inglés; aquí va cada pantalla traducida.

1. Entra a <https://antigravity.google/download> y pulsa **«Download for x64»** (descargar la versión para casi todas las computadoras con Windows). Solo si tu computadora tiene un procesador Snapdragon, pulsa **«Download for ARM64»**.

   > **Captura pendiente `04-descarga`:** la página de descarga con el botón «Download for x64» resaltado.
   >
   > **Por confirmar en la prueba:** los nombres del botón y del archivo (`Antigravity-x64.exe`), tomados de la documentación de Antigravity.

2. Abre el archivo que bajó (`Antigravity-x64.exe`) y sigue los pasos del instalador.

   > **Captura pendiente `04-instalador`:** cada pantalla del instalador, con su traducción y el botón que hay que pulsar.
   >
   > **Por confirmar en la prueba:** las pantallas del instalador y si pide permisos de administrador.

3. Abre Antigravity. Pulsa **«Sign in»** (iniciar sesión). Se abre tu navegador: entra con tu cuenta de Google y acepta. Luego vuelve a Antigravity.

   > **Captura pendiente `04-iniciar-sesion`:** la pantalla de Antigravity con el botón «Sign in».

4. Antigravity pregunta **«What best describes your work?»** (¿qué describe mejor tu trabajo?). Elige **«Knowledge Work»** (trabajo de oficina o de conocimiento) y pulsa **«Continue»** (continuar). Esta elección solo cambia cómo se ve el programa, y se puede cambiar después.

   > **Captura pendiente `04-rol`:** la pantalla «What best describes your work?» con «Knowledge Work» marcado.
   >
   > **Por confirmar en la prueba:** qué rol conviene. Las opciones son Software Engineering, Knowledge Work, Data & Analytics, Science, Design y Other; «Knowledge Work» es una propuesta.

5. Aparece el aviso **«Terms & Data Use»** (términos y uso de datos): dice cómo usa Google lo que escribes y lo que lee el agente. Léelo y acéptalo para seguir.

   > **Captura pendiente `04-terminos`:** el aviso «Terms & Data Use» con el botón para aceptarlo.
   >
   > **Por confirmar en la prueba:** el nombre del botón que acepta el aviso.

## 5. Abrir tu carpeta y escribir «configura mi copia»

1. En la barra de la izquierda de Antigravity, pulsa el ícono **«New Project»** (proyecto nuevo; así llama Antigravity a una carpeta en la que trabaja el agente): una carpeta con un signo de más.
2. Pulsa **«Add Folder»** (agregar carpeta), elige tu copia (la carpeta `JobFinderMX` de adentro, del paso 3) y pulsa **«Create»** (crear).

   > **Captura pendiente `05-abrir-carpeta`:** la ventana «New Project» con la carpeta elegida y el botón «Create».
   >
   > **Por confirmar en la prueba:** el ícono y los nombres «New Project», «Add Folder» y «Create», tomados de la documentación de Antigravity.
   >
   > **Por confirmar en la prueba:** si, con el rol elegido, Antigravity pregunta entre «Local mode» y «New worktree mode». Si pregunta, la guía dice elegir «Local mode» (trabajar directo en tu carpeta).

3. En el cuadro de mensaje, escribe **configura mi copia** y pulsa Enter.

   > **Captura pendiente `05-configura-mi-copia`:** el cuadro de mensaje con «configura mi copia» escrito, dentro del proyecto de la carpeta.

Lo primero que hace el agente es revisar dónde quedó tu copia. Si está en Descargas, te ofrece moverla a una carpeta más segura, `C:\Users\<tu usuario>\JobFinderMX`, porque Descargas se suele limpiar. Si aceptas y la mueve, la conversación se detiene: vuelve a abrir la carpeta en su lugar nuevo con «New Project» → «Add Folder», como en el punto 2, abre una conversación nueva y escribe otra vez **configura mi copia**. Sigue donde se quedó.

> **Captura pendiente `05-mover-carpeta`:** el agente ofreciendo mover la carpeta.
>
> **Por confirmar en la prueba:** si el agente puede mover la carpeta mientras Antigravity la tiene abierta. Si no puede, la copia se queda en Descargas, y la guía debe pedir que no la borres.

Después, el agente te guía. Avanza en pasos cortos: instala lo que hace falta, te entrevista para tu perfil y escribe tu CV. Te explica cada paso en español sencillo.

En el camino te ofrece **git**, un programa que guarda versiones de tus archivos: si algo sale mal, puedes volver atrás, y además te deja recibir las mejoras de JobFinderMX. Es opcional, pero te conviene aceptarlo.

## 6. Aprobar comandos

Para hacer su trabajo, el agente usa **comandos**: órdenes que le da a tu computadora, como instalar un programa o crear un archivo. Antigravity te puede pedir permiso antes de cada uno.

**La regla:** antes de pedirte permiso, el agente te explica en español qué va a hacer. Si eso coincide con lo que están haciendo, aprueba. Si no lo explicó, no entiendes para qué es o no tiene que ver con tu búsqueda de trabajo, no lo apruebes y pregúntale.

> **Captura pendiente `06-aprobar-comando`:** el agente explicando un comando en español y, debajo, el aviso de Antigravity que pide aprobarlo, con sus botones.

Palabras en inglés que vas a ver:

| En pantalla | Qué significa |
| --- | --- |
| Allow | Permitir: el agente hace lo que pidió. |
| Request Review | Pedir revisión: te pregunta antes de cada comando. |
| Default | Predeterminado: te pregunta solo en algunos casos. |
| Auto | Automático: el agente decide qué comandos corre sin preguntarte. |
| Turbo | Turbo: corre todo sin preguntarte. **No lo uses.** |

> **Por confirmar en la prueba:** los botones del aviso para aprobar un comando y su traducción, para agregarlos a la tabla, y que los cuatro modos de permisos, tomados de la documentación de Antigravity, se llamen así.

«Request Review», «Default», «Auto» y «Turbo» son los **modos de permisos** de Antigravity. Usa «Default» o «Request Review». No uses «Turbo» ni «Auto»: en ellos el agente corre comandos sin preguntarte, y la regla deja de servir.

Según tu Windows:

- **Windows 10, o Windows 11 anterior a la versión 24H2 o sin las actualizaciones de agosto de 2026:** vas a aprobar cada comando, uno por uno. Es normal; no está fallando nada.
- **Windows 11 24H2 o posterior, con las actualizaciones de agosto de 2026 o posteriores:** con «Default», Antigravity corre los comandos en un espacio aislado, sin internet. Cuando un comando necesite internet, como al instalar algo o buscar vacantes, el agente te pide cambiar a «Request Review» y te dice cómo.

> **Captura pendiente `06-modo-de-permisos`:** dónde se cambia el modo de permisos, con «Request Review» elegido.

## 7. Cuando se acaba la cuota

El plan gratuito tiene una **cuota semanal**: un límite de uso que se renueva cada semana. Cuánto rinde depende de lo que le pidas; buscar en muchas empresas, por ejemplo, gasta más.

Para aprovecharla, el agente te propone un paso de la configuración por conversación, y te avisa antes de algo que gaste mucha cuota.

Si se acaba, no se descompuso nada y no pierdes tu trabajo: tu carpeta guarda lo que ya hiciste. Espera a que se renueve, abre una conversación nueva y escribe otra vez **configura mi copia**: la configuración sigue donde se quedó. Si estabas pidiendo otra cosa, como una búsqueda, vuelve a pedirla.

> **Captura pendiente `07-cuota-agotada`:** el mensaje de Antigravity cuando se acaba la cuota.
>
> **Por confirmar en la prueba:** qué dice ese mensaje y si indica cuándo se renueva.

## 8. Qué revisar siempre

El agente tiene la regla de no inventar datos, pero puede equivocarse. Tú eres quien conoce tu historia: **revisa todo lo que escribe** antes de usarlo.

En tu perfil y en tu CV, busca:

- Puestos, empresas, fechas o estudios que no sean exactamente los tuyos.
- Cifras que tú no diste, como «aumenté las ventas un 30 %».
- Habilidades, programas o idiomas que no tienes, o con un nivel más alto que el real.
- Frases que exageran lo que hiciste.

Si encuentras algo así, díselo con tus palabras. Por ejemplo:

- «En mi CV dice que aumenté las ventas un 30 %. Yo no di esa cifra; quítala.»
- «Trabajé en esa empresa de 2019 a 2022, no hasta 2023. Corrígelo en mi perfil y en mi CV.»

El agente corrige el archivo y vuelve a generar el CV si hace falta. Tú no tienes que editar nada a mano.

> **Captura pendiente `08-pedir-correccion`:** una corrección pedida en el chat y la respuesta del agente.

## 9. Nivel 2: buscar vacantes

Cuando tu perfil y tu CV estén listos, puedes seguir con la búsqueda. Haz este nivel cuando ya te sientas cómodo con lo anterior.

1. Escribe **configura mi copia**. El agente sigue con los pasos que faltan: te pregunta en qué empresas quieres buscar (si no sabes, te ofrece buscarlas contigo) y crea tu archivo de registros, donde anota cada búsqueda y cada vacante.
2. Cuando termine, pídele: **busca vacantes en mis empresas**. Si son muchas empresas, te avisa antes, por la cuota.
3. El agente te muestra una tabla con las vacantes y qué tanto encaja cada una contigo.

> **Captura pendiente `09-tabla-de-vacantes`:** la tabla resumen de una búsqueda.

Antes de confiar en una evaluación, revisa:

- **Tus condiciones:** que la ciudad, la modalidad (presencial, híbrida o remota) y el sueldo de la vacante sean los que dice el agente.
- **Los requisitos:** si dice que cumples uno, que de verdad lo cumplas.
- **La vacante original:** ábrela con su enlace y léela tú. El agente puede leer mal un anuncio.

Si una te interesa, pídele que adapte tu CV a esa vacante y revísalo como en el paso 8. Postular lo haces tú, en la página de la empresa.

## 10. Si algo falla

Si te atoras o algo no funciona como dice esta guía, avísanos en GitHub Issues: <https://github.com/Ivan-Canedo/JobFinderMX/issues>. GitHub es el sitio donde se publica JobFinderMX, e Issues es su lista de reportes. Necesitas una cuenta gratuita de GitHub.

Pulsa **«New issue»** (reporte nuevo) y cuenta:

- En qué paso de esta guía ibas.
- Qué escribiste y qué te contestó el agente. Una captura de pantalla ayuda mucho.
- Tu versión de Windows.

**Lo que escribes ahí es público.** No pongas tu nombre completo, tu teléfono, tu correo ni datos de tu CV, y tápalos en las capturas.

> **Captura pendiente `10-nuevo-reporte`:** la página de Issues con el botón «New issue».

---

Probada con Antigravity **[X.Y]** en Windows **[N]**, el **[fecha]**.
