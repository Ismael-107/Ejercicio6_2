import json
from pathlib import Path


class ProductoNoDisponibleError(Exception):
    pass


class PedidoInvalidoError(Exception):
    pass


CATALOGO = {
    "teclado": {"precio": 25.0, "stock": 10},
    "raton": {"precio": 15.0, "stock": 20},
    "monitor": {"precio": 120.0, "stock": 5},
    "usb": {"precio": 8.0, "stock": 50},
}


def obtener_producto(nombre):
    if nombre not in CATALOGO:
        raise KeyError(f"Producto no encontrado: {nombre}")
    return CATALOGO[nombre]


def calcular_subtotal(lineas):
    """
    lineas = [{"producto": "teclado", "cantidad": 2}, ...]
    """
    if not lineas:
        raise PedidoInvalidoError("El pedido no puede estar vacío")

    subtotal = 0
    for linea in lineas:
        nombre = linea["producto"]
        cantidad = linea["cantidad"]

        if cantidad <= 0:
            raise PedidoInvalidoError("La cantidad debe ser mayor que cero")

        producto = obtener_producto(nombre)

        if cantidad > producto["stock"]:
            raise ProductoNoDisponibleError(
                f"Stock insuficiente para {nombre}"
            )

        subtotal += producto["precio"] * cantidad

    return round(subtotal, 2)


def aplicar_descuento(subtotal, es_vip=False, cupon=None):
    descuento = 0

    if es_vip:
        descuento += 0.10

    if cupon == "PROMO5":
        descuento += 0.05
    elif cupon == "PROMO10":
        descuento += 0.10

    if descuento > 0.20:
        descuento = 0.20

    return round(subtotal * (1 - descuento), 2)


def calcular_envio(subtotal, provincia, urgente=False):
    if subtotal >= 100:
        envio = 0
    else:
        envio = 6.5

    if provincia.lower() in ("baleares", "canarias"):
        envio += 8

    if urgente:
        envio += 5

    return round(envio, 2)


def calcular_total(lineas, provincia, es_vip=False, cupon=None, urgente=False):
    subtotal = calcular_subtotal(lineas)
    subtotal_desc = aplicar_descuento(subtotal, es_vip=es_vip, cupon=cupon)
    envio = calcular_envio(subtotal_desc, provincia, urgente=urgente)
    return round(subtotal_desc + envio, 2)


def consultar_estado_envio(codigo):
    """
    Simula una llamada a API externa.
    En un caso real esto haría requests.get(...)
    """
    if codigo.startswith("OK"):
        return {"estado": "en reparto", "incidencia": False}
    elif codigo.startswith("ERR"):
        return {"estado": "desconocido", "incidencia": True}
    else:
        raise ConnectionError("No se pudo contactar con la mensajería")


def guardar_pedido(ruta, pedido):
    ruta = Path(ruta)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(pedido, f, ensure_ascii=False, indent=2)
    return True


def cargar_pedido(ruta):
    ruta = Path(ruta)
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)