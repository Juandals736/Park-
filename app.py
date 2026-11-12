from flask import Flask, redirect, url_for, render_template, send_from_directory, make_response, jsonify, request
from flask_login import LoginManager, current_user
from config import Config
from models import db, Usuario, Parqueadero

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    from flask_migrate import Migrate
    migrate = Migrate(app, db)
    # Scheduler para cancelar reservas pendientes expiradas
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        BackgroundScheduler = None
    from datetime import datetime, timezone
    from models import Reserva
    def cancelar_reservas_expiradas():
        with app.app_context():
            now_utc = datetime.now(timezone.utc)
            now_naive = datetime.utcnow()
            # Reservas pendientes cuyo tiempo expiró → cancelar automáticamente
            pendientes = Reserva.query.filter(
                Reserva.estado == 'pendiente',
                Reserva.expires_at.isnot(None)
            ).all()
            expiradas = []
            for r in pendientes:
                dt = r.expires_at
                is_expired = (dt <= now_utc) if dt.tzinfo else (dt <= now_naive)
                if is_expired:
                    expiradas.append(r)

            for r in expiradas:
                r.estado = 'cancelada'
                r.is_active = False
                # Liberar espacio si era para hoy
                from datetime import date
                if r.fecha == date.today() and r.parqueadero.espacios_ocupados > 0:
                    r.parqueadero.espacios_ocupados = max(0, r.parqueadero.espacios_ocupados - 1)
                    r.parqueadero.actualizar_disponibilidad()
                print(f"[Scheduler] Reserva {r.codigo_reserva} cancelada por tiempo expirado.")
            if expiradas:
                from models import db as _db
                _db.session.commit()
    if BackgroundScheduler:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=cancelar_reservas_expiradas, trigger='interval', seconds=30)
        scheduler.start()
    from flask_migrate import Migrate
    migrate = Migrate(app, db)

    # Registrar Blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.parking_admin import parking_admin_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(parking_admin_bp)
    app.register_blueprint(student_bp)

    @app.route('/')
    @app.route('/landing')
    def index():
        parqueaderos = []
        try:
            parqueaderos = Parqueadero.query.order_by(Parqueadero.nombre).all()
        except Exception as e:
            print("Aviso: no se pudieron cargar parqueaderos en landing:", e)
        return render_template('landing.html', parqueaderos=parqueaderos)

    @app.route('/dashboard')
    def dashboard_redirect():
        if current_user.is_authenticated:
            if current_user.rol == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.rol == 'admin_parqueadero':
                return redirect(url_for('parking_admin.dashboard'))
            else:
                return redirect(url_for('student.mapa'))
        return redirect(url_for('auth.login'))

    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('static', 'manifest.json', mimetype='application/json')

    @app.route('/sw.js')
    def service_worker():
        response = make_response(send_from_directory('static', 'sw.js'))
        response.headers['Content-Type'] = 'application/javascript'
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    @app.route('/api/public/parqueaderos')
    def api_public_parqueaderos():
        tipo_vehiculo = request.args.get('tipo', 'todos')
        try:
            query = Parqueadero.query
            if tipo_vehiculo in ['carro', 'moto']:
                query = query.filter((Parqueadero.tipo_vehiculo == tipo_vehiculo) | (Parqueadero.tipo_vehiculo == 'ambos'))
            parqueaderos = query.all()
            return jsonify([p.to_dict() for p in parqueaderos])
        except Exception as e:
            return jsonify([]), 200

    # Manejo de Errores HTTP
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Comandos CLI para base de datos
    @app.cli.command('init-db')
    def init_db_command():
        """Crea todas las tablas de la base de datos en PostgreSQL."""
        db.create_all()
        print("¡Tablas creadas exitosamente en PostgreSQL!")

    @app.cli.command('seed-db')
    def seed_db_command():
        """Puebla la base de datos con datos iniciales reales."""
        from seed import seed_all
        seed_all()
        print("¡Datos de prueba insertados con éxito!")

    # Auto-inicialización segura en caso de ejecutarse en otra máquina
    with app.app_context():
        try:
            db.create_all()
            if Parqueadero.query.first() is None:
                from seed import seed_all
                seed_all()
                print("[*] Base de datos auto-inicializada con parqueaderos y usuarios de prueba.")
        except Exception as e:
            print("[*] Verificación de base de datos:", e)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
