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

Todos aceptan query params opcionales:
  ?fecha_inicio=YYYY-MM-DD   (inicio del rango)
  ?fecha_fin=YYYY-MM-DD      (fin del rango)
Si se omiten, devuelven datos de todo el historial.
"""
from datetime import timedelta, datetime as _dt
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)


def _parse_dates(request):
    """Devuelve (start_dt, end_dt) como datetimes aware, o (None, None)."""
    fi = request.query_params.get('fecha_inicio')
    ff = request.query_params.get('fecha_fin')
    start_dt = end_dt = None
    if fi:
        try:
            start_dt = timezone.make_aware(
                _dt.strptime(fi, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            )
        except Exception:
            pass
    if ff:
        try:
            end_dt = timezone.make_aware(
                _dt.strptime(ff, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            )
        except Exception:
            pass
    return start_dt, end_dt


def _date_filter(start_dt, end_dt, field='created_at'):
    """Construye un Q de rango de fecha para el field dado."""
    q = Q()
    if start_dt:
        q &= Q(**{f'{field}__gte': start_dt})
    if end_dt:
        q &= Q(**{f'{field}__lte': end_dt})
    return q


class TumomitoReportsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """KPIs generales para el dashboard principal."""
        try:
            from apps.products.models import Prenda
            from apps.orders.models import Pedido
            from apps.customers.models import Client

            start_dt, end_dt = _parse_dates(request)
            date_q = _date_filter(start_dt, end_dt)
            has_filter = bool(start_dt or end_dt)

            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

            active_states = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                             'pago_recibido', 'preparando', 'enviado']

            base_q = Q(deleted_at__isnull=True) & date_q

            # Ingresos totales (en el rango si se filtró)
            total_revenue = Pedido.objects.filter(
                base_q, estado__in=active_states
            ).aggregate(t=Sum('total'))['t'] or 0

            # Cambio mes a mes (solo sin filtro de fecha)
            revenue_change = 0
            if not has_filter:
                revenue_this_month = Pedido.objects.filter(
                    estado__in=active_states,
                    created_at__gte=month_start,
                    deleted_at__isnull=True
                ).aggregate(t=Sum('total'))['t'] or 0

                revenue_prev_month = Pedido.objects.filter(
                    estado__in=active_states,
                    created_at__gte=prev_month_start,
                    created_at__lt=month_start,
                    deleted_at__isnull=True
                ).aggregate(t=Sum('total'))['t'] or 0

                if revenue_prev_month and revenue_prev_month > 0:
                    revenue_change = round(
                        ((revenue_this_month - revenue_prev_month) / revenue_prev_month) * 100, 1
                    )

            # Pedidos pendientes (en el rango si se filtró)
            pending_orders = Pedido.objects.filter(
                Q(deleted_at__isnull=True) & date_q, estado='pendiente'
            ).count()

            # Productos y clientes activos son estado actual, sin filtro de fecha
            active_products = Prenda.objects.filter(activa=True, deleted_at__isnull=True).count()
            active_clients = Client.objects.filter(deleted_at__isnull=True).count()

            low_stock_products = Prenda.objects.filter(
                activa=True, deleted_at__isnull=True, stock__lte=F('stock_min')
            ).count()

            stock_alerts = list(
                Prenda.objects.filter(activa=True, deleted_at__isnull=True, stock__lte=F('stock_min'))
                .values('id', 'nombre', 'code', 'stock', 'stock_min')
                .order_by('stock')[:5]
            )

            return Response({
                'total_revenue': float(total_revenue),
                'revenue_this_month': float(total_revenue) if has_filter else float(
                    Pedido.objects.filter(
                        estado__in=active_states, created_at__gte=month_start, deleted_at__isnull=True
                    ).aggregate(t=Sum('total'))['t'] or 0
                ),
                'revenue_change_pct': 0 if has_filter else revenue_change,
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

            start_dt, end_dt = _parse_dates(request)
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']

            date_q = _date_filter(start_dt, end_dt, field='pedido__created_at')

            rows = (
                DetallePedido.objects
                .filter(Q(pedido__estado__in=completed) & Q(deleted_at__isnull=True) & date_q)
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
        """Ventas agrupadas por mes.
        Sin filtro de fecha: últimos N meses (param ?months=12).
        Con filtro de fecha: meses dentro del rango indicado.
        """
        try:
            from apps.orders.models import Pedido
            from calendar import monthrange

            start_dt, end_dt = _parse_dates(request)
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']

            def _agg_month(m_start, m_end):
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
                return {
                    'month': m_start.strftime('%b %Y'),
                    'date': m_start.isoformat(),
                    'total_revenue': float(agg['revenue'] or 0),
                    'confirmed_revenue': float(agg['confirmed_revenue'] or 0),
                    'pending_revenue': float(agg['pending_revenue'] or 0),
                    'order_count': agg['orders'] or 0,
                }

            data = []

            if start_dt or end_dt:
                # Generar meses dentro del rango dado
                range_start = start_dt or (timezone.now() - timedelta(days=365))
                range_end = end_dt or timezone.now()

                current = range_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_month = range_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

                # Límite de seguridad: máximo 120 meses (10 años)
                count = 0
                while current <= end_month and count < 120:
                    _, last_day = monthrange(current.year, current.month)
                    m_end = current.replace(day=last_day, hour=23, minute=59, second=59)
                    data.append(_agg_month(current, m_end))
                    # Siguiente mes
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1, day=1)
                    else:
                        current = current.replace(month=current.month + 1, day=1)
                    count += 1
            else:
                # Comportamiento original: últimos N meses
                months = int(request.query_params.get('months', 12))
                now = timezone.now()
                for i in range(months - 1, -1, -1):
                    md = now - timedelta(days=30 * i)
                    m_start = md.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    _, last = monthrange(md.year, md.month)
                    m_end = md.replace(day=last, hour=23, minute=59, second=59)
                    data.append(_agg_month(m_start, m_end))

            return Response(data)
        except Exception as e:
            logger.error(f"Error monthly: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='top-clients')
    def top_clients(self, request):
        """Top 10 clientes por ingresos totales."""
        try:
            from apps.customers.models import Client

            start_dt, end_dt = _parse_dates(request)

            # Filtros para los orders anidados en el annotate
            order_base = Q(orders__deleted_at__isnull=True) & ~Q(orders__estado='cancelado')
            if start_dt:
                order_base &= Q(orders__created_at__gte=start_dt)
            if end_dt:
                order_base &= Q(orders__created_at__lte=end_dt)

            clients = (
                Client.objects
                .filter(deleted_at__isnull=True)
                .annotate(
                    total_spent=Sum('orders__total', filter=order_base),
                    total_orders=Count('orders', filter=order_base),
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

            start_dt, end_dt = _parse_dates(request)
            date_q = _date_filter(start_dt, end_dt)

            rows = (
                Pedido.objects
                .filter(Q(deleted_at__isnull=True) & date_q)
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
        """Productos con stock bajo o en cero (estado actual, sin filtro de fecha)."""
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

            start_dt, end_dt = _parse_dates(request)
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']
            date_q = _date_filter(start_dt, end_dt, field='pedido__created_at')

            rows = (
                DetallePedido.objects
                .filter(Q(pedido__estado__in=completed) & Q(deleted_at__isnull=True) & date_q)
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

            start_dt, end_dt = _parse_dates(request)
            completed = ['confirmado', 'en_preparacion', 'despachado', 'entregado',
                         'pago_recibido', 'preparando', 'enviado']
            date_q = _date_filter(start_dt, end_dt, field='pedido__created_at')

            rows = (
                DetallePedido.objects
                .filter(Q(pedido__estado__in=completed) & Q(deleted_at__isnull=True) & date_q)
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
        """Feed de actividad reciente."""
        try:
            from apps.orders.models import Pedido
            from apps.products.models import InventoryMovement
            from apps.quotes.models import Quote

            start_dt, end_dt = _parse_dates(request)
            date_q = _date_filter(start_dt, end_dt)

            events = []

            for p in Pedido.objects.filter(Q(deleted_at__isnull=True) & date_q).order_by('-created_at')[:8]:
                events.append({
                    'type': 'order',
                    'description': f"Pedido {p.numero_pedido} — {p.estado}",
                    'amount': float(p.total),
                    'date': p.created_at.isoformat(),
                })

            for m in InventoryMovement.objects.filter(Q(deleted_at__isnull=True) & date_q).order_by('-created_at')[:6]:
                events.append({
                    'type': 'inventory',
                    'description': f"{m.get_movement_type_display()} de {m.product.nombre} ({m.quantity} uds)",
                    'amount': None,
                    'date': m.created_at.isoformat(),
                })

            for q in Quote.objects.filter(Q(deleted_at__isnull=True) & date_q).order_by('-created_at')[:6]:
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
