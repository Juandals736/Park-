#!/bin/bash

echo "========================================================"
echo "          BIENVENIDO A PARK+ (SISTEMA DE PARQUEADEROS)  "
echo "========================================================"
echo ""

# 1. Comprobar Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado."
    exit 1
fi

echo "[*] Python 3 detectado."

# 2. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "[*] Creando entorno virtual..."
    python3 -m venv venv
fi

# 3. Activar entorno virtual
source venv/bin/activate

# 4. Instalar dependencias
echo "[*] Verificando dependencias..."
pip install -q -r requirements.txt

# 5. Abrir navegador en segundo plano
if which xdg-open > /dev/null; then
    xdg-open http://localhost:5000 &
elif which open > /dev/null; then
    open http://localhost:5000 &
fi

# 6. Iniciar servidor
echo ""
echo "========================================================"
echo "  ¡Park+ está listo! Abre: http://localhost:5000"
echo "  Para detener el servidor presiona Ctrl + C"
echo "========================================================"
echo ""

python3 app.py

