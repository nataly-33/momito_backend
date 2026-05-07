from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import User, Role, Permission


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'modulo']


class RoleSerializer(serializers.ModelSerializer):
    permisos = PermissionSerializer(many=True, read_only=True)
    permisos_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'nombre', 'descripcion', 'permisos', 'permisos_ids', 'es_rol_sistema', 'created_at']

    def create(self, validated_data):
        permisos_ids = validated_data.pop('permisos_ids', [])
        role = Role.objects.create(**validated_data)
        if permisos_ids:
            role.permisos.set(permisos_ids)
        return role

    def update(self, instance, validated_data):
        permisos_ids = validated_data.pop('permisos_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permisos_ids is not None:
            instance.permisos.set(permisos_ids)
        return instance


class UserSerializer(serializers.ModelSerializer):
    rol_detalle = RoleSerializer(source='rol', read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    is_client_b2b = serializers.SerializerMethodField()
    client_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nombre', 'apellido', 'nombre_completo',
            'telefono', 'foto_perfil', 'rol', 'rol_detalle', 'rol_nombre',
            'codigo_empleado', 'activo', 'email_verificado',
            'is_client_b2b', 'client_profile',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_client_b2b(self, obj):
        """True si el usuario tiene un perfil de empresa B2B."""
        return hasattr(obj, 'client_profile') and obj.client_profile is not None

    def get_client_profile(self, obj):
        """Devuelve los datos de la empresa si el usuario es un cliente B2B."""
        try:
            profile = obj.client_profile
            if profile is None:
                return None
            return {
                'id': str(profile.id),
                'company_name': profile.company_name,
                'nit': profile.nit,
                'phone': profile.phone,
                'address': profile.address,
                'city': profile.city,
                'credit_limit': str(profile.credit_limit),
                'client_type': profile.client_type,
                'client_type_display': profile.get_client_type_display(),
            }
        except Exception:
            return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Crea un usuario y opcionalmente su perfil de empresa B2B.

    Si se incluye 'company_data' y el rol es 'Cliente', se crea
    automáticamente el Client profile en la misma transacción.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    company_data = serializers.DictField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'nombre', 'apellido',
            'telefono', 'rol', 'codigo_empleado', 'activo', 'company_data'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        company_data = validated_data.pop('company_data', None)

        with transaction.atomic():
            user = User.objects.create_user(password=password, **validated_data)

            # Si el rol es Cliente y se envió company_data, crear el perfil B2B
            if company_data and user.rol and user.rol.nombre == 'Cliente':
                from apps.customers.models import Client
                allowed_fields = {
                    'company_name', 'nit', 'phone', 'address', 'city',
                    'credit_limit', 'client_type'
                }
                clean_data = {k: v for k, v in company_data.items() if k in allowed_fields}
                if clean_data.get('company_name'):
                    Client.objects.create(user=user, **clean_data)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login JWT — devuelve tokens + datos del usuario (incluye client_profile si es B2B)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Auto-registro público de usuarios.
    Acepta opcionalmente 'company_name' para crear un perfil B2B básico.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    company_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'nombre', 'apellido',
                  'telefono', 'company_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        company_name = validated_data.pop('company_name', None)

        with transaction.atomic():
            cliente_role, _ = Role.objects.get_or_create(
                nombre='Cliente',
                defaults={'descripcion': 'Cliente empresa B2B', 'es_rol_sistema': True}
            )
            user = User.objects.create_user(
                password=password,
                rol=cliente_role,
                **validated_data
            )
            if company_name:
                from apps.customers.models import Client
                Client.objects.create(user=user, company_name=company_name)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Las contraseñas no coinciden"})
        return attrs
