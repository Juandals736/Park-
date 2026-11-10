import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

logger = logging.getLogger('EmailService')
logging.basicConfig(level=logging.INFO)

# Memoria de últimos correos para facilitar desarrollo y depuración
DEV_OUTBOX = []

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_password_reset_token(email):
    """Genera un token seguro firmado con validez de 1 hora (3600s)."""
    s = get_serializer()
    return s.dumps(email, salt='password-reset-salt')

def verify_password_reset_token(token, expiration=3600):
    """Valida el token y retorna el email asociado o None si expiró o es inválido."""
    s = get_serializer()
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=expiration)
        return email
    except (SignatureExpired, BadSignature):
        return None

def send_password_reset_email(to_email, reset_url):
    """
    Envía el correo electrónico de restablecimiento de contraseña.
    Si hay credenciales SMTP configuradas en .env, lo envía directamente por internet al destinatario.
    """
    subject = "Recuperación de Contraseña - Park+"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #1e3a8a, #2563eb); padding: 30px 20px; text-align: center; color: #ffffff; }}
            .header h1 {{ margin: 0; font-size: 26px; font-weight: 800; }}
            .content {{ padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 15px; }}
            .btn-box {{ text-align: center; margin: 30px 0; }}
            .btn {{ background-color: #2563eb; color: #ffffff !important; padding: 13px 30px; text-decoration: none; border-radius: 8px; font-weight: 700; display: inline-block; box-shadow: 0 4px 12px rgba(37,99,235,0.3); }}
            .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 13px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            .link-text {{ word-break: break-all; color: #2563eb; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Park+</h1>
            </div>
            <div class="content">
                <p>Hola,</p>
                <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta asociada a <strong>{to_email}</strong>.</p>
                <p>Haz clic en el siguiente botón para continuar. Este enlace tiene una validez de <strong>1 hora</strong>:</p>
                <div class="btn-box">
                    <a href="{reset_url}" class="btn">Restablecer Mi Contraseña</a>
                </div>
                <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                <p class="link-text">{reset_url}</p>
                <p style="margin-top: 30px; font-size: 13px; color: #94a3b8;">Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura.</p>
            </div>
            <div class="footer">
                &copy; 2026 Park+ - Gestión Integral de Parqueaderos. Todos los derechos reservados.
            </div>
        </div>
    </body>
    </html>
    """

    mail_username = current_app.config.get('MAIL_USERNAME', '').strip()
    mail_password = current_app.config.get('MAIL_PASSWORD', '').strip().replace(' ', '')
    mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com').strip()
    mail_port = int(current_app.config.get('MAIL_PORT', 587))
    mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
    default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', '').strip()
    sender_email = mail_username if mail_username else (default_sender or 'noreply@parkplus.com')

    # Guardar en outbox de desarrollo
    DEV_OUTBOX.append({
        'to': to_email,
        'subject': subject,
        'url': reset_url
    })

    if not mail_username or not mail_password:
        logger.warning(f"No se han configurado credenciales de correo (MAIL_USERNAME / MAIL_PASSWORD en .env). Enlace generado: {reset_url}")
        return False, "NO_SMTP_CONFIGURED"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Park+ <{sender_email}>"
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        if mail_port == 465:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=12)
        else:
            server = smtplib.SMTP(mail_server, mail_port, timeout=12)
            if mail_use_tls:
                server.starttls()

        server.login(mail_username, mail_password)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()

        logger.info(f"Correo de recuperación enviado exitosamente a {to_email}")
        return True, "Correo enviado exitosamente."
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.error(f"Error de autenticación SMTP al enviar a {to_email}: {auth_err}")
        return False, "Credenciales SMTP inválidas. Si usas Gmail, asegúrate de activar la verificación en 2 pasos y generar una 'Contraseña de aplicación' de 16 letras, no tu contraseña habitual."
    except smtplib.SMTPConnectError as conn_err:
        logger.error(f"Error de conexión SMTP con {mail_server}:{mail_port}: {conn_err}")
        return False, f"No se pudo conectar al servidor de correo {mail_server}:{mail_port}."
    except Exception as e:
        logger.error(f"Error al enviar correo por SMTP a {to_email}: {e}")
        return False, str(e)
