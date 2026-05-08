"""
Seeder masivo de datos para TUMOMITO S.A.
Genera: categorías, marcas, 50+ productos, 30+ clientes empresa, ~12.000 pedidos (2021-2024)

Uso:
    python manage.py seed_tumomito
    python manage.py seed_tumomito --clear   # limpia datos anteriores primero
"""
import random
import string
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


CATEGORIES = ['Juguetes', 'Iluminación', 'Ropa y Accesorios', 'Bazar', 'Ferretería', 'Decoración']

BRANDS = {
    'Juguetes': 'Chikipoon',
    'Iluminación': 'Acricolor',
    'Ropa y Accesorios': 'Funky Fish',
    'Bazar': 'Chikipoon',
    'Ferretería': 'Acricolor',
    'Decoración': 'Funky Fish',
}

PRODUCTS_BY_CATEGORY = {
    'Juguetes': [
        ('Muñeca Princesa Sofía', 'CHK-001', 35, 45, 'unidad', 6),
        ('Auto Teledirigido Pro', 'CHK-002', 55, 70, 'unidad', 3),
        ('Set Lego 200 piezas', 'CHK-003', 80, 100, 'unidad', 3),
        ('Pelota Saltarina XL', 'CHK-004', 15, 22, 'unidad', 12),
        ('Triciclo Infantil', 'CHK-005', 120, 150, 'unidad', 2),
        ('Juego de Mesa Familia', 'CHK-006', 45, 60, 'unidad', 6),
        ('Patines Ajustables', 'CHK-007', 75, 95, 'par', 3),
        ('Peluche Oso Gigante', 'CHK-008', 60, 80, 'unidad', 3),
        ('Set Cocina Infantil', 'CHK-009', 95, 120, 'unidad', 2),
        ('Pistola de Burbujas', 'CHK-010', 18, 25, 'unidad', 12),
    ],
    'Iluminación': [
        ('Lámpara LED Escritorio', 'ACR-001', 120, 160, 'unidad', 3),
        ('Tira LED RGB 5m', 'ACR-002', 85, 110, 'rollo', 3),
        ('Foco Ahorrador 20W', 'ACR-003', 12, 18, 'unidad', 24),
        ('Lámpara de Pie Moderna', 'ACR-004', 280, 360, 'unidad', 1),
        ('Bombilla Filamento E27', 'ACR-005', 25, 35, 'unidad', 12),
        ('Panel LED 60x60cm', 'ACR-006', 320, 420, 'unidad', 1),
        ('Lámpara Solar Jardín', 'ACR-007', 45, 65, 'unidad', 6),
        ('Foco Dicroico LED', 'ACR-008', 18, 28, 'unidad', 24),
        ('Reflector LED 50W', 'ACR-009', 180, 240, 'unidad', 2),
        ('Lámpara Noche Infantil', 'ACR-010', 35, 50, 'unidad', 6),
    ],
    'Ropa y Accesorios': [
        ('Camisa Oxford Hombre', 'FNK-001', 95, 130, 'unidad', 6),
        ('Vestido Casual Mujer', 'FNK-002', 110, 150, 'unidad', 6),
        ('Jean Slim Fit', 'FNK-003', 130, 175, 'unidad', 6),
        ('Polo Algodón Unisex', 'FNK-004', 45, 65, 'unidad', 12),
        ('Chaqueta Impermeable', 'FNK-005', 220, 295, 'unidad', 3),
        ('Blusa Floral', 'FNK-006', 75, 100, 'unidad', 6),
        ('Pantalón Deportivo', 'FNK-007', 85, 115, 'unidad', 6),
        ('Bufanda Lana', 'FNK-008', 35, 50, 'unidad', 12),
        ('Cinturón Cuero', 'FNK-009', 55, 75, 'unidad', 6),
        ('Gorra Bordada', 'FNK-010', 28, 42, 'unidad', 12),
    ],
    'Bazar': [
        ('Juego de Vasos x6', 'CHK-B01', 55, 75, 'set', 6),
        ('Tabla de Cortar Bambú', 'CHK-B02', 35, 50, 'unidad', 6),
        ('Set Utensilios Cocina', 'CHK-B03', 120, 160, 'set', 3),
        ('Tazas Cerámica x4', 'CHK-B04', 65, 90, 'set', 6),
        ('Cesta Tejida', 'CHK-B05', 45, 65, 'unidad', 6),
        ('Organizador Escritorio', 'CHK-B06', 40, 58, 'unidad', 6),
        ('Botella Termos 1L', 'CHK-B07', 75, 100, 'unidad', 6),
        ('Sartén Antiadherente', 'CHK-B08', 95, 130, 'unidad', 3),
        ('Colador Acero', 'CHK-B09', 28, 40, 'unidad', 12),
        ('Frasco Hermético x3', 'CHK-B10', 45, 65, 'set', 6),
    ],
    'Ferretería': [
        ('Taladro Percutor 750W', 'ACR-F01', 380, 500, 'unidad', 1),
        ('Set Llaves Allen', 'ACR-F02', 45, 65, 'set', 6),
        ('Cinta Métrica 5m', 'ACR-F03', 18, 28, 'unidad', 12),
        ('Juego Destornilladores x8', 'ACR-F04', 55, 78, 'set', 6),
        ('Nivel Digital', 'ACR-F05', 95, 130, 'unidad', 3),
        ('Caja Herramientas 20"', 'ACR-F06', 180, 245, 'unidad', 2),
        ('Sierra Caladora 600W', 'ACR-F07', 450, 595, 'unidad', 1),
        ('Llave Francesa 12"', 'ACR-F08', 35, 50, 'unidad', 6),
        ('Martillo Carpintero', 'ACR-F09', 42, 60, 'unidad', 6),
        ('Brocha Set x5', 'ACR-F10', 28, 42, 'set', 12),
    ],
    'Decoración': [
        ('Cuadro Abstracto 60x80', 'FNK-D01', 180, 250, 'unidad', 1),
        ('Jarrón Cerámica Grande', 'FNK-D02', 120, 165, 'unidad', 2),
        ('Espejo Redondo 80cm', 'FNK-D03', 280, 380, 'unidad', 1),
        ('Cojín Decorativo x2', 'FNK-D04', 65, 90, 'par', 6),
        ('Velas Aromáticas x3', 'FNK-D05', 45, 65, 'set', 12),
        ('Reloj Pared Moderno', 'FNK-D06', 95, 135, 'unidad', 3),
        ('Maceta Colgante', 'FNK-D07', 35, 52, 'unidad', 6),
        ('Portarretrato x3', 'FNK-D08', 55, 78, 'set', 6),
        ('Alfombra Sala 2x3m', 'FNK-D09', 380, 520, 'unidad', 1),
        ('Cortinas Blackout par', 'FNK-D10', 220, 300, 'par', 2),
    ],
}

CLIENTS = [
    ('Supermercado El Sol S.A.', '1234567-0', 'Santa Cruz', 50000),
    ('Distribuidora Norte Ltda.', '2345678-1', 'Cochabamba', 30000),
    ('Tienda La Familiar', '3456789-2', 'La Paz', 15000),
    ('Almacén Central S.R.L.', '4567890-3', 'Santa Cruz', 25000),
    ('Minimarket Express', '5678901-4', 'Tarija', 10000),
    ('Supermercados Unidos', '6789012-5', 'Santa Cruz', 80000),
    ('Distribuciones Oriente', '7890123-6', 'Trinidad', 20000),
    ('Tienda Moderna S.A.', '8901234-7', 'Oruro', 18000),
    ('Comercial del Valle', '9012345-8', 'Sucre', 12000),
    ('Megatienda Andina', '0123456-9', 'La Paz', 45000),
    ('Distribuidora Sur S.R.L.', '1122334-0', 'Potosí', 22000),
    ('Supermercado Familiar', '2233445-1', 'Beni', 16000),
    ('Almacén El Progreso', '3344556-2', 'Cobija', 8000),
    ('Comercial Bolivar', '4455667-3', 'Cochabamba', 35000),
    ('Tienda del Barrio', '5566778-4', 'Santa Cruz', 7000),
    ('Distribuciones Centrales', '6677889-5', 'La Paz', 28000),
    ('Supermercado Nuevo', '7788990-6', 'Santa Cruz', 60000),
    ('Almacén del Norte', '8899001-7', 'Tarija', 14000),
    ('Comercial Yacuiba', '9900112-8', 'Yacuiba', 11000),
    ('Distribuidora Chapare', '1011121-9', 'Cochabamba', 19000),
    ('Tienda Oriental', '2122232-0', 'Santa Cruz', 9000),
    ('Supermercado del Lago', '3233343-1', 'Copacabana', 13000),
    ('Almacén Pacífico', '4344454-2', 'La Paz', 31000),
    ('Comercial Illimani', '5455565-3', 'La Paz', 24000),
    ('Distribuciones Vallegrande', '6566676-4', 'Santa Cruz', 17000),
    ('Tienda de Todo', '7677787-5', 'Cochabamba', 10000),
    ('Supermercado Amboro', '8788898-6', 'Santa Cruz', 42000),
    ('Almacén del Sur', '9899909-7', 'Sucre', 21000),
    ('Comercial Noel', '1920212-8', 'Oruro', 15500),
    ('Distribuidora Yungas', '2021222-9', 'La Paz', 26000),
]

# Seasonality weights per category per month (1-12)
SEASONALITY = {
    'Juguetes':        [1.0, 0.8, 0.9, 0.9, 0.9, 1.4, 1.0, 0.9, 0.9, 1.0, 1.8, 2.5],
    'Iluminación':     [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.4, 1.2],
    'Ropa y Accesorios': [1.0, 0.9, 1.5, 1.6, 1.0, 0.8, 0.9, 1.4, 1.5, 1.0, 1.0, 0.9],
    'Bazar':           [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.3, 1.5],
    'Ferretería':      [1.0, 1.1, 1.2, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 1.1, 1.0, 0.9],
    'Decoración':      [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.6, 1.8],
}


class Command(BaseCommand):
    help = 'Seeder masivo TUMOMITO S.A. — genera productos, clientes y pedidos históricos'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Elimina datos anteriores del seeder')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_data()

        self.stdout.write('=== TUMOMITO SEEDER ===')

        # Paso 0: roles, permisos y usuarios demo (idempotente)
        from django.core.management import call_command
        call_command('setup_demo', verbosity=0)
        self.stdout.write('  OK Roles, permisos y usuarios demo configurados')

        self._create_categories()
        self._create_brands()
        self._create_products()
        self._create_clients_and_users()
        self._create_orders()
        self._create_quotes()
        self._create_inventory_movements()
        self._set_low_stock_products()
        self.stdout.write(self.style.SUCCESS('Seeder completado exitosamente.'))

    def _clear_data(self):
        from apps.orders.models import DetallePedido, Pedido
        from apps.products.models import Prenda, Categoria, Marca, InventoryMovement
        from apps.customers.models import Client
        from apps.quotes.models import QuoteItem, Quote
        self.stdout.write('Limpiando datos anteriores...')
        QuoteItem.objects.all().delete()
        Quote.objects.all().delete()
        DetallePedido.objects.all().delete()
        Pedido.objects.all().delete()
        InventoryMovement.objects.all().delete()
        Prenda.objects.all().delete()
        # Eliminar TODOS los Client profiles (incluyendo los del setup_demo)
        # para que los NIT queden libres y no generen UniqueViolation
        Client.objects.all().delete()

    def _create_categories(self):
        from apps.products.models import Categoria
        for nombre in CATEGORIES:
            Categoria.objects.get_or_create(nombre=nombre, defaults={'activa': True})
        self.stdout.write(f'  OK{len(CATEGORIES)} categorías creadas')

    def _create_brands(self):
        from apps.products.models import Marca
        brand_names = set(BRANDS.values())
        for nombre in brand_names:
            Marca.objects.get_or_create(nombre=nombre, defaults={'activa': True})
        self.stdout.write(f'  OK{len(brand_names)} marcas creadas')

    def _create_products(self):
        from apps.products.models import Prenda, Categoria, Marca
        count = 0
        for cat_name, products in PRODUCTS_BY_CATEGORY.items():
            cat = Categoria.objects.get(nombre=cat_name)
            brand_name = BRANDS[cat_name]
            marca = Marca.objects.get(nombre=brand_name)
            for (name, code, pw, pr, unit, moq) in products:
                p, created = Prenda.objects.get_or_create(
                    code=code,
                    defaults={
                        'nombre': name,
                        'descripcion': f'Producto mayorista: {name}. Marca: {brand_name}.',
                        'precio': Decimal(str(pr)),
                        'price_wholesale': Decimal(str(pw)),
                        'price_retail': Decimal(str(pr)),
                        'unit': unit,
                        'min_order_qty': moq,
                        'stock': random.randint(50, 500),
                        'stock_min': 20,
                        'marca': marca,
                        'activa': True,
                        'color': 'Variado',
                    }
                )
                if created:
                    p.categorias.set([cat])
                    count += 1
        self.stdout.write(f'  OK{count} productos creados')

    def _create_clients_and_users(self):
        from apps.customers.models import Client
        from apps.accounts.models import Role
        from django.db import IntegrityError

        count = 0
        client_role, _ = Role.objects.get_or_create(
            nombre='Cliente',
            defaults={'descripcion': 'Cliente empresa B2B'}
        )

        for (company, nit, city, limit) in CLIENTS:
            username = nit.replace('-', '')
            email = f"empresa{username}@tumomito.com"

            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'nombre': company.split()[0],
                    'apellido': 'Empresa',
                    'activo': True,
                    'rol': client_role,
                }
            )
            if user_created:
                user.set_password('tumomito2024')
                user.save()

            c_type = 'vip' if limit >= 40000 else ('regular' if limit >= 15000 else 'nuevo')

            # Buscar por NIT primero para evitar UniqueViolation
            existing_by_nit = Client.objects.filter(nit=nit).first()
            if existing_by_nit:
                # Ya existe un Client con ese NIT (p.ej. del setup_demo) — reasignar al user del seeder
                if existing_by_nit.user_id != user.id:
                    existing_by_nit.user = user
                    existing_by_nit.company_name = company
                    existing_by_nit.city = city
                    existing_by_nit.credit_limit = Decimal(str(limit))
                    existing_by_nit.client_type = c_type
                    existing_by_nit.save()
            else:
                # Verificar que el user no tenga ya un Client
                if not Client.objects.filter(user=user).exists():
                    try:
                        Client.objects.create(
                            user=user,
                            company_name=company,
                            nit=nit,
                            city=city,
                            credit_limit=Decimal(str(limit)),
                            client_type=c_type,
                        )
                    except IntegrityError:
                        pass  # race condition muy improbable, ignorar

            count += 1
        self.stdout.write(f'  OK{count} clientes empresa creados')

    def _create_orders(self):
        from apps.orders.models import Pedido, DetallePedido
        from apps.products.models import Prenda
        from apps.customers.models import Client

        clients = list(Client.objects.filter(deleted_at__isnull=True))
        products_by_cat = {}
        for cat_name in CATEGORIES:
            prods = list(
                Prenda.objects.filter(
                    categorias__nombre=cat_name, activa=True, deleted_at__isnull=True
                )
            )
            products_by_cat[cat_name] = prods

        all_products = list(Prenda.objects.filter(activa=True, deleted_at__isnull=True))

        orders_created = 0
        target_per_year = 3000
        # 2026 solo hasta el 7 de mayo (fecha actual del sistema)
        years = [2021, 2022, 2023, 2024, 2025, 2026]

        # Get or create admin user for seller
        admin_user = User.objects.filter(is_staff=True).first() or User.objects.first()

        from calendar import monthrange as mr

        for year in years:
            self.stdout.write(f'  Generando pedidos año {year}...')
            orders_this_year = 0

            # Para 2026, solo enero–mayo; mayo solo hasta el día 7
            max_month = 5 if year == 2026 else 12

            for month in range(1, max_month + 1):
                monthly_target = target_per_year // 12

                # Apply seasonality boost
                max_seasonality = max(
                    SEASONALITY[cat][month - 1] for cat in CATEGORIES
                )
                monthly_count = int(monthly_target * max_seasonality)
                # Para 2026 reducir proporcionalmente (datos parciales del año)
                if year == 2026:
                    monthly_count = max(1, monthly_count // 3)

                for _ in range(monthly_count):
                    client = random.choice(clients)

                    _, days_in_month = mr(year, month)
                    # Mayo 2026 solo hasta el día 7
                    max_day = 7 if (year == 2026 and month == 5) else days_in_month

                    day = random.randint(1, max_day)
                    order_date = datetime(year, month, day,
                                         random.randint(8, 18),
                                         random.randint(0, 59),
                                         tzinfo=timezone.get_current_timezone())

                    # Pick products with seasonality influence
                    num_items = random.randint(2, 8)
                    selected_products = []

                    for _ in range(num_items):
                        # Weight categories by seasonality
                        weights = [SEASONALITY[cat][month - 1] for cat in CATEGORIES]
                        cat_name = random.choices(CATEGORIES, weights=weights, k=1)[0]
                        cat_products = products_by_cat.get(cat_name, all_products)
                        if cat_products:
                            selected_products.append(random.choice(cat_products))

                    if not selected_products:
                        continue

                    # Calculate totals
                    subtotal = Decimal('0')
                    items_data = []
                    for product in selected_products:
                        qty = random.randint(product.min_order_qty, max(product.min_order_qty * 20, 100))
                        price = product.price_wholesale
                        sub = price * qty
                        subtotal += sub
                        items_data.append((product, qty, price, sub))

                    estados = ['pendiente', 'confirmado', 'despachado', 'entregado', 'cancelado']
                    weights_estado = [5, 15, 10, 60, 10]
                    estado = random.choices(estados, weights=weights_estado, k=1)[0]

                    pedido = Pedido(
                        usuario=client.user,
                        client=client,
                        seller=admin_user,
                        subtotal=subtotal,
                        total=subtotal,
                        estado=estado,
                        payment_method=random.choice(['transferencia', 'credito', 'efectivo']),
                        notas_internas=f'Pedido seeder {year}-{month}',
                    )
                    pedido.save()
                    # Retroactivar fecha para historicidad
                    Pedido.objects.filter(id=pedido.id).update(created_at=order_date)

                    for (product, qty, price, sub) in items_data:
                        DetallePedido.objects.create(
                            pedido=pedido,
                            prenda=product,
                            cantidad=qty,
                            precio_unitario=price,
                            subtotal=sub,
                        )

                    orders_created += 1
                    orders_this_year += 1

        self.stdout.write(f'  OK{orders_created} pedidos históricos creados (2021-2026)')

    def _create_quotes(self):
        """Crea cotizaciones de ejemplo para el dashboard."""
        from apps.quotes.models import Quote, QuoteItem
        from apps.customers.models import Client
        from apps.products.models import Prenda
        from apps.accounts.models import User

        clients = list(Client.objects.filter(deleted_at__isnull=True)[:10])
        products = list(Prenda.objects.filter(activa=True, deleted_at__isnull=True)[:20])
        seller = User.objects.filter(rol__nombre='Empleado').first() or \
                 User.objects.filter(is_staff=True).first()

        if not clients or not products:
            self.stdout.write('  WARN Sin clientes/productos para cotizaciones')
            return

        statuses = ['borrador', 'enviada', 'aceptada', 'rechazada', 'aceptada', 'aceptada']
        count = 0
        for i, client in enumerate(clients[:8]):
            status = statuses[i % len(statuses)]
            quote = Quote.objects.create(
                client=client,
                seller=seller,
                status=status,
                notes=f'Cotización de prueba #{i+1}',
            )
            # 2-4 ítems por cotización
            selected = random.sample(products, min(random.randint(2, 4), len(products)))
            for product in selected:
                qty = random.randint(product.min_order_qty, product.min_order_qty * 10)
                price = product.price_wholesale
                QuoteItem.objects.create(
                    quote=quote, product=product,
                    quantity=qty, unit_price=price,
                    subtotal=qty * price,
                )
            quote.recalculate_total()
            count += 1
        self.stdout.write(f'  OK{count} cotizaciones creadas')

    def _create_inventory_movements(self):
        """Crea movimientos de inventario de ejemplo."""
        from apps.products.models import Prenda, InventoryMovement
        from apps.accounts.models import User

        admin = User.objects.filter(is_staff=True).first()
        products = list(Prenda.objects.filter(activa=True, deleted_at__isnull=True)[:20])
        if not products or not admin:
            return

        movement_types = [
            ('entrada', 'Importación inicial'),
            ('entrada', 'Reposición de stock'),
            ('salida', 'Venta directa'),
            ('entrada', 'Devolución proveedor'),
            ('ajuste', 'Ajuste de inventario'),
        ]
        count = 0
        for product in products[:15]:
            mt, note = random.choice(movement_types)
            qty = random.randint(10, 200)
            # Crear sin llamar save() para evitar modificar el stock actual
            InventoryMovement.objects.create(
                product=product,
                user=admin,
                movement_type=mt,
                quantity=qty,
                notes=note,
            )
            count += 1
        self.stdout.write(f'  OK{count} movimientos de inventario creados')

    def _set_low_stock_products(self):
        """Pone algunos productos con stock bajo para que se vean en las alertas."""
        from apps.products.models import Prenda
        products = list(Prenda.objects.filter(activa=True, deleted_at__isnull=True))
        low_count = max(8, len(products) // 6)  # ~16% con stock bajo
        selected = random.sample(products, min(low_count, len(products)))
        for product in selected:
            # Stock en 0 o muy por debajo del mínimo
            product.stock = random.choice([0, 0, 1, 2, 3, random.randint(1, product.stock_min - 1) if product.stock_min > 1 else 0])
            product.stock_min = random.randint(15, 30)
            product.save(update_fields=['stock', 'stock_min'])
        self.stdout.write(f'  OK{low_count} productos configurados con stock bajo')
