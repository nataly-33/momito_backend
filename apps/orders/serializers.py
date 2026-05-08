from rest_framework import serializers
from .models import Pedido, DetallePedido, Pago, MetodoPago, HistorialEstadoPedido, Envio, ESTADOS_ENVIO
from apps.products.serializers import PrendaListSerializer, TallaSerializer
from apps.customers.serializers import DireccionSerializer
from apps.accounts.serializers import UserSerializer
from apps.core.constants import ESTADOS_PEDIDO


class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'activo', 'requiere_procesador']


class DetallePedidoSerializer(serializers.ModelSerializer):
    prenda_detalle = PrendaListSerializer(source='prenda', read_only=True)
    talla_detalle = TallaSerializer(source='talla', read_only=True)
    
    class Meta:
        model = DetallePedido
        fields = [
            'id', 'prenda', 'prenda_detalle', 'talla', 'talla_detalle',
            'cantidad', 'precio_unitario', 'subtotal', 'producto_snapshot'
        ]
        read_only_fields = ['subtotal', 'producto_snapshot']


class PagoSerializer(serializers.ModelSerializer):
    metodo_pago_detalle = MetodoPagoSerializer(source='metodo_pago', read_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'id', 'metodo_pago', 'metodo_pago_detalle', 'monto', 'estado',
            'transaction_id', 'created_at'
        ]


class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    usuario_cambio_detalle = UserSerializer(source='usuario_cambio', read_only=True)
    
    class Meta:
        model = HistorialEstadoPedido
        fields = [
            'id', 'estado_anterior', 'estado_nuevo', 'usuario_cambio',
            'usuario_cambio_detalle', 'notas', 'created_at'
        ]


class PedidoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados — muestra empresa B2B o nombre de usuario."""
    total_items = serializers.ReadOnlyField()
    cliente_nombre = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'estado', 'estado_display',
            'total', 'total_items', 'cliente_nombre',
            'payment_method', 'created_at', 'updated_at'
        ]

    def get_cliente_nombre(self, obj):
        """Empresa B2B si existe, nombre completo del usuario si no."""
        try:
            if obj.client and obj.client.company_name:
                return obj.client.company_name
        except Exception:
            pass
        if obj.usuario:
            return f"{obj.usuario.nombre} {obj.usuario.apellido}".strip()
        return "—"

    def get_estado_display(self, obj):
        return dict([
            ('pendiente', 'Pendiente'), ('confirmado', 'Confirmado'),
            ('en_preparacion', 'En preparación'), ('despachado', 'Despachado'),
            ('entregado', 'Entregado'), ('cancelado', 'Cancelado'),
            ('pago_recibido', 'Pago recibido'), ('preparando', 'Preparando'),
            ('enviado', 'Enviado'), ('reembolsado', 'Reembolsado'),
        ]).get(obj.estado, obj.estado)


class PedidoDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalles"""
    usuario_detalle = UserSerializer(source='usuario', read_only=True)
    direccion_envio_detalle = DireccionSerializer(source='direccion_envio', read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)
    historial_estados = HistorialEstadoPedidoSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    puede_cancelar = serializers.ReadOnlyField()
    
    class Meta:
        model = Pedido
        fields = [
            'id', 'numero_pedido', 'usuario', 'usuario_detalle',
            'direccion_envio', 'direccion_envio_detalle', 'direccion_snapshot',
            'subtotal', 'descuento', 'costo_envio', 'total', 'estado',
            'notas_cliente', 'notas_internas', 'detalles', 'pagos',
            'historial_estados', 'total_items', 'puede_cancelar',
            'metadata', 'created_at', 'updated_at'
        ]


METODOS_PAGO_CHECKOUT = ['efectivo', 'tarjeta']


class CheckoutSerializer(serializers.Serializer):
    """
    Checkout TUMOMITO — acepta efectivo o tarjeta (Stripe).
    La dirección de envío es opcional: se puede guardar una existente (por ID)
    o escribir una dirección libre (direccion_texto).
    """
    direccion_envio_id = serializers.UUIDField(required=False, allow_null=True)
    direccion_texto    = serializers.CharField(required=False, allow_blank=True)
    metodo_pago        = serializers.ChoiceField(choices=METODOS_PAGO_CHECKOUT)
    notas_cliente      = serializers.CharField(required=False, allow_blank=True)
    payment_method_id  = serializers.CharField(required=False, allow_blank=True)

    def validate_direccion_envio_id(self, value):
        if value is None:
            return None
        from apps.customers.models import Direccion
        try:
            return Direccion.objects.get(
                id=value,
                usuario=self.context['request'].user,
                deleted_at__isnull=True,
            )
        except Direccion.DoesNotExist:
            raise serializers.ValidationError("Dirección no encontrada")

    def validate(self, data):
        if data.get('metodo_pago') == 'tarjeta' and not data.get('payment_method_id'):
            raise serializers.ValidationError({
                'payment_method_id': 'Requerido para pago con tarjeta.'
            })
        return data


class CambiarEstadoPedidoSerializer(serializers.Serializer):
    """Serializer para cambiar estado del pedido"""
    nuevo_estado = serializers.ChoiceField(choices=[estado[0] for estado in ESTADOS_PEDIDO])
    notas = serializers.CharField(required=False, allow_blank=True)


class EnvioListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados de envíos"""
    pedido_numero = serializers.CharField(source='pedido.numero_pedido', read_only=True)
    
    class Meta:
        model = Envio
        fields = [
            'id', 'numero_seguimiento', 'pedido', 'pedido_numero', 'estado',
            'fecha_envio', 'fecha_entrega_estimada', 'empresa_transportista',
            'created_at'
        ]


class EnvioDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalles de envíos"""
    pedido_detalle = PedidoDetailSerializer(source='pedido', read_only=True)
    asignado_a_detalle = UserSerializer(source='asignado_a', read_only=True)
    
    class Meta:
        model = Envio
        fields = [
            'id', 'numero_seguimiento', 'pedido', 'pedido_detalle', 'estado',
            'asignado_a', 'asignado_a_detalle', 'fecha_envio',
            'fecha_entrega_estimada', 'fecha_entrega_real',
            'empresa_transportista', 'costo_envio', 'notas',
            'created_at', 'updated_at'
        ]