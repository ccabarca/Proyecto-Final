from models import db, Apartamento, Cuarto
from datetime import datetime
from typing import Dict, List, Optional
import logging

class GestionApartamentos:
    """Gestor para la creación y administración de apartamentos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def crear_apartamento(self, numero: int, renta_base: float, direccion: str = None, 
                         descripcion: str = None, numero_cuartos: int = 6) -> Dict:
        """Crea un nuevo apartamento con sus cuartos"""
        try:
            # Verificar si el apartamento ya existe
            if Apartamento.query.filter_by(numero=numero).first():
                return {
                    'success': False,
                    'error': f'El apartamento {numero} ya existe'
                }
            
            # Crear el apartamento
            apartamento = Apartamento(
                numero=numero,
                renta_base=renta_base,
                direccion=direccion,
                descripcion=descripcion,
                numero_cuartos=numero_cuartos,
                fecha_creacion=datetime.utcnow(),
                activo=True
            )
            
            db.session.add(apartamento)
            db.session.flush()  # Para obtener el ID
            
            # Crear los cuartos del apartamento
            cuartos_creados = []
            for i in range(1, numero_cuartos + 1):
                cuarto = Cuarto(
                    numero=i,
                    renta=renta_base,
                    activo=False,
                    apartamento_id=apartamento.id
                )
                db.session.add(cuarto)
                cuartos_creados.append({
                    'numero': i,
                    'renta': renta_base,
                    'activo': False
                })
            
            db.session.commit()
            
            self.logger.info(f'Apartamento {numero} creado exitosamente con {numero_cuartos} cuartos')
            
            return {
                'success': True,
                'apartamento': {
                    'id': apartamento.id,
                    'numero': apartamento.numero,
                    'renta_base': apartamento.renta_base,
                    'direccion': apartamento.direccion,
                    'descripcion': apartamento.descripcion,
                    'numero_cuartos': apartamento.numero_cuartos,
                    'fecha_creacion': apartamento.fecha_creacion.isoformat(),
                    'activo': apartamento.activo
                },
                'cuartos': cuartos_creados,
                'message': f'Apartamento {numero} creado exitosamente'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Error al crear apartamento {numero}: {str(e)}')
            return {
                'success': False,
                'error': f'Error al crear apartamento: {str(e)}'
            }
    
    def obtener_apartamento(self, apartamento_id: int) -> Optional[Dict]:
        """Obtiene un apartamento por ID"""
        try:
            apartamento = Apartamento.query.get(apartamento_id)
            if not apartamento:
                return None
            
            cuartos = Cuarto.query.filter_by(apartamento_id=apartamento_id).all()
            
            return {
                'id': apartamento.id,
                'numero': apartamento.numero,
                'renta_base': apartamento.renta_base,
                'direccion': apartamento.direccion,
                'descripcion': apartamento.descripcion,
                'numero_cuartos': apartamento.numero_cuartos,
                'fecha_creacion': apartamento.fecha_creacion.isoformat(),
                'activo': apartamento.activo,
                'cuartos': [
                    {
                        'id': cuarto.id,
                        'numero': cuarto.numero,
                        'renta': cuarto.renta,
                        'activo': cuarto.activo,
                        'inquilino': cuarto.inquilino,
                        'ultimo_pago': cuarto.ultimo_pago.isoformat() if cuarto.ultimo_pago else None,
                        'limpieza_ultima': cuarto.limpieza_ultima.isoformat() if cuarto.limpieza_ultima else None,
                        'gas_ultimo': cuarto.gas_ultimo.isoformat() if cuarto.gas_ultimo else None
                    }
                    for cuarto in cuartos
                ]
            }
            
        except Exception as e:
            self.logger.error(f'Error al obtener apartamento {apartamento_id}: {str(e)}')
            return None
    
    def obtener_todos_apartamentos(self) -> List[Dict]:
        """Obtiene todos los apartamentos activos"""
        try:
            apartamentos = Apartamento.query.filter_by(activo=True).order_by(Apartamento.numero).all()
            resultado = []
            
            for apartamento in apartamentos:
                cuartos = Cuarto.query.filter_by(apartamento_id=apartamento.id).all()
                cuartos_activos = [c for c in cuartos if c.activo]
                
                resultado.append({
                    'id': apartamento.id,
                    'numero': apartamento.numero,
                    'renta_base': apartamento.renta_base,
                    'direccion': apartamento.direccion,
                    'descripcion': apartamento.descripcion,
                    'numero_cuartos': apartamento.numero_cuartos,
                    'fecha_creacion': apartamento.fecha_creacion.isoformat(),
                    'activo': apartamento.activo,
                    'cuartos_totales': len(cuartos),
                    'cuartos_activos': len(cuartos_activos),
                    'cuartos_libres': len(cuartos) - len(cuartos_activos),
                    'tasa_ocupacion': (len(cuartos_activos) / len(cuartos) * 100) if cuartos else 0
                })
            
            return resultado
            
        except Exception as e:
            self.logger.error(f'Error al obtener apartamentos: {str(e)}')
            return []
    
    def actualizar_apartamento(self, apartamento_id: int, **kwargs) -> Dict:
        """Actualiza un apartamento existente"""
        try:
            apartamento = Apartamento.query.get(apartamento_id)
            if not apartamento:
                return {
                    'success': False,
                    'error': 'Apartamento no encontrado'
                }
            
            # Actualizar campos permitidos
            campos_permitidos = ['numero', 'renta_base', 'direccion', 'descripcion', 'numero_cuartos', 'activo']
            
            for campo, valor in kwargs.items():
                if campo in campos_permitidos and hasattr(apartamento, campo):
                    setattr(apartamento, campo, valor)
            
            db.session.commit()
            
            self.logger.info(f'Apartamento {apartamento.numero} actualizado exitosamente')
            
            return {
                'success': True,
                'message': f'Apartamento {apartamento.numero} actualizado exitosamente',
                'apartamento': {
                    'id': apartamento.id,
                    'numero': apartamento.numero,
                    'renta_base': apartamento.renta_base,
                    'direccion': apartamento.direccion,
                    'descripcion': apartamento.descripcion,
                    'numero_cuartos': apartamento.numero_cuartos,
                    'activo': apartamento.activo
                }
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Error al actualizar apartamento {apartamento_id}: {str(e)}')
            return {
                'success': False,
                'error': f'Error al actualizar apartamento: {str(e)}'
            }
    
    def eliminar_apartamento(self, apartamento_id: int) -> Dict:
        """Elimina un apartamento (soft delete)"""
        try:
            apartamento = Apartamento.query.get(apartamento_id)
            if not apartamento:
                return {
                    'success': False,
                    'error': 'Apartamento no encontrado'
                }
            
            # Soft delete - marcar como inactivo
            apartamento.activo = False
            db.session.commit()
            
            self.logger.info(f'Apartamento {apartamento.numero} eliminado exitosamente')
            
            return {
                'success': True,
                'message': f'Apartamento {apartamento.numero} eliminado exitosamente'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f'Error al eliminar apartamento {apartamento_id}: {str(e)}')
            return {
                'success': False,
                'error': f'Error al eliminar apartamento: {str(e)}'
            }
    
    def obtener_estadisticas_apartamentos(self) -> Dict:
        """Obtiene estadísticas generales de todos los apartamentos"""
        try:
            apartamentos = Apartamento.query.filter_by(activo=True).all()
            
            if not apartamentos:
                return {
                    'total_apartamentos': 0,
                    'total_cuartos': 0,
                    'cuartos_activos': 0,
                    'cuartos_libres': 0,
                    'tasa_ocupacion_promedio': 0,
                    'ingresos_potenciales': 0
                }
            
            total_cuartos = 0
            cuartos_activos = 0
            ingresos_potenciales = 0
            
            for apartamento in apartamentos:
                cuartos = Cuarto.query.filter_by(apartamento_id=apartamento.id).all()
                total_cuartos += len(cuartos)
                cuartos_activos += len([c for c in cuartos if c.activo])
                ingresos_potenciales += apartamento.renta_base * len(cuartos)
            
            cuartos_libres = total_cuartos - cuartos_activos
            tasa_ocupacion = (cuartos_activos / total_cuartos * 100) if total_cuartos > 0 else 0
            
            return {
                'total_apartamentos': len(apartamentos),
                'total_cuartos': total_cuartos,
                'cuartos_activos': cuartos_activos,
                'cuartos_libres': cuartos_libres,
                'tasa_ocupacion_promedio': round(tasa_ocupacion, 1),
                'ingresos_potenciales': round(ingresos_potenciales, 2)
            }
            
        except Exception as e:
            self.logger.error(f'Error al obtener estadísticas: {str(e)}')
            return {
                'total_apartamentos': 0,
                'total_cuartos': 0,
                'cuartos_activos': 0,
                'cuartos_libres': 0,
                'tasa_ocupacion_promedio': 0,
                'ingresos_potenciales': 0
            }
    
    def buscar_apartamentos(self, termino: str) -> List[Dict]:
        """Busca apartamentos por número o dirección"""
        try:
            apartamentos = Apartamento.query.filter(
                Apartamento.activo == True,
                db.or_(
                    Apartamento.numero.like(f'%{termino}%'),
                    Apartamento.direccion.like(f'%{termino}%'),
                    Apartamento.descripcion.like(f'%{termino}%')
                )
            ).order_by(Apartamento.numero).all()
            
            resultado = []
            for apartamento in apartamentos:
                cuartos = Cuarto.query.filter_by(apartamento_id=apartamento.id).all()
                cuartos_activos = [c for c in cuartos if c.activo]
                
                resultado.append({
                    'id': apartamento.id,
                    'numero': apartamento.numero,
                    'renta_base': apartamento.renta_base,
                    'direccion': apartamento.direccion,
                    'descripcion': apartamento.descripcion,
                    'numero_cuartos': apartamento.numero_cuartos,
                    'cuartos_totales': len(cuartos),
                    'cuartos_activos': len(cuartos_activos),
                    'cuartos_libres': len(cuartos) - len(cuartos_activos),
                    'tasa_ocupacion': (len(cuartos_activos) / len(cuartos) * 100) if cuartos else 0
                })
            
            return resultado
            
        except Exception as e:
            self.logger.error(f'Error al buscar apartamentos: {str(e)}')
            return []

# Instancia global del gestor
gestion_apartamentos = GestionApartamentos()



