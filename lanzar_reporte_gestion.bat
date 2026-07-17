@echo off
title IMO Report Generator - Teams 26-28
cd /d "C:\Users\josem\Downloads\bot-cpsl-review"
echo ===================================================
echo   IMO Report Generator - Teams 26-28
echo ===================================================
echo.
echo Selecciona el modo de ejecucion:
echo [1] Ejecutar una sola vez ahora
echo [2] Ejecutar en bucle continuo (cada 3 horas)
echo.
set /p opcion="Introduce tu opcion (1 o 2): "

if "%opcion%"=="1" (
    echo.
    echo Iniciando extraccion unica...
    "C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" reporte_gestion_equipos.py
) else if "%opcion%"=="2" (
    echo.
    echo Iniciando bucle continuo (ejecuta cada 3 horas)...
    "C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" reporte_gestion_equipos.py --loop
) else (
    echo Opcion invalida. Saliendo...
)
pause
