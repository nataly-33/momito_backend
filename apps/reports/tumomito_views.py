"""
Endpoints de reportes específicos para TUMOMITO S.A. ERP B2B
GET /api/reports/dashboard/
GET /api/reports/sales/
GET /api/reports/monthly/
GET /api/reports/top-clients/
GET /api/reports/orders-status/
GET /api/reports/low-stock/
GET /api/reports/brands/
GET /api/reports/categories/
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)


class TumomitoReportsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """KPIs generales para el dashboard principal."""
        try:
            from apps.products.models import Prenda
            from apps.orders.models import Pedido
            from apps.customers.models import Client
            from apps.accounts.models import User

            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

            active_states = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                             'pago_recibido', 'preparando', 'enviado']

            # Ingresos totales
            total_revenue = Pedido.objects.filter(
                estado__in=active_states, deleted_at__isnull=True
            ).aggregate(t=Sum('total'))['t'] or 0

            # Ingresos mes actual
            revenue_this_month = Pedido.objects.filter(
                estado__in=active_states,
                created_at__gte=month_start,
                deleted_at__isnull=True
            ).aggregate(t=Sum('total'))['t'] or 0

            # Ingresos mes anterior
            revenue_prev_month = Pedido.objects.filter(
                estado__in=active_states,
                created_at__gte=prev_month_start,
                created_at__lt=month_start,
                deleted_at__isnull=True
            ).aggregate(t=Sum('total'))['t'] or 0

            revenue_change = 0
            if revenue_prev_month and revenue_prev_month > 0:
                revenue_change = round(((revenue_this_month - revenue_prev_month) / revenue_prev_month) * 100, 1)

            # Pedidos pendientes
            pending_orders = Pedido.objects.filter(
                estado='pendiente', deleted_at__isnull=True
            ).count()

            # Productos activos
            active_products = Prenda.objects.filter(
                activa=True, deleted_at__isnull=True
            ).count()

            # Clientes activos
            active_clients = Client.objects.filter(deleted_at__isnull=True).count()

            # Productos con stock bajo
            low_stock_products = Prenda.objects.filter(
                activa=True, deleted_at__isnull=True,
                stock__lte=F('stock_min')
            ).count()

            # Top 5 alertas de stock crítico
            stock_alerts = list(
                Prenda.objects.filter(activa=True, deleted_at__isnull=True, stock__lte=F('stock_min'))
                .values('id', 'nombre', 'code', 'stock', 'stock_min')
                .order_by('stock')[:5]
            )

            return Response({
                'total_revenue': float(total_revenue),
                'revenue_this_month': float(revenue_this_month),
                'revenue_change_pct': revenue_change,
                'pending_orders': pending_orders,
                'active_products': active_products,
                'active_clients': active_clients,
                'low_stock_products': low_stock_products,
                'stock_alerts': stock_alerts,
            })
        except Exception as e:
            logger.error(f"Error dashboard: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Ventas por producto desde la tabla de detalles de pedidos."""
        try:
            from apps.orders.models import DetallePedido

            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']

            rows = (
                DetallePedido.objects
                .filter(pedido__estado__in=completed, deleted_at__isnull=True)
                .values(
                    product_id=F('prenda__id'),
                    product_code=F('prenda__code'),
                    product_name=F('prenda__nombre'),
                    brand=F('prenda__marca__nombre'),
                )
                .annotate(
                    total_units=Sum('cantidad'),
                    total_revenue=Sum('subtotal'),
                    total_orders=Count('pedido', distinct=True),
                )
                .order_by('-total_revenue')[:50]
            )
            return Response(list(rows))
        except Exception as e:
            logger.error(f"Error sales: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def monthly(self, request):
        """Ventas agrupadas por mes (últimos 12 meses)."""
        try:
            from apps.orders.models import Pedido
            from calendar import monthrange

            months = int(request.query_params.get('months', 12))
            now = timezone.now()
            data = []
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']

            for i in range(months - 1, -1, -1):
                md = now - timedelta(days=30 * i)
                m_start = md.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                _, last = monthrange(md.year, md.month)
                m_end = md.replace(day=last, hour=23, minute=59, second=59)

                agg = Pedido.objects.filter(
                    created_at__gte=m_start,
                    created_at__lte=m_end,
                    deleted_at__isnull=True,
                ).aggregate(
                    revenue=Sum('total'),
                    orders=Count('id'),
                    confirmed_revenue=Sum('total', filter=Q(estado__in=completed)),
                    pending_revenue=Sum('total', filter=Q(estado='pendiente')),
                )
                data.append({
                    'month': md.strftime('%b %Y'),
                    'date': m_start.isoformat(),
                    'total_revenue': float(agg['revenue'] or 0),
                    'confirmed_revenue': float(agg['confirmed_revenue'] or 0),
                    'pending_revenue': float(agg['pending_revenue'] or 0),
                    'order_count': agg['orders'] or 0,
                })
            return Response(data)
        except Exception as e:
            logger.error(f"Error monthly: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='top-clients')
    def top_clients(self, request):
        """Top 10 clientes por ingresos totales."""
        try:
            from apps.customers.models import Client
            clients = (
                Client.objects
                .filter(deleted_at__isnull=True)
                .annotate(
                    total_spent=Sum(
                        'orders__total',
                        filter=Q(orders__deleted_at__isnull=True) & ~Q(orders__estado='cancelado')
                    ),
                    total_orders=Count(
                        'orders',
                        filter=Q(orders__deleted_at__isnull=True) & ~Q(orders__estado='cancelado')
                    )
                )
                .order_by('-total_spent')[:10]
                .values('id', 'company_name', 'city', 'client_type', 'total_spent', 'total_orders')
            )
            return Response(list(clients))
        except Exception as e:
            logger.error(f"Error top-clients: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='orders-status')
    def orders_status(self, request):
        """Distribución de pedidos por estado."""
        try:
            from apps.orders.models import Pedido
            rows = (
                Pedido.objects
                .filter(deleted_at__isnull=True)
                .values('estado')
                .annotate(count=Count('id'), total=Sum('total'))
                .order_by('-count')
            )
            return Response(list(rows))
        except Exception as e:
            logger.error(f"Error orders-status: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """Productos con stock bajo o en cero."""
        try:
            from apps.products.models import Prenda
            products = (
                Prenda.objects
                .filter(activa=True, deleted_at__isnull=True, stock__lte=F('stock_min'))
                .values(
                    'id', 'nombre', 'code', 'stock', 'stock_min',
                    brand=F('marca__nombre'),
                )
                .annotate(deficit=F('stock_min') - F('stock'))
                .order_by('stock')
            )
            return Response(list(products))
        except Exception as e:
            logger.error(f"Error low-stock: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def brands(self, request):
        """Ventas agrupadas por marca."""
        try:
            from apps.orders.models import DetallePedido
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']
            rows = (
                DetallePedido.objects
                .filter(pedido__estado__in=completed, deleted_at__isnull=True)
                .values(brand=F('prenda__marca__nombre'))
                .annotate(
                    total_units=Sum('cantidad'),
                    total_revenue=Sum('subtotal'),
                )
                .order_by('-total_revenue')
            )
            return Response(list(rows))
        except Exception as e:
            logger.error(f"Error brands: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Ventas agrupadas por categoría."""
        try:
            from apps.orders.models import DetallePedido
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']
            rows = (
                DetallePedido.objects
                .filter(pedido__estado__in=completed, deleted_at__isnull=True)
                .values(category=F('prenda__categorias__nombre'))
                .annotate(
                    total_units=Sum('cantidad'),
                    total_revenue=Sum('subtotal'),
                )
                .order_by('-total_revenue')
            )
            return Response(list(rows))
        except Exception as e:
            logger.error(f"Error categories: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='recent-activity')
    def recent_activity(self, request):
        """Feed de actividad reciente (últimos 20 eventos)."""
        try:
            from apps.orders.models import Pedido, HistorialEstadoPedido
            from apps.products.models import InventoryMovement
            from apps.quotes.models import Quote

            events = []

            # Últimos pedidos
            for p in Pedido.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:8]:
                events.append({
                    'type': 'order',
                    'description': f"Pedido {p.numero_pedido} — {p.estado}",
                    'amount': float(p.total),
                    'date': p.created_at.isoformat(),
                })

            # Últimos movimientos de inventario
            for m in InventoryMovement.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:6]:
                events.append({
                    'type': 'inventory',
                    'description': f"{m.get_movement_type_display()} de {m.product.nombre} ({m.quantity} uds)",
                    'amount': None,
                    'date': m.created_at.isoformat(),
                })

            # Últimas cotizaciones
            for q in Quote.objects.filter(deleted_at__isnull=True).order_by('-created_at')[:6]:
                events.append({
                    'type': 'quote',
                    'description': f"Cotización {q.numero_cotizacion} — {q.client.company_name}",
                    'amount': float(q.total),
                    'date': q.created_at.isoformat(),
                })

            events.sort(key=lambda x: x['date'], reverse=True)
            return Response(events[:20])
        except Exception as e:
            logger.error(f"Error recent-activity: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
