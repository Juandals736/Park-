# Park+ 🚗🅿️ - Sistema Integral de Gestión y Reserva de Parqueaderos

**Park+** es una aplicación web y PWA (*Progressive Web App*) moderna desarrollada con **Python (Flask)** y **PostgreSQL** para la búsqueda, visualización y reserva de cupos de estacionamiento en tiempo real, con geolocalización GPS y cálculo de rutas callejeras sin redireccionar a plataformas externas.

---

## 🌟 Características Principales

- **Landing Page Moderna**: Diseño interactivo, responsivo con orbes de luz animados y presentación concisa del servicio.
- **Mapa en Tiempo Real (Leaflet & OpenStreetMap)**: Visualización dinámica de disponibilidad de parqueaderos con pines codificados por color según ocupación (disponible, casi lleno, lleno, cerrado).
- **Ruta Inteligente ("Cómo llegar")**: Cálculo y trazado de rutas vehiculares en vivo sobre el mapa mediante OSRM (*Open Source Routing Machine*) indicando distancia en kilómetros y minutos estimados de llegada, sin salir de la plataforma.
- **Geolocalización GPS del Dispositivo**: Detección de ubicación con ordenamiento automático de parqueaderos por proximidad.
- **Sistema de Reservas**: Permite a los usuarios seleccionar fecha, hora de entrada, hora de salida y tipo de vehículo (carro o moto).
- **Gestión de Roles**:
  - **Estudiante / Conductor**: Búsqueda en mapa, reservas y consulta de historial.
  - **Operador de Parqueadero**: Monitoreo de cupos y control de acceso.
  - **Administrador General**: Panel global de estadísticas, tarifas y usuarios.
- **Autenticación y Seguridad**: Contraseñas encriptadas con bcrypt, protección CSRF y recuperación de contraseña segura vía token firmado por correo SMTP (Gmail).
- **Instalable en Móvil (PWA)**: Compatible con Android e iOS sin necesidad de tiendas de aplicaciones pesadas.

---

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, ItsDangerous, Werkzeug.
- **Base de Datos**: PostgreSQL (con soporte para `psycopg2` y driver puro `pg8000`).
- **Frontend**: HTML5 Semántico, CSS3 Moderno (Variables CSS, Flexbox/Grid, Animaciones), JavaScript vanilla (ES6+).
- **Mapas y Navegación**: Leaflet.js, OpenStreetMap, OSRM API.
- **PWA**: Service Workers y Web App Manifest.

---

## 🚀 Ejecución en Cualquier Computadora (1 Clic)

El proyecto cuenta con detección automática de base de datos y scripts de inicio rápido para que funcione en **cualquier PC sin configuraciones complejas**:

### En Windows:
1. Clona o descarga el proyecto en la otra computadora.
2. Haz **doble clic en el archivo `iniciar.bat`**.
3. El script creará el entorno virtual, instalará las dependencias y abrirá automáticamente tu navegador en `http://localhost:5000`.

### En Linux / macOS:
```bash
chmod +x iniciar.sh
./iniciar.sh
```

> [!NOTE]
> **Base de Datos Inteligente y Portátil**:
> Si el equipo donde se ejecuta tiene PostgreSQL encendido, se conectará a PostgreSQL automáticamente.
> Si el otro equipo **no tiene PostgreSQL instalado**, el sistema cambiará de forma automática a una base de datos local SQLite y auto-poblará los 25 parqueaderos y usuarios de prueba. ¡El proyecto funcionará siempre en cualquier máquina!

---

## 📦 Instalación Manual Paso a Paso

Si prefieres ejecutar los comandos manualmente en terminal:

### 1. Clonar el Repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd Gestion-parqueaderos
```

### 2. Crear y Activar Entorno Virtual
```powershell
# Windows:
python -m venv venv
.\venv\Scripts\activate

# Linux / Mac:
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno (Opcional)
Si deseas conectar tu propio PostgreSQL o Gmail SMTP, copia `.env.example` a `.env`:
```bash
copy .env.example .env     # En Windows
cp .env.example .env       # En Linux/Mac
```

### 5. Iniciar la Aplicación
```bash
python app.py
```
Abre tu navegador en: **`http://localhost:5000`**

---

## ☁️ Despliegue Gratuito en la Nube (Render)

Si quieres compartir la aplicación con cualquier persona por internet (sin necesidad de que tengan Python o que tú tengas encendida tu PC):

1. Sube tu proyecto a un repositorio en **GitHub**.
2. Entra a [render.com](https://render.com/) e inicia sesión con tu cuenta de GitHub.
3. Haz clic en **New +** > **Web Service**.
4. Conecta tu repositorio de Park+.
5. Configura:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Haz clic en **Create Web Service**. ¡En 2 minutos tendrás una URL pública para abrirla desde cualquier computadora o celular!

---

## 👥 Usuarios de Prueba Predeterminados

| Rol | Correo Electrónico | Contraseña |
| :--- | :--- | :--- |
| **Administrador General** | `admin@parqueaderos.com` | `Admin123!` |
| **Operador de Parqueadero** | `operador1@parqueaderos.com` | `Operador123!` |
| **Estudiante / Conductor** | `estudiante1@universidad.edu.co` | `Estudiante123!` |

---

## 📄 Licencia

Este proyecto fue desarrollado con fines académicos y de gestión integral de movilidad urbana. Distribuido bajo la Licencia MIT.

