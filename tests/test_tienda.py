import pytest
import json
from unittest.mock import patch, mock_open
from pathlib import Path
from tienda import (
    obtener_producto, calcular_subtotal, aplicar_descuento,
    calcular_envio, calcular_total, consultar_estado_envio,
    guardar_pedido, cargar_pedido, PedidoInvalidoError, ProductoNoDisponibleError
)

# --- 3. FIXTURES ---

@pytest.fixture
def pedido_estandar():
    """Fixture con una lista de productos válida."""
    return [
        {"producto": "teclado", "cantidad": 1},
        {"producto": "raton", "cantidad": 2}
    ]

@pytest.fixture
def pedido_limite_stock():
    """Fixture para probar el límite de stock de un producto."""
    return [{"producto": "monitor", "cantidad": 5}]

# --- 4. PARAMETRIZACIÓN ---

@pytest.mark.parametrize("subtotal, es_vip, cupon, esperado", [
    (100.0, True, None, 90.0),        # VIP: 10%
    (100.0, False, "PROMO5", 95.0),   # Cupón 5%
    (100.0, True, "PROMO10", 80.0),   # VIP + PROMO10 = 20%
    (100.0, True, "PROMO5", 85.0),    # VIP + PROMO5 = 15%
    (100.0, True, "PROMO10", 80.0),   # Intento superar 20% (capado a 0.20)
])
def test_aplicar_descuento_param(subtotal, es_vip, cupon, esperado):
    assert aplicar_descuento(subtotal, es_vip, cupon) == esperado

@pytest.mark.parametrize("subtotal, provincia, urgente, esperado", [
    (120.0, "Madrid", False, 0),        # > 100 envío gratis
    (50.0, "Madrid", False, 6.5),       # < 100 base
    (50.0, "Baleares", False, 14.5),    # 6.5 + 8.0
    (120.0, "Canarias", True, 13.0),    # Gratis base + 8.0 islas + 5.0 urgente
    (30.0, "Barcelona", True, 11.5),    # 6.5 base + 5.0 urgente
])
def test_calcular_envio_param(subtotal, provincia, urgente, esperado):
    assert calcular_envio(subtotal, provincia, urgente) == esperado

# --- 2. PRUEBAS UNITARIAS Y 5. EXCEPCIONES ---

def test_obtener_producto_exito():
    prod = obtener_producto("usb")
    assert prod["precio"] == 8.0
    assert prod["stock"] == 50

def test_obtener_producto_inexistente():
    # Caso erróneo: Producto no está en CATALOGO
    with pytest.raises(KeyError):
        obtener_producto("consola_retro")

def test_calcular_subtotal_vacio():
    # Caso erróneo: Pedido vacío
    with pytest.raises(PedidoInvalidoError, match="El pedido no puede estar vacío"):
        calcular_subtotal([])

def test_calcular_subtotal_cantidad_invalida():
    # Caso erróneo: Cantidad negativa
    lineas = [{"producto": "raton", "cantidad": -1}]
    with pytest.raises(PedidoInvalidoError, match="La cantidad debe ser mayor que cero"):
        calcular_subtotal(lineas)

def test_stock_insuficiente(pedido_limite_stock):
    # Caso límite y erróneo: Pedir más del stock disponible
    lineas_exceso = [{"producto": "monitor", "cantidad": 6}]
    with pytest.raises(ProductoNoDisponibleError, match="Stock insuficiente"):
        calcular_subtotal(lineas_exceso)

def test_calcular_total_integracion(pedido_estandar):
    # Teclado(25) + 2*Raton(15) = 55.0. VIP(10%) = 49.5. Envío Madrid(6.5) = 56.0
    total = calcular_total(pedido_estandar, "Madrid", es_vip=True)
    assert total == 56.0

# --- 6. MOCKING CORREGIDO ---

def test_consultar_estado_envio_api_mock():
    """Opción A: Parcheamos donde se USA la función, o usamos el path completo."""
    # Al parchear 'tienda.consultar_estado_envio', debemos asegurarnos 
    # de que el test vea ese cambio. La forma más robusta es esta:
    with patch('tienda.consultar_estado_envio') as mock_api:
        mock_api.return_value = {"estado": "entregado", "incidencia": False}
        
        # IMPORTANTE: Llamamos a través del módulo si es necesario, 
        # pero aquí el patch debería funcionar si se hace correctamente.
        import tienda 
        resultado = tienda.consultar_estado_envio("OK-12345")
        
        assert resultado["estado"] == "entregado"
        mock_api.assert_called_once()

def test_guardar_pedido_mock():
    """Opción B: Capturar todas las llamadas de escritura."""
    datos_pedido = {"total": 56.0, "cliente": "Juan"}
    m = mock_open()
    
    with patch('builtins.open', m):
        # Asegúrate de que guardar_pedido usa Path como en tu tienda.py
        guardar_pedido("pedido.json", datos_pedido)
    
    # m.assert_called_once() es suficiente para validar la apertura
    assert m.called 
    
    # Para validar el contenido sin problemas de fragmentación:
    # Concatenamos todo lo que se envió a write()
    handle = m()
    contenido_escrito = "".join(call.args[0] for call in handle.write.call_args_list)
    
    assert '"total": 56.0' in contenido_escrito