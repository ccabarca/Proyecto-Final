from datetime import datetime
from typing import List, Optional

class Cuarto:
    def __init__(self, numero: int, renta: float = 0.0):
        self.numero = numero
        self.inquilino: Optional[str] = None
        self.activo: bool = False  # si hay inquilino
        self.renta: float = renta
        self.dia_vencimiento: int = 1  # día del mes para cobrar
        self.ultimo_pago: Optional[datetime] = None
        self.limpieza_ultima: Optional[datetime] = None
        self.gas_ultimo: Optional[datetime] = None

        # Historiales
        self.historial_limpieza: List[dict] = []
        self.historial_gas: List[dict] = []
        self.historial_pagos: List[dict] = []
        self.historial_inquilinos: List[dict] = []
        self.historial_solicitudes: List[dict] = []  # <<< NUEVO

        self.tiempo_limpieza: int = 0  # en minutos

    # ------ Inquilinos / disponibilidad ------
    def asignar_inquilino(self, nombre: str, renta: float):
        ahora = datetime.now()
        self.inquilino = nombre
        self.renta = renta
        self.activo = True
        self.historial_inquilinos.append({'nombre': nombre, 'fecha_asignacion': ahora})

    def desocupar(self):
        ahora = datetime.now()
        if self.inquilino:
            self.historial_inquilinos.append({'nombre': self.inquilino, 'fecha_salida': ahora})
        self.inquilino = None
        self.activo = False

    # ------ Limpieza ------
    def marcar_limpieza(self, minutos: int, motivo: str = ""):
        self.limpieza_ultima = datetime.now()
        self.tiempo_limpieza = minutos
        self.historial_limpieza.append({
            'fecha': self.limpieza_ultima,
            'minutos': minutos,
            'motivo': motivo
        })

    # ------ Gas ------
    def marcar_compra_gas(self, nota: str = ""):
        self.gas_ultimo = datetime.now()
        self.historial_gas.append({'fecha': self.gas_ultimo, 'nota': nota})

    # ------ Alquiler ------
    def marcar_pago(self, monto: float):
        self.ultimo_pago = datetime.now()
        self.historial_pagos.append({'fecha': self.ultimo_pago, 'monto': monto, 'estado': 'pagado'})

    def solicitar_pago(self, nota: str = ""):  # <<< NUEVO
        ahora = datetime.now()
        self.historial_solicitudes.append({
            'fecha': ahora,
            'nota': nota,
            'monto_sugerido': self.renta
        })
        return ahora

    def necesita_pagar_este_mes(self, hoy: Optional[datetime] = None) -> bool:
        hoy = hoy or datetime.now()
        if not self.activo:
            return False
        if self.ultimo_pago is None:
            return True
        return not (self.ultimo_pago.year == hoy.year and self.ultimo_pago.month == hoy.month)


class Apartamento:
    def __init__(self, numero: int, renta_base: float):
        self.numero = numero
        self.renta_base = renta_base
        self.cuartos: List[Cuarto] = [Cuarto(i+1, renta_base) for i in range(6)]
        self.semilla_limpieza: int = 0
        self.ultimo_gas_cuarto: Optional[int] = None

    def get_cuarto(self, n: int) -> Cuarto:
        return self.cuartos[n-1]

    def cuartos_activos(self) -> List[Cuarto]:
        return [c for c in self.cuartos if c.activo]

    # Rotación limpieza
    def responsable_limpieza_actual(self, fecha: Optional[datetime] = None) -> Optional[Cuarto]:
        fecha = fecha or datetime.now()
        activos = self.cuartos_activos()
        if not activos:
            return None
        activos_orden = sorted(activos, key=lambda c: c.numero)
        semana = fecha.isocalendar()[1]
        idx = (semana + self.semilla_limpieza) % len(activos_orden)
        return activos_orden[idx]

    def cerrar_semana_limpieza(self, minutos: int = 30, motivo: str = "") -> Optional[str]:
        cuarto = self.responsable_limpieza_actual()
        if cuarto is None:
            return "No hay inquilinos activos, no se asigna limpieza."
        cuarto.marcar_limpieza(minutos, motivo)
        self.semilla_limpieza += 1
        return f"Limpieza marcada para cuarto {cuarto.numero} ({minutos} min)."

    # Rotación gas
    def siguiente_responsable_gas(self) -> Optional[Cuarto]:
        activos = [c for c in sorted(self.cuartos, key=lambda c: c.numero) if c.activo]
        if not activos:
            return None
        if self.ultimo_gas_cuarto is None:
            return activos[0]
        numeros = [c.numero for c in activos]
        if self.ultimo_gas_cuarto not in numeros:
            return activos[0]
        pos = numeros.index(self.ultimo_gas_cuarto)
        return activos[(pos + 1) % len(activos)]

    def registrar_compra_gas(self, nota: str = "") -> Optional[str]:
        cuarto = self.siguiente_responsable_gas()
        if cuarto is None:
            return "No hay inquilinos activos para asignar compra de gas."
        cuarto.marcar_compra_gas(nota)
        self.ultimo_gas_cuarto = cuarto.numero
        return f"Gas comprado por cuarto {cuarto.numero}."

    # Pagos
    def pagos_pendientes_mes(self, fecha: Optional[datetime] = None):
        fecha = fecha or datetime.now()
        pendientes = []
        total = 0.0
        for c in self.cuartos:
            if c.necesita_pagar_este_mes(fecha):
                pendientes.append({'cuarto': c.numero, 'renta': c.renta, 'inquilino': c.inquilino})
                total += c.renta if c.activo else 0.0
        return pendientes, total

    # <<< NUEVO: compilar historial para UI
    def historial(self):
        data = {'limpieza': [], 'gas': [], 'pagos': [], 'solicitudes': [], 'inquilinos': []}
        for c in self.cuartos:
            for h in c.historial_limpieza:
                data['limpieza'].append({'cuarto': c.numero, **h})
            for h in c.historial_gas:
                data['gas'].append({'cuarto': c.numero, **h})
            for h in c.historial_pagos:
                data['pagos'].append({'cuarto': c.numero, **h})
            for h in c.historial_solicitudes:
                data['solicitudes'].append({'cuarto': c.numero, **h})
            for h in c.historial_inquilinos:
                data['inquilinos'].append({'cuarto': c.numero, **h})
        # ordenar por fecha descendente cuando exista 'fecha'
        for k in data:
            data[k].sort(key=lambda x: x.get('fecha', datetime.min), reverse=True)
        return data
