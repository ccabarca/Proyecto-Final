from models import db, Apartamento, Cuarto, Pago, Limpieza, Gas
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import statistics

class AnalyticsManager:
    """Gestor de análisis y métricas comerciales para el sistema"""
    
    def __init__(self):
        self.hoy = datetime.now()
        self.mes_actual = self.hoy.month
        self.año_actual = self.hoy.year
    
    def calcular_rentabilidad_apartamento(self, apartamento_id: int) -> Dict:
        """Calcula la rentabilidad de un apartamento específico"""
        apartamento = Apartamento.query.get(apartamento_id)
        if not apartamento:
            return {}
        
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        cuartos_activos = [c for c in cuartos if c.activo]
        
        # Ingresos potenciales vs reales
        ingresos_potenciales = sum(c.renta for c in cuartos_activos)
        ingresos_reales = self._calcular_ingresos_reales(apartamento_id)
        
        # Ocupación
        tasa_ocupacion = len(cuartos_activos) / len(cuartos) * 100 if cuartos else 0
        
        # Análisis de pagos
        pagos_analisis = self._analizar_pagos_apartamento(apartamento_id)
        
        # Costos operativos estimados
        costos_operativos = self._calcular_costos_operativos(apartamento_id)
        
        # ROI estimado
        roi_estimado = ((ingresos_reales - costos_operativos) / costos_operativos * 100) if costos_operativos > 0 else 0
        
        return {
            'apartamento_id': apartamento_id,
            'numero': apartamento.numero,
            'ingresos_potenciales': ingresos_potenciales,
            'ingresos_reales': ingresos_reales,
            'tasa_ocupacion': round(tasa_ocupacion, 1),
            'cuartos_activos': len(cuartos_activos),
            'cuartos_totales': len(cuartos),
            'pagos_analisis': pagos_analisis,
            'costos_operativos': costos_operativos,
            'roi_estimado': round(roi_estimado, 1),
            'rentabilidad_score': self._calcular_rentabilidad_score(tasa_ocupacion, pagos_analisis['puntualidad'])
        }
    
    def obtener_analisis_comparativo(self) -> Dict:
        """Obtiene análisis comparativo entre apartamentos"""
        apartamentos = Apartamento.query.all()
        analisis = []
        
        for apto in apartamentos:
            analisis_apto = self.calcular_rentabilidad_apartamento(apto.id)
            if analisis_apto:
                analisis.append(analisis_apto)
        
        # Ordenar por rentabilidad
        analisis.sort(key=lambda x: x['rentabilidad_score'], reverse=True)
        
        # Estadísticas generales
        stats = {
            'total_apartamentos': len(analisis),
            'promedio_ocupacion': statistics.mean([a['tasa_ocupacion'] for a in analisis]) if analisis else 0,
            'promedio_roi': statistics.mean([a['roi_estimado'] for a in analisis]) if analisis else 0,
            'mejor_apartamento': analisis[0] if analisis else None,
            'peor_apartamento': analisis[-1] if analisis else None,
            'analisis_detallado': analisis
        }
        
        return stats
    
    def predecir_ingresos_mes_siguiente(self) -> Dict:
        """Predice los ingresos del mes siguiente basado en tendencias"""
        # Obtener datos de los últimos 3 meses
        fecha_inicio = self.hoy - timedelta(days=90)
        
        # Calcular tendencia de ocupación
        tendencia_ocupacion = self._calcular_tendencia_ocupacion()
        
        # Calcular tendencia de pagos
        tendencia_pagos = self._calcular_tendencia_pagos()
        
        # Predecir ingresos
        apartamentos = Apartamento.query.all()
        prediccion_ingresos = 0
        
        for apto in apartamentos:
            cuartos = Cuarto.query.filter_by(apartamento_id=apto.id).all()
            cuartos_activos = [c for c in cuartos if c.activo]
            
            # Aplicar tendencia de ocupación
            ocupacion_predicha = len(cuartos_activos) * (1 + tendencia_ocupacion / 100)
            ocupacion_predicha = min(ocupacion_predicha, len(cuartos))  # No más del 100%
            
            # Calcular ingresos predichos
            ingresos_apto = sum(c.renta for c in cuartos_activos) * (1 + tendencia_pagos / 100)
            prediccion_ingresos += ingresos_apto
        
        return {
            'prediccion_ingresos': round(prediccion_ingresos, 2),
            'tendencia_ocupacion': round(tendencia_ocupacion, 1),
            'tendencia_pagos': round(tendencia_pagos, 1),
            'confianza': self._calcular_confianza_prediccion(tendencia_ocupacion, tendencia_pagos)
        }
    
    def identificar_oportunidades_mejora(self) -> List[Dict]:
        """Identifica oportunidades de mejora en la rentabilidad"""
        oportunidades = []
        
        apartamentos = Apartamento.query.all()
        for apto in apartamentos:
            cuartos = Cuarto.query.filter_by(apartamento_id=apto.id).all()
            cuartos_activos = [c for c in cuartos if c.activo]
            cuartos_libres = [c for c in cuartos if not c.activo]
            
            # Oportunidad 1: Cuartos libres
            if cuartos_libres:
                ingresos_perdidos = sum(apto.renta_base for _ in cuartos_libres)
                oportunidades.append({
                    'tipo': 'ocupacion',
                    'apartamento': apto.numero,
                    'descripcion': f'{len(cuartos_libres)} cuartos disponibles',
                    'impacto_potencial': ingresos_perdidos,
                    'prioridad': 'alta' if len(cuartos_libres) > 2 else 'media',
                    'accion_sugerida': 'Promocionar cuartos disponibles'
                })
            
            # Oportunidad 2: Pagos atrasados
            cuartos_atrasados = []
            for cuarto in cuartos_activos:
                if cuarto.ultimo_pago:
                    dias_atraso = (self.hoy - cuarto.ultimo_pago).days
                    if dias_atraso > 5:
                        cuartos_atrasados.append(cuarto)
            
            if cuartos_atrasados:
                ingresos_atrasados = sum(c.renta for c in cuartos_atrasados)
                oportunidades.append({
                    'tipo': 'pagos',
                    'apartamento': apto.numero,
                    'descripcion': f'{len(cuartos_atrasados)} pagos atrasados',
                    'impacto_potencial': ingresos_atrasados,
                    'prioridad': 'alta',
                    'accion_sugerida': 'Contactar inquilinos morosos'
                })
            
            # Oportunidad 3: Optimización de precios
            if cuartos_activos:
                renta_promedio = statistics.mean([c.renta for c in cuartos_activos])
                if renta_promedio < apto.renta_base * 1.1:  # Si está por debajo del 110% de la base
                    oportunidades.append({
                        'tipo': 'precios',
                        'apartamento': apto.numero,
                        'descripcion': 'Renta promedio por debajo del potencial',
                        'impacto_potencial': (apto.renta_base * 1.1 - renta_promedio) * len(cuartos_activos),
                        'prioridad': 'media',
                        'accion_sugerida': 'Revisar y ajustar precios de renta'
                    })
        
        # Ordenar por prioridad e impacto
        prioridad_order = {'alta': 3, 'media': 2, 'baja': 1}
        oportunidades.sort(key=lambda x: (prioridad_order.get(x['prioridad'], 0), x['impacto_potencial']), reverse=True)
        
        return oportunidades
    
    def generar_reporte_comercial(self) -> Dict:
        """Genera un reporte comercial completo"""
        analisis_comparativo = self.obtener_analisis_comparativo()
        prediccion = self.predecir_ingresos_mes_siguiente()
        oportunidades = self.identificar_oportunidades_mejora()
        
        # Calcular KPIs principales
        total_ingresos_mes = self._calcular_ingresos_totales_mes()
        total_ingresos_año = self._calcular_ingresos_totales_año()
        
        return {
            'fecha_reporte': self.hoy.isoformat(),
            'kpis_principales': {
                'ingresos_mes_actual': total_ingresos_mes,
                'ingresos_año_actual': total_ingresos_año,
                'tasa_ocupacion_promedio': analisis_comparativo['promedio_ocupacion'],
                'roi_promedio': analisis_comparativo['promedio_roi']
            },
            'analisis_comparativo': analisis_comparativo,
            'prediccion_ingresos': prediccion,
            'oportunidades_mejora': oportunidades,
            'recomendaciones': self._generar_recomendaciones(analisis_comparativo, oportunidades)
        }
    
    # Métodos privados
    def _calcular_ingresos_reales(self, apartamento_id: int) -> float:
        """Calcula ingresos reales del apartamento en el mes actual"""
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        ingresos = 0
        
        for cuarto in cuartos:
            pagos = Pago.query.filter(
                Pago.cuarto_id == cuarto.id,
                db.extract('year', Pago.fecha) == self.año_actual,
                db.extract('month', Pago.fecha) == self.mes_actual
            ).all()
            ingresos += sum(pago.monto for pago in pagos)
        
        return ingresos
    
    def _analizar_pagos_apartamento(self, apartamento_id: int) -> Dict:
        """Analiza los patrones de pago de un apartamento"""
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        cuartos_activos = [c for c in cuartos if c.activo]
        
        pagos_puntuales = 0
        pagos_atrasados = 0
        total_pagos = 0
        
        for cuarto in cuartos_activos:
            if cuarto.ultimo_pago:
                dias_atraso = (self.hoy - cuarto.ultimo_pago).days
                if dias_atraso <= 5:
                    pagos_puntuales += 1
                else:
                    pagos_atrasados += 1
                total_pagos += 1
        
        puntualidad = (pagos_puntuales / total_pagos * 100) if total_pagos > 0 else 0
        
        return {
            'pagos_puntuales': pagos_puntuales,
            'pagos_atrasados': pagos_atrasados,
            'total_pagos': total_pagos,
            'puntualidad': round(puntualidad, 1)
        }
    
    def _calcular_costos_operativos(self, apartamento_id: int) -> float:
        """Calcula costos operativos estimados del apartamento"""
        # Costos estimados por apartamento (mantenimiento, servicios, etc.)
        costo_base = 200.0  # Costo base mensual
        
        # Ajustar por número de cuartos
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        costo_por_cuarto = 50.0
        costo_total = costo_base + (len(cuartos) * costo_por_cuarto)
        
        return costo_total
    
    def _calcular_rentabilidad_score(self, ocupacion: float, puntualidad: float) -> float:
        """Calcula un score de rentabilidad (0-100)"""
        # Ponderación: 60% ocupación, 40% puntualidad
        score = (ocupacion * 0.6) + (puntualidad * 0.4)
        return round(score, 1)
    
    def _calcular_tendencia_ocupacion(self) -> float:
        """Calcula la tendencia de ocupación en los últimos meses"""
        # Implementación simplificada - en un sistema real se usarían datos históricos
        return 2.5  # 2.5% de crecimiento mensual estimado
    
    def _calcular_tendencia_pagos(self) -> float:
        """Calcula la tendencia de pagos en los últimos meses"""
        # Implementación simplificada
        return 1.0  # 1% de mejora mensual estimada
    
    def _calcular_confianza_prediccion(self, tendencia_ocupacion: float, tendencia_pagos: float) -> str:
        """Calcula el nivel de confianza de la predicción"""
        if abs(tendencia_ocupacion) < 5 and abs(tendencia_pagos) < 5:
            return "alta"
        elif abs(tendencia_ocupacion) < 10 and abs(tendencia_pagos) < 10:
            return "media"
        else:
            return "baja"
    
    def _calcular_ingresos_totales_mes(self) -> float:
        """Calcula ingresos totales del mes actual"""
        ingresos = db.session.query(db.func.sum(Pago.monto)).filter(
            db.extract('year', Pago.fecha) == self.año_actual,
            db.extract('month', Pago.fecha) == self.mes_actual
        ).scalar()
        return float(ingresos) if ingresos else 0.0
    
    def _calcular_ingresos_totales_año(self) -> float:
        """Calcula ingresos totales del año actual"""
        ingresos = db.session.query(db.func.sum(Pago.monto)).filter(
            db.extract('year', Pago.fecha) == self.año_actual
        ).scalar()
        return float(ingresos) if ingresos else 0.0
    
    def _generar_recomendaciones(self, analisis: Dict, oportunidades: List[Dict]) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recomendaciones = []
        
        # Recomendación basada en ocupación
        if analisis['promedio_ocupacion'] < 80:
            recomendaciones.append("Considerar estrategias de marketing para aumentar la ocupación")
        
        # Recomendación basada en ROI
        if analisis['promedio_roi'] < 15:
            recomendaciones.append("Revisar costos operativos y optimizar procesos")
        
        # Recomendación basada en oportunidades
        oportunidades_altas = [o for o in oportunidades if o['prioridad'] == 'alta']
        if len(oportunidades_altas) > 2:
            recomendaciones.append("Priorizar la resolución de problemas de alta prioridad")
        
        # Recomendación general
        if analisis['promedio_ocupacion'] > 90 and analisis['promedio_roi'] > 20:
            recomendaciones.append("Excelente rendimiento - considerar expansión")
        
        return recomendaciones

# Instancia global del analytics
analytics_manager = AnalyticsManager()



