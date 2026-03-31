"""
XGBoost Emission Prediction — Step 2.2b
==========================================
Replaces standard linear models with XGBoost
Regressor as a robust boosting predictor.
"""

try:
    import xgboost as xgb
except ImportError:
    xgb = None
    
import numpy as np
import logging

logger = logging.getLogger("ai_engine.xgboost_model")

class EmissionXGBoost:
    """XGBoost wrapper for highly accurate tabular prediction."""
    
    def __init__(self):
        if xgb is None:
            logger.error("XGBoost library not found. Please pip install xgboost")
            self.model = None
            return
            
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=150,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        self.is_trained = False
        
    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train XGBoost model entirely on tabular 2D data."""
        if self.model is None: return 0.0
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        score = self.model.score(X_train, y_train)
        logger.info(f"XGBoost training completed. R2 Score: {score:.4f}")
        
        return score
        
    def predict(self, X_tabular: np.ndarray) -> np.ndarray:
        """Predict outcomes for tabular batch."""
        if not self.is_trained and self.model is not None:
            logger.warning("XGBoost model predicting without being fit!")
            
        if self.model is None:
            return np.zeros(X_tabular.shape[0])
            
        preds = self.model.predict(X_tabular)
        # Ensure non-negative emissions
        return np.maximum(0.0, preds)
