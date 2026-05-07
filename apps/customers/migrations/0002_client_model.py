"""
Migración TUMOMITO: Modelo Client para clientes empresa B2B
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(null=True, blank=True, verbose_name='Fecha de eliminación')),
                ('company_name', models.CharField(max_length=200, verbose_name='Razón social')),
                ('nit', models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='NIT')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='Teléfono')),
                ('address', models.TextField(blank=True, verbose_name='Dirección')),
                ('city', models.CharField(blank=True, max_length=100, verbose_name='Ciudad')),
                ('credit_limit', models.DecimalField(
                    decimal_places=2, default=0, max_digits=12, verbose_name='Límite de crédito'
                )),
                ('client_type', models.CharField(
                    choices=[('vip', 'VIP'), ('regular', 'Regular'), ('nuevo', 'Nuevo')],
                    default='regular', max_length=20, verbose_name='Tipo de cliente'
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='client_profile',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario'
                )),
            ],
            options={
                'verbose_name': 'Cliente Empresa',
                'verbose_name_plural': 'Clientes Empresa',
                'db_table': 'client',
                'ordering': ['company_name'],
            },
        ),
    ]
