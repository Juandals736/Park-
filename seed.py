import os
import json
from datetime import date, time, datetime
from models import db, Usuario, Parqueadero, Reserva

def parse_date(d_str):
    if not d_str:
        return None
    return datetime.fromisoformat(d_str).date() if 'T' in d_str or len(d_str) > 10 else date.fromisoformat(d_str)

def parse_time(t_str):
    if not t_str:
        return None
    parts = t_str.split(':')
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

def parse_datetime(dt_str):
    if not dt_str:
        return datetime.utcnow()
    return datetime.fromisoformat(dt_str)

def seed_all():
    """
    Importa la base de datos completa exacta (63 usuarios, 25 parqueaderos y 184 reservas)
    desde data_backup.json para que Render o cualquier máquina tenga exactamente la BD de pgAdmin.
    """
    backup_file = os.path.join(os.path.dirname(__file__), 'data_backup.json')
    if not os.path.exists(backup_file):
        print(f"[*] Archivo {backup_file} no encontrado.")
        return

    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Importar Usuarios
    usuarios_data = data.get('usuarios', [])
    for u in usuarios_data:
        usuario = Usuario.query.filter_by(id=u['id']).first() or Usuario.query.filter_by(email=u['email']).first()
        if not usuario:
            usuario = Usuario(
                id=u['id'],
                email=u['email'],
                nombre_completo=u['nombre_completo'],
                password_hash=u['password_hash'],
                rol=u['rol'],
                telefono=u.get('telefono'),
                activo=u.get('activo', True),
                fecha_registro=parse_datetime(u.get('fecha_registro'))
            )
            db.session.add(usuario)
        else:
            usuario.password_hash = u['password_hash']
            usuario.rol = u['rol']
            usuario.nombre_completo = u['nombre_completo']

    db.session.commit()

    # 2. Importar Parqueaderos
    parqueaderos_data = data.get('parqueaderos', [])
    for p in parqueaderos_data:
        parqueadero = Parqueadero.query.filter_by(id=p['id']).first()
        if not parqueadero:
            parqueadero = Parqueadero(
                id=p['id'],
                nombre=p['nombre'],
                direccion=p['direccion'],
                latitud=p['latitud'],
                longitud=p['longitud'],
                capacidad_total=p['capacidad_total'],
                espacios_ocupados=p['espacios_ocupados'],
                espacios_disponibles=p['espacios_disponibles'],
                tipo_vehiculo=p['tipo_vehiculo'],
                tarifa_inicial=p['tarifa_inicial'],
                tarifa_hora=p['tarifa_hora'],
                horario=p['horario'],
                estado=p['estado'],
                administrador_id=p.get('administrador_id'),
                descripcion=p.get('descripcion'),
                telefono_contacto=p.get('telefono_contacto'),
                fecha_creacion=parse_datetime(p.get('fecha_creacion'))
            )
            db.session.add(parqueadero)

    db.session.commit()

    # 3. Importar Reservas
    reservas_data = data.get('reservas', [])
    for r in reservas_data:
        reserva = Reserva.query.filter_by(codigo_reserva=r['codigo_reserva']).first()
        if not reserva:
            reserva = Reserva(
                id=r['id'],
                codigo_reserva=r['codigo_reserva'],
                estudiante_id=r['estudiante_id'],
                parqueadero_id=r['parqueadero_id'],
                fecha=parse_date(r['fecha']),
                hora_inicio=parse_time(r['hora_inicio']),
                hora_finalizacion=parse_time(r['hora_finalizacion']),
                tipo_vehiculo=r.get('tipo_vehiculo', 'carro'),
                placa_vehiculo=r.get('placa_vehiculo'),
                estado=r.get('estado', 'activa'),
                notas=r.get('notas'),
                costo_estimado=r.get('costo_estimado', 0.0),
                fecha_creacion=parse_datetime(r.get('fecha_creacion'))
            )
            db.session.add(reserva)

    db.session.commit()

    # 4. Ajustar secuencias en PostgreSQL si aplica
    try:
        if 'postgresql' in str(db.engine.url):
            db.session.execute(db.text("SELECT setval(pg_get_serial_sequence('usuarios', 'id'), coalesce(max(id), 1)) FROM usuarios;"))
            db.session.execute(db.text("SELECT setval(pg_get_serial_sequence('parqueaderos', 'id'), coalesce(max(id), 1)) FROM parqueaderos;"))
            db.session.execute(db.text("SELECT setval(pg_get_serial_sequence('reservas', 'id'), coalesce(max(id), 1)) FROM reservas;"))
            db.session.commit()
    except Exception as e:
        print("[*] Ajuste de secuencias (SQLite/PostgreSQL):", e)

    print(f"¡Base de datos restaurada con éxito: {len(usuarios_data)} usuarios, {len(parqueaderos_data)} parqueaderos, {len(reservas_data)} reservas!")
