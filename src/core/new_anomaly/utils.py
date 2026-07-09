from datetime import datetime, timedelta
import pandas as pd

def get_start_date(end_date_str: str, date_range: str) -> str:
    """
    Returns the start date based on the end_date and selected range.
    date_range options: '30 Days', '90 Days', '180 Days', 'All Available Data'
    """
    if date_range == "All Available Data":
        return "1900-01-01" # Arbitrary old date to include everything
        
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    if date_range == "30 Days":
        days = 30
    elif date_range == "90 Days":
        days = 90
    elif date_range == "180 Days":
        days = 180
    else:
        raise ValueError(f"Unknown date range: {date_range}")
        
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y-%m-%d")

def normalize_scores(anomaly_scores: pd.Series) -> pd.Series:
    """
    Normalizes anomaly scores to a 0-100 range.
    0 = most normal, 100 = most anomalous
    
    The input anomaly_scores are already inverted so that higher values
    indicate more anomalous behavior.
    """
    min_score = anomaly_scores.min()
    max_score = anomaly_scores.max()
    
    if max_score == min_score:
        return pd.Series(0.0, index=anomaly_scores.index)
        
    normalized = ((anomaly_scores - min_score) / (max_score - min_score)) * 100
    return normalized
