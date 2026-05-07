from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, MarcaViewSet, TallaViewSet, PrendaViewSet, InventoryMovementViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='categoria')
router.register(r'marcas', MarcaViewSet, basename='marca')
router.register(r'tallas', TallaViewSet, basename='talla')
router.register(r'prendas', PrendaViewSet, basename='prenda')
router.register(r'inventory-movements', InventoryMovementViewSet, basename='inventory-movement')

urlpatterns = [
    path('', include(router.urls)),
]