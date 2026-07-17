@echo off
REM ============================================================
REM CREAR PODER SIN LIMITES GLOBAL - AUTOMATIZACION
REM = : Script de ejecucion automatica para el Master Pipeline
REM ============================================================

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

echo [%date% %time%] Iniciando Pipeline Operativo... >> pipeline_log.txt
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" master_pipeline.py >> pipeline_log.txt 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: El pipeline fallo. Revisa pipeline_log.txt >> pipeline_log.txt
) else (
    echo [%date% %time%] EXITO: Pipeline completado satisfactoriamente. >> pipeline_log.txt
)
