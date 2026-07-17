@echo off
chcp 65001 >nul
title [CRM] Servidor Torre de Control
echo ===================================================
echo   INICIANDO SERVIDOR WEB CRM — TORRE DE CONTROL
echo ===================================================
echo.
cd /d "C:\Users\josem\Downloads\bot-cpsl-review"
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" crm_web_server.py
echo.
echo [CRM] Servidor cerrado.
pause
