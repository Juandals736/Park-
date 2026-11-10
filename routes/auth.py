from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from models import db, Usuario
from services.email_service import generate_password_reset_token, verify_password_reset_token, send_password_reset_email, DEV_OUTBOX

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash('Por favor ingresa tu correo y contraseña.', 'danger')
            return render_template('auth/login.html')

        user = Usuario.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Credenciales incorrectas. Verifica tu correo y contraseña.', 'danger')
            return render_template('auth/login.html')

        if not user.activo:
            flash('Esta cuenta se encuentra desactivada. Contacta al administrador.', 'warning')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'¡Bienvenido de nuevo, {user.nombre_completo}!', 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect_by_role(user)

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_by_role(current_user)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validaciones
        if not email or not nombre_completo or not password:
            flash('Todos los campos obligatorios deben ser completados.', 'danger')
            return render_template('auth/register.html')

        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError:
            flash('El correo electrónico ingresado no tiene un formato válido.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html')

        if Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado. Inicia sesión o recupera tu contraseña.', 'warning')
            return render_template('auth/register.html')

        # Crear nuevo usuario (rol estudiante por defecto en registro público)
        nuevo_usuario = Usuario(
            email=email,
            nombre_completo=nombre_completo,
            telefono=telefono,
            rol='estudiante',
            activo=True
        )
        nuevo_usuario.set_password(password)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('¡Registro exitoso! Ya puedes iniciar sesión con tu correo.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    dev_link = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Ingresa tu correo electrónico registrado.', 'danger')
            return render_template('auth/forgot_password.html')

        user = Usuario.query.filter_by(email=email).first()
        if user:
            token = generate_password_reset_token(user.email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            sent, msg = send_password_reset_email(user.email, reset_url)
            
            if sent:
                flash(f'¡Correo enviado exitosamente a {user.email}! Revisa tu bandeja de entrada o la carpeta de spam.', 'success')
            elif msg == "NO_SMTP_CONFIGURED":
                dev_link = reset_url
                flash('Para enviar correos reales por internet, debes colocar tu correo y Contraseña de Aplicación en las variables MAIL_USERNAME y MAIL_PASSWORD del archivo .env. Como aún no están configuradas, puedes usar el botón de acceso directo abajo:', 'warning')
            else:
                dev_link = reset_url
                flash(f'No se pudo enviar el correo por SMTP: {msg}. Puedes usar el botón de acceso directo abajo:', 'danger')
        else:
            flash(f"El correo '{email}' no se encuentra registrado en el sistema Park+. Por favor verifica la dirección o regístrate.", 'danger')

    return render_template('auth/forgot_password.html', dev_link=dev_link)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_password_reset_token(token)
    if not email:
        flash('El enlace de restablecimiento es inválido o ha expirado. Por favor solicita uno nuevo.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    user = Usuario.query.filter_by(email=email).first()
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('auth/reset_password.html', token=token, email=email)

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/reset_password.html', token=token, email=email)

        user.set_password(password)
        db.session.commit()

        flash('Tu contraseña ha sido actualizada con éxito. Ya puedes iniciar sesión con tu nueva clave.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token, email=email)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pwd = request.form.get('current_password', '')
        new_pwd = request.form.get('new_password', '')
        confirm_pwd = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pwd):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('auth/change_password.html')

        if len(new_pwd) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('auth/change_password.html')

        if new_pwd != confirm_pwd:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
            return render_template('auth/change_password.html')

        current_user.set_password(new_pwd)
        db.session.commit()
        flash('Contraseña cambiada exitosamente.', 'success')
        return redirect_by_role(current_user)

    return render_template('auth/change_password.html')


def redirect_by_role(user):
    if user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif user.is_parking_admin:
        return redirect(url_for('parking_admin.dashboard'))
    else:
        return redirect(url_for('student.mapa'))
