"""
Módulo para el control de pagos, recordatorios y cálculo de fechas
"""
from datetime import datetime, timedelta
from models import db, Cuarto, Pago, Notificacion
from backend.notificaciones import SistemaNotificaciones

class ControlPagos:
    def __init__(self):
        self.sistema_notificaciones = SistemaNotificaciones()
    
    def verificar_pago_duplicado(self, cuarto_id, fecha_pago):
        """
        Verifica si ya existe un pago para el mismo cuarto en la misma fecha
        """
        fecha_inicio = fecha_pago.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = fecha_inicio + timedelta(days=1)
        
        pago_existente = Pago.query.filter(
            Pago.cuarto_id == cuarto_id,
            Pago.fecha >= fecha_inicio,
            Pago.fecha < fecha_fin
        ).first()
        
        return pago_existente is not None
    
    def calcular_proximo_pago(self, fecha_entrada, tipo_contrato, ultimo_pago=None):
        """
        Calcula la fecha del próximo pago basado en el tipo de contrato
        """
        if ultimo_pago:
            fecha_base = ultimo_pago
        else:
            fecha_base = fecha_entrada
        
        if tipo_contrato == "quincenal":
            # Cada 15 días
            return fecha_base + timedelta(days=15)
        else:  # mensual
            # Cada 30 días (aproximadamente un mes)
            return fecha_base + timedelta(days=30)
    
    def registrar_pago(self, cuarto_id, monto, fecha_pago=None):
        """
        Registra un pago con validaciones y actualizaciones automáticas
        """
        if fecha_pago is None:
            fecha_pago = datetime.utcnow()
        
        # Verificar pago duplicado
        if self.verificar_pago_duplicado(cuarto_id, fecha_pago):
            return {
                'success': False,
                'msg': 'Ya existe un pago registrado para este cuarto en la fecha de hoy'
            }
        
        # Obtener cuarto
        cuarto = Cuarto.query.get(cuarto_id)
        if not cuarto:
            return {
                'success': False,
                'msg': 'Cuarto no encontrado'
            }
        
        # Crear registro de pago
        pago = Pago(
            fecha=fecha_pago,
            monto=monto,
            estado='pagado',
            cuarto_id=cuarto_id
        )
        
        # Actualizar cuarto
        cuarto.ultimo_pago = fecha_pago
        cuarto.proximo_pago = self.calcular_proximo_pago(
            cuarto.fecha_entrada or fecha_pago,
            cuarto.tipo_contrato,
            fecha_pago
        )
        
        db.session.add(pago)
        db.session.commit()
        
        # Crear notificación de pago registrado
        self.sistema_notificaciones.crear_notificacion(
            tipo='pago_registrado',
            titulo='Pago Registrado',
            mensaje=f'Pago de ${monto:.2f} registrado para habitación {cuarto.numero}',
            prioridad='info',
            cuarto_id=cuarto_id
        )
        
        return {
            'success': True,
            'msg': f'Pago de ${monto:.2f} registrado exitosamente',
            'proximo_pago': cuarto.proximo_pago.strftime('%d/%m/%Y') if cuarto.proximo_pago else None
        }
    
    def asignar_inquilino(self, cuarto_id, nombre, renta, tipo_contrato="mensual", fecha_entrada=None):
        """
        Asigna un inquilino a un cuarto con configuración de contrato
        """
        if fecha_entrada is None:
            fecha_entrada = datetime.utcnow()
        
        cuarto = Cuarto.query.get(cuarto_id)
        if not cuarto:
            return {
                'success': False,
                'msg': 'Cuarto no encontrado'
            }
        
        # Actualizar cuarto
        cuarto.activo = True
        cuarto.inquilino = nombre
        cuarto.renta = renta
        cuarto.tipo_contrato = tipo_contrato
        cuarto.fecha_entrada = fecha_entrada
        cuarto.proximo_pago = self.calcular_proximo_pago(fecha_entrada, tipo_contrato)
        
        db.session.commit()
        
        # Crear notificación de asignación
        self.sistema_notificaciones.crear_notificacion(
            tipo='inquilino_asignado',
            titulo='Inquilino Asignado',
            mensaje=f'{nombre} asignado a habitación {cuarto.numero} - Contrato {tipo_contrato}',
            prioridad='info',
            cuarto_id=cuarto_id
        )
        
        return {
            'success': True,
            'msg': f'Inquilino {nombre} asignado exitosamente',
            'proximo_pago': cuarto.proximo_pago.strftime('%d/%m/%Y') if cuarto.proximo_pago else None
        }
    
    def verificar_pagos_vencidos(self):
        """
        Verifica pagos vencidos y crea notificaciones
        """
        hoy = datetime.utcnow().date()
        cuartos_vencidos = []
        
        # Buscar cuartos con pagos vencidos
        cuartos = Cuarto.query.filter_by(activo=True).all()
        
        for cuarto in cuartos:
            if cuarto.proximo_pago and cuarto.proximo_pago.date() < hoy:
                dias_vencido = (hoy - cuarto.proximo_pago.date()).days
                
                # Crear notificación de pago vencido
                self.sistema_notificaciones.crear_notificacion(
                    tipo='pago_vencido',
                    titulo='Pago Vencido',
                    mensaje=f'Habitación {cuarto.numero} - {cuarto.inquilino}: Pago vencido hace {dias_vencido} días',
                    prioridad='alta' if dias_vencido > 7 else 'media',
                    cuarto_id=cuarto.id
                )
                
                cuartos_vencidos.append({
                    'cuarto': cuarto.numero,
                    'inquilino': cuarto.inquilino,
                    'dias_vencido': dias_vencido,
                    'proximo_pago': cuarto.proximo_pago
                })
        
        return cuartos_vencidos
    
    def verificar_recordatorios_pago(self):
        """
        Verifica y crea recordatorios de pagos próximos a vencer
        """
        hoy = datetime.utcnow().date()
        cuartos_recordatorio = []
        
        # Buscar cuartos con pagos próximos a vencer (3 días antes)
        cuartos = Cuarto.query.filter_by(activo=True).all()
        
        for cuarto in cuartos:
            if cuarto.proximo_pago:
                dias_restantes = (cuarto.proximo_pago.date() - hoy).days
                
                # Recordatorio 3 días antes
                if dias_restantes == 3:
                    self.sistema_notificaciones.crear_notificacion(
                        tipo='recordatorio_pago',
                        titulo='Recordatorio de Pago',
                        mensaje=f'Habitación {cuarto.numero} - {cuarto.inquilino}: Pago vence en 3 días ({cuarto.proximo_pago.strftime("%d/%m/%Y")})',
                        prioridad='media',
                        cuarto_id=cuarto.id
                    )
                    cuartos_recordatorio.append(cuarto)
                
                # Recordatorio 1 día antes
                elif dias_restantes == 1:
                    self.sistema_notificaciones.crear_notificacion(
                        tipo='recordatorio_pago',
                        titulo='Recordatorio Urgente',
                        mensaje=f'Habitación {cuarto.numero} - {cuarto.inquilino}: Pago vence mañana ({cuarto.proximo_pago.strftime("%d/%m/%Y")})',
                        prioridad='alta',
                        cuarto_id=cuarto.id
                    )
                    cuartos_recordatorio.append(cuarto)
        
        return cuartos_recordatorio
    
    def obtener_resumen_pagos(self):
        """
        Obtiene un resumen de todos los pagos y estados
        """
        cuartos = Cuarto.query.filter_by(activo=True).all()
        hoy = datetime.utcnow().date()
        
        resumen = {
            'total_cuartos': len(cuartos),
            'pagos_vencidos': [],
            'pagos_proximos': [],
            'pagos_al_dia': []
        }
        
        for cuarto in cuartos:
            if cuarto.proximo_pago:
                dias_restantes = (cuarto.proximo_pago.date() - hoy).days
                
                cuarto_info = {
                    'numero': cuarto.numero,
                    'inquilino': cuarto.inquilino,
                    'renta': cuarto.renta,
                    'tipo_contrato': cuarto.tipo_contrato,
                    'proximo_pago': cuarto.proximo_pago,
                    'dias_restantes': dias_restantes
                }
                
                if dias_restantes < 0:
                    resumen['pagos_vencidos'].append(cuarto_info)
                elif dias_restantes <= 3:
                    resumen['pagos_proximos'].append(cuarto_info)
                else:
                    resumen['pagos_al_dia'].append(cuarto_info)
        
        return resumen



