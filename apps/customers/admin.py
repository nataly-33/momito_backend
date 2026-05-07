from django.contrib import admin
from .models import Direccion, Favoritos, Client


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'usuario', 'ciudad', 'departamento', 'es_principal', 'activa', 'created_at']
    list_filter = ['es_principal', 'activa', 'ciudad', 'departamento']
    search_fields = ['nombre_completo', 'telefono', 'ciudad', 'usuario__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Datos de Contacto', {
            'fields': ('nombre_completo', 'telefono')
        }),
        ('Dirección', {
            'fields': ('direccion_linea1', 'direccion_linea2', 'ciudad', 'departamento', 'codigo_postal', 'pais', 'referencia')
        }),
        ('Estado', {
            'fields': ('es_principal', 'activa')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Favoritos)
class FavoritosAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'prenda', 'created_at']
    list_filter = ['created_at']
    search_fields = ['usuario__email', 'prenda__nombre']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user_email', 'nit', 'city', 'client_type', 'credit_limit', 'created_at']
    list_filter = ['client_type', 'city']
    search_fields = ['company_name', 'nit', 'user__email', 'city']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user']

    fieldsets = (
        ('Usuario del sistema', {
            'fields': ('user',),
            'description': 'El usuario debe tener rol "Cliente".'
        }),
        ('Datos de la empresa', {
            'fields': ('company_name', 'nit', 'phone', 'city', 'address')
        }),
        ('Condiciones comerciales', {
            'fields': ('client_type', 'credit_limit')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email usuario'
    user_email.admin_order_field = 'user__email'