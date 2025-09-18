from models import db, Notificacion, SolicitudPago, Cuarto, Apartamento, Pago, Gas
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class SistemaNotificaciones:
    """Sistema inteligente de notificaciones para el manejo de apartamentos"""
    
    def __init__(self):
        self.configuraciones = {
            'dias_antes_vencimiento': 3,
            'dias_gas_agotado': 7,
            'dias_limpieza_pendiente': 2,
            'max_recordatorios': 3
        }
    
    def verificar_pagos_vencidos(self) -> List[Dict]:
        """Verifica cuartos con pagos vencidos y crea notificaciones"""
        notificaciones_creadas = []
        hoy = datetime.now()
        
        # Buscar cuartos activos sin pago este mes
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        
        for cuarto in cuartos_activos:
            if not cuarto.ultimo_pago or not self._pago_es_del_mes_actual(cuarto.ultimo_pago, hoy):
                # Verificar si ya existe notificación reciente
                if not self._existe_notificacion_reciente(cuarto.id, 'pago_vencido', dias=1):
                    notif = self._crear_notificacion(
                        tipo='pago_vencido',
                        titulo=f'Pago vencido - Hab. {cuarto.numero}',
                        mensaje=f'El inquilino {cuarto.inquilino} debe ${cuarto.renta:.2f}',
                        prioridad='alta',
                        cuarto_id=cuarto.id,
                        apartamento_id=cuarto.apartamento_id
                    )
                    notificaciones_creadas.append({
                        'tipo': 'pago_vencido',
                        'cuarto': cuarto.numero,
                        'apartamento': cuarto.apartamento.numero,
                        'inquilino': cuarto.inquilino,
                        'monto': cuarto.renta
                    })
        
        return notificaciones_creadas
    
    def verificar_gas_agotado(self) -> List[Dict]:
        """Verifica cuartos que necesitan comprar gas"""
        notificaciones_creadas = []
        hoy = datetime.now()
        dias_limite = self.configuraciones['dias_gas_agotado']
        
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        
        for cuarto in cuartos_activos:
            if not cuarto.gas_ultimo or (hoy - cuarto.gas_ultimo).days >= dias_limite:
                if not self._existe_notificacion_reciente(cuarto.id, 'gas_agotado', dias=2):
                    notif = self._crear_notificacion(
                        tipo='gas_agotado',
                        titulo=f'Gas agotado - Hab. {cuarto.numero}',
                        mensaje=f'Necesita comprar gas (última compra: {cuarto.gas_ultimo.strftime("%d/%m/%Y") if cuarto.gas_ultimo else "Nunca"})',
                        prioridad='media',
                        cuarto_id=cuarto.id,
                        apartamento_id=cuarto.apartamento_id
                    )
                    notificaciones_creadas.append({
                        'tipo': 'gas_agotado',
                        'cuarto': cuarto.numero,
                        'apartamento': cuarto.apartamento.numero,
                        'dias_sin_gas': (hoy - cuarto.gas_ultimo).days if cuarto.gas_ultimo else 999
                    })
        
        return notificaciones_creadas
    
    def verificar_limpieza_pendiente(self) -> List[Dict]:
        """Verifica cuartos con limpieza muy pendiente"""
        notificaciones_creadas = []
        hoy = datetime.now()
        dias_limite = self.configuraciones['dias_limpieza_pendiente']
        
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        
        for cuarto in cuartos_activos:
            if not cuarto.limpieza_ultima or (hoy - cuarto.limpieza_ultima).days >= dias_limite:
                if not self._existe_notificacion_reciente(cuarto.id, 'limpieza_pendiente', dias=1):
                    notif = self._crear_notificacion(
                        tipo='limpieza_pendiente',
                        titulo=f'Limpieza pendiente - Hab. {cuarto.numero}',
                        mensaje=f'Última limpieza hace {(hoy - cuarto.limpieza_ultima).days} días' if cuarto.limpieza_ultima else 'Sin limpieza registrada',
                        prioridad='baja',
                        cuarto_id=cuarto.id,
                        apartamento_id=cuarto.apartamento_id
                    )
                    notificaciones_creadas.append({
                        'tipo': 'limpieza_pendiente',
                        'cuarto': cuarto.numero,
                        'apartamento': cuarto.apartamento.numero,
                        'dias_sin_limpieza': (hoy - cuarto.limpieza_ultima).days if cuarto.limpieza_ultima else 999
                    })
        
        return notificaciones_creadas
    
    def crear_solicitud_pago(self, cuarto_id: int, monto: float, nota: str = "", dias_vencimiento: int = 7) -> SolicitudPago:
        """Crea una solicitud formal de pago"""
        cuarto = Cuarto.query.get(cuarto_id)
        if not cuarto:
            raise ValueError("Cuarto no encontrado")
        
        fecha_vencimiento = datetime.now() + timedelta(days=dias_vencimiento)
        
        solicitud = SolicitudPago(
            cuarto_id=cuarto_id,
            monto=monto,
            fecha_vencimiento=fecha_vencimiento,
            nota=nota,
            estado='pendiente'
        )
        
        db.session.add(solicitud)
        
        # Crear notificación
        self._crear_notificacion(
            tipo='solicitud_pago',
            titulo=f'Nueva solicitud de pago - Hab. {cuarto.numero}',
            mensaje=f'Solicitud de ${monto:.2f} vence el {fecha_vencimiento.strftime("%d/%m/%Y")}',
            prioridad='media',
            cuarto_id=cuarto_id,
            apartamento_id=cuarto.apartamento_id
        )
        
        db.session.commit()
        return solicitud
    
    def marcar_pago_recibido(self, cuarto_id: int, monto: float) -> Dict:
        """Marca un pago como recibido y actualiza solicitudes pendientes"""
        cuarto = Cuarto.query.get(cuarto_id)
        if not cuarto:
            raise ValueError("Cuarto no encontrado")
        
        # Crear registro de pago
        pago = Pago(cuarto_id=cuarto_id, monto=monto)
        cuarto.ultimo_pago = datetime.now()
        db.session.add(pago)
        
        # Marcar solicitudes como pagadas
        solicitudes_pendientes = SolicitudPago.query.filter_by(
            cuarto_id=cuarto_id, 
            estado='pendiente'
        ).all()
        
        for solicitud in solicitudes_pendientes:
            solicitud.estado = 'pagado'
        
        # Marcar notificaciones de pago como leídas
        Notificacion.query.filter_by(
            cuarto_id=cuarto_id,
            tipo='pago_vencido',
            leida=False
        ).update({'leida': True})
        
        db.session.commit()
        
        return {
            'mensaje': f'Pago de ${monto:.2f} registrado para Hab. {cuarto.numero}',
            'solicitudes_actualizadas': len(solicitudes_pendientes)
        }
    
    def obtener_notificaciones_pendientes(self, limite: int = 50) -> List[Dict]:
        """Obtiene notificaciones no leídas ordenadas por prioridad"""
        notificaciones = Notificacion.query.filter_by(leida=False)\
            .order_by(Notificacion.fecha.desc())\
            .limit(limite).all()
        
        return [self._notificacion_a_dict(notif) for notif in notificaciones]
    
    def marcar_notificacion_leida(self, notificacion_id: int) -> bool:
        """Marca una notificación como leída"""
        notif = Notificacion.query.get(notificacion_id)
        if not notif:
            return False
        
        notif.leida = True
        db.session.commit()
        return True
    
    def obtener_estadisticas_alertas(self) -> Dict:
        """Obtiene estadísticas de alertas del sistema"""
        hoy = datetime.now()
        
        # Contar notificaciones por tipo
        stats = {
            'pagos_vencidos': Notificacion.query.filter_by(tipo='pago_vencido', leida=False).count(),
            'gas_agotado': Notificacion.query.filter_by(tipo='gas_agotado', leida=False).count(),
            'limpieza_pendiente': Notificacion.query.filter_by(tipo='limpieza_pendiente', leida=False).count(),
            'solicitudes_pendientes': SolicitudPago.query.filter_by(estado='pendiente').count(),
            'total_notificaciones': Notificacion.query.filter_by(leida=False).count()
        }
        
        # Calcular ingresos pendientes
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        ingresos_pendientes = sum(c.renta for c in cuartos_activos 
                                if not c.ultimo_pago or not self._pago_es_del_mes_actual(c.ultimo_pago, hoy))
        
        stats['ingresos_pendientes'] = ingresos_pendientes
        
        return stats
    
    # Métodos privados
    def _pago_es_del_mes_actual(self, fecha_pago: datetime, fecha_referencia: datetime) -> bool:
        """Verifica si un pago es del mes actual"""
        return (fecha_pago.year == fecha_referencia.year and 
                fecha_pago.month == fecha_referencia.month)
    
    def _existe_notificacion_reciente(self, cuarto_id: int, tipo: str, dias: int = 1) -> bool:
        """Verifica si existe una notificación reciente del mismo tipo"""
        fecha_limite = datetime.now() - timedelta(days=dias)
        return Notificacion.query.filter(
            Notificacion.cuarto_id == cuarto_id,
            Notificacion.tipo == tipo,
            Notificacion.fecha >= fecha_limite
        ).first() is not None
    
    def crear_notificacion(self, tipo: str, titulo: str, mensaje: str, 
                           prioridad: str, cuarto_id: int = None, apartamento_id: int = None) -> Notificacion:
        """Crea una nueva notificación"""
        notif = Notificacion(
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            prioridad=prioridad,
            cuarto_id=cuarto_id,
            apartamento_id=apartamento_id
        )
        db.session.add(notif)
        return notif
    
    def _crear_notificacion(self, tipo: str, titulo: str, mensaje: str, 
                           prioridad: str, cuarto_id: int = None, apartamento_id: int = None) -> Notificacion:
        """Crea una nueva notificación (método privado)"""
        return self.crear_notificacion(tipo, titulo, mensaje, prioridad, cuarto_id, apartamento_id)
    
    def _notificacion_a_dict(self, notif: Notificacion) -> Dict:
        """Convierte una notificación a diccionario"""
        return {
            'id': notif.id,
            'fecha': notif.fecha.strftime('%d/%m/%Y %H:%M'),
            'tipo': notif.tipo,
            'titulo': notif.titulo,
            'mensaje': notif.mensaje,
            'prioridad': notif.prioridad,
            'cuarto_id': notif.cuarto_id,
            'apartamento_id': notif.apartamento_id
        }

# Instancia global del sistema
sistema_notificaciones = SistemaNotificaciones()
