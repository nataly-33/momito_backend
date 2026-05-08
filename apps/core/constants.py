"""Constantes globales del sistema"""

# Módulos del sistema para permisos
PERMISSIONS = {
    'usuarios': ['crear', 'leer', 'actualizar', 'eliminar'],
    'roles': ['crear', 'leer', 'actualizar', 'eliminar'],
    'productos': ['crear', 'leer', 'actualizar', 'eliminar'],
    'categorias': ['crear', 'leer', 'actualizar', 'eliminar'],
    'marcas': ['crear', 'leer', 'actualizar', 'eliminar'],
    'pedidos': ['crear', 'leer', 'actualizar', 'eliminar', 'aprobar'],
    'ventas': ['crear', 'leer', 'cancelar'],
    'clientes': ['crear', 'leer', 'actualizar'],
    'envios': ['crear', 'leer', 'actualizar', 'entregar'],
    'reportes': ['crear', 'leer', 'exportar'],
    'descuentos': ['crear', 'leer', 'actualizar', 'eliminar'],
    'dashboard': ['leer'],
}

ROLES = ['Admin', 'Empleado', 'Cliente', 'Delivery']

ESTADOS_PEDIDO = [
    ('pendiente', 'Pendiente'),
    ('confirmado', 'Confirmado'),
    ('despachado', 'Despachado'),
    ('entregado', 'Entregado'),
    ('cancelado', 'Cancelado'),
    ('pago_recibido', 'Pago recibido'),
    ('preparando', 'Preparando'),
    ('enviado', 'Enviado'),
    ('reembolsado', 'Reembolsado'),
]

METODOS_PAGO = [
    ('efectivo', 'Efectivo'),
    ('tarjeta', 'Tarjeta'),
    ('paypal', 'PayPal'),
    ('billetera', 'Billetera Virtual'),
]

ESTADOS_PAGO = [
    ('pendiente', 'Pendiente'),
    ('procesando', 'Procesando'),
    ('completado', 'Completado'),
    ('fallido', 'Fallido'),
    ('reembolsado', 'Reembolsado'),
]

TALLAS = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

COLORES = [
    'Rojo', 'Azul', 'Verde', 'Amarillo', 'Negro', 'Celeste',
    'Blanco', 'Gris', 'Rosa', 'Morado', 'Naranja', 'Lavanda'
]