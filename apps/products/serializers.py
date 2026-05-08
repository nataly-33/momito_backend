from rest_framework import serializers
from .models import Categoria, Marca, Talla, Prenda, StockPrenda, ImagenPrendaURL, InventoryMovement


class CategoriaSerializer(serializers.ModelSerializer):
    total_prendas = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'imagen', 'imagen_url', 'activa', 'total_prendas', 'created_at']
        read_only_fields = ['id', 'created_at', 'imagen_url']

    def get_total_prendas(self, obj):
        return obj.prendas.filter(activa=True, deleted_at__isnull=True).count()

    def get_imagen_url(self, obj):
        if obj.imagen:
            return obj.imagen.url
        return None


class MarcaSerializer(serializers.ModelSerializer):
    total_prendas = serializers.SerializerMethodField()
    
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'descripcion', 'activa', 'total_prendas', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_total_prendas(self, obj):
        return obj.prendas.filter(activa=True, deleted_at__isnull=True).count()


class TallaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Talla
        fields = ['id', 'nombre', 'orden']
        read_only_fields = ['id']


class ImagenPrendaURLSerializer(serializers.ModelSerializer):
    """Serializer para imágenes URL (S3)"""
    class Meta:
        model = ImagenPrendaURL
        fields = ['id', 'imagen_url', 'es_principal', 'orden', 'alt_text']
        read_only_fields = ['id', 'imagen_url']


class StockPrendaSerializer(serializers.ModelSerializer):
    talla_detalle = TallaSerializer(source='talla', read_only=True)
    alerta_stock_bajo = serializers.ReadOnlyField()
    
    class Meta:
        model = StockPrenda
        fields = ['id', 'talla', 'talla_detalle', 'cantidad', 'stock_minimo', 'alerta_stock_bajo']
        read_only_fields = ['id', 'alerta_stock_bajo']
    
    def to_representation(self, instance):
        """Mostrar talla_detalle en respuestas GET"""
        ret = super().to_representation(instance)
        ret['talla_detalle'] = TallaSerializer(instance.talla).data
        return ret


class PrendaListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados (B2B)"""
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    category_name = serializers.ReadOnlyField()
    imagen_principal = serializers.ReadOnlyField()
    stock_total = serializers.ReadOnlyField()
    tiene_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Prenda
        fields = [
            'id', 'code', 'nombre', 'precio', 'price_wholesale', 'price_retail',
            'unit', 'min_order_qty', 'stock', 'stock_min', 'stock_total',
            'marca_nombre', 'category_name', 'imagen_principal',
            'tiene_stock', 'is_low_stock', 'activa', 'slug', 'created_at',
        ]


class PrendaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalles (B2B)"""
    marca_detalle = MarcaSerializer(source='marca', read_only=True)
    categorias_detalle = CategoriaSerializer(source='categorias', many=True, read_only=True)
    tallas_disponibles_detalle = TallaSerializer(source='tallas_disponibles', many=True, read_only=True)
    imagenes_url = ImagenPrendaURLSerializer(many=True, read_only=True)
    stocks = StockPrendaSerializer(many=True, read_only=True)
    stock_total = serializers.ReadOnlyField()
    tiene_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    category_name = serializers.ReadOnlyField()

    class Meta:
        model = Prenda
        fields = [
            'id', 'code', 'nombre', 'descripcion', 'precio',
            'price_wholesale', 'price_retail', 'unit', 'min_order_qty',
            'stock', 'stock_min', 'stock_total', 'is_low_stock',
            'marca', 'marca_detalle', 'categorias', 'categorias_detalle',
            'category_name', 'tallas_disponibles', 'tallas_disponibles_detalle',
            'color', 'material', 'activa', 'destacada', 'es_novedad',
            'imagenes_url', 'stocks', 'tiene_stock',
            'slug', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'stock_total', 'created_at', 'updated_at']


class InventoryMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.nombre', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    user_name = serializers.SerializerMethodField()
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)

    class Meta:
        model = InventoryMovement
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'user', 'user_name', 'movement_type', 'movement_type_display',
            'quantity', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.nombre} {obj.user.apellido}"
        return None


class PrendaCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar productos B2B"""
    stocks = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    imagen = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Prenda
        fields = [
            'nombre', 'descripcion', 'precio', 'price_wholesale', 'price_retail',
            'unit', 'min_order_qty', 'stock', 'stock_min',
            'marca', 'categorias', 'tallas_disponibles', 'color', 'material',
            'activa', 'destacada', 'es_novedad', 'metadata', 'stocks', 'code', 'imagen'
        ]

    def to_internal_value(self, data):
        """
        Parsear el campo stocks si viene como JSON string (desde FormData)
        """
        import json

        # Si stocks viene como string JSON (desde FormData), parsearlo
        if 'stocks' in data and isinstance(data.get('stocks'), str):
            try:
                # Crear una copia mutable de data si es un QueryDict
                if hasattr(data, '_mutable'):
                    data._mutable = True

                parsed_stocks = json.loads(data['stocks'])
                data['stocks'] = parsed_stocks

                if hasattr(data, '_mutable'):
                    data._mutable = False
            except (json.JSONDecodeError, TypeError) as e:
                raise serializers.ValidationError({
                    'stocks': f'El campo stocks debe ser un JSON válido: {str(e)}'
                })

        return super().to_internal_value(data)
    
    def create(self, validated_data):
        categorias = validated_data.pop('categorias', [])
        tallas = validated_data.pop('tallas_disponibles', [])
        stocks_data = validated_data.pop('stocks', [])
        
        prenda = Prenda.objects.create(**validated_data)
        prenda.categorias.set(categorias)
        prenda.tallas_disponibles.set(tallas)
        
        # Crear stocks por talla si se proporcionan
        for stock_data in stocks_data:
            if isinstance(stock_data, dict):
                talla_id = stock_data.get('talla')
                cantidad = int(stock_data.get('cantidad', 0))
                stock_minimo = int(stock_data.get('stock_minimo', 5))
                
                if talla_id:
                    StockPrenda.objects.get_or_create(
                        prenda=prenda,
                        talla_id=talla_id,
                        defaults={'cantidad': cantidad, 'stock_minimo': stock_minimo}
                    )
        
        return prenda
    
    def update(self, instance, validated_data):
        categorias = validated_data.pop('categorias', None)
        tallas = validated_data.pop('tallas_disponibles', None)
        stocks_data = validated_data.pop('stocks', None)
        
        # Actualizar campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar relaciones many-to-many
        if categorias is not None:
            instance.categorias.set(categorias)
        if tallas is not None:
            instance.tallas_disponibles.set(tallas)
        
        # Actualizar stocks si se proporcionan
        if stocks_data is not None:
            # Obtener IDs de tallas en el nuevo stock
            new_talla_ids = set()
            
            for stock_data in stocks_data:
                if isinstance(stock_data, dict):
                    talla_id = stock_data.get('talla')
                    cantidad = int(stock_data.get('cantidad', 0))
                    stock_minimo = int(stock_data.get('stock_minimo', 5))
                    
                    if talla_id:
                        new_talla_ids.add(talla_id)
                        stock, created = StockPrenda.objects.get_or_create(
                            prenda=instance,
                            talla_id=talla_id,
                            defaults={'cantidad': cantidad, 'stock_minimo': stock_minimo}
                        )
                        
                        if not created:
                            stock.cantidad = cantidad
                            stock.stock_minimo = stock_minimo
                            stock.save()
            
            # Eliminar stocks de tallas que ya no están en el nuevo set
            instance.stocks.exclude(talla_id__in=new_talla_ids).delete()
        
        return instance