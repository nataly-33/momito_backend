"""
Migración inicial del módulo de Cotizaciones TUMOMITO
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('customers', '0002_client_model'),
        ('products', '0002_tumomito_b2b_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(null=True, blank=True, verbose_name='Fecha de eliminación')),
                ('numero_cotizacion', models.CharField(
                    editable=False, max_length=50, unique=True,
                    verbose_name='Número de cotización'
                )),
                ('status', models.CharField(
                    choices=[
                        ('borrador', 'Borrador'),
                        ('enviada', 'Enviada'),
                        ('aceptada', 'Aceptada'),
                        ('rechazada', 'Rechazada'),
                    ],
                    default='borrador', max_length=20, verbose_name='Estado'
                )),
                ('total', models.DecimalField(
                    decimal_places=2, default=0, max_digits=12, verbose_name='Total'
                )),
                ('valid_until', models.DateField(null=True, blank=True, verbose_name='Válida hasta')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='quotes',
                    to='customers.client',
                    verbose_name='Cliente'
                )),
                ('seller', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='quotes_created',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Vendedor'
                )),
            ],
            options={
                'verbose_name': 'Cotización',
                'verbose_name_plural': 'Cotizaciones',
                'db_table': 'quote',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='QuoteItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(null=True, blank=True, verbose_name='Fecha de eliminación')),
                ('quantity', models.IntegerField(verbose_name='Cantidad')),
                ('unit_price', models.DecimalField(
                    decimal_places=2, max_digits=10, verbose_name='Precio unitario'
                )),
                ('subtotal', models.DecimalField(
                    decimal_places=2, max_digits=12, verbose_name='Subtotal'
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to='products.prenda',
                    verbose_name='Producto'
                )),
                ('quote', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='quotes.quote',
                    verbose_name='Cotización'
                )),
            ],
            options={
                'verbose_name': 'Línea de Cotización',
                'verbose_name_plural': 'Líneas de Cotización',
                'db_table': 'quote_item',
            },
        ),
    ]
