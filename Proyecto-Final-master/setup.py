#!/usr/bin/env python3
"""
Script de configuración inicial para el sistema de gestión de apartamentos
"""

import os
import sys
from datetime import datetime

def crear_directorios():
    """Crea los directorios necesarios para el sistema"""
    directorios = [
        'backups',
        'logs',
        'static/uploads',
        'templates/partials'
    ]
    
    for directorio in directorios:
        if not os.path.exists(directorio):
            os.makedirs(directorio)
            print(f"✓ Directorio creado: {directorio}")
        else:
            print(f"✓ Directorio ya existe: {directorio}")

def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    dependencias = [
        'flask',
        'flask_sqlalchemy',
        'sqlite3'
    ]
    
    faltantes = []
    
    for dep in dependencias:
        try:
            if dep == 'sqlite3':
                import sqlite3
            else:
                __import__(dep)
            print(f"✓ {dep} está instalado")
        except ImportError:
            faltantes.append(dep)
            print(f"✗ {dep} NO está instalado")
    
    if faltantes:
        print(f"\n⚠️  Dependencias faltantes: {', '.join(faltantes)}")
        print("Instala con: pip install " + " ".join(faltantes))
        return False
    
    return True

def inicializar_base_datos():
    """Inicializa la base de datos con datos de ejemplo"""
    try:
        from main import app, db
        from models import Apartamento, Cuarto, Configuracion
        
        with app.app_context():
            # Crear todas las tablas
            db.create_all()
            print("✓ Base de datos inicializada")
            
            # Verificar si ya hay datos
            if Apartamento.query.count() == 0:
                print("✓ Creando datos de ejemplo...")
                
                # Crear apartamentos de ejemplo
                apartamentos = [
                    Apartamento(numero=1, renta_base=500.0, direccion="Calle Principal 123", descripcion="Apartamento moderno con 6 habitaciones", numero_cuartos=6),
                    Apartamento(numero=2, renta_base=550.0, direccion="Avenida Central 456", descripcion="Apartamento amplio con vista al jardín", numero_cuartos=6),
                    Apartamento(numero=3, renta_base=600.0, direccion="Calle Secundaria 789", descripcion="Apartamento premium con balcón", numero_cuartos=6),
                    Apartamento(numero=4, renta_base=650.0, direccion="Boulevard Norte 321", descripcion="Apartamento de lujo con terraza", numero_cuartos=6)
                ]
                
                for apto in apartamentos:
                    db.session.add(apto)
                
                db.session.commit()
                
                # Crear cuartos para cada apartamento
                for apto in apartamentos:
                    for i in range(1, 7):  # 6 cuartos por apartamento
                        cuarto = Cuarto(
                            numero=i,
                            renta=apto.renta_base,
                            activo=False,
                            apartamento_id=apto.id
                        )
                        db.session.add(cuarto)
                
                db.session.commit()
                
                # Crear configuraciones por defecto
                configuraciones = [
                    Configuracion(clave='dias_antes_vencimiento', valor='3', descripcion='Días antes del vencimiento para alertas'),
                    Configuracion(clave='dias_gas_agotado', valor='7', descripcion='Días sin gas para considerar agotado'),
                    Configuracion(clave='dias_limpieza_pendiente', valor='2', descripcion='Días sin limpieza para alerta'),
                    Configuracion(clave='max_recordatorios', valor='3', descripcion='Máximo número de recordatorios'),
                    Configuracion(clave='backup_automatico', valor='true', descripcion='Respaldos automáticos habilitados'),
                    Configuracion(clave='dias_retener_respaldos', valor='30', descripcion='Días para retener respaldos')
                ]
                
                for config in configuraciones:
                    db.session.add(config)
                
                db.session.commit()
                print("✓ Datos de ejemplo creados")
            else:
                print("✓ Base de datos ya contiene datos")
        
        return True
        
    except Exception as e:
        print(f"✗ Error inicializando base de datos: {e}")
        return False

def crear_script_respaldo_automatico():
    """Crea un script para respaldos automáticos"""
    script_content = '''#!/usr/bin/env python3
"""
Script para respaldos automáticos
Ejecutar con cron: 0 2 * * * /usr/bin/python3 /ruta/al/proyecto/backup_automatico.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.respaldos import sistema_respaldos
from datetime import datetime

if __name__ == "__main__":
    print(f"[{datetime.now()}] Iniciando respaldo automático...")
    
    try:
        success = sistema_respaldos.programar_respaldos_automaticos()
        if success:
            print(f"[{datetime.now()}] Respaldo automático completado exitosamente")
        else:
            print(f"[{datetime.now()}] Error en respaldo automático")
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")
'''
    
    with open('backup_automatico.py', 'w') as f:
        f.write(script_content)
    
    # Hacer el script ejecutable en sistemas Unix
    if os.name != 'nt':  # No es Windows
        os.chmod('backup_automatico.py', 0o755)
    
    print("✓ Script de respaldo automático creado: backup_automatico.py")

def crear_requirements():
    """Crea el archivo requirements.txt"""
    requirements = """Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Werkzeug==2.3.7
Jinja2==3.1.2
MarkupSafe==2.1.3
itsdangerous==2.1.2
click==8.1.7
blinker==1.6.2
SQLAlchemy==2.0.21
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    
    print("✓ Archivo requirements.txt creado")

def main():
    """Función principal de configuración"""
    print("🏠 Configuración del Sistema de Gestión de Apartamentos")
    print("=" * 60)
    
    # Verificar dependencias
    print("\n1. Verificando dependencias...")
    if not verificar_dependencias():
        print("\n❌ Instala las dependencias faltantes antes de continuar")
        return False
    
    # Crear directorios
    print("\n2. Creando directorios...")
    crear_directorios()
    
    # Crear requirements.txt
    print("\n3. Creando archivo de dependencias...")
    crear_requirements()
    
    # Inicializar base de datos
    print("\n4. Inicializando base de datos...")
    if not inicializar_base_datos():
        print("\n❌ Error inicializando la base de datos")
        return False
    
    # Crear script de respaldo
    print("\n5. Creando script de respaldo automático...")
    crear_script_respaldo_automatico()
    
    print("\n" + "=" * 60)
    print("✅ ¡Configuración completada exitosamente!")
    print("\nPara iniciar el servidor:")
    print("  python main.py")
    print("\nPara respaldos automáticos, configura cron:")
    print("  0 2 * * * /usr/bin/python3 /ruta/al/proyecto/backup_automatico.py")
    print("\nAcceso web: http://localhost:5000")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
