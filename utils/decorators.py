from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorador que verifica que el usuario autenticado tenga uno de los roles permitidos.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            # Normalización y sinónimos de roles (ej: datos masivos)
            role_aliases = {
                'administrador': 'admin',
                'conductor': 'estudiante',
                'operador': 'admin_parqueadero'
            }
            user_role = getattr(current_user, 'rol', '')
            norm_role = role_aliases.get(user_role, user_role)
            
            allowed = set(roles)
            for r in roles:
                if r == 'admin':
                    allowed.add('administrador')
                elif r == 'estudiante':
                    allowed.add('conductor')
                elif r == 'admin_parqueadero':
                    allowed.add('operador')

            if user_role not in allowed and norm_role not in allowed:
                flash('No tienes permisos suficientes para acceder a esta sección.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
