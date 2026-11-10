import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def _get_database_uri():
    import socket
    from urllib.parse import urlparse

    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASSWORD', 'root')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'Gestion_parqueaderos')
    
    db_url = os.environ.get(
        'DATABASE_URL',
        f"postgresql+psycopg2://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
    )
    
    # Verificar si el driver psycopg2 está bloqueado por el sistema operativo
    try:
        import psycopg2  # noqa: F401
    except (ImportError, Exception):
        if 'psycopg2' in db_url:
            db_url = db_url.replace('postgresql+psycopg2://', 'postgresql+pg8000://')
        elif db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgresql+pg8000://')

    # Comprobar si PostgreSQL está activo en el puerto indicado.
    # Si este proyecto se clona en otra computadora que no tiene PostgreSQL instalado o encendido,
    # hace fallback automático y transparente a SQLite local para que NUNCA falle ni requiera configuración manual.
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 5432
        s = socket.create_connection((host, port), timeout=1.2)
        s.close()
    except Exception:
        # PostgreSQL no está disponible en este equipo, usar SQLite local
        base_dir = os.path.abspath(os.path.dirname(__file__))
        sqlite_path = os.path.join(base_dir, 'parkplus.db').replace('\\', '/')
        print(f"[*] PostgreSQL no detectado en {db_host}:{db_port}. Activando base de datos portátil SQLite: sqlite:///{sqlite_path}")
        return f"sqlite:///{sqlite_path}"
            
    return db_url

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_super_segura_parqueaderos_2026_xYz987!')
    
    # Parámetros de conexión a PostgreSQL
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'root')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'Gestion_parqueaderos')
    
    # URI de conexión para SQLAlchemy
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Correo / SMTP
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@gestionparqueaderos.com')
