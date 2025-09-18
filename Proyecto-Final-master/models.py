from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Apartamento(db.Model):
    __tablename__ = "apartamentos"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    renta_base = db.Column(db.Float, nullable=False)
    direccion = db.Column(db.String(255))
    descripcion = db.Column(db.Text)
    numero_cuartos = db.Column(db.Integer, default=6)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

    cuartos = db.relationship("Cuarto", backref="apartamento", lazy=True, cascade="all, delete-orphan")

class Cuarto(db.Model):
    __tablename__ = "cuartos"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    renta = db.Column(db.Float, default=0.0)
    activo = db.Column(db.Boolean, default=False)
    inquilino = db.Column(db.String(120))
    ultimo_pago = db.Column(db.DateTime)
    limpieza_ultima = db.Column(db.DateTime)
    gas_ultimo = db.Column(db.DateTime)
    
    # Nuevos campos para control de pagos
    tipo_contrato = db.Column(db.String(20), default="mensual")  # "mensual" o "quincenal"
    fecha_entrada = db.Column(db.DateTime)  # Fecha cuando entró el inquilino
    proximo_pago = db.Column(db.DateTime)  # Fecha del próximo pago calculada

    apartamento_id = db.Column(db.Integer, db.ForeignKey("apartamentos.id"), nullable=False)

    pagos = db.relationship("Pago", backref="cuarto", lazy=True, cascade="all, delete-orphan")
    limpiezas = db.relationship("Limpieza", backref="cuarto", lazy=True, cascade="all, delete-orphan")
    compras_gas = db.relationship("Gas", backref="cuarto", lazy=True, cascade="all, delete-orphan")

class Pago(db.Model):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    monto = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(50), default="pagado")
    cuarto_id = db.Column(db.Integer, db.ForeignKey("cuartos.id"), nullable=False)

class Limpieza(db.Model):
    __tablename__ = "limpiezas"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    minutos = db.Column(db.Integer, default=30)
    motivo = db.Column(db.String(255))
    cuarto_id = db.Column(db.Integer, db.ForeignKey("cuartos.id"), nullable=False)

class Gas(db.Model):
    __tablename__ = "gas"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    nota = db.Column(db.String(255))
    cuarto_id = db.Column(db.Integer, db.ForeignKey("cuartos.id"), nullable=False)

class SolicitudPago(db.Model):
    __tablename__ = "solicitudes_pago"
    id = db.Column(db.Integer, primary_key=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime)
    monto = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(50), default="pendiente")  # pendiente, pagado, vencido
    nota = db.Column(db.String(255))
    recordatorios_enviados = db.Column(db.Integer, default=0)
    cuarto_id = db.Column(db.Integer, db.ForeignKey("cuartos.id"), nullable=False)

class Notificacion(db.Model):
    __tablename__ = "notificaciones"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(50), nullable=False)  # pago_vencido, gas_agotado, limpieza_pendiente
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.String(255))
    leida = db.Column(db.Boolean, default=False)
    prioridad = db.Column(db.String(20), default="media")  # baja, media, alta, critica
    cuarto_id = db.Column(db.Integer, db.ForeignKey("cuartos.id"), nullable=True)
    apartamento_id = db.Column(db.Integer, db.ForeignKey("apartamentos.id"), nullable=True)

class Configuracion(db.Model):
    __tablename__ = "configuraciones"
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.String(255))
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)