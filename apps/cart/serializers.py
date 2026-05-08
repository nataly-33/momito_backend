from rest_framework import serializers
from .models import Carrito, ItemCarrito
from apps.products.serializers import PrendaListSerializer, TallaSerializer
from apps.products.models import StockPrenda


class ItemCarritoSerializer(serializers.ModelSerializer):
    prenda_detalle = PrendaListSerializer(source='prenda', read_only=True)
    talla_detalle = TallaSerializer(source='talla', read_only=True)
    subtotal = serializers.SerializerMethodField()
    stock_disponible = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = [
            'id', 'prenda', 'prenda_detalle', 'talla', 'talla_detalle',
            'cantidad', 'precio_unitario', 'subtotal', 'stock_disponible',
            'created_at'
        ]
        read_only_fields = ['id', 'precio_unitario', 'created_at']

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_stock_disponible(self, obj):
        if obj.talla:
            stock = StockPrenda.objects.filter(prenda=obj.prenda, talla=obj.talla).first()
            return stock.cantidad if stock else 0
        return obj.prenda.stock  # B2B: stock directo en prenda


class CarritoSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    cantidad_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = ['id', 'usuario', 'items', 'total_items', 'cantidad_items',
                  'subtotal', 'total', 'created_at', 'updated_at']
        read_only_fields = ['id', 'usuario', 'created_at', 'updated_at']

    def get_items(self, obj):
        items_activos = obj.items.filter(deleted_at__isnull=True)
        return ItemCarritoSerializer(items_activos, many=True, context=self.context).data

    def get_total_items(self, obj): return obj.total_items
    def get_cantidad_items(self, obj): return obj.cantidad_total_items
    def get_subtotal(self, obj): return obj.subtotal
    def get_total(self, obj): return obj.total


class AgregarItemCarritoSerializer(serializers.Serializer):
    """
    Agrega un producto al carrito.

    - 'talla' es opcional: si el producto no tiene tallas (B2B), se omite.
    - La cantidad mínima respeta 'min_order_qty' del producto B2B.
    """
    prenda = serializers.UUIDField()
    talla = serializers.UUIDField(required=False, allow_null=True)
    cantidad = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        from apps.products.models import Prenda, Talla

        # Verificar que la prenda existe y está activa
        try:
            prenda = Prenda.objects.get(id=data['prenda'], activa=True, deleted_at__isnull=True)
            data['prenda_obj'] = prenda
        except Prenda.DoesNotExist:
            raise serializers.ValidationError({"prenda": "Producto no encontrado o no disponible"})

        cantidad = data['cantidad']

        # Validar cantidad mínima de pedido mayorista
        if prenda.min_order_qty and cantidad < prenda.min_order_qty:
            raise serializers.ValidationError({
                "cantidad": f"La cantidad mínima de pedido para este producto es {prenda.min_order_qty} unidades."
            })

        talla_id = data.get('talla')

        if talla_id:
            # Flujo B2C con talla
            try:
                talla = Talla.objects.get(id=talla_id, deleted_at__isnull=True)
                data['talla_obj'] = talla
            except Talla.DoesNotExist:
                raise serializers.ValidationError({"talla": "Talla no encontrada"})

            if not prenda.tallas_disponibles.filter(id=talla.id).exists():
                raise serializers.ValidationError({"talla": "Esta talla no está disponible para este producto"})

            stock = StockPrenda.objects.filter(prenda=prenda, talla=talla).first()
            if not stock or stock.cantidad < cantidad:
                disponible = stock.cantidad if stock else 0
                raise serializers.ValidationError({
                    "cantidad": f"Stock insuficiente. Solo hay {disponible} unidades disponibles"
                })
        else:
            # Flujo B2B sin talla — verificar stock directo
            data['talla_obj'] = None
            if prenda.stock < cantidad:
                raise serializers.ValidationError({
                    "cantidad": f"Stock insuficiente. Solo hay {prenda.stock} unidades disponibles"
                })

        return data


class ActualizarCantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=0)

    def validate_cantidad(self, value):
        if value > 9999:
            raise serializers.ValidationError("La cantidad máxima es 9999")
        return value
