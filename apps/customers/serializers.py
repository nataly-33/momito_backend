from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Direccion, Favoritos, Client
from apps.products.serializers import PrendaListSerializer

User = get_user_model()


class DireccionSerializer(serializers.ModelSerializer):
    direccion_completa = serializers.ReadOnlyField()

    class Meta:
        model = Direccion
        fields = [
            'id', 'nombre_completo', 'telefono',
            'direccion_linea1', 'direccion_linea2',
            'ciudad', 'departamento', 'codigo_postal', 'pais',
            'referencia', 'es_principal', 'activa',
            'direccion_completa', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Perfil del usuario autenticado — incluye info de empresa si es Cliente B2B."""
    direccion_principal = serializers.SerializerMethodField()
    total_compras = serializers.SerializerMethodField()
    total_favoritos = serializers.SerializerMethodField()
    client_profile = serializers.SerializerMethodField()
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nombre', 'apellido', 'nombre_completo',
            'telefono', 'foto_perfil', 'rol_nombre',
            'email_verificado', 'direccion_principal', 'client_profile',
            'total_compras', 'total_favoritos', 'created_at'
        ]
        read_only_fields = ['id', 'email', 'email_verificado', 'created_at']

    def get_direccion_principal(self, obj):
        direccion = obj.direcciones.filter(es_principal=True).first()
        return DireccionSerializer(direccion).data if direccion else None

    def get_total_compras(self, obj):
        return obj.pedidos.filter(deleted_at__isnull=True).exclude(estado='cancelado').count()

    def get_total_favoritos(self, obj):
        return obj.favoritos.filter(deleted_at__isnull=True).count()

    def get_client_profile(self, obj):
        """Devuelve datos de empresa si el usuario es un cliente B2B."""
        try:
            profile = obj.client_profile
            if not profile:
                return None
            return {
                'id': str(profile.id),
                'company_name': profile.company_name,
                'nit': profile.nit,
                'city': profile.city,
                'client_type': profile.client_type,
                'client_type_display': profile.get_client_type_display(),
                'credit_limit': str(profile.credit_limit),
            }
        except Exception:
            return None


class FavoritosSerializer(serializers.ModelSerializer):
    prenda_detalle = PrendaListSerializer(source='prenda', read_only=True)

    class Meta:
        model = Favoritos
        fields = ['id', 'prenda', 'prenda_detalle', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer para clientes empresa B2B.

    Para leer: expone user_email, nombre, métricas de compra.
    Para crear/actualizar: acepta el campo 'user' (UUID del usuario existente)
      O el bloque 'new_user' para crear usuario+client en un solo paso.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    client_type_display = serializers.CharField(source='get_client_type_display', read_only=True)
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()

    # Campo write-only para crear usuario nuevo junto con el cliente
    new_user = serializers.DictField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = Client
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'company_name', 'nit', 'phone', 'address', 'city',
            'credit_limit', 'client_type', 'client_type_display',
            'total_orders', 'total_spent', 'new_user', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'user': {'required': False},
        }

    def get_user_name(self, obj):
        return f"{obj.user.nombre} {obj.user.apellido}"

    def get_total_orders(self, obj):
        return obj.orders.filter(deleted_at__isnull=True).exclude(estado='cancelado').count()

    def get_total_spent(self, obj):
        from django.db.models import Sum
        total = obj.orders.filter(
            deleted_at__isnull=True
        ).exclude(estado='cancelado').aggregate(t=Sum('total'))['t']
        return float(total or 0)

    def validate(self, attrs):
        new_user = attrs.get('new_user')
        user = attrs.get('user')
        if not user and not new_user:
            raise serializers.ValidationError(
                "Debes proveer 'user' (usuario existente) o 'new_user' (datos para crear usuario nuevo)."
            )
        if new_user and not new_user.get('email'):
            raise serializers.ValidationError({"new_user": "El campo 'email' es requerido en new_user."})
        if new_user and not new_user.get('password'):
            raise serializers.ValidationError({"new_user": "El campo 'password' es requerido en new_user."})
        return attrs

    def create(self, validated_data):
        new_user_data = validated_data.pop('new_user', None)
        user = validated_data.get('user')

        with transaction.atomic():
            if new_user_data and not user:
                # Crear usuario con rol Cliente
                from apps.accounts.models import Role
                from django.contrib.auth.hashers import make_password
                cliente_role, _ = Role.objects.get_or_create(
                    nombre='Cliente',
                    defaults={'descripcion': 'Cliente empresa B2B', 'es_rol_sistema': True}
                )
                password = new_user_data.pop('password')
                user_obj = User(
                    email=new_user_data.get('email'),
                    nombre=new_user_data.get('nombre', ''),
                    apellido=new_user_data.get('apellido', ''),
                    telefono=new_user_data.get('telefono', ''),
                    rol=cliente_role,
                    activo=True,
                )
                user_obj.set_password(password)
                user_obj.save()
                validated_data['user'] = user_obj

            client = Client.objects.create(**validated_data)
        return client
