from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, LoginAudit


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'nombre', 'apellido', 'rol', 'activo', 'created_at']
    list_filter = ['rol', 'activo', 'email_verificado']
    search_fields = ['email', 'nombre', 'apellido', 'codigo_empleado']
    ordering = ['-created_at']
    filter_horizontal = ()
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('email', 'nombre', 'apellido', 'telefono', 'foto_perfil')
        }),
        ('Permisos y Rol', {
            'fields': ('rol', 'activo', 'email_verificado', 'is_staff', 'is_superuser')
        }),
        ('Información Adicional', {
            'fields': ('codigo_empleado',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Crear Usuario', {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellido', 'password1', 'password2', 'rol', 'activo'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'es_rol_sistema', 'created_at']
    search_fields = ['nombre']
    filter_horizontal = ['permisos']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'modulo', 'created_at']
    list_filter = ['modulo']
    search_fields = ['codigo', 'nombre']


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'success', 'created_at']
    list_filter = ['success', 'created_at']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'success', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False