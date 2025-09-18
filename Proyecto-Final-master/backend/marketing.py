from models import db, Apartamento, Cuarto, Notificacion
from datetime import datetime, timedelta
from typing import Dict, List
import random

class MarketingManager:
    """Gestor de estrategias de marketing y promociones"""
    
    def __init__(self):
        self.hoy = datetime.now()
    
    def generar_campanas_promocionales(self) -> List[Dict]:
        """Genera campañas promocionales basadas en el estado actual"""
        campanas = []
        
        # Obtener apartamentos con baja ocupación
        apartamentos = Apartamento.query.all()
        
        for apto in apartamentos:
            cuartos = Cuarto.query.filter_by(apartamento_id=apto.id).all()
            cuartos_libres = [c for c in cuartos if not c.activo]
            
            if len(cuartos_libres) >= 2:  # Si hay 2 o más cuartos libres
                campana = self._crear_campana_ocupacion(apto, cuartos_libres)
                campanas.append(campana)
        
        return campanas
    
    def crear_promocion_descuento(self, apartamento_id: int, porcentaje_descuento: float, 
                                 duracion_dias: int = 30) -> Dict:
        """Crea una promoción de descuento para un apartamento"""
        apartamento = Apartamento.query.get(apartamento_id)
        if not apartamento:
            return {'error': 'Apartamento no encontrado'}
        
        fecha_fin = self.hoy + timedelta(days=duracion_dias)
        
        promocion = {
            'tipo': 'descuento',
            'apartamento_id': apartamento_id,
            'apartamento_numero': apartamento.numero,
            'porcentaje_descuento': porcentaje_descuento,
            'fecha_inicio': self.hoy.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'renta_original': apartamento.renta_base,
            'renta_promocional': apartamento.renta_base * (1 - porcentaje_descuento / 100),
            'ahorro_mensual': apartamento.renta_base * (porcentaje_descuento / 100),
            'descripcion': f'Descuento del {porcentaje_descuento}% por {duracion_dias} días'
        }
        
        # Crear notificación de promoción
        self._crear_notificacion_promocion(promocion)
        
        return promocion
    
    def crear_promocion_paquete(self, apartamento_id: int, meses_incluidos: int = 2) -> Dict:
        """Crea una promoción de paquete (ej: 2 meses por el precio de 1)"""
        apartamento = Apartamento.query.get(apartamento_id)
        if not apartamento:
            return {'error': 'Apartamento no encontrado'}
        
        promocion = {
            'tipo': 'paquete',
            'apartamento_id': apartamento_id,
            'apartamento_numero': apartamento.numero,
            'meses_incluidos': meses_incluidos,
            'fecha_inicio': self.hoy.isoformat(),
            'fecha_fin': (self.hoy + timedelta(days=60)).isoformat(),
            'renta_original': apartamento.renta_base,
            'renta_promocional': apartamento.renta_base / meses_incluidos,
            'ahorro_total': apartamento.renta_base * (meses_incluidos - 1),
            'descripcion': f'{meses_incluidos} meses por el precio de 1'
        }
        
        self._crear_notificacion_promocion(promocion)
        
        return promocion
    
    def generar_estrategias_retencion(self) -> List[Dict]:
        """Genera estrategias para retener inquilinos actuales"""
        estrategias = []
        
        apartamentos = Apartamento.query.all()
        
        for apto in apartamentos:
            cuartos = Cuarto.query.filter_by(apartamento_id=apto.id, activo=True).all()
            
            for cuarto in cuartos:
                if cuarto.ultimo_pago:
                    dias_inquilino = (self.hoy - cuarto.ultimo_pago).days
                    
                    # Estrategia para inquilinos de larga duración
                    if dias_inquilino > 365:  # Más de un año
                        estrategia = {
                            'tipo': 'fidelidad',
                            'apartamento': apto.numero,
                            'cuarto': cuarto.numero,
                            'inquilino': cuarto.inquilino,
                            'dias_inquilino': dias_inquilino,
                            'estrategia': 'Descuento por fidelidad',
                            'descuento_sugerido': 10,
                            'descripcion': f'Descuento del 10% por ser inquilino por {dias_inquilino} días'
                        }
                        estrategias.append(estrategia)
                    
                    # Estrategia para inquilinos puntuales
                    elif dias_inquilino > 90 and self._es_inquilino_puntual(cuarto.id):
                        estrategia = {
                            'tipo': 'puntualidad',
                            'apartamento': apto.numero,
                            'cuarto': cuarto.numero,
                            'inquilino': cuarto.inquilino,
                            'dias_inquilino': dias_inquilino,
                            'estrategia': 'Bonificación por puntualidad',
                            'bonificacion_sugerida': 50,
                            'descripcion': 'Bonificación de $50 por pagos puntuales'
                        }
                        estrategias.append(estrategia)
        
        return estrategias
    
    def calcular_roi_marketing(self, campana: Dict) -> Dict:
        """Calcula el ROI de una campaña de marketing"""
        apartamento = Apartamento.query.get(campana['apartamento_id'])
        if not apartamento:
            return {'error': 'Apartamento no encontrado'}
        
        # Costos de la campaña (estimados)
        costos_campana = self._calcular_costos_campana(campana)
        
        # Ingresos potenciales
        cuartos_libres = Cuarto.query.filter_by(apartamento_id=campana['apartamento_id'], activo=False).all()
        ingresos_potenciales = len(cuartos_libres) * apartamento.renta_base
        
        # ROI estimado
        roi = ((ingresos_potenciales - costos_campana) / costos_campana * 100) if costos_campana > 0 else 0
        
        return {
            'costos_campana': costos_campana,
            'ingresos_potenciales': ingresos_potenciales,
            'roi_estimado': round(roi, 1),
            'cuartos_disponibles': len(cuartos_libres),
            'renta_promedio': apartamento.renta_base
        }
    
    def generar_contenido_marketing(self, apartamento_id: int) -> Dict:
        """Genera contenido de marketing para un apartamento"""
        apartamento = Apartamento.query.get(apartamento_id)
        if not apartamento:
            return {'error': 'Apartamento no encontrado'}
        
        cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
        cuartos_libres = [c for c in cuartos if not c.activo]
        
        contenido = {
            'titulo': f"Apartamento {apartamento.numero} - Oportunidad Única",
            'subtitulo': f"{len(cuartos_libres)} habitaciones disponibles",
            'descripcion': self._generar_descripcion_atractiva(apartamento, cuartos_libres),
            'caracteristicas': self._generar_caracteristicas(apartamento),
            'precios': self._generar_info_precios(apartamento, cuartos_libres),
            'llamada_accion': self._generar_llamada_accion(apartamento),
            'hashtags': self._generar_hashtags(apartamento),
            'imagenes_sugeridas': self._generar_sugerencias_imagenes(apartamento)
        }
        
        return contenido
    
    def crear_campana_estacional(self, tipo_estacion: str) -> Dict:
        """Crea una campaña estacional"""
        campanas_estacionales = {
            'verano': {
                'nombre': 'Promoción de Verano',
                'descuento': 15,
                'duracion': 60,
                'descripcion': 'Aprovecha el verano con descuentos especiales',
                'color_tema': '#FF6B35',
                'icono': '☀️'
            },
            'invierno': {
                'nombre': 'Oferta de Invierno',
                'descuento': 20,
                'duracion': 90,
                'descripcion': 'Calienta tu invierno con nuestras mejores ofertas',
                'color_tema': '#4A90E2',
                'icono': '❄️'
            },
            'primavera': {
                'nombre': 'Renovación de Primavera',
                'descuento': 10,
                'duracion': 45,
                'descripcion': 'Renueva tu hogar esta primavera',
                'color_tema': '#7ED321',
                'icono': '🌸'
            },
            'otoño': {
                'nombre': 'Oferta de Otoño',
                'descuento': 12,
                'duracion': 50,
                'descripcion': 'Prepara tu hogar para el otoño',
                'color_tema': '#F5A623',
                'icono': '🍂'
            }
        }
        
        if tipo_estacion not in campanas_estacionales:
            return {'error': 'Tipo de estación no válido'}
        
        campana = campanas_estacionales[tipo_estacion]
        campana['fecha_inicio'] = self.hoy.isoformat()
        campana['fecha_fin'] = (self.hoy + timedelta(days=campana['duracion'])).isoformat()
        
        return campana
    
    # Métodos privados
    def _crear_campana_ocupacion(self, apartamento: Apartamento, cuartos_libres: List[Cuarto]) -> Dict:
        """Crea una campaña para aumentar la ocupación"""
        descuento_sugerido = min(20, len(cuartos_libres) * 5)  # Hasta 20% de descuento
        
        return {
            'tipo': 'ocupacion',
            'apartamento_id': apartamento.id,
            'apartamento_numero': apartamento.numero,
            'cuartos_libres': len(cuartos_libres),
            'descuento_sugerido': descuento_sugerido,
            'renta_original': apartamento.renta_base,
            'renta_promocional': apartamento.renta_base * (1 - descuento_sugerido / 100),
            'ahorro_mensual': apartamento.renta_base * (descuento_sugerido / 100),
            'descripcion': f'Descuento del {descuento_sugerido}% para {len(cuartos_libres)} habitaciones disponibles',
            'prioridad': 'alta' if len(cuartos_libres) > 3 else 'media'
        }
    
    def _crear_notificacion_promocion(self, promocion: Dict):
        """Crea una notificación de promoción"""
        notificacion = Notificacion(
            tipo='promocion',
            titulo=f'Promoción: {promocion["descripcion"]}',
            mensaje=f'Apartamento {promocion["apartamento_numero"]} - {promocion["descripcion"]}',
            prioridad='media',
            apartamento_id=promocion['apartamento_id']
        )
        db.session.add(notificacion)
        db.session.commit()
    
    def _es_inquilino_puntual(self, cuarto_id: int) -> bool:
        """Verifica si un inquilino es puntual en los pagos"""
        # Implementación simplificada - en un sistema real se analizaría el historial
        return random.choice([True, False])  # Simulación
    
    def _calcular_costos_campana(self, campana: Dict) -> float:
        """Calcula los costos estimados de una campaña"""
        costos_base = 100.0  # Costo base de marketing
        
        if campana['tipo'] == 'descuento':
            apartamento = Apartamento.query.get(campana['apartamento_id'])
            cuartos_libres = Cuarto.query.filter_by(apartamento_id=campana['apartamento_id'], activo=False).all()
            costos_descuento = len(cuartos_libres) * apartamento.renta_base * (campana['porcentaje_descuento'] / 100)
            return costos_base + costos_descuento
        
        return costos_base
    
    def _generar_descripcion_atractiva(self, apartamento: Apartamento, cuartos_libres: List[Cuarto]) -> str:
        """Genera una descripción atractiva para marketing"""
        return f"""
        ¡Oportunidad única! Apartamento {apartamento.numero} con {len(cuartos_libres)} habitaciones disponibles.
        Ubicación estratégica, servicios incluidos, ambiente familiar y seguro.
        Perfecto para estudiantes, trabajadores y familias.
        ¡No pierdas esta oportunidad!
        """
    
    def _generar_caracteristicas(self, apartamento: Apartamento) -> List[str]:
        """Genera características atractivas del apartamento"""
        return [
            "6 habitaciones individuales",
            "Servicios básicos incluidos",
            "Área común compartida",
            "Seguridad 24/7",
            "Cerca de transporte público",
            "Ambiente familiar y seguro"
        ]
    
    def _generar_info_precios(self, apartamento: Apartamento, cuartos_libres: List[Cuarto]) -> Dict:
        """Genera información de precios atractiva"""
        return {
            'precio_base': apartamento.renta_base,
            'precio_promocional': apartamento.renta_base * 0.9,  # 10% descuento
            'ahorro_mensual': apartamento.renta_base * 0.1,
            'ahorro_anual': apartamento.renta_base * 0.1 * 12,
            'cuartos_disponibles': len(cuartos_libres)
        }
    
    def _generar_llamada_accion(self, apartamento: Apartamento) -> str:
        """Genera una llamada a la acción efectiva"""
        return f"¡Reserva tu habitación en el Apartamento {apartamento.numero} ahora! Oferta limitada por tiempo."
    
    def _generar_hashtags(self, apartamento: Apartamento) -> List[str]:
        """Genera hashtags relevantes para marketing"""
        return [
            f"#Apartamento{apartamento.numero}",
            "#HabitacionesDisponibles",
            "#RentaAccesible",
            "#HogarSeguro",
            "#OportunidadUnica",
            "#ViveMejor"
        ]
    
    def _generar_sugerencias_imagenes(self, apartamento: Apartamento) -> List[str]:
        """Genera sugerencias de imágenes para marketing"""
        return [
            "Fachada del apartamento",
            "Habitación individual",
            "Área común",
            "Cocina compartida",
            "Baño compartido",
            "Vista desde la ventana"
        ]

# Instancia global del marketing
marketing_manager = MarketingManager()



