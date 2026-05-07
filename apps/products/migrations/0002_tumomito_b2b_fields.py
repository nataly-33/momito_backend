"""
Migración TUMOMITO: agrega campos B2B al modelo Prenda y crea InventoryMovement
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Campos B2B en Prenda
        migrations.AddField(
            model_name='prenda',
            name='code',
            field=models.CharField(
                max_length=50, unique=True, blank=True, null=True,
                verbose_name='Código SKU'
            ),
        ),
        migrations.AddField(
            model_name='prenda',
            name='unit',
            field=models.CharField(max_length=30, default='unidad', verbose_name='Unidad de medida'),
        ),
        migrations.AddField(
            model_name='prenda',
            name='min_order_qty',
            field=models.IntegerField(default=1, verbose_name='Cantidad mínima de pedido'),
        ),
        migrations.AddField(
            model_name='prenda',
            name='price_wholesale',
            field=models.DecimalField(
                max_digits=10, decimal_places=2, default=0,
                verbose_name='Precio mayorista'
            ),
        ),
        migrations.AddField(
            model_name='prenda',
            name='price_retail',
            field=models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True,
                verbose_name='Precio retail sugerido'
            ),
        ),
        migrations.AddField(
            model_name='prenda',
            name='stock',
            field=models.IntegerField(default=0, verbose_name='Stock total'),
        ),
        migrations.AddField(
            model_name='prenda',
            name='stock_min',
            field=models.IntegerField(default=0, verbose_name='Stock mínimo (alerta)'),
        ),
        # Hacer color opcional en Prenda (ya era CharField, solo allow blank)
        migrations.AlterField(
            model_name='prenda',
            name='color',
            field=models.CharField(max_length=50, blank=True, verbose_name='Color'),
        ),
        # Hacer tallas_disponibles opcional en Prenda
        migrations.AlterField(
            model_name='prenda',
            name='tallas_disponibles',
            field=models.ManyToManyField(
                blank=True,
                related_name='prendas',
                to='products.Talla',
                verbose_name='Tallas disponibles'
            ),
        ),
        # Crear modelo InventoryMovement
        migrations.CreateModel(
            name='InventoryMovement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(null=True, blank=True, verbose_name='Fecha de eliminación')),
                ('movement_type', models.CharField(
                    max_length=20,
                    choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')],
                    verbose_name='Tipo'
                )),
                ('quantity', models.IntegerField(verbose_name='Cantidad')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='movements',
                    to='products.prenda',
                    verbose_name='Producto'
                )),
                ('user', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='inventory_movements',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario'
                )),
            ],
            options={
                'verbose_name': 'Movimiento de Inventario',
                'verbose_name_plural': 'Movimientos de Inventario',
                'db_table': 'inventory_movement',
                'ordering': ['-created_at'],
            },
        ),
    ]
