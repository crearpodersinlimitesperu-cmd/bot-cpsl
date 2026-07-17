# PROCESO DE CONFIGURACIÓN Y USO DEL AGENTE FINANCIERO

Este documento describe la arquitectura, la configuración del acceso de seguridad (Google Gmail OAuth2) y las instrucciones operativas del **Agente Financiero Autónomo**.

---

## 1. ARQUITECTURA Y MÓDULOS DEL AGENTE

El agente financiero consta de cinco pilares principales integrados en un único script modular (`agente_financiero.py`):

1. **Motor de Aprendizaje Estructural (`--learn`)**: Escanea los archivos existentes en la carpeta de entrada (por defecto `./datos_financieros/`). Detecta los encabezados de columnas (si son Excel o CSV) o patrones de texto clave (si son PDFs o TXT) y genera un diccionario estructurado de correspondencias en `maestro_estructura.json`. Adicionalmente, importa todos los datos históricos locales en el archivo maestro de control.
2. **Acceso a Gmail mediante OAuth2 (`--update`)**: Se conecta a la API de Gmail en modo lectura (`readonly`) y lee de forma segura los correos correspondientes al BCP e invoices del periodo de consulta, realizando la extracción de datos mediante expresiones regulares y lógica heurística.
3. **Módulo de Actualización en Tiempo Real**: Valida y añade los registros de transacciones al presupuesto maestro (`presupuesto_maestro.xlsx`), aplicando un filtro de control de duplicidad robusto basado en el ID de mensaje único de Gmail y los hashes de origen de datos locales.
4. **Validación Contable**: 
   - Transforma los gastos negativos en montos absolutos positivos (los gastos se guardan siempre en positivo, clasificados como tipo `Egreso`).
   - Descarta transacciones sin fechas y escribe los detalles fallidos en `errores_parseo.log`.
   - Lanza alertas críticas por consola si el acumulado de una categoría del mes excede por más del 10% el presupuesto asignado en la hoja de configuración del Excel.
5. **Generador de Balance Financiero (`--balance`)**: Genera el informe mensual consolidado `balance_financiero_YYYYMMDD.xlsx` con tres hojas diseñadas profesionalmente y un gráfico de barras horizontal de Matplotlib integrado.

---

## 2. CONFIGURACIÓN DEL ACCESO DE SEGURIDAD (GMAIL OAUTH 2.0)

Para permitir que el agente lea tus correos del BCP de manera segura, debes habilitar la API de Gmail y generar credenciales de aplicación:

### Paso 2.1: Crear Proyecto y Habilitar la API de Gmail
1. Ingresa a la consola de [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuevo proyecto llamado **Agente Financiero**.
3. En la barra de búsqueda superior, busca **Gmail API** y haz clic en **Habilitar**.

### Paso 2.2: Configurar la Pantalla de Consentimiento OAuth
1. En el menú de navegación izquierdo, ve a **APIs y servicios** > **Pantalla de consentimiento de OAuth**.
2. Selecciona Tipo de usuario: **Externo** y haz clic en **Crear**.
3. Completa los datos obligatorios (Nombre de la aplicación, correo de soporte y contacto).
4. En el paso de **Permisos (Scopes)**, haz clic en **Agregar o quitar permisos** y añade el permiso:
   - `https://www.googleapis.com/auth/gmail.readonly` (Ver mensajes de correo electrónico y metadatos).
5. En la sección **Usuarios de prueba**, agrega la dirección de correo de Gmail desde la que se recibirán los estados de cuenta y correos financieros.
6. Haz clic en **Guardar y continuar**.

### Paso 2.3: Generar Credenciales OAuth (Cliente de Escritorio)
1. Ve al menú izquierdo: **Credenciales**.
2. Haz clic en **+ Crear credenciales** en la parte superior y selecciona **ID de cliente de OAuth**.
3. En Tipo de aplicación, selecciona **Aplicación de escritorio** (Desktop Application).
4. Dale un nombre identificativo (ej. `Agente Local`) y haz clic en **Crear**.
5. En la ventana emergente, haz clic en **Descargar JSON**. 
6. Cambia el nombre de este archivo a `credentials.json` y colócalo en el directorio raíz donde ejecutarás el agente financiero (`c:\Users\josem\Downloads\`).

---

## 3. AUTENTICACIÓN INICIAL Y EJECUCIÓN EN LIMA TIME

Toda la lógica de fechas del agente se procesa nativamente en la zona horaria de **Lima, Perú** (`America/Lima`). 

Al ejecutarse por primera vez la opción de Gmail, el agente buscará el archivo `credentials.json` e iniciará un servidor local para realizar la autenticación:

```bash
python agente_financiero.py --update
```

* **Comportamiento en Cloud Shell / Entorno Remoto**: Si estás en un servidor web o en la terminal donde no se puede abrir el navegador automáticamente, el agente imprimirá en la consola una URL de autenticación. Debes abrir esa URL en tu navegador local, iniciar sesión con tu cuenta de Gmail, dar los permisos del permiso `readonly` y, tras redirigirte, la API de Google guardará de forma automática el archivo `token.json` localmente.
* **Seguridad**: En ejecuciones futuras, el agente usará directamente `token.json` de manera silenciosa sin requerir interacción, hasta que el token expire o sea revocado.

---

## 4. APRENDIZAJE E IMPORTACIÓN DE ARCHIVOS LOCALES

El motor lee la carpeta `./datos_financieros/` y autodetecta la estructura.

### Estructuras Soportadas:
- **Hojas Tabulares (Excel / CSV)**: Escanea los encabezados buscando palabras clave relacionadas con la fecha, descripción, monto, tipo y categoría.
- **Documentos de Texto y PDFs (TXT / PDF)**: Analiza el documento línea por línea, identifica relaciones del tipo `Clave: Valor` (ej. `Monto: 179.10`) y aprende patrones dinámicos de extracción basados en expresiones regulares que escribe en `maestro_estructura.json`.

---

## 5. COMANDOS MANUALES Y GUÍA DE USO

### A. Aprender e Importar Archivos Locales Existentes
Analiza la estructura de los archivos de `./datos_financieros/` e importa sus movimientos en el presupuesto maestro:
```bash
python agente_financiero.py --learn
```
*Si deseas apuntar a otra carpeta en el disco, puedes especificarla:*
```bash
python agente_financiero.py --learn "C:\Ruta\A\Tus\Archivos"
```

### B. Revisar Nuevos Correos de Gmail
Busca correos sobre BCP o facturas recibidos en los últimos 7 días y actualiza la hoja de movimientos excluyendo los duplicados:
```bash
python agente_financiero.py --update
```

### C. Generar Reporte de Balance Financiero
Genera el informe consolidado en Excel junto con un gráfico analítico de Matplotlib integrado:
```bash
python agente_financiero.py --balance
```

---

## 6. GESTIÓN DE ERRORES Y BITÁCORAS
* **Correos no parseables**: Si un correo financiero tiene un formato extraño y no se puede extraer el monto o la fecha, el agente registrará de forma segura el asunto, remitente e ID de mensaje en `errores_parseo.log` y continuará con la ejecución de los demás elementos sin detenerse.
* **Logs Operacionales**: Cada paso del agente financiero se registra de forma cronológica en el archivo `agente_financiero.log` en el directorio de trabajo.
