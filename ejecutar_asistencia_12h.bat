@echo off
chcp 65001 >nul
echo [%date% %time%] Ejecutando scraper de asistencia REAL E28...
cd /d "C:\Users\josem\Downloads\bot-cpsl-review"
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" scraper_asistencia_real_e28.py >> reporte_asistencia_e28.log 2>&1
echo [%date% %time%] Scraper completado.

