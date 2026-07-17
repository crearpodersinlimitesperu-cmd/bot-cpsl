@echo off
echo --- PREPARANDO REPOSITORIO PARA CLOUD ---
cd crear-poder-sin-limites-cloud
git init
git add .
git commit -m "feat: Initial cloud-native deployment with MacroDroid Gateway"

echo.
echo ======================================================
echo PASO 2: VINCULAR CON GITHUB
echo ======================================================
echo 1. Crea un repositorio PRIVADO en github.com con el nombre:
echo    crear-poder-sin-limites-cloud
echo.
echo 2. Copia la URL del repositorio (HTTPS) y pegala abajo.
echo    Ejemplo: https://github.com/tu-usuario/repo.git
echo.
set /p REPO_URL="URL del Repositorio: "

git remote add origin %REPO_URL%
git branch -M main
git push -u origin main

echo.
echo --- PROCESO COMPLETADO ---
echo Ahora ve a Render.com para conectar este repositorio.
pause
