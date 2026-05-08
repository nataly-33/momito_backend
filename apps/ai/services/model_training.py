"""
Servicio de entrenamiento del modelo Random Forest

Este módulo se encarga de:
1. Entrenar el modelo Random Forest con datos históricos
2. Evaluar el rendimiento del modelo
3. Guardar el modelo serializado
4. Registrar métricas en la base de datos
"""

import os
import joblib
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from django.conf import settings

from apps.ai.models import MLModel
from apps.ai.services.data_preparation import DataPreparationService


class ModelTrainingService:
    """
    Servicio para entrenar y gestionar el modelo de predicción de ventas
    """
    
    def __init__(self):
        self.data_service = DataPreparationService()
        self.models_dir = os.path.join(settings.BASE_DIR, 'models')
        
        # Crear directorio si no existe
        os.makedirs(self.models_dir, exist_ok=True)
    
    def train_model(self, months_back=36, n_estimators=100, max_depth=10, random_state=42, test_size=0.2):
        """
        Entrena un nuevo modelo Random Forest
        
        Args:
            months_back (int): Meses de datos históricos a usar (36 = 3 años, 24 = 2 años)
            n_estimators (int): Número de árboles en el bosque
            max_depth (int): Profundidad máxima de los árboles
            random_state (int): Semilla para reproducibilidad
            test_size (float): Proporción de datos para testing
            
        Returns:
            dict: Información del modelo entrenado y métricas
        """
        print("=" * 60)
        print("INICIANDO ENTRENAMIENTO DEL MODELO DE PREDICCION DE VENTAS")
        print("=" * 60)

        # 1. Obtener datos históricos
        print(f"\nPaso 1: Obteniendo datos historicos ({months_back} meses = {months_back/12:.1f} anos)...")
        df = self.data_service.get_historical_sales_data(months_back=months_back)
        print(f"OK {len(df)} registros obtenidos")

        # 2. Preparar features
        print("\nPaso 2: Preparando features...")
        X, y, feature_columns = self.data_service.prepare_features(df, months_back=months_back)
        print(f"OK {len(feature_columns)} features creadas")
        print(f"   Samples: {len(X)}, Features: {X.shape[1]}")

        # 3. Dividir en train/test
        print(f"\nPaso 3: Dividiendo datos (train: {int((1-test_size)*100)}%, test: {int(test_size*100)}%)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        print(f"OK Train: {len(X_train)} samples | Test: {len(X_test)} samples")

        # 4. Entrenar modelo
        print(f"\nPaso 4: Entrenando Random Forest (n_estimators={n_estimators}, max_depth={max_depth})...")
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,  # Usar todos los cores disponibles
            verbose=0
        )
        
        model.fit(X_train, y_train)
        print("OK Modelo entrenado exitosamente")

        # 5. Evaluar modelo
        print("\nPaso 5: Evaluando rendimiento...")
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        # Métricas en train
        mae_train = mean_absolute_error(y_train, y_pred_train)
        mse_train = mean_squared_error(y_train, y_pred_train)
        rmse_train = np.sqrt(mse_train)
        r2_train = r2_score(y_train, y_pred_train)
        
        # Métricas en test
        mae_test = mean_absolute_error(y_test, y_pred_test)
        mse_test = mean_squared_error(y_test, y_pred_test)
        rmse_test = np.sqrt(mse_test)
        r2_test = r2_score(y_test, y_pred_test)
        
        print("\n" + "=" * 60)
        print("METRICAS DE RENDIMIENTO")
        print("=" * 60)
        print("\nTRAIN SET:")
        print(f"   MAE:  {mae_train:.2f}")
        print(f"   MSE:  {mse_train:.2f}")
        print(f"   RMSE: {rmse_train:.2f}")
        print(f"   R2:   {r2_train:.4f}")

        print("\nTEST SET:")
        print(f"   MAE:  {mae_test:.2f}")
        print(f"   MSE:  {mse_test:.2f}")
        print(f"   RMSE: {rmse_test:.2f}")
        print(f"   R2:   {r2_test:.4f}")

        # Importancia de features
        print("\nTOP 10 FEATURES MAS IMPORTANTES:")
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in feature_importance.head(10).iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
        
        # 6. Guardar modelo
        print("\n💾 Paso 6: Guardando modelo...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version = f"v1.0_{timestamp}"
        model_filename = f"ventas_predictor_{version}.pkl"
        model_path = os.path.join(self.models_dir, model_filename)
        
        # Guardar modelo con joblib
        joblib.dump({
            'model': model,
            'feature_columns': feature_columns,
            'version': version,
            'trained_at': datetime.now().isoformat(),
            'months_back': months_back
        }, model_path)
        
        print(f"OK Modelo guardado en: {model_path}")

        # 7. Registrar en base de datos
        print("\nPaso 7: Registrando en base de datos...")
        ml_model = MLModel.objects.create(
            nombre='Predictor de Ventas',
            version=version,
            descripcion=f'Random Forest Regressor entrenado con {len(X_train)} muestras ({months_back} meses de datos)',
            archivo_modelo=model_path,
            mae=mae_test,
            mse=mse_test,
            rmse=rmse_test,
            r2_score=r2_test,
            registros_entrenamiento=len(X_train),
            features_utilizadas=feature_columns,
            hiperparametros={
                'n_estimators': n_estimators,
                'max_depth': max_depth,
                'random_state': random_state,
                'test_size': test_size,
                'months_back': months_back
            },
            activo=True  # Activar automáticamente el nuevo modelo
        )
        
        # Desactivar modelos anteriores
        MLModel.objects.filter(activo=True).exclude(id=ml_model.id).update(activo=False)
        
        print(f"OK Modelo registrado con ID: {ml_model.id}")

        print("\n" + "=" * 60)
        print("ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        
        return {
            'model_id': ml_model.id,
            'version': version,
            'model_path': model_path,
            'months_back': months_back,
            'metrics': {
                'train': {
                    'mae': mae_train,
                    'mse': mse_train,
                    'rmse': rmse_train,
                    'r2': r2_train
                },
                'test': {
                    'mae': mae_test,
                    'mse': mse_test,
                    'rmse': rmse_test,
                    'r2': r2_test
                }
            },
            'feature_importance': feature_importance.to_dict('records'),
            'num_samples': len(X)
        }
    
    def load_active_model(self):
        """
        Carga el modelo activo desde el archivo
        
        Returns:
            tuple: (modelo_ml, sklearn_model, feature_columns)
        """
        try:
            # Obtener modelo activo de la BD
            ml_model = MLModel.objects.filter(activo=True).latest('fecha_entrenamiento')
            
            # Cargar archivo
            if not os.path.exists(ml_model.archivo_modelo):
                raise FileNotFoundError(f"Archivo del modelo no encontrado: {ml_model.archivo_modelo}")
            
            model_data = joblib.load(ml_model.archivo_modelo)
            
            return ml_model, model_data['model'], model_data['feature_columns']
        
        except MLModel.DoesNotExist:
            raise Exception("No hay ningún modelo activo. Por favor, entrena un modelo primero.")
    
    def retrain_model(self):
        """
        Re-entrena el modelo con datos actualizados
        
        Returns:
            dict: Información del nuevo modelo
        """
        print("\nRE-ENTRENANDO MODELO CON DATOS ACTUALIZADOS...")
        return self.train_model()


# Importar pandas solo si se necesita
import pandas as pd
