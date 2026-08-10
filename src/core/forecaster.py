import os
import joblib
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from src.pipeline.preprocessor import TimeSeriesPreprocessor
from src.utils.logger import setup_logger

logger = setup_logger("forecaster")

class ProductForecaster:
    def __init__(self, models_dir: str, preprocessor_path: str):
        self.models_dir = models_dir
        self.preprocessor_path = preprocessor_path
        self.preprocessor: Optional[TimeSeriesPreprocessor] = None
        self.models: Dict[str, Any] = {}
        self.step_residuals: Dict[str, List[float]] = {}
        self.load_artifacts()

    def load_artifacts(self):
        if not os.path.exists(self.preprocessor_path):
            logger.warning(f"Preprocessor not found at {self.preprocessor_path}. Models cannot run inference.")
            return
            
        self.preprocessor = TimeSeriesPreprocessor.load(self.preprocessor_path)
        logger.info("Preprocessor loaded successfully.")
        
        for target in self.preprocessor.target_cols:
            target_lower = target.lower()
            model_path = os.path.join(self.models_dir, target_lower, "model.joblib")
            if os.path.exists(model_path):
                self.models[target_lower] = joblib.load(model_path)
                logger.info(f"Loaded LightGBM model for target: {target_lower}")
            else:
                logger.warning(f"Model for {target_lower} not found at {model_path}")
                
            # Load step residuals standard deviation
            meta_path = os.path.join(self.models_dir, target_lower, "model_metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                        self.step_residuals[target_lower] = meta.get("step_residuals_std", [])  
                        logger.info(f"Loaded step residuals for target: {target_lower}")
                except Exception as e:
                    logger.error(f"Error loading metadata for {target_lower}: {e}")
                    self.step_residuals[target_lower] = [0.0] * 100
            else:
                self.step_residuals[target_lower] = [0.0] * 100

    def forecast(
        self,
        historical_df: pd.DataFrame,
        product_id: str,
        horizon_days: int,
        future_overrides: Optional[Dict[str, List[float]]] = None,
        current_features: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Performs recursive (autoregressive) multi-step forecasting for a single product using lowercase schema.
        Supports seeding/override of last known historical day (t=0) using current_features.
        """
        if self.preprocessor is None or not self.models:
            raise ValueError("Models and preprocessor are not fully loaded.")
            
        # Filter for the specific product and sort by date
        prod_data = historical_df[historical_df["product_id"] == product_id].copy()
        if len(prod_data) == 0:
            matched_prod = [p for p in historical_df["product_id"].unique() if str(p).lower() == str(product_id).lower()]
            if matched_prod:
                prod_data = historical_df[historical_df["product_id"] == matched_prod[0]].copy()
                product_id = matched_prod[0]
            else:
                raise ValueError(f"Product ID {product_id} not found in historical data.")
            
        prod_data["date"] = pd.to_datetime(prod_data["date"])
        prod_data = prod_data.sort_values(by="date").reset_index(drop=True)
        
        # Get metadata for the product
        category = prod_data["category"].iloc[-1]
        
        # Max lag/rolling window is 30, so keep last 40 days
        history_window = 40
        last_history = prod_data.tail(history_window).copy()
        
        # Override the last day of history (t=0) with current features if provided
        if current_features:
            for key, val in current_features.items():
                key_lower = key.lower()
                if key_lower == "price":
                    key_lower = "avg_selling_price"
                elif key_lower == "inventory":
                    key_lower = "inventory_available"
                    
                if key_lower in last_history.columns:
                    last_history.at[last_history.index[-1], key_lower] = val
                    logger.debug(f"Overwrote current feature {key_lower} with {val} at last historical day (t=0)")
        
        last_date = last_history["date"].iloc[-1]
        
        # Determine if discount is on a scale of 0-100 or 0-1
        last_disc = last_history["discount_pct"].iloc[-1]
        is_int_percent = last_disc > 1.0
        
        # Build future dataframe shell
        future_rows = []
        for i in range(1, horizon_days + 1):
            future_date = last_date + timedelta(days=i)
            
            # Carry forward default values from the (possibly overwritten) last day of history
            marketing_spend = last_history["marketing_spend"].iloc[-1]
            discount_pct = last_history["discount_pct"].iloc[-1]
            shipping_fee = last_history["shipping_fee"].iloc[-1]
            avg_selling_price = last_history["avg_selling_price"].iloc[-1]
            inventory_available = last_history["inventory_available"].iloc[-1]
            traffic = last_history["traffic"].iloc[-1]
            
            # Apply overrides
            if future_overrides:
                idx = i - 1
                if "marketing_spend" in future_overrides and idx < len(future_overrides["marketing_spend"]):
                    marketing_spend = future_overrides["marketing_spend"][idx]
                if "discount_pct" in future_overrides and idx < len(future_overrides["discount_pct"]):
                    raw_override = future_overrides["discount_pct"][idx]
                    if is_int_percent and raw_override <= 1.0:
                        discount_pct = raw_override * 100.0
                    else:
                        discount_pct = raw_override
                if "shipping_fee" in future_overrides and idx < len(future_overrides["shipping_fee"]):
                    shipping_fee = future_overrides["shipping_fee"][idx]
                if "avg_selling_price" in future_overrides and idx < len(future_overrides["avg_selling_price"]):
                    avg_selling_price = future_overrides["avg_selling_price"][idx]
                
            future_rows.append({
                "date": future_date,
                "product_id": product_id,
                "category": category,
                "avg_selling_price": avg_selling_price,
                "discount_pct": discount_pct,
                "shipping_fee": shipping_fee,
                "marketing_spend": marketing_spend,
                "inventory_available": inventory_available,
                "traffic": traffic,
                # Targets are set to nan initially
                "revenue": np.nan,
                "profit": np.nan,
                "orders": np.nan,
                "conversion_rate": np.nan,
                "retention_rate": np.nan
            })
            
        future_df = pd.DataFrame(future_rows)
        combined_df = pd.concat([last_history, future_df], ignore_index=True)
        
        # Multi-step autoregressive loop
        start_idx = len(last_history)
        end_idx = len(combined_df)
        
        for current_idx in range(start_idx, end_idx):
            sub_df = combined_df.iloc[:current_idx + 1].copy()
            transformed_sub = self.preprocessor.transform(sub_df)
            
            pred_row = transformed_sub.iloc[[-1]]
            X_pred = pred_row[self.preprocessor.feature_cols]
            
            for target in self.preprocessor.target_cols:
                target_lower = target.lower()
                model = self.models[target_lower]
                pred_val = model.predict(X_pred)[0]
                
                # Logical bounding
                if target_lower in ["orders", "revenue", "profit"] and pred_val < 0:
                    pred_val = 0.0
                elif target_lower in ["conversion_rate", "retention_rate"]:
                    pred_val = max(0.0, min(1.0, pred_val))
                    
                combined_df.at[current_idx, target_lower] = pred_val
                
        forecast_df = combined_df.iloc[start_idx:].copy().reset_index(drop=True)
        
        # 3. Calculate and append Empirical Confidence Intervals per step
        for target in self.preprocessor.target_cols:
            target_lower = target.lower()
            std_errors = self.step_residuals.get(target_lower) or [0.0] * 100
            
            conf_lowers = []
            conf_uppers = []
            
            for idx in range(len(forecast_df)):
                pred_val = forecast_df.at[idx, target_lower]
                
                # Fetch step-specific std error (fallback to last if horizon exceeds error list length)
                std_err = std_errors[idx] if idx < len(std_errors) else std_errors[-1]
                
                # 95% Confidence Interval (z = 1.96)
                margin = 1.96 * std_err
                lower = pred_val - margin
                upper = pred_val + margin
                
                # Logical clipping to prevent nonsensical business metrics
                if target_lower in ["revenue", "orders"]:
                    lower = max(0.0, lower)
                elif target_lower == "profit":
                    # Profits can be negative in business, but let's bound lower based on logical minimum costs if needed
                    # Keep as is, but clip lower bound of confidence if it goes extremely negative (say max(lower, -10x of predicted or 0))
                    # Let's keep profit unclipped on the negative side since negative profit is possible
                    pass
                elif target_lower in ["conversion_rate", "retention_rate"]:
                    lower = max(0.0, min(1.0, lower))
                    upper = max(0.0, min(1.0, upper))
                    
                conf_lowers.append(lower)
                conf_uppers.append(upper)
                
            forecast_df[f"{target_lower}_conf_lower"] = conf_lowers
            forecast_df[f"{target_lower}_conf_upper"] = conf_uppers
            
        return forecast_df
