from models import db, Cuarto, Pago, Limpieza, Gas
from datetime import datetime

def toggle_disponibilidad(cuarto: Cuarto, activo: bool, nombre: str, renta: float):
    cuarto.activo = activo
    if activo:
        cuarto.inquilino = nombre
        cuarto.renta = renta
    else:
        cuarto.inquilino = None
        cuarto.renta = 0
    db.session.commit()
    return f"Disponibilidad de cuarto {cuarto.numero} actualizada"

def marcar_limpieza_manual(apto, cuarto_num, minutos=30, motivo=""):
    cuarto = Cuarto.query.filter_by(apartamento_id=apto.id, numero=cuarto_num).first()
    if not cuarto:
        return "Cuarto no encontrado"
    limpieza = Limpieza(cuarto_id=cuarto.id, minutos=minutos, motivo=motivo)
    cuarto.limpieza_ultima = datetime.utcnow()
    db.session.add(limpieza)
    db.session.commit()
    return f"Limpieza registrada en cuarto {cuarto_num}"

def swap_responsables(apto, a, b, motivo=""):
    # Aquí la lógica de intercambio de responsables
    return f"Responsables intercambiados entre cuartos {a} y {b}"

def marcar_pago_cuarto(cuarto: Cuarto, monto: float):
    pago = Pago(cuarto_id=cuarto.id, monto=monto)
    cuarto.ultimo_pago = datetime.utcnow()
    db.session.add(pago)
    db.session.commit()
    return f"Pago de {monto} registrado en cuarto {cuarto.numero}"

def asignar_inquilino_y_renta(cuarto: Cuarto, nombre: str, renta: float):
    cuarto.activo = True
    cuarto.inquilino = nombre
    cuarto.renta = renta
    db.session.commit()
    return f"Inquilino {nombre} asignado al cuarto {cuarto.numero}"

def liberar_cuarto(cuarto: Cuarto):
    cuarto.activo = False
    cuarto.inquilino = None
    cuarto.renta = 0
    db.session.commit()
    return f"Cuarto {cuarto.numero} liberado"

def solicitar_pago_cuarto(cuarto: Cuarto, nota: str):
    # Aquí podrías registrar en otra tabla de "solicitudes" si quieres
    return f"Pago solicitado al cuarto {cuarto.numero}. Nota: {nota}"
