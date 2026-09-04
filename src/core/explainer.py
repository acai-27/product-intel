import os
import joblib
import pandas as pd
import numpy as np
import shap
from typing import Dict, List, Any, Optional

from src.pipeline.preprocessor import TimeSeriesPreprocessor
from src.core.forecaster import ProductForecaster
from src.utils.logger import setup_logger

logger = setup_logger("explainer")

# Dictionary to map technical feature names to clean business terms
FEATURE_TRANSLATION = {
    "avg_selling_price": "Price of the product",
    "discount_pct": "Discount percentage",
    "shipping_fee": "Shipping fee",
    "marketing_spend": "Ad spend / marketing budget",
    "inventory_available": "Inventory in stock",
    "traffic": "Product details page traffic / views",
    "day_of_week": "Day of the week",
    "day_of_month": "Day of the month",
    "month": "Month of the year",
    "is_weekend": "Weekend seasonality",
    "product_id_code": "Product historical baseline",
    "category_code": "Category baseline"
}

def get_clean_feature_name(feature: str) -> str:
    # Handle Lags e.g. revenue_lag_7
    if "_lag_" in feature:
        base, lag = feature.split("_lag_")
        base_clean = FEATURE_TRANSLATION.get(base, base.replace("_", " "))
        return f"{base_clean} from {lag} days ago"
    # Handle Rolling e.g. revenue_roll_mean_7
    if "_roll_mean_" in feature:
        base, win = feature.split("_roll_mean_")
        base_clean = FEATURE_TRANSLATION.get(base, base.replace("_", " "))
        return f"Average {base_clean} over the last {win} days"
    if "_roll_std_" in feature:
        base, win = feature.split("_roll_std_")
        base_clean = FEATURE_TRANSLATION.get(base, base.replace("_", " "))
        return f"Volatility of {base_clean} over the last {win} days"
        
    return FEATURE_TRANSLATION.get(feature, feature.replace("_", " "))

class PredictionExplainer:
    def __init__(self, forecaster: ProductForecaster):
        self.forecaster = forecaster
        self.explainers: Dict[str, shap.TreeExplainer] = {}
        self.background_samples: Dict[str, pd.DataFrame] = {}
        self.global_importance_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.initialize_explainers()

    def initialize_explainers(self):
        for target, model in self.forecaster.models.items():
            bg_path = os.path.join(self.forecaster.models_dir, target.lower(), "background_sample.joblib")
            if os.path.exists(bg_path):
                bg_sample = joblib.load(bg_path)
                self.background_samples[target] = bg_sample
                # For tree models, passing background data allows computing expectation-based SHAP values
                self.explainers[target] = shap.TreeExplainer(model, data=bg_sample)
            else:
                self.explainers[target] = shap.TreeExplainer(model)
            logger.info(f"Initialized TreeExplainer for target: {target}")

    def explain_prediction(
        self,
        historical_df: pd.DataFrame,
        product_id: str,
        target_metric: str,
        date: str
    ) -> Dict[str, Any]:
        """
        Explains a specific product prediction at a specific date.
        If the date is in the future, it forecasts the target first.
        """
        target_metric_cap = target_metric.title()
        if target_metric_cap not in self.forecaster.models:
            # Try original formatting
            matched = [t for t in self.forecaster.models if t.lower() == target_metric.lower()]
            if matched:
                target_metric_cap = matched[0]
            else:
                raise ValueError(f"Target metric {target_metric} not supported.")
                
        model = self.forecaster.models[target_metric_cap]
        explainer = self.explainers[target_metric_cap]
        preprocessor = self.forecaster.preprocessor
        
        # Parse date
        target_date = pd.to_datetime(date)
        max_hist_date = pd.to_datetime(historical_df["date"]).max()
        
        # Check if historical or future
        if target_date <= max_hist_date:
            # Historical date explanation
            prod_df = historical_df[historical_df["product_id"] == product_id].copy()
            if len(prod_df) == 0:
                raise ValueError(f"Product {product_id} not found in historical data.")
            prod_df["date"] = pd.to_datetime(prod_df["date"])
            
            # Run transformation to get features
            transformed = preprocessor.transform(prod_df)
            row_idx = transformed[transformed["date"] == target_date]
            if len(row_idx) == 0:
                raise ValueError(f"No data available for product {product_id} on date {target_date}.")
            
            X_explain = row_idx[preprocessor.feature_cols]
            pred_value = row_idx[target_metric_cap].values[0]
        else:
            # Future date explanation: run forecast first
            horizon_days = (target_date - max_hist_date).days
            forecast_df = self.forecaster.forecast(historical_df, product_id, horizon_days)
            forecast_df["date"] = pd.to_datetime(forecast_df["date"])
            
            # Predict has already run within forecast, let's grab the features
            # Combine history and forecast to compute features
            history_subset = historical_df[historical_df["product_id"] == product_id].tail(40).copy()
            history_subset["date"] = pd.to_datetime(history_subset["date"])
            forecast_subset = forecast_df.copy()
            combined = pd.concat([history_subset, forecast_subset], ignore_index=True)
            
            transformed = preprocessor.transform(combined)
            row_idx = transformed[transformed["date"] == target_date]
            if len(row_idx) == 0:
                raise ValueError(f"Failed to generate forecast features for product {product_id} on date {target_date}.")
                
            X_explain = row_idx[preprocessor.feature_cols]
            pred_value = row_idx[target_metric_cap].values[0]
            
        # Compute SHAP values
        shap_output = explainer(X_explain, check_additivity=False)
        
        # SHAP returns an object. For a single row, grab values, base_values, and data
        # Handle shape differences between SHAP versions
        shap_vals = shap_output.values[0]
        base_value = shap_output.base_values[0]
        
        # If model is multi-output (though our LightGBMs are single target regressors, sometimes SHAP wraps outputs)
        if isinstance(base_value, np.ndarray) and len(base_value) > 1:
            base_value = base_value[0]
        if len(shap_vals.shape) > 1:
            shap_vals = shap_vals[:, 0]
            
        # Create list of feature contributions
        contributions = []
        positive_drivers = []
        negative_drivers = []
        
        for feat_name, shap_val, actual_val in zip(preprocessor.feature_cols, shap_vals, X_explain.iloc[0]):
            if abs(shap_val) > 1e-4:  # Filter out trivial contributions
                item = {
                    "feature": feat_name,
                    "clean_name": get_clean_feature_name(feat_name),
                    "actual_value": float(actual_val),
                    "shap_value": float(shap_val)
                }
                contributions.append(item)
                if shap_val > 0:
                    positive_drivers.append(item)
                else:
                    negative_drivers.append(item)
                    
        # Sort drivers
        contributions = sorted(contributions, key=lambda x: abs(x["shap_value"]), reverse=True)
        positive_drivers = sorted(positive_drivers, key=lambda x: x["shap_value"], reverse=True)
        negative_drivers = sorted(negative_drivers, key=lambda x: x["shap_value"], reverse=False) # Most negative first
        
        # Generate clean natural language explanation summary
        diff = pred_value - base_value
        direction = "higher" if diff >= 0 else "lower"
        
        explanation_summary = (
            f"The predicted {target_metric.replace('_', ' ')} of {pred_value:,.4f} is {direction} than the "
            f"baseline of {base_value:,.4f} by {abs(diff):,.4f}. "
        )
        
        pos_terms = [f"{d['clean_name']} (+{d['shap_value']:.4f})" for d in positive_drivers[:2]]
        neg_terms = [f"{d['clean_name']} ({d['shap_value']:.4f})" for d in negative_drivers[:2]]
        
        if pos_terms:
            explanation_summary += f"The key positive factors driving this increase were: {', '.join(pos_terms)}. "
        if neg_terms:
            explanation_summary += f"The primary dampening factors were: {', '.join(neg_terms)}."
            
        global_importance = self.get_global_importance(target_metric)
        
        return {
            "target_metric": target_metric,
            "product_id": product_id,
            "date": date,
            "prediction_value": float(pred_value),
            "base_value": float(base_value),
            "explanation_summary": explanation_summary.strip(),
            "positive_drivers": positive_drivers[:10],
            "negative_drivers": negative_drivers[:10],
            "global_importance": global_importance
        }

    def get_global_importance(self, target_metric: str) -> List[Dict[str, Any]]:
        """
        Computes global feature importance for a target metric based on the background sample.
        Calculated as the mean absolute SHAP value for each feature.
        """
        target_metric_cap = target_metric.title()
        if target_metric_cap not in self.explainers:
            matched = [t for t in self.explainers.keys() if t.lower() == target_metric.lower()]
            if matched:
                target_metric_cap = matched[0]
            else:
                raise ValueError(f"Target metric {target_metric} not supported.")
                
        if target_metric_cap in self.global_importance_cache:
            return self.global_importance_cache[target_metric_cap]
            
        explainer = self.explainers[target_metric_cap]
        bg_sample = self.background_samples.get(target_metric_cap)
        
        if bg_sample is None:
            # Fallback to model feature importances if bg_sample is not available
            model = self.forecaster.models[target_metric_cap]
            feat_imp = model.feature_importance(importance_type="gain")
            feature_names = self.forecaster.preprocessor.feature_cols
            
            global_imp = []
            for name, imp in zip(feature_names, feat_imp):
                global_imp.append({
                    "feature": name,
                    "clean_name": get_clean_feature_name(name),
                    "importance_value": float(imp)
                })
            total_imp = sum(x["importance_value"] for x in global_imp) or 1.0
            for x in global_imp:
                x["importance_value"] = round(x["importance_value"] / total_imp * 100, 2)
            return sorted(global_imp, key=lambda x: x["importance_value"], reverse=True)[:15]
            
        # Compute SHAP values for the background sample
        shap_values = explainer.shap_values(bg_sample, check_additivity=False)
        
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        elif len(shap_values.shape) > 2:
            shap_values = shap_values[:, :, 0]
            
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        feature_names = self.forecaster.preprocessor.feature_cols
        
        global_imp = []
        for name, imp_val in zip(feature_names, mean_abs_shap):
            global_imp.append({
                "feature": name,
                "clean_name": get_clean_feature_name(name),
                "importance_value": float(imp_val)
            })
            
        global_imp = sorted(global_imp, key=lambda x: x["importance_value"], reverse=True)
        self.global_importance_cache[target_metric_cap] = global_imp[:15]
        return self.global_importance_cache[target_metric_cap]
