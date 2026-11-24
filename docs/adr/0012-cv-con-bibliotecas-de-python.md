# CV con bibliotecas de Python, sin LibreOffice ni poppler

`generar_cv.py` genera el PDF con fpdf2 y el DOCX con python-docx, y revisa el PDF (páginas, fuentes incrustadas, texto y su orden, vistas PNG) con pypdf y pypdfium2. Las cuatro se instalan con pip en el entorno virtual de la copia, el mismo de `openpyxl`, y la fuente Carlito viaja en la plantilla como archivo TTF (licencia OFL). LibreOffice y poppler salen de la plantilla en todos los sistemas.

El motivo es el titular principiante: en Windows sin permisos de administrador, LibreOffice no se instala (su MSI es para toda la máquina) y poppler necesita el VC++ Redistributable, que también pide administrador. Las bibliotecas de pip no piden nada de eso.

## Considered Options

- **Bibliotecas de pip solo en Windows, LibreOffice en los demás:** dos generadores que mantener, y el de Windows solo se prueba en un equipo con Windows.
- **Solo DOCX, y el titular exporta el PDF en Word o Google Docs:** el PDF quedaba sin revisar, y la conversión ajena puede cambiar la fuente o el espaciado.
- **Word por COM cuando está instalado:** suma pywin32 y un camino que solo existe en algunos equipos.
- **LibreOffice Portable:** sin confirmar que funcione sin administrador ni sin interfaz, y pesa cientos de MB.

## Consequences

- El PDF y el DOCX salen de dos generadores, no de un mismo FODT: las pruebas comparan el texto de ambos con el contenido, no solo el del PDF.
- El diseño de 09/CV-PLANTILLA se reproduce dos veces (fpdf2 y python-docx); un cambio de diseño se hace en los dos.
- `/configurar` deja de instalar paquetes del sistema para el CV, y el hook de Code en la nube deja de instalarlos.
- Las copias existentes dejan de necesitar LibreOffice y poppler; `CAMBIOS.md` lo dice en la versión que lo trae.
