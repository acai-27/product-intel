import pandas as pd
from typing import List, Optional
from .models import AnomalyPoint, AnomalySummary, AnomalyResult
from .data_loader import load_product_data
from .feature_builder import build_features
from .detector import run_isolation_forest
from .threshold_calibrator import calibrate_and_classify
from .utils import get_start_date, normalize_scores

def detect_anomalies(
    file_path: str,
    product_id: str,
    kpi: str,
    date_range: str,
    target_date: Optional[str] = None
) -> AnomalyResult:
    """
    Main orchestration layer for generating anomaly detection results.
    Trains on full product history, classifies anomalies, and filters output to requested range.
    """
    # Load all data for the product
    df_raw = load_product_data(file_path, product_id, kpi)
    
    if df_raw.empty:
        raise ValueError(f"No data found for product_id: {product_id}")
        
    if target_date:
        max_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
        df_raw = df_raw[df_raw["date"] <= pd.to_datetime(target_date)]
    else:
        max_date = df_raw["date"].max().strftime("%Y-%m-%d")
        
    start_date = get_start_date(max_date, date_range)
    
    # Build temporal features on full history
    feature_df = build_features(df_raw, kpi)
    
    # Columns used for modeling
    feature_cols = [
        kpi,
        f"{kpi}_lag_1",
        f"{kpi}_lag_7",
        f"{kpi}_roll_mean_7",
        f"{kpi}_roll_std_7"
    ]
    
    # Train Isolation Forest & generate raw scores on full history
    raw_scores = run_isolation_forest(feature_df, feature_cols)
    
    # Normalize scores (0-100)
    normalized_scores = normalize_scores(raw_scores)
    
    # Classify anomalies
    is_anomaly_series, threshold_percentile, threshold_value = calibrate_and_classify(normalized_scores, kpi)
    
    # Build complete points with business classification
    all_points: List[AnomalyPoint] = []
    
    for idx, row in feature_df.iterrows():
        current_val = float(row[kpi])
        roll_mean = float(row[f"{kpi}_roll_mean_7"])
        is_anomaly = bool(is_anomaly_series.iloc[idx])
        
        anomaly_type = None
        status = "Normal"
        deviation_pct = None
        
        if roll_mean != 0:
            deviation_pct = ((current_val - roll_mean) / roll_mean) * 100
            
            if is_anomaly:
                if deviation_pct > 0:
                    anomaly_type = "positive_spike"
                    status = "Opportunity"
                elif deviation_pct < 0:
                    anomaly_type = "negative_drop"
                    status = "Attention Required"
        else:
            # Handle edge case where roll_mean is 0
            if is_anomaly and current_val > 0:
                deviation_pct = 100.0 # arbitrary large number
                anomaly_type = "positive_spike"
                status = "Opportunity"
        
        point = AnomalyPoint(
            date=row["date"].strftime("%Y-%m-%d"),
            value=current_val,
            score=round(float(normalized_scores.iloc[idx]), 2),
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
            deviation_pct=round(deviation_pct, 2) if deviation_pct is not None else None,
            status=status
        )
        all_points.append(point)
        

        
    # Filter down to the requested date range
    filtered_points = [p for p in all_points if start_date <= p.date <= max_date]
    anomalies = [p for p in filtered_points if p.is_anomaly]
    
    positive_count = sum(1 for p in anomalies if p.anomaly_type == "positive_spike")
    negative_count = sum(1 for p in anomalies if p.anomaly_type == "negative_drop")
    
    summary = AnomalySummary(
        total_points=len(filtered_points),
        anomaly_count=len(anomalies),
        positive_anomalies=positive_count,
        negative_anomalies=negative_count,
        threshold_method="percentile",
        threshold_percentile=threshold_percentile,
        threshold_value=round(threshold_value, 2)
    )
    
    return AnomalyResult(
        product_id=product_id,
        kpi=kpi,
        summary=summary,
        graph_data=filtered_points,
        anomalies=anomalies
    )
