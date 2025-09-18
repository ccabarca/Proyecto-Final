from models import db, Apartamento, Cuarto, Pago, Limpieza, Gas, SolicitudPago, Notificacion
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

class DashboardManager:
    """Gestor de métricas y estadísticas para el dashboard"""
    
    def __init__(self):
        self.hoy = datetime.now()
        self.mes_actual = self.hoy.month
        self.año_actual = self.hoy.year
    
    def obtener_metricas_generales(self) -> Dict:
        """Obtiene métricas generales del sistema"""
        # Estadísticas básicas
        total_apartamentos = Apartamento.query.count()
        total_cuartos = Cuarto.query.count()
        cuartos_activos = Cuarto.query.filter_by(activo=True).count()
        cuartos_disponibles = total_cuartos - cuartos_activos
        
        # Ocupación
        tasa_ocupacion = (cuartos_activos / total_cuartos * 100) if total_cuartos > 0 else 0
        
        # Ingresos del mes actual
        ingresos_mes_actual = self._calcular_ingresos_mes_actual()
        ingresos_pendientes = self._calcular_ingresos_pendientes()
        
        # Alertas
        alertas_criticas = Notificacion.query.filter_by(leida=False, prioridad='critica').count()
        alertas_altas = Notificacion.query.filter_by(leida=False, prioridad='alta').count()
        
        return {
            'total_apartamentos': total_apartamentos,
            'total_cuartos': total_cuartos,
            'cuartos_activos': cuartos_activos,
            'cuartos_disponibles': cuartos_disponibles,
            'tasa_ocupacion': round(tasa_ocupacion, 1),
            'ingresos_mes_actual': ingresos_mes_actual,
            'ingresos_pendientes': ingresos_pendientes,
            'alertas_criticas': alertas_criticas,
            'alertas_altas': alertas_altas
        }
    
    def obtener_estadisticas_por_apartamento(self) -> List[Dict]:
        """Obtiene estadísticas detalladas por apartamento"""
        apartamentos = Apartamento.query.all()
        estadisticas = []
        
        for apto in apartamentos:
            cuartos_activos = Cuarto.query.filter_by(apartamento_id=apto.id, activo=True).count()
            cuartos_totales = Cuarto.query.filter_by(apartamento_id=apto.id).count()
            
            # Ingresos del mes
            ingresos_mes = self._calcular_ingresos_apartamento_mes(apto.id)
            ingresos_pendientes = self._calcular_ingresos_pendientes_apartamento(apto.id)
            
            # Alertas del apartamento
            alertas = Notificacion.query.filter_by(apartamento_id=apto.id, leida=False).count()
            
            # Próximas tareas
            responsable_limpieza = self._obtener_responsable_limpieza(apto)
            responsable_gas = self._obtener_responsable_gas(apto)
            
            estadisticas.append({
                'apartamento': apto.numero,
                'renta_base': apto.renta_base,
                'cuartos_activos': cuartos_activos,
                'cuartos_totales': cuartos_totales,
                'tasa_ocupacion': round((cuartos_activos / cuartos_totales * 100) if cuartos_totales > 0 else 0, 1),
                'ingresos_mes': ingresos_mes,
                'ingresos_pendientes': ingresos_pendientes,
                'alertas': alertas,
                'responsable_limpieza': responsable_limpieza,
                'responsable_gas': responsable_gas
            })
        
        return sorted(estadisticas, key=lambda x: x['apartamento'])
    
    def obtener_ingresos_por_mes(self, meses_atras: int = 6) -> List[Dict]:
        """Obtiene ingresos por mes de los últimos N meses"""
        ingresos_por_mes = []
        
        for i in range(meses_atras):
            fecha = self.hoy - timedelta(days=30 * i)
            mes = fecha.month
            año = fecha.year
            
            # Calcular ingresos del mes
            ingresos = db.session.query(db.func.sum(Pago.monto)).filter(
                db.extract('year', Pago.fecha) == año,
                db.extract('month', Pago.fecha) == mes
            ).scalar() or 0
            
            ingresos_por_mes.append({
                'mes': fecha.strftime('%Y-%m'),
                'mes_nombre': fecha.strftime('%B %Y'),
                'ingresos': float(ingresos)
            })
        
        return list(reversed(ingresos_por_mes))
    
    def obtener_estadisticas_limpieza(self) -> Dict:
        """Obtiene estadísticas de limpieza"""
        # Limpiezas del mes actual
        limpiezas_mes = Limpieza.query.filter(
            db.extract('year', Limpieza.fecha) == self.año_actual,
            db.extract('month', Limpieza.fecha) == self.mes_actual
        ).count()
        
        # Tiempo total de limpieza
        tiempo_total = db.session.query(db.func.sum(Limpieza.minutos)).filter(
            db.extract('year', Limpieza.fecha) == self.año_actual,
            db.extract('month', Limpieza.fecha) == self.mes_actual
        ).scalar() or 0
        
        # Cuartos con limpieza pendiente
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        limpieza_pendiente = 0
        
        for cuarto in cuartos_activos:
            if not cuarto.limpieza_ultima or (self.hoy - cuarto.limpieza_ultima).days > 2:
                limpieza_pendiente += 1
        
        return {
            'limpiezas_mes': limpiezas_mes,
            'tiempo_total_horas': round(tiempo_total / 60, 1),
            'limpieza_pendiente': limpieza_pendiente,
            'promedio_por_cuarto': round(tiempo_total / len(cuartos_activos), 1) if cuartos_activos else 0
        }
    
    def obtener_estadisticas_gas(self) -> Dict:
        """Obtiene estadísticas de gas"""
        # Compras de gas del mes
        compras_mes = Gas.query.filter(
            db.extract('year', Gas.fecha) == self.año_actual,
            db.extract('month', Gas.fecha) == self.mes_actual
        ).count()
        
        # Cuartos que necesitan gas
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        gas_pendiente = 0
        
        for cuarto in cuartos_activos:
            if not cuarto.gas_ultimo or (self.hoy - cuarto.gas_ultimo).days > 7:
                gas_pendiente += 1
        
        return {
            'compras_mes': compras_mes,
            'gas_pendiente': gas_pendiente,
            'total_cuartos_activos': len(cuartos_activos)
        }
    
    def obtener_top_inquilinos(self, limite: int = 5) -> List[Dict]:
        """Obtiene los inquilinos con mejor historial de pagos"""
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        inquilinos_stats = []
        
        for cuarto in cuartos_activos:
            if cuarto.inquilino:
                # Calcular puntuación basada en pagos puntuales
                pagos_mes = Pago.query.filter(
                    Pago.cuarto_id == cuarto.id,
                    db.extract('year', Pago.fecha) == self.año_actual,
                    db.extract('month', Pago.fecha) == self.mes_actual
                ).count()
                
                # Calcular días de retraso promedio
                dias_retraso = 0
                if cuarto.ultimo_pago:
                    dias_retraso = (self.hoy - cuarto.ultimo_pago).days
                
                inquilinos_stats.append({
                    'nombre': cuarto.inquilino,
                    'cuarto': cuarto.numero,
                    'apartamento': cuarto.apartamento.numero,
                    'renta': cuarto.renta,
                    'pagos_mes': pagos_mes,
                    'dias_retraso': dias_retraso,
                    'puntuacion': max(0, 100 - dias_retraso * 5)  # Puntuación simple
                })
        
        return sorted(inquilinos_stats, key=lambda x: x['puntuacion'], reverse=True)[:limite]
    
    def obtener_alertas_urgentes(self) -> List[Dict]:
        """Obtiene alertas que requieren atención inmediata"""
        alertas = []
        
        # Pagos vencidos hace más de 5 días
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        for cuarto in cuartos_activos:
            if cuarto.ultimo_pago:
                dias_sin_pago = (self.hoy - cuarto.ultimo_pago).days
                if dias_sin_pago > 5:
                    alertas.append({
                        'tipo': 'pago_vencido',
                        'prioridad': 'critica',
                        'titulo': f'Pago vencido - Hab. {cuarto.numero}',
                        'mensaje': f'{cuarto.inquilino} debe ${cuarto.renta:.2f} (hace {dias_sin_pago} días)',
                        'cuarto': cuarto.numero,
                        'apartamento': cuarto.apartamento.numero
                    })
        
        # Gas agotado hace más de 10 días
        for cuarto in cuartos_activos:
            if cuarto.gas_ultimo:
                dias_sin_gas = (self.hoy - cuarto.gas_ultimo).days
                if dias_sin_gas > 10:
                    alertas.append({
                        'tipo': 'gas_agotado',
                        'prioridad': 'alta',
                        'titulo': f'Gas agotado - Hab. {cuarto.numero}',
                        'mensaje': f'Sin gas hace {dias_sin_gas} días',
                        'cuarto': cuarto.numero,
                        'apartamento': cuarto.apartamento.numero
                    })
        
        return sorted(alertas, key=lambda x: x['prioridad'], reverse=True)
    
    # Métodos privados
    def _calcular_ingresos_mes_actual(self) -> float:
        """Calcula ingresos del mes actual"""
        ingresos = db.session.query(db.func.sum(Pago.monto)).filter(
            db.extract('year', Pago.fecha) == self.año_actual,
            db.extract('month', Pago.fecha) == self.mes_actual
        ).scalar()
        return float(ingresos) if ingresos else 0.0
    
    def _calcular_ingresos_pendientes(self) -> float:
        """Calcula ingresos pendientes de cobrar"""
        cuartos_activos = Cuarto.query.filter_by(activo=True).all()
        total_pendiente = 0.0
        
        for cuarto in cuartos_activos:
            if not cuarto.ultimo_pago or not self._pago_es_del_mes_actual(cuarto.ultimo_pago):
                total_pendiente += cuarto.renta
        
        return total_pendiente
    
    def _calcular_ingresos_apartamento_mes(self, apartamento_id: int) -> float:
        """Calcula ingresos de un apartamento en el mes actual"""
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        ingresos = 0.0
        
        for cuarto in cuartos:
            pagos = Pago.query.filter(
                Pago.cuarto_id == cuarto.id,
                db.extract('year', Pago.fecha) == self.año_actual,
                db.extract('month', Pago.fecha) == self.mes_actual
            ).all()
            ingresos += sum(pago.monto for pago in pagos)
        
        return ingresos
    
    def _calcular_ingresos_pendientes_apartamento(self, apartamento_id: int) -> float:
        """Calcula ingresos pendientes de un apartamento"""
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id, activo=True).all()
        pendiente = 0.0
        
        for cuarto in cuartos:
            if not cuarto.ultimo_pago or not self._pago_es_del_mes_actual(cuarto.ultimo_pago):
                pendiente += cuarto.renta
        
        return pendiente
    
    def _obtener_responsable_limpieza(self, apartamento: Apartamento) -> str:
        """Obtiene el responsable actual de limpieza"""
        # Implementar lógica de rotación de limpieza
        cuartos_activos = [c for c in apartamento.cuartos if c.activo]
        if not cuartos_activos:
            return "Sin inquilinos"
        
        # Lógica simple de rotación por semana
        semana = self.hoy.isocalendar()[1]
        indice = semana % len(cuartos_activos)
        return f"Hab. {cuartos_activos[indice].numero}"
    
    def _obtener_responsable_gas(self, apartamento: Apartamento) -> str:
        """Obtiene el próximo responsable de gas"""
        cuartos_activos = [c for c in apartamento.cuartos if c.activo]
        if not cuartos_activos:
            return "Sin inquilinos"
        
        # Encontrar el cuarto con gas más antiguo
        cuarto_mas_antiguo = min(cuartos_activos, 
                               key=lambda c: c.gas_ultimo or datetime.min)
        return f"Hab. {cuarto_mas_antiguo.numero}"
    
    def _pago_es_del_mes_actual(self, fecha_pago: datetime) -> bool:
        """Verifica si un pago es del mes actual"""
        return (fecha_pago.year == self.año_actual and 
                fecha_pago.month == self.mes_actual)

# Instancia global del dashboard
dashboard_manager = DashboardManager()



