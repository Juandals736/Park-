from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Parqueadero, Reserva
from utils.decorators import role_required

parking_admin_bp = Blueprint('parking_admin', __name__, url_prefix='/parking-admin')

@parking_admin_bp.before_request
@login_required
@role_required('admin_parqueadero', 'admin')
def check_parking_admin_access():
    pass

def get_operador_parqueadero():
    """Retorna el único parqueadero vinculado al operador actual."""
    parqueadero = Parqueadero.query.filter_by(administrador_id=current_user.id).first()
    if not parqueadero and current_user.is_admin:
        parqueadero = Parqueadero.query.first()
    return parqueadero

@parking_admin_bp.route('/')
@parking_admin_bp.route('/dashboard')
def dashboard():
    p = get_operador_parqueadero()
    if not p:
        flash('No tienes ningún parqueadero asignado a tu cuenta de operador.', 'warning')
        return render_template('parking_admin/sin_parqueadero.html')

    capacidad_total = p.capacidad_total
    espacios_ocupados = p.espacios_ocupados
    espacios_disponibles = p.espacios_disponibles

    # Reservas exclusivas de este único parqueadero
    reservas_query = Reserva.query.filter_by(parqueadero_id=p.id)
    total_reservas = reservas_query.count()
    reservas_pendientes = reservas_query.filter_by(estado='pendiente').count()
    reservas_activas = reservas_query.filter_by(estado='activa').count()
    reservas_hoy = reservas_query.filter(Reserva.fecha == date.today()).count()

    return render_template(
        'parking_admin/dashboard.html',
        parqueadero=p,
        total_parqueaderos=1,
        capacidad_total=capacidad_total,
        espacios_ocupados=espacios_ocupados,
        espacios_disponibles=espacios_disponibles,
        total_reservas=total_reservas,
        reservas_pendientes=reservas_pendientes,
        reservas_activas=reservas_activas,
        reservas_hoy=reservas_hoy
    )

@parking_admin_bp.route('/api/stats')
def api_stats():
    """Endpoint con métricas y gráficos exclusivos del parqueadero del operador."""
    p = get_operador_parqueadero()
    if not p:
        return jsonify({
            'parqueaderos': {'categorias': [], 'ocupados': [], 'disponibles': []},
            'estados': [],
            'tendencia': {'dias': [], 'conteos': []}
        })

    # 1. Gráfico de Capacidad vs Ocupación del Parqueadero
    categorias_nombres = [p.nombre]
    datos_ocupados = [p.espacios_ocupados]
    datos_disponibles = [p.espacios_disponibles]

    # 2. Gráfico de Reservas por Estado
    estados_conteo = db.session.query(
        Reserva.estado, func.count(Reserva.id)
    ).filter(
        Reserva.parqueadero_id == p.id
    ).group_by(Reserva.estado).all()

    datos_estados = []
    color_map = {
        'pendiente': '#f59e0b',
        'activa': '#10b981',
        'completada': '#2563eb',
        'cancelada': '#ef4444'
    }
    for est, cnt in estados_conteo:
        datos_estados.append({
            'name': est.capitalize(),
            'y': cnt,
            'color': color_map.get(est, '#94a3b8')
        })

    # 3. Tendencia de Reservas últimos 7 días
    hoy = date.today()
    ultimos_dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
    dias_labels = [d.strftime('%a %d') for d in ultimos_dias]
    
    reservas_por_dia = []
    for d in ultimos_dias:
        cnt = db.session.query(func.count(Reserva.id)).filter(
            Reserva.parqueadero_id == p.id,
            Reserva.fecha == d
        ).scalar() or 0
        reservas_por_dia.append(cnt)

    return jsonify({
        'parqueaderos': {
            'categorias': categorias_nombres,
            'ocupados': datos_ocupados,
            'disponibles': datos_disponibles
        },
        'estados': datos_estados,
        'tendencia': {
            'dias': dias_labels,
            'conteos': reservas_por_dia
        }
    })

@parking_admin_bp.route('/parqueaderos')
def parqueaderos():
    p = get_operador_parqueadero()
    parqueaderos_lista = [p] if p else []
    return render_template('parking_admin/parqueaderos.html', parqueaderos=parqueaderos_lista, parqueadero=p)

@parking_admin_bp.route('/parqueaderos/<int:id>/actualizar-ocupacion', methods=['POST'])
def actualizar_ocupacion(id):
    p = get_operador_parqueadero()
    if not p or p.id != id:
        return jsonify({'error': 'No autorizado para este parqueadero'}), 403

    cambio = request.form.get('cambio')
    if cambio == '+1':
        p.espacios_ocupados = min(p.capacidad_total, p.espacios_ocupados + 1)
    elif cambio == '-1':
        p.espacios_ocupados = max(0, p.espacios_ocupados - 1)
    else:
        nuevo_valor = request.form.get('espacios_ocupados')
        if nuevo_valor is not None:
            p.espacios_ocupados = max(0, min(p.capacidad_total, int(nuevo_valor)))

    p.actualizar_disponibilidad()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            'success': True,
            'espacios_ocupados': p.espacios_ocupados,
            'espacios_disponibles': p.espacios_disponibles,
            'porcentaje_ocupacion': p.porcentaje_ocupacion,
            'estado': p.estado
        })

    flash(f'Ocupación de "{p.nombre}" actualizada.', 'success')
    return redirect(url_for('parking_admin.parqueaderos'))

@parking_admin_bp.route('/parqueaderos/<int:id>/editar-info', methods=['POST'])
def editar_info(id):
    p = get_operador_parqueadero()
    if not p or p.id != id:
        flash('No autorizado para modificar este parqueadero.', 'danger')
        return redirect(url_for('parking_admin.parqueaderos'))

    p.capacidad_total = int(request.form.get('capacidad_total', p.capacidad_total))
    p.espacios_ocupados = int(request.form.get('espacios_ocupados', p.espacios_ocupados))
    p.horario = request.form.get('horario', p.horario).strip()
    p.tarifa_inicial = float(request.form.get('tarifa_inicial', p.tarifa_inicial))
    p.tarifa_hora = float(request.form.get('tarifa_hora', p.tarifa_hora))
    p.estado = request.form.get('estado', p.estado)
    p.tipo_vehiculo = request.form.get('tipo_vehiculo', p.tipo_vehiculo)
    
    p.actualizar_disponibilidad()
    db.session.commit()

    flash(f'Información de "{p.nombre}" actualizada con éxito.', 'success')
    return redirect(url_for('parking_admin.parqueaderos'))

@parking_admin_bp.route('/reservas')
def reservas():
    p = get_operador_parqueadero()
    if not p:
        flash('No tienes ningún parqueadero asignado.', 'warning')
        return redirect(url_for('parking_admin.dashboard'))

    estado_filtro = request.args.get('estado', '')

    # Consultar estrictamente las reservas de SU parqueadero
    reservas_q = Reserva.query.filter_by(parqueadero_id=p.id)

    if estado_filtro:
        reservas_q = reservas_q.filter_by(estado=estado_filtro)

    reservas_list = reservas_q.order_by(Reserva.fecha.desc(), Reserva.hora_inicio.desc()).all()

    return render_template(
        'parking_admin/reservas.html',
        reservas=reservas_list,
        parqueadero=p,
        estado_filtro=estado_filtro
    )

@parking_admin_bp.route('/reservas/<int:id>/cambiar-estado', methods=['POST'])
def cambiar_estado_reserva(id):
    p = get_operador_parqueadero()
    reserva = Reserva.query.filter_by(id=id, parqueadero_id=p.id).first_or_404()
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ['pendiente', 'activa', 'completada', 'cancelada']:
        reserva.estado = nuevo_estado
        if nuevo_estado in ['activa', 'completada']:
            reserva.is_active = True
        elif nuevo_estado == 'cancelada':
            reserva.is_active = False
            if reserva.fecha == date.today() and p.espacios_ocupados > 0:
                p.espacios_ocupados = max(0, p.espacios_ocupados - 1)
                p.actualizar_disponibilidad()
        db.session.commit()
        flash(f'Reserva {reserva.codigo_reserva} marcada como {nuevo_estado}.', 'success')
    return redirect(url_for('parking_admin.reservas'))


# ─── Escáner QR ────────────────────────────────────────────────────────────────

@parking_admin_bp.route('/escanear-qr')
def escanear_qr():
    """Página con cámara para escanear el QR de una reserva del parqueadero."""
    p = get_operador_parqueadero()
    return render_template('parking_admin/escanear_qr.html', parqueadero=p)


@parking_admin_bp.route('/api/validar-qr', methods=['POST'])
def validar_qr():
    """Recibe el código escaneado y valida si pertenece al parqueadero del operador."""
    p = get_operador_parqueadero()
    if not p:
        return jsonify({'ok': False, 'mensaje': 'No tienes parqueadero asignado.'}), 403

    data = request.get_json(force=True)
    codigo = (data.get('codigo') or '').strip().upper()

    if not codigo:
        return jsonify({'ok': False, 'mensaje': 'Código de reserva vacío.'}), 400

    reserva = Reserva.query.filter_by(codigo_reserva=codigo).first()
    if not reserva:
        return jsonify({'ok': False, 'mensaje': f'No existe ninguna reserva con el código {codigo}.'}), 404

    # Validar que la reserva pertenezca al parqueadero de este operador
    if reserva.parqueadero_id != p.id:
        return jsonify({
            'ok': False,
            'mensaje': f'⚠️ Esta reserva pertenece a "{reserva.parqueadero.nombre}". Tu parqueadero es "{p.nombre}".'
        }), 403

    if reserva.estado == 'completada':
        return jsonify({'ok': False, 'mensaje': f'La reserva {reserva.codigo_reserva} ya fue completada anteriormente.'})

    if reserva.estado == 'cancelada':
        return jsonify({'ok': False, 'mensaje': f'La reserva {reserva.codigo_reserva} fue cancelada o expiró el temporizador de 15 minutos.'})

    # Marcar como activa y completada al validar la llegada
    reserva.is_active = True
    reserva.estado = 'completada'
    db.session.commit()

    return jsonify({
        'ok': True,
        'mensaje': f'✅ Reserva {reserva.codigo_reserva} validada y completada con éxito en {p.nombre}.',
        'estudiante': reserva.estudiante.nombre_completo,
        'parqueadero': p.nombre,
        'vehiculo': f"{reserva.tipo_vehiculo.capitalize()} ({reserva.placa_vehiculo or 'S/P'})",
        'fecha': reserva.fecha.strftime('%d/%m/%Y'),
        'horario': f"{reserva.hora_inicio.strftime('%H:%M')} - {reserva.hora_finalizacion.strftime('%H:%M')}"
    })
