@echo off
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%
echo [%date% %time%] Iniciando Sincronizacion de Estatus 12h... >> auditoria_log.txt
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" sincronizar_estatus_db.py >> auditoria_log.txt 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: La sincronizacion de estatus fallo. >> auditoria_log.txt
) else (
    echo [%date% %time%] EXITO: Sincronizacion de estatus completada. >> auditoria_log.txt
)
