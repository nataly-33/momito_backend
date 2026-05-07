from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Categoria, Marca, Talla, Prenda, StockPrenda, ImagenPrendaURL, InventoryMovement
from .serializers import (
    CategoriaSerializer, MarcaSerializer, TallaSerializer,
    PrendaListSerializer, PrendaDetailSerializer, PrendaCreateUpdateSerializer,
    StockPrendaSerializer, ImagenPrendaURLSerializer, InventoryMovementSerializer
)
from apps.core.permissions import IsAdminUser, IsEmpleadoOrAdmin


class CategoriaViewSet(viewsets.ModelViewSet):
    """CRUD de categorías"""
    queryset = Categoria.objects.filter(deleted_at__isnull=True)
    serializer_class = CategoriaSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsEmpleadoOrAdmin()]
    
    def perform_destroy(self, instance):
        instance.soft_delete()


class MarcaViewSet(viewsets.ModelViewSet):
    """CRUD de marcas"""
    queryset = Marca.objects.filter(deleted_at__isnull=True)
    serializer_class = MarcaSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsEmpleadoOrAdmin()]
    
    def perform_destroy(self, instance):
        instance.soft_delete()


class TallaViewSet(viewsets.ModelViewSet):
    """CRUD de tallas"""
    queryset = Talla.objects.filter(deleted_at__isnull=True)
    serializer_class = TallaSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    def perform_destroy(self, instance):
        instance.soft_delete()


class PrendaViewSet(viewsets.ModelViewSet):
    """CRUD de productos mayoristas con filtros B2B"""
    queryset = Prenda.objects.filter(deleted_at__isnull=True).prefetch_related(
        'marca', 'categorias', 'tallas_disponibles', 'imagenes_url', 'stocks'
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['marca', 'categorias', 'activa', 'destacada']
    search_fields = ['nombre', 'descripcion', 'code', 'marca__nombre']
    ordering_fields = ['price_wholesale', 'precio', 'created_at', 'nombre', 'stock']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PrendaListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PrendaCreateUpdateSerializer
        return PrendaDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'search']:
            return [AllowAny()]
        return [IsEmpleadoOrAdmin()]

    def get_object(self):
        """Primero mira si existe el slug, luego por PK solo si el valor de búsqueda
        es un UUID válido. Esto evita intentos de coerción de slugs no UUID en
        el campo UUID PK (lo que generó ValidationError y produjo 500s).
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        queryset = self.filter_queryset(self.get_queryset())

        # First try lookup by slug
        try:
            obj = queryset.get(slug=lookup_value)
        except Prenda.DoesNotExist:
            # If not found by slug, only attempt PK lookup when the value
            # is a valid UUID to avoid Django validation errors.
            import uuid
            try:
                uuid.UUID(str(lookup_value))
            except (ValueError, TypeError):
                from django.http import Http404
                raise Http404

            try:
                obj = queryset.get(pk=lookup_value)
            except Prenda.DoesNotExist:
                from django.http import Http404
                raise Http404

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_queryset(self):
        """
        Personaliza el queryset: empleados/admin ven todos los productos,
        usuarios públicos solo ven productos activos
        """
        queryset = super().get_queryset()

        # Si el usuario es empleado/admin, puede ver todos los productos (activos e inactivos)
        if self.request.user.is_authenticated:
            user_perms = getattr(self.request.user, 'permisos_usuario', [])
            is_staff_or_admin = (
                self.request.user.is_staff or
                'products.view_prenda' in user_perms or
                hasattr(self.request.user, 'codigo_empleado')
            )
            if not is_staff_or_admin:
                # Usuario autenticado sin permisos, solo productos activos
                queryset = queryset.filter(activa=True)
        else:
            # Usuarios no autenticados solo ven productos activos
            queryset = queryset.filter(activa=True)

        # Filtro por rango de precio
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)

        # Filtro por talla
        talla = self.request.query_params.get('talla')
        if talla:
            queryset = queryset.filter(tallas_disponibles__id=talla)

        # Filtro por disponibilidad (stock en StockPrenda)
        solo_con_stock = self.request.query_params.get('con_stock')
        if solo_con_stock == 'true':
            queryset = queryset.filter(stocks__cantidad__gt=0).distinct()

        # Filtro B2B: solo productos con stock bajo
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            from django.db.models import F
            queryset = queryset.filter(stock__lte=F('stock_min'))

        # Filtro por marca (nombre)
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(marca__nombre__icontains=brand)

        return queryset
    
    @action(detail=False, methods=['get'])
    def destacadas(self, request):
        """Obtener prendas destacadas"""
        prendas = self.get_queryset().filter(destacada=True)[:12]
        serializer = PrendaListSerializer(prendas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def novedades(self, request):
        """Obtener novedades"""
        prendas = self.get_queryset().filter(es_novedad=True)[:12]
        serializer = PrendaListSerializer(prendas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def agregar_imagen(self, request, pk=None):
        """Agregar imagen URL a una prenda"""
        prenda = self.get_object()
        serializer = ImagenPrendaURLSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(prenda=prenda)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'put'])
    def stock(self, request, pk=None):
        """Ver o actualizar stock de una prenda"""
        prenda = self.get_object()
        
        if request.method == 'GET':
            stocks = prenda.stocks.all()
            serializer = StockPrendaSerializer(stocks, many=True)
            return Response({
                'prenda': prenda.nombre,
                'stock_total': prenda.stock_total,
                'stocks_por_talla': serializer.data
            })
        
        elif request.method == 'PUT':
            # Actualizar stocks
            stocks_data = request.data.get('stocks', [])
            for stock_data in stocks_data:
                talla_id = stock_data.get('talla')
                cantidad = stock_data.get('cantidad')
                
                stock, created = StockPrenda.objects.get_or_create(
                    prenda=prenda,
                    talla_id=talla_id,
                    defaults={'cantidad': cantidad}
                )
                if not created:
                    stock.cantidad = cantidad
                    stock.save()
            
            stocks = prenda.stocks.all()
            serializer = StockPrendaSerializer(stocks, many=True)
            return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.soft_delete()


class InventoryMovementViewSet(viewsets.ModelViewSet):
    """CRUD de movimientos de inventario B2B"""
    queryset = InventoryMovement.objects.filter(deleted_at__isnull=True).select_related(
        'product', 'user'
    )
    serializer_class = InventoryMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'movement_type']
    search_fields = ['product__nombre', 'product__code', 'notes']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsEmpleadoOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)