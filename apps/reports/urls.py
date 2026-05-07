from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReportsViewSet, AnalyticsViewSet
from .tumomito_views import TumomitoReportsViewSet

router = DefaultRouter()
router.register(r'reports', ReportsViewSet, basename='reports')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

# TUMOMITO dashboard endpoints — mapped manually to avoid router prefix conflict
_tv = TumomitoReportsViewSet

urlpatterns = [
    path('', include(router.urls)),
    path('reports/dashboard/', _tv.as_view({'get': 'dashboard'}), name='tumomito-dashboard'),
    path('reports/sales/', _tv.as_view({'get': 'sales'}), name='tumomito-sales'),
    path('reports/monthly/', _tv.as_view({'get': 'monthly'}), name='tumomito-monthly'),
    path('reports/top-clients/', _tv.as_view({'get': 'top_clients'}), name='tumomito-top-clients'),
    path('reports/orders-status/', _tv.as_view({'get': 'orders_status'}), name='tumomito-orders-status'),
    path('reports/low-stock/', _tv.as_view({'get': 'low_stock'}), name='tumomito-low-stock'),
    path('reports/brands/', _tv.as_view({'get': 'brands'}), name='tumomito-brands'),
    path('reports/categories/', _tv.as_view({'get': 'categories'}), name='tumomito-categories'),
    path('reports/recent-activity/', _tv.as_view({'get': 'recent_activity'}), name='tumomito-activity'),
]
