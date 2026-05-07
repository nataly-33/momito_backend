from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerProfileViewSet, DireccionViewSet, FavoritosViewSet, ClientViewSet

router = DefaultRouter()
router.register(r'profile', CustomerProfileViewSet, basename='customer-profile')
router.register(r'addresses', DireccionViewSet, basename='address')
router.register(r'favorites', FavoritosViewSet, basename='favorite')
router.register(r'clients', ClientViewSet, basename='client')

urlpatterns = [
    path('', include(router.urls)),
]