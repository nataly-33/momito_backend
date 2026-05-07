from rest_framework import serializers
from .models import Quote, QuoteItem
from apps.products.models import Prenda


class QuoteItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.nombre', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)

    class Meta:
        model = QuoteItem
        fields = ['id', 'product', 'product_name', 'product_code',
                  'quantity', 'unit_price', 'subtotal']
        read_only_fields = ['id', 'subtotal', 'product_name', 'product_code']


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, required=False)
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    seller_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Quote
        fields = [
            'id', 'numero_cotizacion', 'client', 'client_name',
            'seller', 'seller_name', 'status', 'status_display',
            'total', 'valid_until', 'notes', 'items', 'created_at'
        ]
        read_only_fields = ['id', 'numero_cotizacion', 'total', 'created_at']

    def get_seller_name(self, obj):
        if obj.seller:
            return f"{obj.seller.nombre} {obj.seller.apellido}"
        return None

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        quote = Quote.objects.create(**validated_data)
        for item_data in items_data:
            QuoteItem.objects.create(quote=quote, **item_data)
        quote.recalculate_total()
        return quote

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                QuoteItem.objects.create(quote=instance, **item_data)
            instance.recalculate_total()
        return instance
