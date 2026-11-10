@echo off
title Park+ - Servidor Local
chcp 65001 >nul
cls

echo ========================================================
echo           BIENVENIDO A PARK+ (SISTEMA DE PARQUEADEROS)
echo ========================================================
echo.

:: 1. Comprobar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no se encuentra en el PATH.
    echo Por favor descarga e instala Python desde: https://www.python.org/downloads/
    echo (Asegúrate de marcar la casilla "Add python.exe to PATH" durante la instalación).
    echo.
    pause
    exit /b
)

echo [*] Python detectado correctamente.

:: 2. Crear entorno virtual si no existe
if not exist "venv\Scripts\activate.bat" (
    echo [*] Creando entorno virtual (esto toma unos segundos)...
    python -m venv venv
)

:: 3. Activar entorno virtual
echo [*] Activando entorno virtual...
call .\venv\Scripts\activate.bat

:: 4. Instalar dependencias
echo [*] Verificando dependencias...
pip install -q -r requirements.txt

:: 5. Abrir navegador automáticamente
start "" http://localhost:5000

:: 6. Ejecutar servidor Flask
echo.
echo ========================================================
echo  ¡Park+ está listo y en ejecución!
echo  Dirección: http://localhost:5000
echo  Para detener el servidor presiona Ctrl + C
echo ========================================================
echo.

python app.py
pause

