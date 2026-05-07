"""
Vistas para la API de Reportes

Proporciona endpoints para:
- Generar reportes desde prompts de texto
- Obtener analytics y estadísticas
- Generar reportes predefinidos
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
import logging

from .serializers import (
    GenerateReportSerializer,
    PredefinedReportSerializer,
    AnalyticsSerializer
)
from .services import (
    AnalyticsService,
    ReportGeneratorService,
    ReportGeneratorServiceError
)

logger = logging.getLogger(__name__)


class ReportsViewSet(viewsets.ViewSet):
    """
    ViewSet para generación de reportes dinámicos y analytics.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generar un reporte a partir de un prompt en lenguaje natural.

        POST /api/reports/generate/
        Body: {
            "prompt": "Reporte de ventas de septiembre en PDF",
            "format": "excel"  // Opcional: sobreescribe el formato del prompt
        }

        Returns:
            Archivo del reporte en el formato especificado
        """
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data['prompt']
        format_override = serializer.validated_data.get('format')  # Formato del select

        try:
            # Obtener nombre del usuario
            user_name = request.user.nombre_completo

            # Generar reporte (el formato del select tiene prioridad)
            file_content, filename, mime_type = ReportGeneratorService.generate_from_prompt(
                prompt=prompt,
                user_name=user_name,
                organization_name="TUMOMITO S.A.",
                format_override=format_override  # Prioridad al formato del select
            )

            # Retornar archivo
            response = HttpResponse(file_content, content_type=mime_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            logger.info(f"Reporte generado exitosamente: {filename} para {user_name}")
            return response

        except ReportGeneratorServiceError as e:
            logger.error(f"Error al generar reporte: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error inesperado al generar reporte: {e}", exc_info=True)
            return Response(
                {'error': 'Error interno al generar el reporte'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def predefined(self, request):
        """
        Generar un reporte predefinido sin usar prompts.

        POST /api/reports/predefined/
        Body: {
            "report_type": "ventas",
            "format": "pdf",
            "filters": {"estado": "confirmado"}
        }

        Returns:
            Archivo del reporte
        """
        serializer = PredefinedReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_type = serializer.validated_data['report_type']
        format_type = serializer.validated_data['format']
        filters = serializer.validated_data.get('filters', {})

        try:
            user_name = request.user.nombre_completo

            file_content, filename, mime_type = ReportGeneratorService.generate_predefined_report(
                report_type=report_type,
                format_type=format_type,
                filters=filters,
                user_name=user_name,
                organization_name="TUMOMITO S.A."
            )

            response = HttpResponse(file_content, content_type=mime_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            logger.error(f"Error al generar reporte predefinido: {e}", exc_info=True)
            return Response(
                {'error': f'Error al generar reporte: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """
        Previsualizar un reporte sin generarlo completamente.
        Devuelve máximo 20 filas de muestra.

        POST /api/reports/preview/
        Body: {
            "prompt": "Reporte de ventas del último mes"
        }

        Returns:
            {
                "data": [...],  // Máximo 20 filas
                "metadata": {...},
                "total_rows": 123,
                "config": {...}
            }
        """
        from .services.prompt_parser import PromptParser, PromptParseError
        from .services.query_builder import QueryBuilder, QueryBuilderError

        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data['prompt']

        try:
            # Parsear el prompt
            config = PromptParser.parse(prompt)

            # Forzar límite de 20 para preview
            config['limit'] = 20

            # Construir query y obtener datos
            result = QueryBuilder.build(config)

            return Response({
                'data': result['data'][:20],
                'metadata': result['metadata'],
                'total_rows': result['metadata'].get('total_records', len(result['data'])),
                'config': config,
                'message': 'Preview generado. Los datos reales pueden ser más extensos.'
            }, status=status.HTTP_200_OK)

        except PromptParseError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except QueryBuilderError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error en preview: {e}", exc_info=True)
            return Response(
                {'error': 'Error al generar preview'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def templates(self, request):
        """
        Obtener plantillas de reportes predefinidos.

        GET /api/reports/templates/

        Returns:
            [
                {
                    "id": "ventas_mes",
                    "name": "Ventas del mes",
                    "description": "...",
                    "prompt_example": "...",
                    "category": "ventas"
                },
                ...
            ]
        """
        templates = [
            {
                'id': 'ventas_mes_actual',
                'name': 'Ventas del mes actual',
                'description': 'Listado completo de todas las ventas del mes en curso',
                'prompt_example': 'Ventas del mes actual en PDF',
                'category': 'ventas'
            },
            {
                'id': 'ventas_2025',
                'name': 'Ventas del año 2025',
                'description': 'Todas las ventas realizadas en el año 2025',
                'prompt_example': 'Ventas del año 2025 en Excel',
                'category': 'ventas'
            },
            {
                'id': 'ventas_por_producto',
                'name': 'Ventas agrupadas por producto',
                'description': 'Reporte de ventas agrupado por cada producto',
                'prompt_example': 'Reporte de ventas del último mes agrupado por producto en PDF',
                'category': 'ventas'
            },
            {
                'id': 'ventas_por_cliente',
                'name': 'Ventas agrupadas por cliente',
                'description': 'Reporte de ventas agrupado por cliente con totales',
                'prompt_example': 'Ventas agrupadas por cliente del año 2025 en Excel',
                'category': 'ventas'
            },
            {
                'id': 'pedidos_pendientes',
                'name': 'Pedidos pendientes',
                'description': 'Listado de pedidos en estado pendiente',
                'prompt_example': 'Pedidos pendientes en PDF',
                'category': 'ventas'
            },
            {
                'id': 'top_productos',
                'name': 'Top 10 productos más vendidos',
                'description': 'Los 10 productos con mayor cantidad de ventas',
                'prompt_example': 'Top 10 productos más vendidos del año 2025 en PDF',
                'category': 'productos'
            },
            {
                'id': 'productos_stock_bajo',
                'name': 'Productos con stock bajo',
                'description': 'Productos que tienen poco stock disponible',
                'prompt_example': 'Productos con stock bajo en Excel',
                'category': 'productos'
            },
            {
                'id': 'inventario_completo',
                'name': 'Inventario completo',
                'description': 'Listado de todos los productos con su stock actual',
                'prompt_example': 'Inventario completo en Excel',
                'category': 'productos'
            },
            {
                'id': 'productos_por_categoria',
                'name': 'Productos agrupados por categoría',
                'description': 'Reporte de productos organizados por categoría',
                'prompt_example': 'Productos agrupados por categoría en PDF',
                'category': 'productos'
            },
            {
                'id': 'clientes_nuevos_mes',
                'name': 'Clientes registrados este mes',
                'description': 'Nuevos clientes que se registraron en el mes actual',
                'prompt_example': 'Clientes registrados este mes en Excel',
                'category': 'clientes'
            },
            {
                'id': 'clientes_2025',
                'name': 'Clientes del año 2025',
                'description': 'Todos los clientes registrados en el año 2025',
                'prompt_example': 'Clientes del año 2025 en Excel',
                'category': 'clientes'
            },
            {
                'id': 'clientes_top_compradores',
                'name': 'Top 10 mejores clientes',
                'description': 'Los 10 clientes con mayor volumen de compras',
                'prompt_example': 'Top 10 clientes con más compras en PDF',
                'category': 'clientes'
            },
            {
                'id': 'logins_hoy',
                'name': 'Logins de hoy',
                'description': 'Registro de inicios de sesión del día de hoy',
                'prompt_example': 'Logins de hoy en Excel',
                'category': 'analytics'
            },
            {
                'id': 'logins_7_dias',
                'name': 'Logins últimos 7 días',
                'description': 'Registro de inicios de sesión de los últimos 7 días',
                'prompt_example': 'Logins de los últimos 7 días en Excel',
                'category': 'analytics'
            },
            {
                'id': 'logins_30_dias',
                'name': 'Logins últimos 30 días',
                'description': 'Registro de inicios de sesión de los últimos 30 días',
                'prompt_example': 'Logins de los últimos 30 días en Excel',
                'category': 'analytics'
            },
            {
                'id': 'carritos_activos',
                'name': 'Carritos activos',
                'description': 'Carritos de compra que tienen items pendientes',
                'prompt_example': 'Carritos activos con items en PDF',
                'category': 'analytics'
            },
            {
                'id': 'ingresos_mes',
                'name': 'Ingresos por día del mes',
                'description': 'Reporte de ingresos diarios del mes actual',
                'prompt_example': 'Ingresos por día del mes actual en Excel',
                'category': 'analytics'
            },
            {
                'id': 'ingresos_2025',
                'name': 'Ingresos del año 2025',
                'description': 'Reporte de ingresos por día del año 2025',
                'prompt_example': 'Ingresos del año 2025 en Excel',
                'category': 'analytics'
            },
            {
                'id': 'analytics_completo',
                'name': 'Analytics completo',
                'description': 'Reporte completo con todas las métricas y estadísticas',
                'prompt_example': 'Reporte de analytics completo en PDF',
                'category': 'analytics'
            },
            {
                'id': 'resumen_mensual',
                'name': 'Resumen mensual',
                'description': 'Resumen de ventas, productos y clientes del mes',
                'prompt_example': 'Resumen del mes actual en PDF',
                'category': 'analytics'
            }
        ]

        return Response(templates, status=status.HTTP_200_OK)


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet para analytics y estadísticas del sistema.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Obtener resumen analítico completo.

        GET /api/analytics/overview/?months=12&days=30

        Returns:
            {
                "sales_by_month": [...],
                "products_by_category": [...],
                "activity_by_day": [...],
                "top_selling_products": [...],
                "summary": {...}
            }
        """
        serializer = AnalyticsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        months = serializer.validated_data['months']
        days = serializer.validated_data['days']

        try:
            data = {
                'sales_by_month': AnalyticsService.get_sales_by_month(months),
                'products_by_category': AnalyticsService.get_products_by_category(),
                'activity_by_day': AnalyticsService.get_activity_by_day(days),
                'top_selling_products': AnalyticsService.get_top_selling_products(limit=10),
                'sales_by_status': AnalyticsService.get_sales_by_status(),
                'summary': AnalyticsService.get_summary(),
                'inventory_summary': AnalyticsService.get_inventory_summary(),
                'customer_analytics': AnalyticsService.get_customer_analytics(),
                'yearly_comparison': AnalyticsService.get_yearly_comparison(),  # NUEVO
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en analytics overview: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Obtener resumen general del sistema.

        GET /api/analytics/summary/

        Returns:
            {
                "total_orders": 123,
                "orders_this_month": 45,
                "total_sales": 12345.67,
                ...
            }
        """
        try:
            summary = AnalyticsService.get_summary()
            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener resumen: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener resumen: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def sales(self, request):
        """
        Obtener datos de ventas por mes.

        GET /api/analytics/sales/?months=12

        Returns:
            [
                {"month": "Nov 2024", "total_sales": 1234.56, "order_count": 10},
                ...
            ]
        """
        months = int(request.query_params.get('months', 12))

        try:
            data = AnalyticsService.get_sales_by_month(months)
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener ventas: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener ventas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def products(self, request):
        """
        Obtener productos por categoría y más vendidos.

        GET /api/analytics/products/

        Returns:
            {
                "by_category": [...],
                "top_selling": [...]
            }
        """
        try:
            data = {
                'by_category': AnalyticsService.get_products_by_category(),
                'top_selling': AnalyticsService.get_top_selling_products(limit=10),
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener analytics de productos: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener datos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """
        Obtener resumen de inventario.

        GET /api/analytics/inventory/

        Returns:
            {
                "total_products": 123,
                "total_stock": 4567,
                "low_stock_items": 12,
                "out_of_stock_items": 3
            }
        """
        try:
            data = AnalyticsService.get_inventory_summary()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener resumen de inventario: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener inventario: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def customers(self, request):
        """
        Obtener analytics de clientes.

        GET /api/analytics/customers/

        Returns:
            {
                "total_customers": 123,
                "customers_with_orders": 45,
                "average_order_value": 123.45,
                ...
            }
        """
        try:
            data = AnalyticsService.get_customer_analytics()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener analytics de clientes: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener datos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def yearly_comparison(self, request):
        """
        Obtener comparativa detallada 2024 vs 2025.

        GET /api/analytics/yearly_comparison/

        Returns:
            {
                "year_2024": {
                    "total_ventas": 12345.67,
                    "total_pedidos": 123,
                    "nuevos_clientes": 45,
                    "nuevos_productos": 67,
                    "ticket_promedio": 123.45,
                    "ventas_por_mes": [...]
                },
                "year_2025": {...},
                "comparison": {
                    "cambio_ventas_porcentaje": 15.5,
                    "cambio_pedidos_porcentaje": 20.3,
                    ...
                }
            }
        """
        try:
            data = AnalyticsService.get_yearly_comparison()
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error al obtener comparativa anual: {e}", exc_info=True)
            return Response(
                {'error': f'Error al obtener comparativa: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

