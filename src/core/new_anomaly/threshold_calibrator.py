import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

from typing import Tuple

def calibrate_and_classify(normalized_scores: pd.Series, kpi: str) -> Tuple[pd.Series, int, float]:
    """
    Applies KPI-specific percentile thresholds on normalized scores.
    Since all KPIs use the 95th percentile, we simply use 95.
    Returns a tuple containing:
      - boolean Series where True indicates an anomaly
      - the percentile used for thresholding
      - the actual threshold value
    """
    
    # User requested 95th percentile for all KPIs
    threshold_percentile = 95
    
    # Calculate the actual score threshold corresponding to the percentile
    threshold_value = float(np.percentile(normalized_scores, threshold_percentile))
    
    # Classify anomalies (score >= threshold)
    is_anomaly = normalized_scores >= threshold_value
    
    return is_anomaly, threshold_percentile, threshold_value
