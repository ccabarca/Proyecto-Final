from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from models import db, Apartamento, Cuarto, Pago, Limpieza, Gas, SolicitudPago, Notificacion
from datetime import datetime, timedelta
from backend.apartamento import Apartamento
from backend.tareas import (
    toggle_disponibilidad, marcar_limpieza_manual, swap_responsables,
    marcar_pago_cuarto, asignar_inquilino_y_renta, liberar_cuarto,
    solicitar_pago_cuarto
)
from backend.notificaciones import sistema_notificaciones
from backend.dashboard import dashboard_manager
from backend.respaldos import sistema_respaldos
from backend.analytics import analytics_manager
from backend.marketing import marketing_manager
from backend.gestion_apartamentos import gestion_apartamentos

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///apartamentos_simple.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'super_secret_key'

db.init_app(app)

with app.app_context():
    db.create_all()

# ----- Datos demo: 4 apartamentos, 6 cuartos cada uno -----
apartamentos = [Apartamento(i+1, 500 + i*50) for i in range(4)]

# Activar algunos cuartos de ejemplo
for apto in apartamentos:
    for n in range(1, 7):
        if n % 2 == 1:  # activar impares como demo
            apto.get_cuarto(n).asignar_inquilino(f"Inquilino {apto.numero}-{n}", apto.renta_base)

@app.route('/')
def index():
    # Verificar notificaciones automáticamente
    sistema_notificaciones.verificar_pagos_vencidos()
    sistema_notificaciones.verificar_gas_agotado()
    sistema_notificaciones.verificar_limpieza_pendiente()
    
    # Obtener apartamentos desde la base de datos
    apartamentos_db = gestion_apartamentos.obtener_todos_apartamentos()
    
    # Para cada apartamento, quién limpia esta semana y a quién le toca gas
    contexto = []
    for apto_data in apartamentos_db:
        # Crear objeto apartamento temporal para compatibilidad
        apto = type('Apartamento', (), {
            'numero': apto_data['numero'],
            'renta_base': apto_data['renta_base'],
            'cuartos': []  # Se llenará con datos de la base de datos
        })()
        
        # Obtener cuartos del apartamento desde la base de datos
        cuartos = Cuarto.query.filter_by(apartamento_id=apto_data['id']).all()
        apto.cuartos = cuartos
        
        # Calcular limpieza y gas (simplificado)
        limpieza_actual = None
        gas_siguiente = None
        if cuartos:
            cuartos_activos = [c for c in cuartos if c.activo]
            if cuartos_activos:
                limpieza_actual = cuartos_activos[0].numero
                gas_siguiente = cuartos_activos[0].numero
        
        # Calcular pendientes
        pendientes = []
        total = 0
        for cuarto in cuartos:
            if cuarto.activo and cuarto.inquilino:
                pendientes.append({
                    'cuarto': cuarto.numero,
                    'renta': cuarto.renta or apto.renta_base
                })
                total += cuarto.renta or apto.renta_base
        
        contexto.append({
            'apto': apto,
            'apto_data': apto_data,
            'limpieza_actual': limpieza_actual,
            'gas_siguiente': gas_siguiente,
            'pendientes': pendientes,
            'total': total
        })
    
    # Obtener métricas del dashboard
    metricas = dashboard_manager.obtener_metricas_generales()
    alertas_urgentes = dashboard_manager.obtener_alertas_urgentes()
    notificaciones_pendientes = sistema_notificaciones.obtener_notificaciones_pendientes(10)
    
    return render_template('index.html', 
                         contexto=contexto, 
                         hoy=datetime.now(),
                         metricas=metricas,
                         alertas_urgentes=alertas_urgentes,
                         notificaciones_pendientes=notificaciones_pendientes)

# ----- Limpieza -----
@app.route('/limpieza/cerrar/<int:apto_num>', methods=['POST'])
def cerrar_semana(apto_num):
    from models import Apartamento, Cuarto, Limpieza
    
    minutos = int(request.form.get('minutos', 30))
    motivo = request.form.get('motivo', '')
    
    # Buscar apartamento en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        flash('Apartamento no encontrado', 'error')
        return redirect(url_for('index'))
    
    # Buscar cuarto responsable de limpieza (simplificado: primer cuarto activo)
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, activo=True).first()
    if not cuarto:
        flash('No hay cuartos activos en este apartamento', 'error')
        return redirect(url_for('index'))
    
    # Crear registro de limpieza
    limpieza = Limpieza(
        fecha=datetime.utcnow(),
        minutos=minutos,
        motivo=motivo,
        cuarto_id=cuarto.id
    )
    
    db.session.add(limpieza)
    db.session.commit()
    
    flash(f'Limpieza registrada para habitación {cuarto.numero} - {minutos} minutos', 'success')
    return redirect(url_for('index'))

@app.route('/limpieza/marcar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def marcar_limpieza(apto_num, cuarto_num):
    from models import Apartamento, Cuarto, Limpieza
    
    minutos = int(request.form.get('minutos', 30))
    motivo = request.form.get('motivo', '')
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        flash('Apartamento no encontrado', 'error')
        return redirect(url_for('index'))
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        flash('Habitación no encontrada', 'error')
        return redirect(url_for('index'))
    
    # Crear registro de limpieza
    limpieza = Limpieza(
        fecha=datetime.utcnow(),
        minutos=minutos,
        motivo=motivo,
        cuarto_id=cuarto.id
    )
    
    db.session.add(limpieza)
    db.session.commit()
    
    flash(f'Limpieza registrada para habitación {cuarto_num} - {minutos} minutos', 'success')
    return redirect(url_for('index'))

@app.route('/api/limpieza/marcar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def marcar_limpieza_api(apto_num, cuarto_num):
    from models import Apartamento, Cuarto, Limpieza
    
    data = request.get_json()
    minutos = int(data.get('minutos', 30))
    motivo = data.get('motivo', '')
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'ok': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'ok': False, 'msg': 'Habitación no encontrada'})
    
    # Crear registro de limpieza
    limpieza = Limpieza(
        fecha=datetime.utcnow(),
        minutos=minutos,
        motivo=motivo,
        cuarto_id=cuarto.id
    )
    
    db.session.add(limpieza)
    db.session.commit()
    
    # Buscar siguiente cuarto ocupado para limpiar
    siguiente_cuarto = Cuarto.query.filter_by(
        apartamento_id=apartamento.id, 
        activo=True
    ).filter(Cuarto.numero != cuarto_num).first()
    
    siguiente_info = None
    if siguiente_cuarto:
        siguiente_info = {
            'numero': siguiente_cuarto.numero,
            'inquilino': siguiente_cuarto.inquilino or 'Sin inquilino'
        }
    
    return jsonify({
        'ok': True, 
        'msg': f'Limpieza registrada para habitación {cuarto_num}',
        'siguiente_cuarto': siguiente_info
    })

@app.route('/limpieza/swap/<int:apto_num>', methods=['POST'])
def swap(apto_num):
    a = int(request.form['cuarto_a'])
    b = int(request.form['cuarto_b'])
    motivo = request.form.get('motivo', 'Acuerdo entre cuartos')
    apto = apartamentos[apto_num-1]
    msg = swap_responsables(apto, a, b, motivo)
    flash(msg, 'success')
    return redirect(url_for('index'))

# ----- Gas -----
@app.route('/gas/registrar/<int:apto_num>', methods=['POST'])
def registrar_gas(apto_num):
    from models import Apartamento, Cuarto, Gas
    
    nota = request.form.get('nota', 'Compra registrada')
    
    # Buscar apartamento en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        flash('Apartamento no encontrado', 'error')
        return redirect(url_for('index'))
    
    # Buscar cuarto responsable de gas (simplificado: primer cuarto activo)
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, activo=True).first()
    if not cuarto:
        flash('No hay cuartos activos en este apartamento', 'error')
        return redirect(url_for('index'))
    
    # Crear registro de gas
    gas = Gas(
        fecha=datetime.utcnow(),
        nota=nota,
        cuarto_id=cuarto.id
    )
    
    db.session.add(gas)
    db.session.commit()
    
    flash(f'Compra de gas registrada para habitación {cuarto.numero}', 'success')
    return redirect(url_for('index'))

@app.route('/api/gas/registrar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def registrar_gas_api(apto_num, cuarto_num):
    from models import Apartamento, Cuarto, Gas
    
    data = request.get_json()
    nota = data.get('nota', 'Compra registrada')
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'ok': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'ok': False, 'msg': 'Habitación no encontrada'})
    
    # Crear registro de gas
    gas = Gas(
        fecha=datetime.utcnow(),
        nota=nota,
        cuarto_id=cuarto.id
    )
    
    db.session.add(gas)
    db.session.commit()
    
    # Buscar siguiente cuarto ocupado para gas
    siguiente_cuarto = Cuarto.query.filter_by(
        apartamento_id=apartamento.id, 
        activo=True
    ).filter(Cuarto.numero != cuarto_num).first()
    
    siguiente_info = None
    if siguiente_cuarto:
        siguiente_info = {
            'numero': siguiente_cuarto.numero,
            'inquilino': siguiente_cuarto.inquilino or 'Sin inquilino'
        }
    
    return jsonify({
        'ok': True, 
        'msg': f'Compra de gas registrada para habitación {cuarto_num}',
        'siguiente_cuarto': siguiente_info
    })

# ----- Disponibilidad / Inquilinos -----
@app.route('/cuarto/toggle/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def toggle(apto_num, cuarto_num):
    from models import Apartamento, Cuarto
    
    activo = request.form.get('activo') == 'on'
    nombre = request.form.get('nombre', '')
    renta = float(request.form.get('renta', 0))
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'success': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'success': False, 'msg': 'Habitación no encontrada'})
    
    # Actualizar estado del cuarto
    cuarto.activo = activo
    if activo:
        cuarto.inquilino = nombre
        cuarto.renta = renta if renta > 0 else apartamento.renta_base
    else:
        cuarto.inquilino = None
        cuarto.renta = apartamento.renta_base
    
    db.session.commit()
    
    if activo:
        msg = f'Habitación {cuarto_num} asignada a {nombre} - Renta: ${cuarto.renta:.2f}'
    else:
        msg = f'Habitación {cuarto_num} liberada'
    
    return jsonify({
        'success': True, 
        'msg': msg,
        'cuarto': {
            'numero': cuarto.numero,
            'activo': cuarto.activo,
            'inquilino': cuarto.inquilino,
            'renta': cuarto.renta
        }
    })

# API para liberar cuarto
@app.route('/api/cuarto/liberar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def liberar_cuarto_api(apto_num, cuarto_num):
    from models import Apartamento, Cuarto
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'ok': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'ok': False, 'msg': 'Habitación no encontrada'})
    
    # Liberar cuarto
    cuarto.activo = False
    cuarto.inquilino = None
    cuarto.renta = apartamento.renta_base
    
    db.session.commit()
    
    return jsonify({
        'ok': True, 
        'msg': f'Habitación {cuarto_num} liberada',
        'cuarto': {
            'numero': cuarto.numero,
            'activo': cuarto.activo,
            'inquilino': cuarto.inquilino,
            'renta': cuarto.renta
        }
    })

# API para registrar pago
@app.route('/api/pagos/registrar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def registrar_pago_api(apto_num, cuarto_num):
    from models import Apartamento, Cuarto
    from backend.control_pagos import ControlPagos
    
    data = request.get_json()
    monto = float(data.get('monto', 0))
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'msg': 'Habitación no encontrada'})
    
    # Usar renta del cuarto si no se especifica monto
    if monto <= 0:
        monto = cuarto.renta or apartamento.renta_base
    
    # Usar el sistema de control de pagos
    control_pagos = ControlPagos()
    resultado = control_pagos.registrar_pago(cuarto.id, monto)
    
    return jsonify(resultado)

# API para asignar cuarto
@app.route('/api/cuarto/asignar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def asignar_cuarto_api(apto_num, cuarto_num):
    from models import Apartamento, Cuarto
    from backend.control_pagos import ControlPagos
    
    data = request.get_json()
    nombre = data.get('nombre', '')
    renta = float(data.get('renta', 0))
    tipo_contrato = data.get('tipo_contrato', 'mensual')
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'ok': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'ok': False, 'msg': 'Habitación no encontrada'})
    
    # Usar el sistema de control de pagos
    control_pagos = ControlPagos()
    resultado = control_pagos.asignar_inquilino(
        cuarto.id, 
        nombre, 
        renta if renta > 0 else apartamento.renta_base,
        tipo_contrato
    )
    
    if resultado['success']:
        return jsonify({
            'ok': True, 
            'msg': resultado['msg'],
            'proximo_pago': resultado.get('proximo_pago'),
            'cuarto': {
                'numero': cuarto.numero,
                'activo': cuarto.activo,
                'inquilino': cuarto.inquilino,
                'renta': cuarto.renta,
                'tipo_contrato': cuarto.tipo_contrato
            }
        })
    else:
        return jsonify({'ok': False, 'msg': resultado['msg']})

# ----- Pagos -----
@app.route('/pagos/marcar/<int:apto_num>/<int:cuarto_num>', methods=['POST'])
def marcar_pago(apto_num, cuarto_num):
    from models import Apartamento, Cuarto, Pago
    
    monto = float(request.form.get('monto', 0))
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        flash('Apartamento no encontrado', 'error')
        return redirect(url_for('index'))
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        flash('Habitación no encontrada', 'error')
        return redirect(url_for('index'))
    
    # Usar renta del cuarto si no se especifica monto
    if monto <= 0:
        monto = cuarto.renta or apartamento.renta_base
    
    # Crear registro de pago
    pago = Pago(
        fecha=datetime.utcnow(),
        monto=monto,
        estado='pagado',
        cuarto_id=cuarto.id
    )
    
    # Actualizar último pago del cuarto
    cuarto.ultimo_pago = datetime.utcnow()
    
    db.session.add(pago)
    db.session.commit()
    
    flash(f'Pago registrado para habitación {cuarto_num} - ${monto:.2f}', 'success')
    return redirect(url_for('index'))

@app.template_filter('moneda')
def moneda(valor):
    try:
        return "${:,.2f}".format(float(valor))
    except Exception:
        return valor

@app.post('/api/pagos/solicitar/<int:apto_num>/<int:cuarto_num>')
def api_solicitar_pago(apto_num, cuarto_num):
    from models import Apartamento, Cuarto, SolicitudPago
    from backend.notificaciones import sistema_notificaciones
    
    data = request.get_json(force=True, silent=True) or {}
    nota = data.get('nota', '')
    monto = float(data.get('monto', 500.0))
    
    # Buscar apartamento y cuarto en la base de datos
    apartamento = Apartamento.query.filter_by(numero=apto_num, activo=True).first()
    if not apartamento:
        return jsonify({'ok': False, 'msg': 'Apartamento no encontrado'})
    
    cuarto = Cuarto.query.filter_by(apartamento_id=apartamento.id, numero=cuarto_num).first()
    if not cuarto:
        return jsonify({'ok': False, 'msg': 'Habitación no encontrada'})
    
    # Crear solicitud de pago
    solicitud = SolicitudPago(
        apartamento_id=apartamento.id,
        cuarto_id=cuarto.id,
        monto=monto,
        fecha_solicitud=datetime.now(),
        fecha_vencimiento=datetime.now() + timedelta(days=7),
        estado='pendiente',
        nota=nota
    )
    
    db.session.add(solicitud)
    db.session.commit()
    
    # Crear notificación
    sistema_notificaciones.crear_notificacion(
        tipo='solicitud_pago',
        titulo='Solicitud de Pago',
        mensaje=f'Solicitud de pago de ${monto:.2f} para habitación {cuarto_num} - {cuarto.inquilino or "Sin inquilino"}',
        prioridad='media',
        cuarto_id=cuarto.id,
        apartamento_id=apartamento.id
    )
    
    return jsonify({
        'ok': True, 
        'msg': f'Solicitud de pago enviada para habitación {cuarto_num}',
        'solicitud_id': solicitud.id
    })

@app.get('/historial')
def ver_historial():
    from models import Apartamento, Cuarto, Pago, Limpieza, Gas, SolicitudPago
    
    resumen = []
    
    # Obtener apartamentos desde la base de datos
    apartamentos_db = Apartamento.query.filter_by(activo=True).order_by(Apartamento.numero).all()
    
    for apartamento in apartamentos_db:
        # Obtener cuartos del apartamento
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento.id).all()
        
        # Obtener registros de limpieza
        limpieza_records = []
        for cuarto in cuartos:
            limpiezas = Limpieza.query.filter_by(cuarto_id=cuarto.id).order_by(Limpieza.fecha.desc()).all()
            for limpieza in limpiezas:
                limpieza_records.append({
                    'fecha': limpieza.fecha,
                    'cuarto': cuarto.numero,
                    'minutos': limpieza.minutos,
                    'motivo': limpieza.motivo
                })
        
        # Obtener registros de gas
        gas_records = []
        for cuarto in cuartos:
            gases = Gas.query.filter_by(cuarto_id=cuarto.id).order_by(Gas.fecha.desc()).all()
            for gas in gases:
                gas_records.append({
                    'fecha': gas.fecha,
                    'cuarto': cuarto.numero,
                    'nota': gas.nota
                })
        
        # Obtener registros de pagos
        pagos_records = []
        for cuarto in cuartos:
            pagos = Pago.query.filter_by(cuarto_id=cuarto.id).order_by(Pago.fecha.desc()).all()
            for pago in pagos:
                pagos_records.append({
                    'fecha': pago.fecha,
                    'cuarto': cuarto.numero,
                    'monto': pago.monto,
                    'estado': pago.estado
                })
        
        # Obtener solicitudes de pago
        solicitudes_records = []
        for cuarto in cuartos:
            solicitudes = SolicitudPago.query.filter_by(cuarto_id=cuarto.id).order_by(SolicitudPago.fecha_solicitud.desc()).all()
            for solicitud in solicitudes:
                solicitudes_records.append({
                    'fecha': solicitud.fecha_solicitud,
                    'cuarto': cuarto.numero,
                    'nota': solicitud.nota,
                    'monto_sugerido': solicitud.monto
                })
        
        # Obtener movimientos de inquilinos (simplificado)
        inquilinos_records = []
        for cuarto in cuartos:
            if cuarto.inquilino and cuarto.activo:
                inquilinos_records.append({
                    'cuarto': cuarto.numero,
                    'nombre': cuarto.inquilino,
                    'fecha_asignacion': cuarto.ultimo_pago if cuarto.ultimo_pago else datetime.now(),  # Usar último pago como proxy
                    'fecha_salida': None
                })
        
        # Solo agregar apartamento si tiene registros
        has_records = (
            len(limpieza_records) > 0 or 
            len(gas_records) > 0 or 
            len(pagos_records) > 0 or 
            len(solicitudes_records) > 0 or 
            len(inquilinos_records) > 0
        )
        
        if has_records:
            resumen.append({
                'apto': apartamento.numero,
                'limpieza': sorted(limpieza_records, key=lambda x: x['fecha'], reverse=True),
                'gas': sorted(gas_records, key=lambda x: x['fecha'], reverse=True),
                'pagos': sorted(pagos_records, key=lambda x: x['fecha'], reverse=True),
                'solicitudes': sorted(solicitudes_records, key=lambda x: x['fecha'], reverse=True),
                'inquilinos': sorted(inquilinos_records, key=lambda x: x.get('fecha_asignacion') or datetime.now(), reverse=True)
            })
    
    return render_template('historial.html', resumen=resumen, hoy=datetime.now())

# ----- Control de Pagos -----
@app.route('/api/pagos/verificar-vencidos', methods=['POST'])
def verificar_pagos_vencidos():
    from backend.control_pagos import ControlPagos
    
    control_pagos = ControlPagos()
    cuartos_vencidos = control_pagos.verificar_pagos_vencidos()
    
    return jsonify({
        'success': True,
        'cuartos_vencidos': cuartos_vencidos,
        'total': len(cuartos_vencidos)
    })

@app.route('/api/pagos/verificar-recordatorios', methods=['POST'])
def verificar_recordatorios():
    from backend.control_pagos import ControlPagos
    
    control_pagos = ControlPagos()
    cuartos_recordatorio = control_pagos.verificar_recordatorios_pago()
    
    return jsonify({
        'success': True,
        'cuartos_recordatorio': len(cuartos_recordatorio),
        'total': len(cuartos_recordatorio)
    })

@app.route('/api/pagos/resumen', methods=['GET'])
def resumen_pagos():
    from backend.control_pagos import ControlPagos
    
    control_pagos = ControlPagos()
    resumen = control_pagos.obtener_resumen_pagos()
    
    return jsonify(resumen)

# ----- Dashboard y Notificaciones -----
@app.route('/dashboard')
def dashboard():
    metricas = dashboard_manager.obtener_metricas_generales()
    estadisticas_apartamentos = dashboard_manager.obtener_estadisticas_por_apartamento()
    ingresos_por_mes = dashboard_manager.obtener_ingresos_por_mes()
    estadisticas_limpieza = dashboard_manager.obtener_estadisticas_limpieza()
    estadisticas_gas = dashboard_manager.obtener_estadisticas_gas()
    top_inquilinos = dashboard_manager.obtener_top_inquilinos()
    alertas_urgentes = dashboard_manager.obtener_alertas_urgentes()
    
    return render_template('dashboard.html',
                         metricas=metricas,
                         estadisticas_apartamentos=estadisticas_apartamentos,
                         ingresos_por_mes=ingresos_por_mes,
                         estadisticas_limpieza=estadisticas_limpieza,
                         estadisticas_gas=estadisticas_gas,
                         top_inquilinos=top_inquilinos,
                         alertas_urgentes=alertas_urgentes,
                         hoy=datetime.now())

@app.route('/notificaciones')
def notificaciones():
    notificaciones_pendientes = sistema_notificaciones.obtener_notificaciones_pendientes(50)
    estadisticas_alertas = sistema_notificaciones.obtener_estadisticas_alertas()
    
    return render_template('notificaciones.html',
                         notificaciones=notificaciones_pendientes,
                         estadisticas=estadisticas_alertas,
                         hoy=datetime.now())

@app.post('/api/notificaciones/<int:notif_id>/marcar-leida')
def marcar_notificacion_leida(notif_id):
    success = sistema_notificaciones.marcar_notificacion_leida(notif_id)
    return jsonify(ok=success)

@app.post('/api/solicitudes-pago/crear')
def crear_solicitud_pago():
    data = request.get_json()
    cuarto_id = data.get('cuarto_id')
    monto = float(data.get('monto', 0))
    nota = data.get('nota', '')
    dias_vencimiento = int(data.get('dias_vencimiento', 7))
    
    try:
        solicitud = sistema_notificaciones.crear_solicitud_pago(cuarto_id, monto, nota, dias_vencimiento)
        return jsonify(ok=True, solicitud_id=solicitud.id, msg="Solicitud creada exitosamente")
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.post('/api/pagos/registrar-mejorado')
def registrar_pago_mejorado():
    data = request.get_json()
    cuarto_id = data.get('cuarto_id')
    monto = float(data.get('monto', 0))
    
    try:
        resultado = sistema_notificaciones.marcar_pago_recibido(cuarto_id, monto)
        return jsonify(ok=True, **resultado)
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# ----- Respaldos -----
@app.route('/respaldos')
def respaldos():
    lista_respaldos = sistema_respaldos.obtener_lista_respaldos()
    estadisticas = sistema_respaldos.obtener_estadisticas_respaldos()
    
    return render_template('respaldos.html',
                         respaldos=lista_respaldos,
                         estadisticas=estadisticas,
                         hoy=datetime.now())

@app.post('/api/respaldos/crear')
def crear_respaldo():
    tipo = request.json.get('tipo', 'completo')
    
    try:
        if tipo == 'completo':
            respaldo_path = sistema_respaldos.crear_respaldo_completo()
        elif tipo == 'incremental':
            respaldo_path = sistema_respaldos.crear_respaldo_incremental()
        else:
            return jsonify(ok=False, error="Tipo de respaldo no válido")
        
        return jsonify(ok=True, respaldo_path=respaldo_path, msg="Respaldo creado exitosamente")
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.post('/api/respaldos/restaurar')
def restaurar_respaldo():
    data = request.get_json()
    backup_path = data.get('backup_path')
    
    try:
        sistema_respaldos.restaurar_respaldo(backup_path)
        return jsonify(ok=True, msg="Base de datos restaurada exitosamente")
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.post('/api/respaldos/limpiar')
def limpiar_respaldos():
    dias = request.json.get('dias', 30)
    
    try:
        eliminados = sistema_respaldos.limpiar_respaldos_antiguos(dias)
        return jsonify(ok=True, eliminados=eliminados, msg=f"Eliminados {eliminados} respaldos antiguos")
    except Exception as e:
        return jsonify(ok=False, error=str(e))

# =========================
# RUTAS DE ANALYTICS
# =========================

@app.route('/analytics')
def analytics():
    """Página de analytics y métricas comerciales"""
    try:
        reporte_comercial = analytics_manager.generar_reporte_comercial()
        return render_template('analytics.html', reporte=reporte_comercial)
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/analytics/rentabilidad/<int:apartamento_id>')
def obtener_rentabilidad_apartamento(apartamento_id):
    """Obtiene análisis de rentabilidad de un apartamento específico"""
    try:
        analisis = analytics_manager.calcular_rentabilidad_apartamento(apartamento_id)
        return jsonify({'success': True, 'data': analisis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/prediccion')
def obtener_prediccion_ingresos():
    """Obtiene predicción de ingresos del mes siguiente"""
    try:
        prediccion = analytics_manager.predecir_ingresos_mes_siguiente()
        return jsonify({'success': True, 'data': prediccion})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analytics/oportunidades')
def obtener_oportunidades_mejora():
    """Obtiene oportunidades de mejora identificadas"""
    try:
        oportunidades = analytics_manager.identificar_oportunidades_mejora()
        return jsonify({'success': True, 'data': oportunidades})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================
# RUTAS DE MARKETING
# =========================

@app.route('/marketing')
def marketing():
    """Página de marketing y promociones"""
    try:
        campanas = marketing_manager.generar_campanas_promocionales()
        estrategias = marketing_manager.generar_estrategias_retencion()
        return render_template('marketing.html', campanas=campanas, estrategias=estrategias)
    except Exception as e:
        flash(f'Error al cargar marketing: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/marketing/promocion/descuento', methods=['POST'])
def crear_promocion_descuento():
    """Crea una promoción de descuento"""
    try:
        data = request.get_json()
        apartamento_id = data.get('apartamento_id')
        porcentaje = data.get('porcentaje', 10)
        duracion = data.get('duracion', 30)
        
        promocion = marketing_manager.crear_promocion_descuento(apartamento_id, porcentaje, duracion)
        return jsonify({'success': True, 'data': promocion})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/marketing/contenido/<int:apartamento_id>')
def obtener_contenido_marketing(apartamento_id):
    """Obtiene contenido de marketing para un apartamento"""
    try:
        contenido = marketing_manager.generar_contenido_marketing(apartamento_id)
        return jsonify({'success': True, 'data': contenido})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/marketing/campana/estacional', methods=['POST'])
def crear_campana_estacional():
    """Crea una campaña estacional"""
    try:
        data = request.get_json()
        tipo_estacion = data.get('tipo_estacion', 'verano')
        
        campana = marketing_manager.crear_campana_estacional(tipo_estacion)
        return jsonify({'success': True, 'data': campana})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =========================
# RUTAS DE GESTIÓN DE APARTAMENTOS
# =========================

@app.route('/api/apartamentos', methods=['GET'])
def obtener_apartamentos():
    """Obtiene todos los apartamentos"""
    try:
        apartamentos = gestion_apartamentos.obtener_todos_apartamentos()
        return jsonify({'success': True, 'data': apartamentos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos', methods=['POST'])
def crear_apartamento():
    """Crea un nuevo apartamento"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data.get('numero') or not data.get('renta_base'):
            return jsonify({
                'success': False, 
                'error': 'Número y renta base son requeridos'
            }), 400
        
        resultado = gestion_apartamentos.crear_apartamento(
            numero=data['numero'],
            renta_base=data['renta_base'],
            direccion=data.get('direccion'),
            descripcion=data.get('descripcion'),
            numero_cuartos=data.get('numero_cuartos', 6)
        )
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos/<int:apartamento_id>', methods=['GET'])
def obtener_apartamento(apartamento_id):
    """Obtiene un apartamento específico"""
    try:
        apartamento = gestion_apartamentos.obtener_apartamento(apartamento_id)
        if apartamento:
            return jsonify({'success': True, 'data': apartamento})
        else:
            return jsonify({'success': False, 'error': 'Apartamento no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos/<int:apartamento_id>', methods=['PUT'])
def actualizar_apartamento(apartamento_id):
    """Actualiza un apartamento existente"""
    try:
        data = request.get_json()
        resultado = gestion_apartamentos.actualizar_apartamento(apartamento_id, **data)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos/<int:apartamento_id>', methods=['DELETE'])
def eliminar_apartamento(apartamento_id):
    """Elimina un apartamento"""
    try:
        resultado = gestion_apartamentos.eliminar_apartamento(apartamento_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos/estadisticas', methods=['GET'])
def obtener_estadisticas_apartamentos():
    """Obtiene estadísticas de todos los apartamentos"""
    try:
        estadisticas = gestion_apartamentos.obtener_estadisticas_apartamentos()
        return jsonify({'success': True, 'data': estadisticas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apartamentos/buscar', methods=['GET'])
def buscar_apartamentos():
    """Busca apartamentos por término"""
    try:
        termino = request.args.get('q', '')
        if not termino:
            return jsonify({'success': False, 'error': 'Término de búsqueda requerido'}), 400
        
        apartamentos = gestion_apartamentos.buscar_apartamentos(termino)
        return jsonify({'success': True, 'data': apartamentos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
