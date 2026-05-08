from django.db import models
from django.db.models import Sum, F
from apps.core.models import BaseModel
from apps.accounts.models import User
from apps.products.models import Prenda, Talla
from decimal import Decimal

class Carrito(BaseModel):
    """Carrito de compras del usuario"""
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='carrito',
        verbose_name='Usuario'
    )
    
    class Meta:
        db_table = 'carrito'
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'
    
    def __str__(self):
        return f"Carrito de {self.usuario.nombre_completo}"
    
    @property
    def total_items(self):
        """Total de items ACTIVOS en el carrito"""
        return self.items.filter(deleted_at__isnull=True).count()
    
    @property
    def cantidad_total_items(self):
        """Cantidad total de productos (suma de cantidades)"""
        result = self.items.filter(deleted_at__isnull=True).aggregate(
            total=Sum('cantidad')
        )
        return result['total'] or 0
    
    @property
    def subtotal(self):
        """Subtotal sin descuentos - solo items ACTIVOS"""
        items_activos = self.items.filter(deleted_at__isnull=True)
        return sum((item.subtotal for item in items_activos), Decimal('0.00'))
    
    @property
    def total(self):
        """Total con descuentos - solo items ACTIVOS"""
        # Por ahora es igual al subtotal, luego agregaremos descuentos
        return self.subtotal
    
    def limpiar(self):
        """Vaciar el carrito"""
        from django.utils import timezone
        self.items.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())


class ItemCarrito(BaseModel):
    """Items individuales del carrito"""
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Carrito'
    )
    prenda = models.ForeignKey(
        Prenda,
        on_delete=models.CASCADE,
        related_name='items_carrito',
        verbose_name='Prenda'
    )
    talla = models.ForeignKey(
        Talla,
        on_delete=models.CASCADE,
        related_name='items_carrito',
        null=True, blank=True,      # null para productos B2B sin talla
        verbose_name='Talla'
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio unitario'
    )

    class Meta:
        db_table = 'item_carrito'
        verbose_name = 'Item de Carrito'
        verbose_name_plural = 'Items de Carrito'
        # Nota: talla puede ser NULL (B2B), así que unique_together no puede incluirla
        # La unicidad real se maneja en la vista al buscar item existente.
        ordering = ['-created_at']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['carrito', '-created_at']),
        ]
    
    def __str__(self):
        talla_str = f" - Talla {self.talla.nombre}" if self.talla else ""
        return f"{self.prenda.nombre}{talla_str} x{self.cantidad}"
    
    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            # B2B: usar price_wholesale; B2C: usar precio normal
            if not self.talla and self.prenda.price_wholesale:
                self.precio_unitario = self.prenda.price_wholesale
            else:
                self.precio_unitario = self.prenda.precio
        super().save(*args, **kwargs)
    
    @property
    def subtotal(self):
        """Subtotal del item"""
        # Keep subtotal as Decimal to avoid mixing Decimal and float elsewhere
        from decimal import Decimal
        return (self.precio_unitario * Decimal(self.cantidad))
    
    def verificar_stock(self):
        """Verificar si hay stock disponible (B2C por talla / B2B directo en prenda)"""
        if self.talla:
            from apps.products.models import StockPrenda
            stock = StockPrenda.objects.filter(
                prenda=self.prenda, talla=self.talla
            ).first()
            if not stock:
                return False, "No hay stock para esta talla"
            if stock.cantidad < self.cantidad:
                return False, f"Solo hay {stock.cantidad} unidades disponibles"
        else:
            if self.prenda.stock < self.cantidad:
                return False, f"Solo hay {self.prenda.stock} unidades disponibles"
        return True, "Stock disponible"
    
    def soft_delete(self):
        """Soft delete del item"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])