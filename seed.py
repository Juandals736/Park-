from datetime import date, time, datetime, timedelta
from models import db, Usuario, Parqueadero, Reserva

def seed_all():
    # 1. Crear Usuarios de prueba si no existen
    usuarios_data = [
        {
            'email': 'admin@parqueaderos.com',
            'nombre': 'Carlos Rodríguez (Administrador General)',
            'password': 'Admin123!',
            'rol': 'admin',
            'telefono': '3001234567'
        },
        {
            'email': 'operador1@parqueaderos.com',
            'nombre': 'Laura Martínez (Operador Central)',
            'password': 'Operador123!',
            'rol': 'admin_parqueadero',
            'telefono': '3109876543'
        },
        {
            'email': 'operador2@parqueaderos.com',
            'nombre': 'Andrés Gómez (Operador Norte)',
            'password': 'Operador123!',
            'rol': 'admin_parqueadero',
            'telefono': '3156781234'
        },
        {
            'email': 'estudiante1@universidad.edu.co',
            'nombre': 'Mariana Silva Gómez',
            'password': 'Estudiante123!',
            'rol': 'estudiante',
            'telefono': '3204567890'
        },
        {
            'email': 'estudiante2@universidad.edu.co',
            'nombre': 'Juan Camilo Castro',
            'password': 'Estudiante123!',
            'rol': 'estudiante',
            'telefono': '3015556677'
        },
        {
            'email': 'estudiante3@universidad.edu.co',
            'nombre': 'Valentina Ríos Ospina',
            'password': 'Estudiante123!',
            'rol': 'estudiante',
            'telefono': '3182223344'
        }
    ]

    usuarios_dict = {}
    for u in usuarios_data:
        usuario = Usuario.query.filter_by(email=u['email']).first()
        if not usuario:
            usuario = Usuario(
                email=u['email'],
                nombre_completo=u['nombre'],
                rol=u['rol'],
                telefono=u['telefono'],
                activo=True
            )
            usuario.set_password(u['password'])
            db.session.add(usuario)
            db.session.flush()
        usuarios_dict[u['email']] = usuario

    db.session.commit()

    # 2. Crear Parqueaderos con coordenadas y detalles completos
    op1 = usuarios_dict.get('operador1@parqueaderos.com')
    op2 = usuarios_dict.get('operador2@parqueaderos.com')

    parqueaderos_data = [
        {
            'nombre': 'ParkMas Centro',
            'direccion': 'Carrera 24 # 18-42, Centro',
            'latitud': 1.195923,
            'longitud': -77.292206,
            'capacidad_total': 53,
            'espacios_ocupados': 15,
            'tipo_vehiculo': 'ambos',
            'tarifa_inicial': 1500.0,
            'tarifa_hora': 3500.0,
            'horario': '24 horas',
            'estado': 'disponible',
            'administrador_id': op1.id if op1 else None,
            'telefono_contacto': '6027230500',
            'descripcion': 'Parqueadero céntrico en Pasto con vigilancia continua y fácil acceso.'
        },
        {
            'nombre': 'Parqueadero Las Cuadras',
            'direccion': 'Calle 18 # 31-25, Las Cuadras',
            'latitud': 1.218896,
            'longitud': -77.296911,
            'capacidad_total': 44,
            'espacios_ocupados': 7,
            'tipo_vehiculo': 'ambos',
            'tarifa_inicial': 3000.0,
            'tarifa_hora': 2500.0,
            'horario': '24 horas',
            'estado': 'disponible',
            'administrador_id': op1.id if op1 else None,
            'telefono_contacto': '6027384984',
            'descripcion': 'Parqueadero en zona Las Cuadras, ideal para estudiantes y profesionales en Pasto.'
        },
        {
            'nombre': 'Parking Maridiaz',
            'direccion': 'Calle 17 # 33-18, Maridiaz',
            'latitud': 1.212623,
            'longitud': -77.289781,
            'capacidad_total': 77,
            'espacios_ocupados': 25,
            'tipo_vehiculo': 'ambos',
            'tarifa_inicial': 3000.0,
            'tarifa_hora': 2200.0,
            'horario': '06:30 - 23:00',
            'estado': 'disponible',
            'administrador_id': op2.id if op2 else None,
            'telefono_contacto': '6027876152',
            'descripcion': 'Ubicado en el sector Maridiaz de Pasto, con amplias bahías para carros y motos.'
        },
        {
            'nombre': 'ParkMas Pandiaco',
            'direccion': 'Calle 19A # 42-16, Pandiaco',
            'latitud': 1.197944,
            'longitud': -77.272679,
            'capacidad_total': 41,
            'espacios_ocupados': 9,
            'tipo_vehiculo': 'ambos',
            'tarifa_inicial': 2500.0,
            'tarifa_hora': 3500.0,
            'horario': '06:30 - 23:00',
            'estado': 'disponible',
            'administrador_id': op2.id if op2 else None,
            'telefono_contacto': '6027572623',
            'descripcion': 'Servicio de estacionamiento en el sector Pandiaco de Pasto con atención personalizada.'
        },
        {
            'nombre': 'Parqueadero Mijitayo',
            'direccion': 'Avenida Mijitayo # 15-60',
            'latitud': 1.203035,
            'longitud': -77.267726,
            'capacidad_total': 76,
            'espacios_ocupados': 20,
            'tipo_vehiculo': 'ambos',
            'tarifa_inicial': 2500.0,
            'tarifa_hora': 1800.0,
            'horario': '06:30 - 23:00',
            'estado': 'disponible',
            'administrador_id': op1.id if op1 else None,
            'telefono_contacto': '6027685142',
            'descripcion': 'Estacionamiento cómodo y seguro sobre la Avenida Mijitayo en Pasto.'
        }
    ]

    parqueaderos_dict = {}
    for p in parqueaderos_data:
        parq = Parqueadero.query.filter_by(nombre=p['nombre']).first()
        if not parq:
            parq = Parqueadero(**p)
            parq.actualizar_disponibilidad()
            db.session.add(parq)
            db.session.flush()
        parqueaderos_dict[p['nombre']] = parq

    db.session.commit()

    # 3. Crear Reservas de demostración
    est1 = usuarios_dict.get('estudiante1@universidad.edu.co')
    est2 = usuarios_dict.get('estudiante2@universidad.edu.co')
    est3 = usuarios_dict.get('estudiante3@universidad.edu.co')

    p_centro = parqueaderos_dict.get('ParkMas Centro') or Parqueadero.query.filter_by(nombre='ParkMas Centro').first()
    p_cuadras = parqueaderos_dict.get('Parqueadero Las Cuadras') or Parqueadero.query.filter_by(nombre='Parqueadero Las Cuadras').first()
    p_maridiaz = parqueaderos_dict.get('Parking Maridiaz') or Parqueadero.query.filter_by(nombre='Parking Maridiaz').first()

    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    manana = hoy + timedelta(days=1)

    reservas_data = [
        {
            'codigo_reserva': 'RES-948211',
            'estudiante_id': est1.id,
            'parqueadero_id': p_centro.id if p_centro else None,
            'fecha': hoy,
            'hora_inicio': time(8, 0),
            'hora_finalizacion': time(12, 30),
            'tipo_vehiculo': 'carro',
            'placa_vehiculo': 'KHM-452',
            'estado': 'activa',
            'costo_estimado': 16100.0
        },
        {
            'codigo_reserva': 'RES-738192',
            'estudiante_id': est2.id,
            'parqueadero_id': p_maridiaz.id if p_maridiaz else None,
            'fecha': hoy,
            'hora_inicio': time(9, 30),
            'hora_finalizacion': time(14, 0),
            'tipo_vehiculo': 'moto',
            'placa_vehiculo': 'QWR-88F',
            'estado': 'activa',
            'costo_estimado': 8550.0
        },
        {
            'codigo_reserva': 'RES-615243',
            'estudiante_id': est3.id,
            'parqueadero_id': p_cuadras.id if p_cuadras else None,
            'fecha': manana,
            'hora_inicio': time(7, 0),
            'hora_finalizacion': time(11, 0),
            'tipo_vehiculo': 'carro',
            'placa_vehiculo': 'BVT-109',
            'estado': 'activa',
            'costo_estimado': 16000.0
        },
        {
            'codigo_reserva': 'RES-554433',
            'estudiante_id': est1.id,
            'parqueadero_id': p_centro.id if p_centro else None,
            'fecha': ayer,
            'hora_inicio': time(14, 0),
            'hora_finalizacion': time(18, 0),
            'tipo_vehiculo': 'carro',
            'placa_vehiculo': 'KHM-452',
            'estado': 'completada',
            'costo_estimado': 14700.0
        },
        {
            'codigo_reserva': 'RES-112233',
            'estudiante_id': est2.id,
            'parqueadero_id': p_cuadras.id if p_cuadras else None,
            'fecha': ayer,
            'hora_inicio': time(10, 0),
            'hora_finalizacion': time(12, 0),
            'tipo_vehiculo': 'carro',
            'placa_vehiculo': 'TLX-391',
            'estado': 'cancelada',
            'costo_estimado': 9100.0
        }
    ]

    for r in reservas_data:
        res = Reserva.query.filter_by(codigo_reserva=r['codigo_reserva']).first()
        if not res:
            res = Reserva(**r)
            db.session.add(res)

    db.session.commit()
    print("Base de datos inicializada y poblada exitosamente.")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        db.create_all()
        seed_all()
