import sys
import os
# Inject parent directory into path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import joblib
import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import Dict, Any

from src.pipeline.preprocessor import TimeSeriesPreprocessor
from src.utils.metrics import calculate_metrics

def train_pipeline(data_path: str, models_dir: str, preprocessor_path: str, fast_mode: bool = False) -> Dict[str, Any]:
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    print("Fitting and transforming data using TimeSeriesPreprocessor...")
    preprocessor = TimeSeriesPreprocessor()
    df_processed = preprocessor.fit_transform(df)
    
    # Save the preprocessor
    os.makedirs(os.path.dirname(preprocessor_path), exist_ok=True)
    preprocessor.save(preprocessor_path)
    print(f"Saved preprocessor to {preprocessor_path}")
    
    # Split the dataset
    train_df, val_df, test_df = preprocessor.split_data(df_processed)
    
    if fast_mode:
        print("Fast mode enabled. Training on a subset of 1000 rows with 5 estimators.")
        train_df = train_df.tail(1000).copy()
        val_df = val_df.tail(200).copy()
        test_df = test_df.tail(200).copy()
        
    print(f"Split sizes - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    features = preprocessor.feature_cols
    targets = preprocessor.target_cols
    
    results_report = {}
    os.makedirs(models_dir, exist_ok=True)
    
    # 1. Train models
    for target in targets:
        print(f"\n--- Training LightGBM Model for target: {target} ---")
        
        X_train, y_train = train_df[features], train_df[target]
        X_val, y_val = val_df[features], val_df[target]
        X_test, y_test = test_df[features], test_df[target]
        
        cat_features = [c for c in features if c.endswith('_code')]
        train_data = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_features)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, categorical_feature=cat_features)
        
        params = {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "n_estimators": 5 if fast_mode else 500,
            "learning_rate": 0.1,
            "num_leaves": 15 if fast_mode else 31,
            "max_depth": 4 if fast_mode else 6,
            "min_child_samples": 10 if fast_mode else 20,
            "verbose": -1,
            "n_jobs": -1,
            "random_state": 42
        }
        
        model = lgb.train(
            params,
            train_data,
            valid_sets=[val_data],
            callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)] if not fast_mode else []
        )
        
        y_pred = model.predict(X_test)
        metrics = calculate_metrics(y_test, y_pred)
        print(f"Test performance for {target}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
            
        target_model_dir = os.path.join(models_dir, target.lower())
        os.makedirs(target_model_dir, exist_ok=True)
        model_path = os.path.join(target_model_dir, "model.joblib")
        joblib.dump(model, model_path)
        print(f"Saved {target} model to {model_path}")
        
        bg_sample = X_train.sample(n=min(100, len(X_train)), random_state=42)
        bg_path = os.path.join(target_model_dir, "background_sample.joblib")
        joblib.dump(bg_sample, bg_path)
        
        results_report[target] = {
            "metrics": metrics,
            "best_iteration": model.best_iteration if hasattr(model, 'best_iteration') else 5,
            "features_used": features
        }

    # 2. Run recursive test evaluations and calculate empirical step-by-step standard errors
    print("\n--- Calculating Step-by-Step Empirical Standard Errors on Test Split ---")
    from src.core.forecaster import ProductForecaster
    
    forecaster = ProductForecaster(models_dir=models_dir, preprocessor_path=preprocessor_path)
    
    df["date"] = pd.to_datetime(df["date"])
    # Split raw df chronologically for history and test actuals
    history_df = df[df["date"] <= pd.to_datetime("2025-09-30")].copy()
    test_actuals_df = df[df["date"] > pd.to_datetime("2025-09-30")].copy()
    
    horizon_days = 92
    unique_prods = test_actuals_df["product_id"].unique()
    
    step_errors = {target: [[] for _ in range(horizon_days)] for target in targets}
    
    # Evaluate a sample of products if in fast_mode to speed up, else evaluate all 100 products
    eval_prods = unique_prods[:5] if fast_mode else unique_prods
    
    for prod_id in eval_prods:
        try:
            forecast_df = forecaster.forecast(
                historical_df=history_df,
                product_id=prod_id,
                horizon_days=horizon_days
            )
            
            actual_prod = test_actuals_df[test_actuals_df["product_id"] == prod_id].sort_values(by="date").reset_index(drop=True)
            min_len = min(len(forecast_df), len(actual_prod))
            
            for target in targets:
                pred_vals = forecast_df[target].values[:min_len]
                actual_vals = actual_prod[target].values[:min_len]
                
                for t in range(min_len):
                    err = actual_vals[t] - pred_vals[t]
                    step_errors[target][t].append(err)
        except Exception as e:
            print(f"Error evaluating product {prod_id}: {e}")
            
    # Compute standard errors per step and save to model directories
    for target in targets:
        step_stds = []
        for t in range(horizon_days):
            errors_at_t = step_errors[target][t]
            if len(errors_at_t) > 0:
                std_val = float(np.std(errors_at_t))
            else:
                std_val = 0.0
            step_stds.append(std_val)
            
        # Suppress zeros using forward-filling
        for i in range(len(step_stds)):
            if step_stds[i] == 0.0 and i > 0:
                step_stds[i] = step_stds[i-1]
        
        # Save to models/<target>/model_metadata.json
        metadata_path = os.path.join(models_dir, target.lower(), "model_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump({
                "target_metric": target,
                "step_residuals_std": step_stds
            }, f, indent=4)
        print(f"Saved step-by-step empirical standard errors to {metadata_path}")
        
    report_path = os.path.join(models_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(results_report, f, indent=4)
    print(f"\nSaved global evaluation report to {report_path}")
    
    return results_report

if __name__ == "__main__":
    train_pipeline(
        data_path="temporal_dataset.csv",
        models_dir="models",
        preprocessor_path="models/preprocessor.joblib",
        fast_mode=False
    )
