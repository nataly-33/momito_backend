"""
Servicio de preparación de datos para ML — TUMOMITO S.A.
Categorías: Juguetes, Iluminación, Ropa y Accesorios, Bazar, Ferretería, Decoración
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Sum, Count, F
from django.utils import timezone

from apps.orders.models import Pedido, DetallePedido
from apps.products.models import Prenda, Categoria

# Estados válidos del sistema TUMOMITO
ESTADOS_COMPLETADOS = [
    'confirmado', 'despachado', 'entregado',
    'pago_recibido', 'preparando', 'enviado',
]

CATEGORIAS_TUMOMITO = [
    'Juguetes', 'Iluminación', 'Ropa y Accesorios',
    'Bazar', 'Ferretería', 'Decoración',
]

MARCAS_TUMOMITO = ['Chikipoon', 'Acricolor', 'Funky Fish']


class DataPreparationService:
    def __init__(self):
        self.min_records_for_training = 50

    def get_historical_sales_data(self, months_back=60):
        """Extrae datos históricos de ventas."""
        fecha_inicio = timezone.now() - timedelta(days=months_back * 30)

        detalles = DetallePedido.objects.filter(
            pedido__created_at__gte=fecha_inicio,
            pedido__estado__in=ESTADOS_COMPLETADOS,
            deleted_at__isnull=True,
        ).select_related('prenda', 'prenda__marca', 'pedido').prefetch_related('prenda__categorias')

        data = []
        for detalle in detalles:
            categoria_principal = detalle.prenda.categorias.first()
            data.append({
                'fecha': detalle.pedido.created_at,
                'producto_id': str(detalle.prenda.id),
                'producto_nombre': detalle.prenda.nombre,
                'categoria': categoria_principal.nombre if categoria_principal else 'Sin categoría',
                'marca': detalle.prenda.marca.nombre if detalle.prenda.marca else 'Sin marca',
                'precio_unitario': float(detalle.precio_unitario),
                'cantidad': detalle.cantidad,
                'subtotal': float(detalle.subtotal),
                'mes': detalle.pedido.created_at.month,
                'año': detalle.pedido.created_at.year,
                'dia_semana': detalle.pedido.created_at.weekday(),
                'trimestre': (detalle.pedido.created_at.month - 1) // 3 + 1,
            })

        df = pd.DataFrame(data)

        if len(df) < self.min_records_for_training:
            print(f"WARN Solo {len(df)} registros reales. Generando datos sinteticos TUMOMITO...")
            df = self._generate_synthetic_data(real_data=df if not df.empty else None)

        return df

    def prepare_features(self, df, months_back=60):
        """Prepara features para el modelo con categorías TUMOMITO."""
        df_agg = df.groupby(['año', 'mes', 'categoria']).agg({
            'cantidad': 'sum',
            'subtotal': 'sum',
            'precio_unitario': 'mean',
            'producto_id': 'count'
        }).reset_index()
        df_agg.columns = ['año', 'mes', 'categoria', 'cantidad_vendida',
                          'total_ventas', 'precio_promedio', 'num_transacciones']

        # Rango completo de meses
        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(days=months_back * 30)
        all_months = []
        current = fecha_inicio.replace(day=1)
        while current <= fecha_fin:
            all_months.append({'año': current.year, 'mes': current.month})
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        all_combinations = [
            {'año': m['año'], 'mes': m['mes'], 'categoria': cat}
            for m in all_months
            for cat in CATEGORIAS_TUMOMITO
        ]

        df_complete = pd.DataFrame(all_combinations)
        df_merged = df_complete.merge(df_agg, on=['año', 'mes', 'categoria'], how='left')

        for col in ['cantidad_vendida', 'total_ventas', 'precio_promedio', 'num_transacciones']:
            df_merged[col] = df_merged[col].fillna(0)

        df_merged['mes_sin'] = np.sin(2 * np.pi * df_merged['mes'] / 12)
        df_merged['mes_cos'] = np.cos(2 * np.pi * df_merged['mes'] / 12)
        df_merged['trimestre'] = (df_merged['mes'] - 1) // 3 + 1

        df_encoded = pd.get_dummies(df_merged, columns=['categoria'], prefix='cat')

        # Columnas de categorías TUMOMITO
        cat_cols = [f'cat_{c.replace(" ", "_").replace("á", "a").replace("é", "e").replace("ó", "o").replace("ú", "u")}' for c in CATEGORIAS_TUMOMITO]
        # Usar los nombres que get_dummies generó realmente
        actual_cat_cols = [c for c in df_encoded.columns if c.startswith('cat_')]

        feature_columns = ['año', 'mes', 'mes_sin', 'mes_cos', 'trimestre'] + actual_cat_cols

        for col in feature_columns:
            if col not in df_encoded:
                df_encoded[col] = 0

        X = df_encoded[feature_columns]
        y = df_encoded['cantidad_vendida']

        print(f"Dataset: {len(X)} registros ({len(all_months)} meses x {len(CATEGORIAS_TUMOMITO)} categorias)")
        return X, y, feature_columns

    def _generate_synthetic_data(self, real_data=None, num_months=60, records_per_month=80):
        """Genera datos sintéticos con estacionalidad TUMOMITO."""
        np.random.seed(42)

        # Estacionalidad por categoría (índice 0=enero)
        seasonality = {
            'Juguetes':           [1.0, 0.8, 0.9, 0.9, 0.9, 1.4, 1.0, 0.9, 0.9, 1.0, 1.8, 2.5],
            'Iluminación':        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.4, 1.2],
            'Ropa y Accesorios':  [1.0, 0.9, 1.5, 1.6, 1.0, 0.8, 0.9, 1.4, 1.5, 1.0, 1.0, 0.9],
            'Bazar':              [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.3, 1.5],
            'Ferretería':         [1.0, 1.1, 1.2, 1.1, 1.0, 0.9, 0.9, 1.0, 1.1, 1.1, 1.0, 0.9],
            'Decoración':         [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.6, 1.8],
        }
        precios_base = {
            'Juguetes': 35.0,
            'Iluminación': 85.0,
            'Ropa y Accesorios': 95.0,
            'Bazar': 55.0,
            'Ferretería': 60.0,
            'Decoración': 120.0,
        }

        synthetic_data = []
        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(days=num_months * 30)

        for _ in range(num_months * records_per_month):
            random_days = np.random.randint(0, num_months * 30)
            fecha = fecha_inicio + timedelta(days=random_days)
            categoria = np.random.choice(CATEGORIAS_TUMOMITO)
            mes = fecha.month
            s = seasonality[categoria][mes - 1]
            precio = precios_base[categoria] * np.random.uniform(0.8, 1.3)
            cantidad = max(1, int(np.random.randint(12, 100) * s))

            synthetic_data.append({
                'fecha': fecha,
                'producto_id': str(np.random.randint(1000, 9999)),
                'producto_nombre': f'{categoria} - Producto {np.random.randint(1, 60)}',
                'categoria': categoria,
                'marca': np.random.choice(MARCAS_TUMOMITO),
                'precio_unitario': round(precio, 2),
                'cantidad': cantidad,
                'subtotal': round(precio * cantidad, 2),
                'mes': fecha.month,
                'año': fecha.year,
                'dia_semana': fecha.weekday(),
                'trimestre': (fecha.month - 1) // 3 + 1,
            })

        df_synthetic = pd.DataFrame(synthetic_data)

        if real_data is not None and not real_data.empty:
            return pd.concat([real_data, df_synthetic], ignore_index=True)
        return df_synthetic

    def get_aggregated_sales_by_period(self, period='month'):
        if period == 'month':
            ventas = Pedido.objects.filter(
                estado__in=ESTADOS_COMPLETADOS
            ).annotate(
                mes=F('created_at__month'),
                año=F('created_at__year')
            ).values('año', 'mes').annotate(
                total_ventas=Sum('total'),
                num_pedidos=Count('id')
            ).order_by('año', 'mes')
            return list(ventas)
        return []

    def get_top_selling_products(self, limit=10):
        return list(
            DetallePedido.objects.filter(
                pedido__estado__in=ESTADOS_COMPLETADOS,
                deleted_at__isnull=True,
            ).values('prenda__id', 'prenda__nombre').annotate(
                total_vendido=Sum('cantidad'),
                ingresos_totales=Sum('subtotal')
            ).order_by('-ingresos_totales')[:limit]
        )

    def get_sales_by_category(self):
        ventas_por_categoria = {}
        detalles = DetallePedido.objects.filter(
            pedido__estado__in=ESTADOS_COMPLETADOS,
            deleted_at__isnull=True,
        ).select_related('prenda').prefetch_related('prenda__categorias')

        for detalle in detalles:
            categoria = detalle.prenda.categorias.first()
            nombre = categoria.nombre if categoria else 'Sin categoría'
            if nombre not in ventas_por_categoria:
                ventas_por_categoria[nombre] = {
                    'categoria': nombre,
                    'total_ventas': 0,
                    'cantidad_vendida': 0,
                    'num_productos': 0,
                }
            ventas_por_categoria[nombre]['total_ventas'] += float(detalle.subtotal)
            ventas_por_categoria[nombre]['cantidad_vendida'] += detalle.cantidad
            ventas_por_categoria[nombre]['num_productos'] += 1

        return list(ventas_por_categoria.values())
