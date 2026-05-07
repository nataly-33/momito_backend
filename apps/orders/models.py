from django.db import models
from apps.core.models import BaseModel
from apps.core.constants import ESTADOS_PEDIDO, METODOS_PAGO, ESTADOS_PAGO
from apps.accounts.models import User
from apps.products.models import Prenda, Talla
from apps.customers.models import Direccion, Client
from decimal import Decimal


class MetodoPago(BaseModel):
    """Métodos de pago disponibles"""
    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    requiere_procesador = models.BooleanField(default=False, verbose_name='Requiere procesador externo')
    
    # Configuración para procesadores externos
    configuracion = models.JSONField(default=dict, blank=True, verbose_name='Configuración')
    
    class Meta:
        db_table = 'metodo_pago'
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


PAYMENT_METHOD_CHOICES = [
    ('stripe', 'Stripe (Tarjeta)'),
    ('transferencia', 'Transferencia bancaria'),
    ('credito', 'Crédito'),
    ('efectivo', 'Efectivo'),
]


class Pedido(BaseModel):
    """Pedido de compra B2B"""
    # Relaciones de cliente
    usuario = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='pedidos', verbose_name='Usuario'
    )
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT,
        related_name='orders', null=True, blank=True,
        verbose_name='Cliente empresa'
    )
    seller = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales',
        verbose_name='Vendedor asignado'
    )

    # Número de pedido único
    numero_pedido = models.CharField(max_length=50, unique=True, editable=False, verbose_name='Número de pedido')

    # Dirección de envío (opcional en B2B)
    direccion_envio = models.ForeignKey(
        Direccion, on_delete=models.PROTECT,
        related_name='pedidos', null=True, blank=True,
        verbose_name='Dirección de envío'
    )
    direccion_snapshot = models.JSONField(default=dict, verbose_name='Datos de dirección')

    # Montos
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Subtotal')
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Descuento')
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo de envío')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Total')

    # Estado B2B
    estado = models.CharField(max_length=50, choices=ESTADOS_PEDIDO, default='pendiente', verbose_name='Estado')

    # Método de pago
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES,
        default='transferencia', verbose_name='Método de pago'
    )

    # Notas
    notas_cliente = models.TextField(blank=True, verbose_name='Notas del cliente')
    notas_internas = models.TextField(blank=True, verbose_name='Notas internas')
    notes = models.TextField(blank=True, verbose_name='Notas adicionales')

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    
    class Meta:
        db_table = 'pedido'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario', '-created_at']),
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['estado', '-created_at']),
        ]
    
    def __str__(self):
        return f"Pedido {self.numero_pedido}"
    
    def save(self, *args, **kwargs):
        # Generar número de pedido
        if not self.numero_pedido:
            import random
            import string
            from django.utils import timezone
            
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.numero_pedido = f"ORD-{timestamp}-{random_str}"
        
        if self.direccion_envio and not self.direccion_snapshot:
            self.direccion_snapshot = {
                'nombre_completo': self.direccion_envio.nombre_completo,
                'telefono': self.direccion_envio.telefono,
                'direccion_completa': self.direccion_envio.direccion_completa,
                'ciudad': self.direccion_envio.ciudad,
                'departamento': self.direccion_envio.departamento,
                'pais': self.direccion_envio.pais,
                'referencia': self.direccion_envio.referencia,
            }
        
        super().save(*args, **kwargs)
    
    def cambiar_estado(self, nuevo_estado, usuario_cambio=None, notas=''):
        """Cambiar estado del pedido y registrar en historial"""
        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save()
        
        # Registrar en historial
        HistorialEstadoPedido.objects.create(
            pedido=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario_cambio=usuario_cambio,
            notas=notas
        )
    
    @property
    def total_items(self):
        """Total de items en el pedido"""
        return self.detalles.aggregate(total=models.Sum('cantidad'))['total'] or 0
    
    @property
    def puede_cancelar(self):
        return self.estado in ['pendiente', 'confirmado', 'pago_recibido']


class DetallePedido(BaseModel):
    """Detalle de items en el pedido"""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Pedido'
    )
    prenda = models.ForeignKey(
        Prenda,
        on_delete=models.PROTECT,
        related_name='detalles_pedido',
        verbose_name='Prenda'
    )
    talla = models.ForeignKey(
        Talla,
        on_delete=models.PROTECT,
        related_name='detalles_pedido',
        null=True, blank=True,
        verbose_name='Talla'
    )
    
    cantidad = models.PositiveIntegerField(verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio unitario')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')
    
    # Snapshot del producto (por si se elimina o cambia)
    producto_snapshot = models.JSONField(default=dict, verbose_name='Datos del producto')
    
    class Meta:
        db_table = 'detalle_pedido'
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedidos'
        indexes = [
            models.Index(fields=['pedido', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.prenda.nombre} x{self.cantidad}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal = self.precio_unitario * self.cantidad
        
        # Guardar snapshot del producto
        if not self.producto_snapshot:
            self.producto_snapshot = {
                'nombre': self.prenda.nombre,
                'descripcion': self.prenda.descripcion,
                'marca': self.prenda.marca.nombre if self.prenda.marca else '',
                'color': self.prenda.color,
                'imagen': self.prenda.imagen_principal,
            }
        
        super().save(*args, **kwargs)


class Pago(BaseModel):
    """Registro de pagos"""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Pedido'
    )
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        related_name='pagos',
        verbose_name='Método de pago'
    )
    
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto')
    estado = models.CharField(max_length=50, choices=ESTADOS_PAGO, default='pendiente', verbose_name='Estado')
    
    # IDs de transacciones externas
    transaction_id = models.CharField(max_length=255, blank=True, verbose_name='ID de transacción')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, verbose_name='Stripe Payment Intent ID')
    paypal_order_id = models.CharField(max_length=255, blank=True, verbose_name='PayPal Order ID')
    
    # Información adicional
    response_data = models.JSONField(default=dict, blank=True, verbose_name='Datos de respuesta')
    notas = models.TextField(blank=True, verbose_name='Notas')
    
    class Meta:
        db_table = 'pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pedido', '-created_at']),
            models.Index(fields=['estado']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"Pago {self.id} - {self.pedido.numero_pedido}"
    
    def marcar_completado(self):
        """Marcar pago como completado"""
        self.estado = 'completado'
        self.save()
        
        # Actualizar estado del pedido
        if self.pedido.estado == 'pendiente':
            self.pedido.cambiar_estado('pago_recibido', notas=f'Pago completado via {self.metodo_pago.nombre}')


class HistorialEstadoPedido(BaseModel):
    """Historial de cambios de estado del pedido"""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historial_estados',
        verbose_name='Pedido'
    )
    estado_anterior = models.CharField(max_length=50, choices=ESTADOS_PEDIDO, verbose_name='Estado anterior')
    estado_nuevo = models.CharField(max_length=50, choices=ESTADOS_PEDIDO, verbose_name='Estado nuevo')
    
    usuario_cambio = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cambios_estado_pedido',
        verbose_name='Usuario que hizo el cambio'
    )
    
    notas = models.TextField(blank=True, verbose_name='Notas')
    
    class Meta:
        db_table = 'historial_estado_pedido'
        verbose_name = 'Historial de Estado'
        verbose_name_plural = 'Historial de Estados'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pedido', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.pedido.numero_pedido}: {self.estado_anterior} → {self.estado_nuevo}"


ESTADOS_ENVIO = [
    ('pendiente', 'Pendiente'),
    ('preparando', 'Preparando'),
    ('recogido', 'Recogido'),
    ('en_transito', 'En tránsito'),
    ('entregado', 'Entregado'),
    ('devuelto', 'Devuelto'),
    ('cancelado', 'Cancelado'),
]


class Envio(BaseModel):
    """Gestión de envíos de pedidos"""
    numero_seguimiento = models.CharField(
        max_length=100, 
        unique=True, 
        editable=False, 
        verbose_name='Número de seguimiento'
    )
    
    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name='envio',
        verbose_name='Pedido'
    )
    
    # Información de envío
    estado = models.CharField(
        max_length=50, 
        choices=ESTADOS_ENVIO, 
        default='pendiente', 
        verbose_name='Estado del envío'
    )
    
    # Personal de entrega
    asignado_a = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'rol__nombre': 'Delivery'},
        related_name='envios_asignados',
        verbose_name='Asignado a (Delivery)'
    )
    
    # Fechas
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de envío')
    fecha_entrega_estimada = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de entrega estimada')
    fecha_entrega_real = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de entrega real')
    
    # Información del transportista
    empresa_transportista = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Empresa transportista'
    )
    costo_envio = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='Costo del envío'
    )
    
    # Notas
    notas = models.TextField(blank=True, verbose_name='Notas')
    
    class Meta:
        db_table = 'envio'
        verbose_name = 'Envío'
        verbose_name_plural = 'Envíos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pedido', '-created_at']),
            models.Index(fields=['numero_seguimiento']),
            models.Index(fields=['estado', '-created_at']),
            models.Index(fields=['asignado_a', 'estado']),
        ]
    
    def __str__(self):
        return f"Envío {self.numero_seguimiento} - Pedido {self.pedido.numero_pedido}"
    
    def save(self, *args, **kwargs):
        # Generar número de seguimiento
        if not self.numero_seguimiento:
            import random
            import string
            from django.utils import timezone
            
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.numero_seguimiento = f"SHIP-{timestamp}-{random_str}"
        
        super().save(*args, **kwargs)