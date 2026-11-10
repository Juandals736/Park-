from datetime import datetime, date, time
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from models import db, Usuario, Parqueadero, Reserva
from utils.decorators import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@role_required('admin')
def check_admin_access():
    pass


# ----------------------------------------------------
# DASHBOARD GENERAL
# ----------------------------------------------------
@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    total_usuarios = Usuario.query.count()
    total_estudiantes = Usuario.query.filter_by(rol='estudiante').count()
    total_operadores = Usuario.query.filter_by(rol='admin_parqueadero').count()
    
    total_parqueaderos = Parqueadero.query.count()
    capacidad_total = db.session.query(func.coalesce(func.sum(Parqueadero.capacidad_total), 0)).scalar()
    espacios_ocupados = db.session.query(func.coalesce(func.sum(Parqueadero.espacios_ocupados), 0)).scalar()
    espacios_disponibles = max(0, capacidad_total - espacios_ocupados)
    
    total_reservas = Reserva.query.count()
    reservas_activas = Reserva.query.filter_by(estado='activa').count()
    reservas_hoy = Reserva.query.filter_by(fecha=date.today()).count()

    parqueaderos_recientes = Parqueadero.query.order_by(Parqueadero.id.desc()).limit(5).all()
    reservas_recientes = Reserva.query.order_by(Reserva.id.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_usuarios=total_usuarios,
        total_estudiantes=total_estudiantes,
        total_operadores=total_operadores,
        total_parqueaderos=total_parqueaderos,
        capacidad_total=capacidad_total,
        espacios_ocupados=espacios_ocupados,
        espacios_disponibles=espacios_disponibles,
        total_reservas=total_reservas,
        reservas_activas=reservas_activas,
        reservas_hoy=reservas_hoy,
        parqueaderos_recientes=parqueaderos_recientes,
        reservas_recientes=reservas_recientes
    )


# ----------------------------------------------------
# CRUD DE USUARIOS
# ----------------------------------------------------
@admin_bp.route('/usuarios')
def usuarios_list():
    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


@admin_bp.route('/usuarios/crear', methods=['POST'])
def usuarios_crear():
    email = request.form.get('email', '').strip().lower()
    nombre_completo = request.form.get('nombre_completo', '').strip()
    rol = request.form.get('rol', 'estudiante')
    telefono = request.form.get('telefono', '').strip()
    password = request.form.get('password', '')

    if not email or not nombre_completo or not password:
        flash('Email, nombre y contraseña son requeridos.', 'danger')
        return redirect(url_for('admin.usuarios_list'))

    if Usuario.query.filter_by(email=email).first():
        flash('Ya existe un usuario registrado con ese correo electrónico.', 'danger')
        return redirect(url_for('admin.usuarios_list'))

    nuevo_user = Usuario(
        email=email,
        nombre_completo=nombre_completo,
        rol=rol,
        telefono=telefono,
        activo=True
    )
    nuevo_user.set_password(password)

    db.session.add(nuevo_user)
    db.session.commit()
    flash(f'Usuario {email} creado exitosamente.', 'success')
    return redirect(url_for('admin.usuarios_list'))


@admin_bp.route('/usuarios/<int:id>/editar', methods=['POST'])
def usuarios_editar(id):
    user = Usuario.query.get_or_404(id)
    email = request.form.get('email', '').strip().lower()
    nombre_completo = request.form.get('nombre_completo', '').strip()
    rol = request.form.get('rol', user.rol)
    telefono = request.form.get('telefono', '').strip()
    activo = bool(request.form.get('activo'))
    nueva_password = request.form.get('password', '').strip()

    if not email or not nombre_completo:
        flash('El correo y nombre completo son obligatorios.', 'danger')
        return redirect(url_for('admin.usuarios_list'))

    # Verificar duplicado de email
    existente = Usuario.query.filter_by(email=email).first()
    if existente and existente.id != user.id:
        flash('Ese correo electrónico ya está en uso por otro usuario.', 'danger')
        return redirect(url_for('admin.usuarios_list'))

    user.email = email
    user.nombre_completo = nombre_completo
    user.rol = rol
    user.telefono = telefono
    user.activo = activo

    if nueva_password:
        if len(nueva_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('admin.usuarios_list'))
        user.set_password(nueva_password)

    db.session.commit()
    flash('Usuario actualizado correctamente.', 'success')
    return redirect(url_for('admin.usuarios_list'))


@admin_bp.route('/usuarios/<int:id>/eliminar', methods=['POST'])
def usuarios_eliminar(id):
    if id == current_user.id:
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('admin.usuarios_list'))

    user = Usuario.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.email} eliminado exitosamente.', 'success')
    return redirect(url_for('admin.usuarios_list'))


# ----------------------------------------------------
# CRUD DE PARQUEADEROS
# ----------------------------------------------------
@admin_bp.route('/parqueaderos')
def parqueaderos_list():
    parqueaderos = Parqueadero.query.order_by(Parqueadero.id.asc()).all()
    operadores = Usuario.query.filter_by(rol='admin_parqueadero', activo=True).all()
    return render_template('admin/parqueaderos.html', parqueaderos=parqueaderos, operadores=operadores)


@admin_bp.route('/parqueaderos/crear', methods=['POST'])
def parqueaderos_crear():
    nombre = request.form.get('nombre', '').strip()
    direccion = request.form.get('direccion', '').strip()
    latitud = float(request.form.get('latitud', 1.2136))
    longitud = float(request.form.get('longitud', -77.2811))
    capacidad_total = int(request.form.get('capacidad_total', 50))
    espacios_ocupados = int(request.form.get('espacios_ocupados', 0))
    tipo_vehiculo = request.form.get('tipo_vehiculo', 'ambos')
    tarifa_inicial = float(request.form.get('tarifa_inicial', 3000.0))
    tarifa_hora = float(request.form.get('tarifa_hora', 2500.0))
    horario = request.form.get('horario', 'Lunes a Sábado: 06:00 - 22:00').strip()
    estado = request.form.get('estado', 'disponible')
    administrador_id = request.form.get('administrador_id')
    descripcion = request.form.get('descripcion', '').strip()
    telefono_contacto = request.form.get('telefono_contacto', '').strip()

    admin_id = int(administrador_id) if administrador_id and administrador_id != '' else None

    parqueadero = Parqueadero(
        nombre=nombre,
        direccion=direccion,
        latitud=latitud,
        longitud=longitud,
        capacidad_total=capacidad_total,
        espacios_ocupados=espacios_ocupados,
        tipo_vehiculo=tipo_vehiculo,
        tarifa_inicial=tarifa_inicial,
        tarifa_hora=tarifa_hora,
        horario=horario,
        estado=estado,
        administrador_id=admin_id,
        descripcion=descripcion,
        telefono_contacto=telefono_contacto
    )
    parqueadero.actualizar_disponibilidad()

    db.session.add(parqueadero)
    db.session.commit()
    flash(f'Parqueadero "{nombre}" creado con éxito.', 'success')
    return redirect(url_for('admin.parqueaderos_list'))


@admin_bp.route('/parqueaderos/<int:id>/editar', methods=['POST'])
def parqueaderos_editar(id):
    p = Parqueadero.query.get_or_404(id)
    
    p.nombre = request.form.get('nombre', p.nombre).strip()
    p.direccion = request.form.get('direccion', p.direccion).strip()
    p.latitud = float(request.form.get('latitud', p.latitud))
    p.longitud = float(request.form.get('longitud', p.longitud))
    p.capacidad_total = int(request.form.get('capacidad_total', p.capacidad_total))
    p.espacios_ocupados = int(request.form.get('espacios_ocupados', p.espacios_ocupados))
    p.tipo_vehiculo = request.form.get('tipo_vehiculo', p.tipo_vehiculo)
    p.tarifa_inicial = float(request.form.get('tarifa_inicial', p.tarifa_inicial))
    p.tarifa_hora = float(request.form.get('tarifa_hora', p.tarifa_hora))
    p.horario = request.form.get('horario', p.horario).strip()
    p.estado = request.form.get('estado', p.estado)
    
    admin_id = request.form.get('administrador_id')
    p.administrador_id = int(admin_id) if admin_id and admin_id != '' else None
    
    p.descripcion = request.form.get('descripcion', p.descripcion)
    p.telefono_contacto = request.form.get('telefono_contacto', p.telefono_contacto)

    p.actualizar_disponibilidad()
    db.session.commit()
    flash(f'Parqueadero "{p.nombre}" actualizado correctamente.', 'success')
    return redirect(url_for('admin.parqueaderos_list'))


@admin_bp.route('/parqueaderos/<int:id>/eliminar', methods=['POST'])
def parqueaderos_eliminar(id):
    p = Parqueadero.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash(f'Parqueadero "{p.nombre}" eliminado exitosamente.', 'success')
    return redirect(url_for('admin.parqueaderos_list'))


# ----------------------------------------------------
# CRUD DE RESERVAS CON DATATABLE SERVER-SIDE
# ----------------------------------------------------
@admin_bp.route('/reservas')
def reservas_list():
    estudiantes = Usuario.query.filter_by(rol='estudiante', activo=True).order_by(Usuario.nombre_completo).all()
    parqueaderos = Parqueadero.query.filter_by(estado='disponible').order_by(Parqueadero.nombre).all()
    todos_parqueaderos = Parqueadero.query.order_by(Parqueadero.nombre).all()
    return render_template('admin/reservas.html', estudiantes=estudiantes, parqueaderos=parqueaderos, todos_parqueaderos=todos_parqueaderos)


@admin_bp.route('/api/reservas/serverside', methods=['GET', 'POST'])
def reservas_serverside():
    """
    Procesamiento Server-Side para DataTables con paginación,
    búsqueda multi-campo y ordenación dinámica optimizada en PostgreSQL.
    """
    params = request.values
    draw = int(params.get('draw', 1))
    start = int(params.get('start', 0))
    length = int(params.get('length', 10))
    search_value = params.get('search[value]', '').strip()

    # Mapeo de índices de columnas para ordenamiento
    column_map = {
        0: Reserva.id,
        1: Reserva.codigo_reserva,
        2: Usuario.nombre_completo,
        3: Parqueadero.nombre,
        4: Reserva.fecha,
        5: Reserva.hora_inicio,
        6: Reserva.hora_finalizacion,
        7: Reserva.tipo_vehiculo,
        8: Reserva.placa_vehiculo,
        9: Reserva.estado,
        10: Reserva.fecha_creacion
    }

    order_column_index = int(params.get('order[0][column]', 0))
    order_dir = params.get('order[0][dir]', 'desc')
    order_column = column_map.get(order_column_index, Reserva.id)

    # Base query con joins
    query = db.session.query(Reserva).join(Usuario, Reserva.estudiante_id == Usuario.id).join(Parqueadero, Reserva.parqueadero_id == Parqueadero.id)

    records_total = db.session.query(func.count(Reserva.id)).scalar()

    # Filtro de búsqueda global
    if search_value:
        search_pattern = f"%{search_value}%"
        query = query.filter(
            or_(
                Reserva.codigo_reserva.ilike(search_pattern),
                Usuario.nombre_completo.ilike(search_pattern),
                Usuario.email.ilike(search_pattern),
                Parqueadero.nombre.ilike(search_pattern),
                Reserva.placa_vehiculo.ilike(search_pattern),
                Reserva.estado.ilike(search_pattern)
            )
        )

    records_filtered = query.count()

    # Ordenamiento
    if order_dir == 'asc':
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())

    # Paginación (LIMIT / OFFSET)
    if length > 0:
        reservas = query.offset(start).limit(length).all()
    else:
        reservas = query.all()

    data = []
    for r in reservas:
        # Estado con badge formateado
        estado_badge = ''
        if r.estado == 'activa':
            estado_badge = '<span class="badge badge-success"><i class="fas fa-check-circle"></i> Activa</span>'
        elif r.estado == 'completada':
            estado_badge = '<span class="badge badge-blue"><i class="fas fa-flag-checkered"></i> Completada</span>'
        elif r.estado == 'cancelada':
            estado_badge = '<span class="badge badge-danger"><i class="fas fa-times-circle"></i> Cancelada</span>'
        else:
            estado_badge = f'<span class="badge badge-gray">{r.estado}</span>'

        acciones = f"""
        <div class="table-actions">
            <button class="btn-icon btn-edit" onclick="abrirModalEditarReserva({r.id}, '{r.codigo_reserva}', '{r.estado}', '{r.placa_vehiculo or ''}', '{r.tipo_vehiculo}')" title="Editar Reserva">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn-icon btn-delete" onclick="confirmarEliminarReserva({r.id}, '{r.codigo_reserva}')" title="Eliminar Reserva">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        """

        data.append([
            r.id,
            f"<strong>{r.codigo_reserva}</strong>",
            f"<div><strong>{r.estudiante.nombre_completo}</strong><br><small class='text-muted'>{r.estudiante.email}</small></div>",
            f"<div><strong>{r.parqueadero.nombre}</strong><br><small class='text-muted'>{r.parqueadero.direccion}</small></div>",
            r.fecha.strftime('%d/%m/%Y') if r.fecha else '',
            f"{r.hora_inicio.strftime('%H:%M')} - {r.hora_finalizacion.strftime('%H:%M')}",
            f"<i class='fas fa-{'car' if r.tipo_vehiculo == 'carro' else 'motorcycle'}'></i> {r.tipo_vehiculo.capitalize()}",
            r.placa_vehiculo or '<span class="text-muted">N/A</span>',
            estado_badge,
            r.fecha_creacion.strftime('%d/%m/%Y %H:%M') if r.fecha_creacion else '',
            acciones
        ])

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })


@admin_bp.route('/reservas/crear', methods=['POST'])
def reservas_crear():
    estudiante_id = int(request.form.get('estudiante_id'))
    parqueadero_id = int(request.form.get('parqueadero_id'))
    fecha_str = request.form.get('fecha')
    hora_inicio_str = request.form.get('hora_inicio')
    hora_fin_str = request.form.get('hora_finalizacion')
    tipo_vehiculo = request.form.get('tipo_vehiculo', 'carro')
    placa = request.form.get('placa_vehiculo', '').strip().upper()
    estado = request.form.get('estado', 'activa')

    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    hora_ini_obj = datetime.strptime(hora_inicio_str, '%H:%M').time()
    hora_fin_obj = datetime.strptime(hora_fin_str, '%H:%M').time()

    parqueadero = Parqueadero.query.get_or_404(parqueadero_id)
    # Estimación de costo basada en horas
    horas = max(1.0, (datetime.combine(date.min, hora_fin_obj) - datetime.combine(date.min, hora_ini_obj)).total_seconds() / 3600.0)
    costo_estimado = float(parqueadero.tarifa_inicial) + (horas * float(parqueadero.tarifa_hora))

    nueva_reserva = Reserva(
        estudiante_id=estudiante_id,
        parqueadero_id=parqueadero_id,
        fecha=fecha_obj,
        hora_inicio=hora_ini_obj,
        hora_finalizacion=hora_fin_obj,
        tipo_vehiculo=tipo_vehiculo,
        placa_vehiculo=placa,
        estado=estado,
        costo_estimado=costo_estimado
    )

    db.session.add(nueva_reserva)
    db.session.commit()
    flash(f'Reserva creada exitosamente con código {nueva_reserva.codigo_reserva}.', 'success')
    return redirect(url_for('admin.reservas_list'))


@admin_bp.route('/reservas/<int:id>/editar', methods=['POST'])
def reservas_editar(id):
    r = Reserva.query.get_or_404(id)
    r.estado = request.form.get('estado', r.estado)
    r.tipo_vehiculo = request.form.get('tipo_vehiculo', r.tipo_vehiculo)
    r.placa_vehiculo = request.form.get('placa_vehiculo', r.placa_vehiculo).strip().upper()
    db.session.commit()
    flash(f'Reserva {r.codigo_reserva} actualizada correctamente.', 'success')
    return redirect(url_for('admin.reservas_list'))


@admin_bp.route('/reservas/<int:id>/eliminar', methods=['POST'])
def reservas_eliminar(id):
    r = Reserva.query.get_or_404(id)
    codigo = r.codigo_reserva
    db.session.delete(r)
    db.session.commit()
    flash(f'Reserva {codigo} eliminada exitosamente.', 'success')
    return redirect(url_for('admin.reservas_list'))
