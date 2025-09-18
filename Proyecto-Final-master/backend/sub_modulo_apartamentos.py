from models import db, Apartamento, Cuarto

def agregar_apartamento(numero, renta_base):
    apto = Apartamento(numero=numero, renta_base=renta_base)
    db.session.add(apto)
    for i in range(1, 7):  # cada apartamento tiene 6 cuartos
        cuarto = Cuarto(numero=i, renta=renta_base, apartamento=apto)
        db.session.add(cuarto)
    db.session.commit()
    return apto

def obtener_apartamentos():
    return Apartamento.query.all()

def obtener_apartamento(numero):
    return Apartamento.query.filter_by(numero=numero).first()

def eliminar_apartamento(numero):
    apto = obtener_apartamento(numero)
    if apto:
        db.session.delete(apto)
        db.session.commit()
