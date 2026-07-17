@echo off
chcp 65001 >nul
cd /d "C:\Users\josem\Downloads\bot-cpsl-review"
"C:\Users\josem\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app_buscador.py --server.port 8515 > streamlit_output.log 2>&1
