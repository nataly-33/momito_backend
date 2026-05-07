from django.db import models
from apps.core.models import BaseModel
from apps.accounts.models import User
from apps.products.models import Prenda


class Direccion(BaseModel):
    """Direcciones de envío de los clientes"""
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='direcciones',
        verbose_name='Usuario'
    )
    
    # Datos de la dirección
    nombre_completo = models.CharField(max_length=200, verbose_name='Nombre completo')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    
    # Dirección
    direccion_linea1 = models.CharField(max_length=255, verbose_name='Dirección línea 1')
    direccion_linea2 = models.CharField(max_length=255, blank=True, verbose_name='Dirección línea 2')
    ciudad = models.CharField(max_length=100, verbose_name='Ciudad')
    departamento = models.CharField(max_length=100, verbose_name='Departamento/Estado')
    codigo_postal = models.CharField(max_length=20, blank=True, verbose_name='Código postal')
    pais = models.CharField(max_length=100, default='Bolivia', verbose_name='País')
    
    # Referencias
    referencia = models.TextField(blank=True, verbose_name='Referencias')
    
    # Estado
    es_principal = models.BooleanField(default=False, verbose_name='Es principal')
    activa = models.BooleanField(default=True, verbose_name='Activa')
    
    class Meta:
        db_table = 'direccion'
        verbose_name = 'Dirección'
        verbose_name_plural = 'Direcciones'
        ordering = ['-es_principal', '-created_at']
        indexes = [
            models.Index(fields=['usuario', 'es_principal']),
            models.Index(fields=['ciudad', 'departamento']),
        ]
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.ciudad}"
    
    def save(self, *args, **kwargs):
        # Si es principal, desmarcar las demás del mismo usuario
        if self.es_principal:
            Direccion.objects.filter(
                usuario=self.usuario, 
                es_principal=True
            ).exclude(id=self.id).update(es_principal=False)
        
        # Si es la primera dirección, marcarla como principal
        if not Direccion.objects.filter(usuario=self.usuario).exists():
            self.es_principal = True
        
        super().save(*args, **kwargs)
    
    @property
    def direccion_completa(self):
        """Retorna la dirección completa en una línea"""
        partes = [self.direccion_linea1]
        if self.direccion_linea2:
            partes.append(self.direccion_linea2)
        partes.extend([self.ciudad, self.departamento, self.pais])
        return ', '.join(partes)


class Client(BaseModel):
    """Cliente empresa B2B (supermercado, distribuidora, tienda)"""
    CLIENT_TYPES = [
        ('vip', 'VIP'),
        ('regular', 'Regular'),
        ('nuevo', 'Nuevo'),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='client_profile', verbose_name='Usuario'
    )
    company_name = models.CharField(max_length=200, verbose_name='Razón social')
    nit = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='NIT')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    address = models.TextField(blank=True, verbose_name='Dirección')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Límite de crédito')
    client_type = models.CharField(
        max_length=20, default='regular',
        choices=CLIENT_TYPES, verbose_name='Tipo de cliente'
    )

    class Meta:
        db_table = 'client'
        verbose_name = 'Cliente Empresa'
        verbose_name_plural = 'Clientes Empresa'
        ordering = ['company_name']

    def __str__(self):
        return f"{self.company_name} ({self.client_type})"


class Favoritos(BaseModel):
    """Lista de productos favoritos del cliente"""
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='favoritos',
        verbose_name='Usuario'
    )
    prenda = models.ForeignKey(
        Prenda, 
        on_delete=models.CASCADE, 
        related_name='favoritos',
        verbose_name='Prenda'
    )
    
    class Meta:
        db_table = 'favoritos'
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        unique_together = [['usuario', 'prenda']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.usuario.nombre_completo} - {self.prenda.nombre}"