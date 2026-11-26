# Diagnosticar al fallar: `/configurar` no revisa el equipo en cada conversación

`/configurar` corría los pasos 1 y 2 (copia privada y herramientas) en cada invocación. En la prueba en Windows con Antigravity y el plan gratuito, cada conversación nueva repitió el aviso de ubicación y la oferta de git, y dijo que Python no estaba instalado aunque sí lo estaba, porque la terminal del agente conservaba el `PATH` de antes de instalarlo. Cada comando del agente vuelve a leer toda la conversación, así que esas revisiones gastaban cuota en cada arranque y quitaban el ahorro de abrir una conversación nueva por paso.

La regla es que el paso 2 corre solo mientras ninguna fila de ESTADO esté «Configurado», y que el paso 1 se reduce a la revisión de privacidad, en silencio salvo que haya un remoto público. Lo demás se diagnostica cuando un comando falla: si el Python del `.venv` no existe o no importa sus bibliotecas, el agente repara con el paso 2; si git falla al cerrar, lo busca en sus rutas de instalación antes de decir que falta.

## Considered Options

- **Revisar en cada conversación, pero en silencio:** quitaba los mensajes repetidos, pero no los comandos ni su costo.
- **Una bandera en la copia** (una fila de ESTADO o un archivo que diga que el equipo está listo): miente cuando la copia cambia de computadora o se borra el `.venv`, y una fila sin módulo rompe el esquema de ESTADO que fusiona `/actualizar`.

## Consequences

- Un problema del equipo aparece a mitad de un paso y no al inicio. Como el paso 2 deja instalado todo lo técnico, incluidas las bibliotecas del CV y de los registros, ese paso ya no instala nada salvo una reparación.
- Antes de decir que falta un programa, el agente corre la búsqueda completa en sus rutas de instalación, no solo en el `PATH`.
