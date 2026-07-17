@echo off
title CREAR GLOBAL - Enterprise Web CRM
color 0F

echo Iniciando entorno operativo de CREAR GLOBAL (Modo Web)...
echo Verificando dependencias y levantando servidor...

:: Configurar PYTHONPATH al directorio actual
set PYTHONPATH=%cd%

:: Iniciar el servidor de Flask en segundo plano (start /B o start para abrir en consola separada, mejor en consola para ver logs si falla)
start "CREAR CRM Backend" cmd /k ""C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" crm_web_server.py"

:: Esperar 3 segundos para asegurar que el servidor levantó
timeout /t 3 /nobreak > NUL

:: Abrir el navegador predeterminado en la dirección del dashboard
echo Abriendo Interfaz Visual en el navegador...
start http://127.0.0.1:5000/

:: Salir de esta ventana negra, el backend queda en la otra ventana o en segundo plano
exit
