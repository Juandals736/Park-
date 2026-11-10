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

def get_admin_parqueaderos_query():
    """Retorna los parqueaderos asignados al operador o todos si es admin general o no tiene asignación específica."""
    if current_user.is_admin:
        return Parqueadero.query
    parqueaderos = Parqueadero.query.filter_by(administrador_id=current_user.id)
    if parqueaderos.count() == 0:
        # Si no tiene asignado específicamente, permitir gestionar todos los parqueaderos en el sistema
        return Parqueadero.query
    return parqueaderos

@parking_admin_bp.route('/')
@parking_admin_bp.route('/dashboard')
def dashboard():
    query = get_admin_parqueaderos_query()
    parqueaderos = query.all()
    parqueadero_ids = [p.id for p in parqueaderos]

    total_parqueaderos = len(parqueaderos)
    capacidad_total = sum(p.capacidad_total for p in parqueaderos)
    espacios_ocupados = sum(p.espacios_ocupados for p in parqueaderos)
    espacios_disponibles = max(0, capacidad_total - espacios_ocupados)

    # Reservas de estos parqueaderos
    reservas_query = Reserva.query.filter(Reserva.parqueadero_id.in_(parqueadero_ids)) if parqueadero_ids else Reserva.query.filter_by(id=-1)
    total_reservas = reservas_query.count()
    reservas_activas = reservas_query.filter_by(estado='activa').count()
    reservas_hoy = reservas_query.filter(Reserva.fecha == date.today()).count()

    return render_template(
        'parking_admin/dashboard.html',
        parqueaderos=parqueaderos,
        total_parqueaderos=total_parqueaderos,
        capacidad_total=capacidad_total,
        espacios_ocupados=espacios_ocupados,
        espacios_disponibles=espacios_disponibles,
        total_reservas=total_reservas,
        reservas_activas=reservas_activas,
        reservas_hoy=reservas_hoy
    )

@parking_admin_bp.route('/api/stats')
def api_stats():
    """Endpoint que suministra los datos estructurados para los gráficos Highcharts."""
    query = get_admin_parqueaderos_query()
    parqueaderos = query.all()
    parqueadero_ids = [p.id for p in parqueaderos]

    # 1. Gráfico de Capacidad vs Ocupación por Parqueadero
    categorias_nombres = [p.nombre for p in parqueaderos]
    datos_ocupados = [p.espacios_ocupados for p in parqueaderos]
    datos_disponibles = [p.espacios_disponibles for p in parqueaderos]

    # 2. Gráfico de Reservas por Estado
    estados_conteo = db.session.query(
        Reserva.estado, func.count(Reserva.id)
    ).filter(
        Reserva.parqueadero_id.in_(parqueadero_ids) if parqueadero_ids else False
    ).group_by(Reserva.estado).all()

    datos_estados = []
    color_map = {
        'activa': '#10b981',      # Verde
        'completada': '#2563eb',  # Azul
        'cancelada': '#ef4444'    # Rojo
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
            Reserva.parqueadero_id.in_(parqueadero_ids) if parqueadero_ids else False,
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
    query = get_admin_parqueaderos_query()
    parqueaderos = query.all()
    return render_template('parking_admin/parqueaderos.html', parqueaderos=parqueaderos)

@parking_admin_bp.route('/parqueaderos/<int:id>/actualizar-ocupacion', methods=['POST'])
def actualizar_ocupacion(id):
    query = get_admin_parqueaderos_query()
    p = query.filter_by(id=id).first_or_404()

    cambio = request.form.get('cambio') # '+1', '-1' o valor exacto
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
    query = get_admin_parqueaderos_query()
    p = query.filter_by(id=id).first_or_404()

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
    query = get_admin_parqueaderos_query()
    parqueaderos = query.all()
    parqueadero_ids = [p.id for p in parqueaderos]

    # Filtros opcionales
    estado_filtro = request.args.get('estado', '')
    parqueadero_filtro = request.args.get('parqueadero_id', '')

    reservas_q = Reserva.query.filter(Reserva.parqueadero_id.in_(parqueadero_ids)) if parqueadero_ids else Reserva.query.filter_by(id=-1)

    if estado_filtro:
        reservas_q = reservas_q.filter(Reserva.estado == estado_filtro)
    if parqueadero_filtro and parqueadero_filtro.isdigit():
        reservas_q = reservas_q.filter(Reserva.parqueadero_id == int(parqueadero_filtro))

    reservas_list = reservas_q.order_by(Reserva.fecha.desc(), Reserva.hora_inicio.desc()).all()

    return render_template(
        'parking_admin/reservas.html',
        reservas=reservas_list,
        parqueaderos=parqueaderos,
        estado_filtro=estado_filtro,
        parqueadero_filtro=parqueadero_filtro
    )

@parking_admin_bp.route('/reservas/<int:id>/cambiar-estado', methods=['POST'])
def cambiar_estado_reserva(id):
    query = get_admin_parqueaderos_query()
    parqueadero_ids = [p.id for p in query.all()]
    
    reserva = Reserva.query.filter(Reserva.id == id, Reserva.parqueadero_id.in_(parqueadero_ids)).first_or_404()
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ['activa', 'completada', 'cancelada']:
        reserva.estado = nuevo_estado
        db.session.commit()
        flash(f'Reserva {reserva.codigo_reserva} marcada como {nuevo_estado}.', 'success')
    return redirect(url_for('parking_admin.reservas'))
