"""
Migración: hace talla opcional en ItemCarrito para soportar productos B2B sin talla.
También elimina unique_together que incluía talla (NULL != NULL en SQL).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0001_initial'),
        ('products', '0001_initial'),
    ]

    operations = [
        # Eliminar unique_together que incluía talla (no funciona bien con NULL)
        migrations.AlterUniqueTogether(
            name='itemcarrito',
            unique_together=set(),
        ),
        # Hacer talla nullable
        migrations.AlterField(
            model_name='itemcarrito',
            name='talla',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='items_carrito',
                to='products.talla',
                verbose_name='Talla',
            ),
        ),
    ]
