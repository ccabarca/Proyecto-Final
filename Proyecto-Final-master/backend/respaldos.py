import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
import gzip
import json

class SistemaRespaldos:
    """Sistema automático de respaldos para la base de datos"""
    
    def __init__(self, db_path: str = "apartamentos.db", backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Asegura que el directorio de respaldos existe"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def crear_respaldo_completo(self) -> str:
        """Crea un respaldo completo de la base de datos"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"respaldo_completo_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Copiar la base de datos
            shutil.copy2(self.db_path, backup_path)
            
            # Comprimir el respaldo
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Eliminar el archivo sin comprimir
            os.remove(backup_path)
            
            # Crear metadatos del respaldo
            metadata = {
                'fecha_creacion': datetime.now().isoformat(),
                'tipo': 'completo',
                'tamaño_original': os.path.getsize(self.db_path),
                'tamaño_comprimido': os.path.getsize(compressed_path),
                'archivo': compressed_path
            }
            
            metadata_path = f"{compressed_path}.meta"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return compressed_path
            
        except Exception as e:
            raise Exception(f"Error creando respaldo: {str(e)}")
    
    def crear_respaldo_incremental(self) -> str:
        """Crea un respaldo incremental (solo cambios desde el último respaldo)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"respaldo_incremental_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Obtener el último respaldo para comparar
            ultimo_respaldo = self.obtener_ultimo_respaldo()
            fecha_ultimo = None
            
            if ultimo_respaldo:
                fecha_ultimo = datetime.fromisoformat(ultimo_respaldo['fecha_creacion'])
            
            # Extraer solo los cambios recientes
            cambios = self.extraer_cambios_desde(fecha_ultimo)
            
            # Crear respaldo incremental
            respaldo_data = {
                'fecha_creacion': datetime.now().isoformat(),
                'tipo': 'incremental',
                'fecha_base': fecha_ultimo.isoformat() if fecha_ultimo else None,
                'cambios': cambios
            }
            
            with open(backup_path, 'w') as f:
                json.dump(respaldo_data, f, indent=2, default=str)
            
            # Comprimir
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            os.remove(backup_path)
            
            return compressed_path
            
        except Exception as e:
            raise Exception(f"Error creando respaldo incremental: {str(e)}")
    
    def extraer_cambios_desde(self, fecha_desde: datetime = None) -> Dict:
        """Extrae cambios desde una fecha específica"""
        if not fecha_desde:
            fecha_desde = datetime.now() - timedelta(days=1)
        
        cambios = {
            'pagos': [],
            'limpiezas': [],
            'gas': [],
            'solicitudes': [],
            'notificaciones': [],
            'cuartos_modificados': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Pagos recientes
            cursor.execute("""
                SELECT * FROM pagos 
                WHERE fecha > ? 
                ORDER BY fecha DESC
            """, (fecha_desde,))
            cambios['pagos'] = [dict(row) for row in cursor.fetchall()]
            
            # Limpiezas recientes
            cursor.execute("""
                SELECT * FROM limpiezas 
                WHERE fecha > ? 
                ORDER BY fecha DESC
            """, (fecha_desde,))
            cambios['limpiezas'] = [dict(row) for row in cursor.fetchall()]
            
            # Gas reciente
            cursor.execute("""
                SELECT * FROM gas 
                WHERE fecha > ? 
                ORDER BY fecha DESC
            """, (fecha_desde,))
            cambios['gas'] = [dict(row) for row in cursor.fetchall()]
            
            # Solicitudes recientes
            cursor.execute("""
                SELECT * FROM solicitudes_pago 
                WHERE fecha_solicitud > ? 
                ORDER BY fecha_solicitud DESC
            """, (fecha_desde,))
            cambios['solicitudes'] = [dict(row) for row in cursor.fetchall()]
            
            # Notificaciones recientes
            cursor.execute("""
                SELECT * FROM notificaciones 
                WHERE fecha > ? 
                ORDER BY fecha DESC
            """, (fecha_desde,))
            cambios['notificaciones'] = [dict(row) for row in cursor.fetchall()]
            
            # Cuartos modificados
            cursor.execute("""
                SELECT * FROM cuartos 
                WHERE ultimo_pago > ? OR limpieza_ultima > ? OR gas_ultimo > ?
                ORDER BY id
            """, (fecha_desde, fecha_desde, fecha_desde))
            cambios['cuartos_modificados'] = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
        except Exception as e:
            print(f"Error extrayendo cambios: {e}")
        
        return cambios
    
    def obtener_lista_respaldos(self) -> List[Dict]:
        """Obtiene la lista de todos los respaldos disponibles"""
        respaldos = []
        
        if not os.path.exists(self.backup_dir):
            return respaldos
        
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.gz'):
                filepath = os.path.join(self.backup_dir, filename)
                metadata_path = f"{filepath}.meta"
                
                # Obtener metadatos si existen
                metadata = {}
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                # Información del archivo
                stat = os.stat(filepath)
                respaldos.append({
                    'archivo': filename,
                    'ruta': filepath,
                    'tamaño': stat.st_size,
                    'fecha_modificacion': datetime.fromtimestamp(stat.st_mtime),
                    'tipo': metadata.get('tipo', 'desconocido'),
                    'fecha_creacion': metadata.get('fecha_creacion', stat.st_mtime),
                    'tamaño_original': metadata.get('tamaño_original', stat.st_size)
                })
        
        # Ordenar por fecha de modificación (más recientes primero)
        respaldos.sort(key=lambda x: x['fecha_modificacion'], reverse=True)
        return respaldos
    
    def obtener_ultimo_respaldo(self) -> Dict:
        """Obtiene el último respaldo creado"""
        respaldos = self.obtener_lista_respaldos()
        return respaldos[0] if respaldos else None
    
    def restaurar_respaldo(self, backup_path: str) -> bool:
        """Restaura la base de datos desde un respaldo"""
        try:
            # Verificar que el respaldo existe
            if not os.path.exists(backup_path):
                raise Exception("Archivo de respaldo no encontrado")
            
            # Crear respaldo de la base actual antes de restaurar
            respaldo_actual = self.crear_respaldo_completo()
            print(f"Respaldo de seguridad creado: {respaldo_actual}")
            
            # Descomprimir si es necesario
            if backup_path.endswith('.gz'):
                temp_path = backup_path[:-3]  # Remover .gz
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path
            
            # Restaurar la base de datos
            shutil.copy2(backup_path, self.db_path)
            
            # Limpiar archivo temporal si se creó
            if backup_path.endswith('.db') and not backup_path.endswith('.gz'):
                if os.path.exists(backup_path) and backup_path != self.db_path:
                    os.remove(backup_path)
            
            return True
            
        except Exception as e:
            raise Exception(f"Error restaurando respaldo: {str(e)}")
    
    def limpiar_respaldos_antiguos(self, dias_retener: int = 30):
        """Elimina respaldos más antiguos que el número de días especificado"""
        fecha_limite = datetime.now() - timedelta(days=dias_retener)
        respaldos = self.obtener_lista_respaldos()
        eliminados = 0
        
        for respaldo in respaldos:
            if respaldo['fecha_modificacion'] < fecha_limite:
                try:
                    # Eliminar archivo principal
                    if os.path.exists(respaldo['ruta']):
                        os.remove(respaldo['ruta'])
                    
                    # Eliminar metadatos si existen
                    metadata_path = f"{respaldo['ruta']}.meta"
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    
                    eliminados += 1
                except Exception as e:
                    print(f"Error eliminando respaldo {respaldo['archivo']}: {e}")
        
        return eliminados
    
    def programar_respaldos_automaticos(self):
        """Programa respaldos automáticos (debe ejecutarse como tarea programada)"""
        try:
            # Verificar si ya existe un respaldo hoy
            respaldos_hoy = self.obtener_respaldos_del_dia()
            
            if not respaldos_hoy:
                # Crear respaldo completo diario
                respaldo_path = self.crear_respaldo_completo()
                print(f"Respaldo automático creado: {respaldo_path}")
            
            # Limpiar respaldos antiguos
            eliminados = self.limpiar_respaldos_antiguos()
            if eliminados > 0:
                print(f"Eliminados {eliminados} respaldos antiguos")
            
            return True
            
        except Exception as e:
            print(f"Error en respaldo automático: {e}")
            return False
    
    def obtener_respaldos_del_dia(self) -> List[Dict]:
        """Obtiene respaldos creados hoy"""
        hoy = datetime.now().date()
        respaldos = self.obtener_lista_respaldos()
        
        return [r for r in respaldos if r['fecha_modificacion'].date() == hoy]
    
    def obtener_estadisticas_respaldos(self) -> Dict:
        """Obtiene estadísticas de los respaldos"""
        respaldos = self.obtener_lista_respaldos()
        
        if not respaldos:
            return {
                'total_respaldos': 0,
                'tamaño_total': 0,
                'ultimo_respaldo': None,
                'respaldos_hoy': 0
            }
        
        hoy = datetime.now().date()
        respaldos_hoy = [r for r in respaldos if r['fecha_modificacion'].date() == hoy]
        
        return {
            'total_respaldos': len(respaldos),
            'tamaño_total': sum(r['tamaño'] for r in respaldos),
            'ultimo_respaldo': respaldos[0]['fecha_modificacion'] if respaldos else None,
            'respaldos_hoy': len(respaldos_hoy),
            'tamaño_promedio': sum(r['tamaño'] for r in respaldos) / len(respaldos) if respaldos else 0
        }

# Instancia global del sistema de respaldos
sistema_respaldos = SistemaRespaldos()



