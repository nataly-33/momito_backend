from django.db import models
from apps.core.models import BaseModel
from apps.customers.models import Client
from apps.products.models import Prenda
from apps.accounts.models import User


class Quote(BaseModel):
    """Cotización B2B para cliente empresa"""
    STATUS_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT,
        related_name='quotes', verbose_name='Cliente'
    )
    seller = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quotes_created', verbose_name='Vendedor'
    )
    numero_cotizacion = models.CharField(
        max_length=50, unique=True, editable=False,
        verbose_name='Número de cotización'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='borrador', verbose_name='Estado'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name='Total'
    )
    valid_until = models.DateField(
        null=True, blank=True, verbose_name='Válida hasta'
    )
    notes = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        db_table = 'quote'
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"Cotización {self.numero_cotizacion} - {self.client.company_name}"

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            import random
            import string
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            rnd = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.numero_cotizacion = f"COT-{ts}-{rnd}"
        super().save(*args, **kwargs)

    def recalculate_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total = total
        self.save(update_fields=['total'])


class QuoteItem(BaseModel):
    """Línea de producto en una cotización"""
    quote = models.ForeignKey(
        Quote, on_delete=models.CASCADE,
        related_name='items', verbose_name='Cotización'
    )
    product = models.ForeignKey(
        Prenda, on_delete=models.PROTECT,
        verbose_name='Producto'
    )
    quantity = models.IntegerField(verbose_name='Cantidad')
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Precio unitario'
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Subtotal'
    )

    class Meta:
        db_table = 'quote_item'
        verbose_name = 'Línea de Cotización'
        verbose_name_plural = 'Líneas de Cotización'

    def __str__(self):
        return f"{self.product.nombre} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
