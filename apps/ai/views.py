from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import MLModel, PrediccionVentas
from .serializers import (
    MLModelSerializer,
    MLModelListSerializer,
    PrediccionVentasSerializer,
    PredictRequestSerializer,
    TrainModelSerializer,
    DashboardResponseSerializer
)
from .services.model_training import ModelTrainingService
from .services.prediction import PredictionService


class AIViewSet(viewsets.ViewSet):
    """
    ViewSet para endpoints de Inteligencia Artificial y predicción de ventas
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.training_service = ModelTrainingService()
        self.prediction_service = PredictionService()
    
    @extend_schema(
        summary="Dashboard de predicción de ventas",
        description="""
        Retorna datos completos para el dashboard de predicción:
        - Ventas históricas (últimos 6 meses)
        - Predicciones futuras (próximos 3 meses)
        - Predicciones por categoría
        - Top 10 productos más vendidos
        - Ventas por categoría
        - Información del modelo activo
        """,
        responses={200: DashboardResponseSerializer},
        parameters=[
            OpenApiParameter(name='months_back', type=int, default=6, description='Meses históricos'),
            OpenApiParameter(name='months_forward', type=int, default=3, description='Meses futuros'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        GET /api/ai/dashboard/
        
        Retorna todos los datos necesarios para el dashboard de predicción
        """
        try:
            months_back = int(request.query_params.get('months_back', 24))
            months_forward = int(request.query_params.get('months_forward', 6))
            force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'

            data = self.prediction_service.get_sales_forecast_dashboard(
                months_back=months_back,
                months_forward=months_forward,
                use_cache=not force_refresh,
            )
            
            return Response(data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Error al generar dashboard',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Predecir ventas futuras",
        description="""
        Genera predicciones de ventas para los próximos N meses.
        
        Parámetros opcionales:
        - categoria: Filtrar por categoría específica
        - n_months: Número de meses a predecir (default: 1, máx: 12)
        """,
        request=PredictRequestSerializer,
        responses={200: PrediccionVentasSerializer(many=True)}
    )
    @action(detail=False, methods=['post'], url_path='predictions/sales-forecast')
    def sales_forecast(self, request):
        """
        POST /api/ai/predictions/sales-forecast/
        
        Body:
        {
            "categoria": "Vestidos",  // opcional
            "n_months": 3             // opcional, default 1
        }
        """
        try:
            serializer = PredictRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            categoria = serializer.validated_data.get('categoria')
            n_months = serializer.validated_data.get('n_months', 1)
            
            if n_months == 1:
                # Predicción de un solo mes
                prediction = self.prediction_service.predict_next_month(categoria=categoria)
                return Response(prediction, status=status.HTTP_200_OK)
            else:
                # Predicción de múltiples meses
                predictions = self.prediction_service.predict_next_n_months(
                    n_months=n_months,
                    categoria=categoria
                )
                return Response({
                    'predictions': predictions,
                    'count': len(predictions)
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Error al generar predicción',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Entrenar o re-entrenar modelo",
        description="""
        Entrena un nuevo modelo Random Forest con datos históricos de ventas.
        
        El proceso incluye:
        1. Extracción de datos históricos (últimos 12 meses)
        2. Preparación de features
        3. Entrenamiento del modelo
        4. Evaluación de métricas (MAE, MSE, RMSE, R²)
        5. Serialización y guardado del modelo
        6. Registro en base de datos
        
        **Nota**: Este proceso puede tardar varios segundos dependiendo de la cantidad de datos.
        """,
        request=TrainModelSerializer,
        responses={200: MLModelSerializer}
    )
    @action(detail=False, methods=['post'], url_path='train-model')
    def train_model(self, request):
        """
        POST /api/ai/train-model/
        
        Body:
        {
            "n_estimators": 100,    // opcional
            "max_depth": 10,        // opcional
            "test_size": 0.2        // opcional
        }
        """
        try:
            serializer = TrainModelSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = self.training_service.train_model(
                n_estimators=serializer.validated_data.get('n_estimators', 100),
                max_depth=serializer.validated_data.get('max_depth', 10),
                test_size=serializer.validated_data.get('test_size', 0.2)
            )
            
            # Obtener modelo recién creado
            ml_model = MLModel.objects.get(id=result['model_id'])
            model_serializer = MLModelSerializer(ml_model)
            
            return Response({
                'message': 'Modelo entrenado exitosamente',
                'model': model_serializer.data,
                'training_info': {
                    'num_samples': result['num_samples'],
                    'test_metrics': result['metrics']['test']
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Error al entrenar modelo',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @extend_schema(
        summary="Obtener modelo activo",
        description="Retorna información del modelo de ML actualmente activo",
        responses={200: MLModelSerializer}
    )
    @action(detail=False, methods=['get'], url_path='active-model')
    def active_model(self, request):
        """
        GET /api/ai/active-model/
        """
        try:
            ml_model, _, _ = self.training_service.load_active_model()
            serializer = MLModelSerializer(ml_model)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'No hay modelo activo',
                'detail': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary="Listar todos los modelos",
        description="Retorna lista de todos los modelos entrenados (activos e inactivos)",
        responses={200: MLModelListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='models')
    def list_models(self, request):
        """
        GET /api/ai/models/
        """
        models = MLModel.objects.all().order_by('-fecha_entrenamiento')
        serializer = MLModelListSerializer(models, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Historial de predicciones",
        description="Retorna historial de predicciones realizadas",
        responses={200: PrediccionVentasSerializer(many=True)},
        parameters=[
            OpenApiParameter(name='categoria', type=str, description='Filtrar por categoría'),
            OpenApiParameter(name='limit', type=int, default=50, description='Número de resultados'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='predictions/history')
    def predictions_history(self, request):
        """
        GET /api/ai/predictions/history/
        """
        queryset = PrediccionVentas.objects.select_related('modelo').order_by('-fecha_prediccion')
        
        # Filtros opcionales
        categoria = request.query_params.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        limit = int(request.query_params.get('limit', 50))
        queryset = queryset[:limit]
        
        serializer = PrediccionVentasSerializer(queryset, many=True)
        return Response({
            'predictions': serializer.data,
            'count': len(serializer.data)
        }, status=status.HTTP_200_OK)
