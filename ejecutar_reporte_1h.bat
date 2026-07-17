@echo off
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%
echo [%date% %time%] Iniciando extraccion de reporte de gestion de usuario (1h)... >> reporte_log.txt
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" reporte_gestion_equipos.py >> reporte_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: La extraccion del reporte fallo. >> reporte_log.txt
) else (
    echo [%date% %time%] EXITO: Reporte extraido correctamente. >> reporte_log.txt
)
