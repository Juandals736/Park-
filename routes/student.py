from datetime import datetime, date, time, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Parqueadero, Reserva
from utils.decorators import role_required
import qrcode, os

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@login_required
def check_student_access():
    # Cualquier usuario logueado (incluidos admins) puede ver la vista de estudiante si lo desea
    pass

@student_bp.route('/')
@student_bp.route('/mapa')
def mapa():
    parqueaderos = Parqueadero.query.order_by(Parqueadero.nombre).all()
    return render_template('student/mapa.html', parqueaderos=parqueaderos)

@student_bp.route('/api/parqueaderos')
def api_parqueaderos():
    tipo_vehiculo = request.args.get('tipo', 'todos')
    solo_disponibles = request.args.get('disponibles', 'false').lower() == 'true'

    query = Parqueadero.query

    if tipo_vehiculo in ['carro', 'moto']:
        query = query.filter((Parqueadero.tipo_vehiculo == tipo_vehiculo) | (Parqueadero.tipo_vehiculo == 'ambos'))

    if solo_disponibles:
        query = query.filter(Parqueadero.estado.in_(['disponible', 'casi_lleno']), Parqueadero.espacios_disponibles > 0)

    parqueaderos = query.all()
    return jsonify([p.to_dict() for p in parqueaderos])

@student_bp.route('/reservas/crear', methods=['POST'])
def crear_reserva():
    parqueadero_id = int(request.form.get('parqueadero_id'))
    fecha_str = request.form.get('fecha')
    hora_inicio_str = request.form.get('hora_inicio')
    hora_fin_str = request.form.get('hora_finalizacion')
    tipo_vehiculo = request.form.get('tipo_vehiculo', 'carro')
    placa = request.form.get('placa_vehiculo', '').strip().upper()
    notas = request.form.get('notas', '').strip()

    parqueadero = Parqueadero.query.get_or_404(parqueadero_id)

    # Validaciones
    if parqueadero.estado == 'cerrado':
        flash('El parqueadero seleccionado se encuentra cerrado actualmente.', 'danger')
        return redirect(url_for('student.mapa'))

    if parqueadero.espacios_disponibles <= 0:
        flash('El parqueadero no tiene cupos disponibles en este momento.', 'danger')
        return redirect(url_for('student.mapa'))

    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        hora_ini_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
        hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time()
    except ValueError:
        flash('Formato de fecha u hora incorrecto.', 'danger')
        return redirect(url_for('student.mapa'))

    if fecha_obj < date.today():
        flash('La fecha de la reserva no puede ser anterior al día de hoy.', 'danger')
        return redirect(url_for('student.mapa'))

    if hora_fin_obj <= hora_ini_obj:
        flash('La hora de finalización debe ser posterior a la hora de inicio.', 'danger')
        return redirect(url_for('student.mapa'))

    # Calcular costo estimado
    duracion_horas = max(1.0, (datetime.combine(date.min, hora_fin_obj) - datetime.combine(date.min, hora_ini_obj)).total_seconds() / 3600.0)
    costo_estimado = float(parqueadero.tarifa_inicial) + (duracion_horas * float(parqueadero.tarifa_hora))

    nueva_reserva = Reserva(
        estudiante_id=current_user.id,
        parqueadero_id=parqueadero.id,
        fecha=fecha_obj,
        hora_inicio=hora_ini_obj,
        hora_finalizacion=hora_fin_obj,
        tipo_vehiculo=tipo_vehiculo,
        placa_vehiculo=placa,
        # nuevos campos
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        is_active=False,
        payment_status='pending',
        estado='pendiente',
        notas=notas,
        costo_estimado=costo_estimado
    )

    # Si la reserva es para hoy, descontar un espacio disponible en tiempo real
    if fecha_obj == date.today():
        parqueadero.espacios_ocupados = min(parqueadero.capacidad_total, parqueadero.espacios_ocupados + 1)
        parqueadero.actualizar_disponibilidad()

    db.session.add(nueva_reserva)
    db.session.commit()

    flash(f'¡Reserva confirmada con éxito! Código: {nueva_reserva.codigo_reserva}', 'success')
    return redirect(url_for('student.mis_reservas'))

@student_bp.route('/mis-reservas')
def mis_reservas():
    filtro_estado = request.args.get('estado', '')
    query = Reserva.query.filter_by(estudiante_id=current_user.id)

    if filtro_estado in ['activa', 'completada', 'cancelada', 'pendiente']:
        query = query.filter_by(estado=filtro_estado)

    reservas = query.order_by(Reserva.fecha.desc(), Reserva.hora_inicio.desc()).all()
    return render_template('student/mis_reservas.html', reservas=reservas, filtro_estado=filtro_estado)

# Detalle de reserva con QR y temporizador
@student_bp.route('/reservas/<int:id>/detalle')
def detalle_reserva(id):
    reserva = Reserva.query.filter_by(id=id, estudiante_id=current_user.id).first_or_404()
    qr_dir = os.path.join('static', 'qrcodes')
    qr_filename = f"{reserva.codigo_reserva}.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    full_qr_path = os.path.join('C:\\Users\\RYZEN\\Desktop\\Gestion-parqueaderos', qr_path)
    if not os.path.isfile(full_qr_path):
        os.makedirs(os.path.dirname(full_qr_path), exist_ok=True)
        img = qrcode.make(reserva.codigo_reserva)
        img.save(full_qr_path)
    return render_template('student/reserva_detalle.html', reserva=reserva, qr_path='/' + qr_path.replace('\\\\', '/'))

@student_bp.route('/reservas/<int:id>/cancelar', methods=['POST'])
def cancelar_reserva(id):
    reserva = Reserva.query.filter_by(id=id, estudiante_id=current_user.id).first_or_404()

    if reserva.estado not in ('activa', 'pendiente'):
        flash('Solo puedes cancelar reservas activas o pendientes.', 'warning')
        return redirect(url_for('student.mis_reservas'))

    reserva.estado = 'cancelada'
    
    # Liberar espacio en el parqueadero si era para hoy
    if reserva.fecha == date.today() and reserva.parqueadero.espacios_ocupados > 0:
        reserva.parqueadero.espacios_ocupados = max(0, reserva.parqueadero.espacios_ocupados - 1)
        reserva.parqueadero.actualizar_disponibilidad()

    db.session.commit()
    flash(f'La reserva {reserva.codigo_reserva} ha sido cancelada exitosamente.', 'info')
    return redirect(url_for('student.mis_reservas'))
