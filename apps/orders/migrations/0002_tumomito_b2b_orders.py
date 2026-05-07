"""
Migración TUMOMITO: campos B2B en Pedido (client, seller, payment_method, notes)
y talla opcional en DetallePedido
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
        ('customers', '0002_client_model'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Añadir client FK a Pedido
        migrations.AddField(
            model_name='pedido',
            name='client',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='orders',
                to='customers.client',
                verbose_name='Cliente empresa'
            ),
        ),
        # Añadir seller FK a Pedido
        migrations.AddField(
            model_name='pedido',
            name='seller',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sales',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Vendedor asignado'
            ),
        ),
        # Añadir payment_method a Pedido
        migrations.AddField(
            model_name='pedido',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('stripe', 'Stripe (Tarjeta)'),
                    ('transferencia', 'Transferencia bancaria'),
                    ('credito', 'Crédito'),
                    ('efectivo', 'Efectivo'),
                ],
                default='transferencia', max_length=20,
                verbose_name='Método de pago'
            ),
        ),
        # Añadir notes a Pedido
        migrations.AddField(
            model_name='pedido',
            name='notes',
            field=models.TextField(blank=True, verbose_name='Notas adicionales'),
        ),
        # Hacer direccion_envio opcional en Pedido
        migrations.AlterField(
            model_name='pedido',
            name='direccion_envio',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pedidos',
                to='customers.direccion',
                verbose_name='Dirección de envío'
            ),
        ),
        # Hacer subtotal y total con default=0
        migrations.AlterField(
            model_name='pedido',
            name='subtotal',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, verbose_name='Subtotal'
            ),
        ),
        migrations.AlterField(
            model_name='pedido',
            name='total',
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, verbose_name='Total'
            ),
        ),
        # Hacer talla opcional en DetallePedido
        migrations.AlterField(
            model_name='detallepedido',
            name='talla',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='detalles_pedido',
                to='products.talla',
                verbose_name='Talla'
            ),
        ),
        # Actualizar estados de pedido para incluir B2B
        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmado', 'Confirmado'),
                    ('en_preparacion', 'En preparación'),
                    ('despachado', 'Despachado'),
                    ('entregado', 'Entregado'),
                    ('cancelado', 'Cancelado'),
                    ('pago_recibido', 'Pago recibido'),
                    ('preparando', 'Preparando'),
                    ('enviado', 'Enviado'),
                    ('reembolsado', 'Reembolsado'),
                ],
                default='pendiente', max_length=50, verbose_name='Estado'
            ),
        ),
        migrations.AlterField(
            model_name='historialestadopedido',
            name='estado_anterior',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmado', 'Confirmado'),
                    ('en_preparacion', 'En preparación'),
                    ('despachado', 'Despachado'),
                    ('entregado', 'Entregado'),
                    ('cancelado', 'Cancelado'),
                    ('pago_recibido', 'Pago recibido'),
                    ('preparando', 'Preparando'),
                    ('enviado', 'Enviado'),
                    ('reembolsado', 'Reembolsado'),
                ],
                max_length=50, verbose_name='Estado anterior'
            ),
        ),
        migrations.AlterField(
            model_name='historialestadopedido',
            name='estado_nuevo',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmado', 'Confirmado'),
                    ('en_preparacion', 'En preparación'),
                    ('despachado', 'Despachado'),
                    ('entregado', 'Entregado'),
                    ('cancelado', 'Cancelado'),
                    ('pago_recibido', 'Pago recibido'),
                    ('preparando', 'Preparando'),
                    ('enviado', 'Enviado'),
                    ('reembolsado', 'Reembolsado'),
                ],
                max_length=50, verbose_name='Estado nuevo'
            ),
        ),
    ]
