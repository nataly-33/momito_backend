"""
Servicio de predicción de ventas

Este módulo se encarga de:
1. Cargar el modelo entrenado
2. Generar predicciones para períodos futuros
3. Guardar predicciones en la base de datos
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone

from apps.ai.models import PrediccionVentas
from apps.ai.services.model_training import ModelTrainingService
from apps.ai.services.data_preparation import DataPreparationService


class PredictionService:
    """
    Servicio para generar predicciones de ventas futuras
    """
    
    def __init__(self):
        self.training_service = ModelTrainingService()
        self.data_service = DataPreparationService()
    
    def predict_next_month(self, categoria=None):
        """
        Predice las ventas del próximo mes
        
        Args:
            categoria (str): Categoría específica (opcional)
            
        Returns:
            dict: Predicción de ventas
        """
        # Cargar modelo activo
        ml_model, model, feature_columns = self.training_service.load_active_model()
        
        # Preparar features para el próximo mes
        next_month_features = self._prepare_next_month_features(categoria, feature_columns)
        
        # Hacer predicción
        prediction = model.predict(next_month_features)[0]
        
        # Calcular período
        next_month = timezone.now() + timedelta(days=30)
        periodo = next_month.strftime('%Y-%m')
        
        # Guardar predicción en BD
        prediccion = PrediccionVentas.objects.create(
            modelo=ml_model,
            periodo_predicho=periodo,
            ventas_predichas=prediction,
            categoria=categoria or 'Total',
            features_input=next_month_features.to_dict('records')[0]
        )
        
        return {
            'periodo': periodo,
            'ventas_predichas': round(prediction, 2),
            'categoria': categoria or 'Total',
            'prediccion_id': prediccion.id,
            'confianza': self._calculate_confidence(ml_model)
        }
    
    def predict_next_n_months(self, n_months=3, categoria=None):
        """
        Predice las ventas de los próximos N meses
        
        Args:
            n_months (int): Número de meses a predecir
            categoria (str): Categoría específica (opcional)
            
        Returns:
            list: Lista de predicciones
        """
        ml_model, model, feature_columns = self.training_service.load_active_model()
        
        predictions = []
        
        for i in range(n_months):
            # Calcular fecha del mes a predecir
            target_date = timezone.now() + timedelta(days=30 * (i + 1))
            periodo = target_date.strftime('%Y-%m')
            
            # Preparar features
            features = self._prepare_features_for_date(target_date, categoria, feature_columns)
            
            # Hacer predicción
            prediction = model.predict(features)[0]
            
            # Guardar en BD
            prediccion = PrediccionVentas.objects.create(
                modelo=ml_model,
                periodo_predicho=periodo,
                ventas_predichas=prediction,
                categoria=categoria or 'Total',
                features_input=features.to_dict('records')[0]
            )
            
            predictions.append({
                'periodo': periodo,
                'ventas_predichas': round(prediction, 2),
                'categoria': categoria or 'Total',
                'mes': target_date.month,
                'año': target_date.year
            })
        
        return predictions
    
    def predict_by_category(self, n_months=6, use_cache=True):
        """
        Predice ventas de los próximos N meses para cada categoría.
        Si use_cache=True y ya existen predicciones en BD para el modelo activo,
        las devuelve directamente sin re-ejecutar el modelo (mucho más rápido).
        """
        from apps.ai.services.data_preparation import CATEGORIAS_TUMOMITO
        categorias = CATEGORIAS_TUMOMITO
        ml_model, model, feature_columns = self.training_service.load_active_model()

        # Calcular períodos esperados
        expected_periods = []
        for i in range(n_months):
            target_date = timezone.now() + timedelta(days=30 * (i + 1))
            expected_periods.append(target_date.strftime('%Y-%m'))

        # ── Caché: devolver predicciones guardadas si están completas ──────────
        if use_cache:
            cached = list(
                PrediccionVentas.objects.filter(
                    modelo=ml_model,
                    periodo_predicho__in=expected_periods,
                    categoria__in=categorias,
                ).order_by('periodo_predicho', 'categoria')
            )
            if len(cached) >= n_months * len(categorias):
                confianza = self._calculate_confidence(ml_model)
                return [
                    {
                        'periodo': p.periodo_predicho,
                        'ventas_predichas': round(float(p.ventas_predichas), 2),
                        'categoria': p.categoria,
                        'prediccion_id': str(p.id),
                        'confianza': confianza,
                    }
                    for p in cached
                ]

        # ── Generar predicciones nuevas ────────────────────────────────────────
        predictions = []
        for i, periodo in enumerate(expected_periods):
            target_date = timezone.now() + timedelta(days=30 * (i + 1))
            for categoria in categorias:
                try:
                    features = self._prepare_features_for_date(target_date, categoria, feature_columns)
                    prediction = max(0.0, float(model.predict(features)[0]))

                    prediccion, _ = PrediccionVentas.objects.update_or_create(
                        modelo=ml_model,
                        periodo_predicho=periodo,
                        categoria=categoria,
                        defaults={
                            'ventas_predichas': prediction,
                            'features_input': features.to_dict('records')[0],
                        },
                    )

                    predictions.append({
                        'periodo': periodo,
                        'ventas_predichas': round(prediction, 2),
                        'categoria': categoria,
                        'prediccion_id': str(prediccion.id),
                        'confianza': self._calculate_confidence(ml_model),
                    })
                except Exception as e:
                    print(f"⚠️ Error prediciendo {categoria} para {periodo}: {e}")

        return predictions

    def get_sales_forecast_dashboard(self, months_back=24, months_forward=6, use_cache=True):
        """
        Genera datos completos para el dashboard de predicción.
        use_cache=True: devuelve predicciones guardadas en BD (rápido).
        use_cache=False: re-ejecuta el modelo y sobreescribe (lento, solo en "Generar").
        """
        # 1. Datos históricos
        historical_data = self._get_historical_data_aggregated(months_back)

        # 2. Predicciones por categoría
        category_predictions = self.predict_by_category(
            n_months=months_forward, use_cache=use_cache
        )
        
        # 3. Calcular predicciones totales por mes sumando las categorías
        future_predictions = []
        predictions_by_month = {}
        
        for pred in category_predictions:
            periodo = pred['periodo']
            if periodo not in predictions_by_month:
                predictions_by_month[periodo] = {
                    'periodo': periodo,
                    'ventas_predichas': 0,
                    'mes': int(periodo.split('-')[1]),
                    'año': int(periodo.split('-')[0])
                }
            predictions_by_month[periodo]['ventas_predichas'] += pred['ventas_predichas']
        
        future_predictions = list(predictions_by_month.values())
        
        # 4. Top productos
        top_products = self.data_service.get_top_selling_products(limit=10)
        
        # 5. Ventas por categoría histórica
        category_sales = self.data_service.get_sales_by_category()
        
        # 6. Modelo activo
        ml_model, _, _ = self.training_service.load_active_model()
        
        return {
            'historical': historical_data,
            'predictions': future_predictions,
            'predictions_by_category': category_predictions,
            'top_products': top_products,
            'category_sales': category_sales,
            'model_info': {
                'version': ml_model.version,
                'trained_at': ml_model.fecha_entrenamiento.isoformat(),
                'r2_score': ml_model.r2_score,
                'mae': ml_model.mae,
                'features_used': ml_model.features_utilizadas
            }
        }
    
    def _prepare_next_month_features(self, categoria, feature_columns):
        """
        Prepara features para predecir el próximo mes
        """
        next_month = timezone.now() + timedelta(days=30)
        return self._prepare_features_for_date(next_month, categoria, feature_columns)
    
    def _prepare_features_for_date(self, target_date, categoria, feature_columns):
        """
        Prepara features para una fecha específica
        """
        # Features base
        features = {
            'año': target_date.year,
            'mes': target_date.month,
            'mes_sin': np.sin(2 * np.pi * target_date.month / 12),
            'mes_cos': np.cos(2 * np.pi * target_date.month / 12),
            'trimestre': (target_date.month - 1) // 3 + 1,
        }
        
        # One-hot encoding para categorías
        from apps.ai.services.data_preparation import CATEGORIAS_TUMOMITO
        categorias_disponibles = CATEGORIAS_TUMOMITO + ['Sin categoría']
        for cat in categorias_disponibles:
            col_name = f'cat_{cat}'
            if col_name in feature_columns:
                features[col_name] = 1 if categoria == cat else 0
        
        # Crear DataFrame con las columnas en el orden correcto
        df = pd.DataFrame([features])
        
        # Asegurar que tengamos todas las columnas necesarias
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0
        
        # Reordenar columnas según el orden de entrenamiento
        df = df[feature_columns]
        
        return df
    
    def _get_historical_data_aggregated(self, months_back):
        """
        Obtiene datos históricos agregados por mes
        """
        df = self.data_service.get_historical_sales_data(months_back=months_back)
        
        if df.empty:
            return []
        
        # Agrupar por año y mes
        monthly = df.groupby(['año', 'mes']).agg({
            'cantidad': 'sum',
            'subtotal': 'sum'
        }).reset_index()
        
        monthly.columns = ['año', 'mes', 'cantidad_vendida', 'total_ventas']
        monthly['periodo'] = monthly.apply(lambda x: f"{int(x['año'])}-{int(x['mes']):02d}", axis=1)
        
        return monthly[['periodo', 'cantidad_vendida', 'total_ventas']].to_dict('records')
    
    def _calculate_confidence(self, ml_model):
        """
        Calcula un nivel de confianza basado en el R² score
        """
        if ml_model.r2_score >= 0.8:
            return 'Alta'
        elif ml_model.r2_score >= 0.6:
            return 'Media'
        else:
            return 'Baja'
    
    def compare_prediction_with_real(self, prediccion_id):
        """
        Compara una predicción con ventas reales (cuando estén disponibles)
        
        Args:
            prediccion_id (int): ID de la predicción
            
        Returns:
            dict: Comparación entre predicción y realidad
        """
        try:
            prediccion = PrediccionVentas.objects.get(id=prediccion_id)
            
            # Parsear período (formato: 'YYYY-MM')
            año, mes = map(int, prediccion.periodo_predicho.split('-'))
            
            # Obtener ventas reales de ese período
            df = self.data_service.get_historical_sales_data(months_back=24)
            
            if not df.empty:
                ventas_reales = df[(df['año'] == año) & (df['mes'] == mes)]['cantidad'].sum()
                
                # Actualizar predicción
                prediccion.ventas_reales = ventas_reales
                prediccion.calcular_error()
                
                return {
                    'prediccion_id': prediccion_id,
                    'periodo': prediccion.periodo_predicho,
                    'ventas_predichas': prediccion.ventas_predichas,
                    'ventas_reales': ventas_reales,
                    'error': prediccion.error,
                    'error_porcentaje': (prediccion.error / ventas_reales * 100) if ventas_reales > 0 else None
                }
            
            return {'error': 'No hay datos reales disponibles para este período'}
        
        except PrediccionVentas.DoesNotExist:
            return {'error': 'Predicción no encontrada'}
