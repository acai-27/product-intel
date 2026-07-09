import pandas as pd
from sklearn.ensemble import IsolationForest

def run_isolation_forest(features_df: pd.DataFrame, feature_cols: list) -> pd.Series:
    """
    Trains an Isolation Forest on the provided feature columns and generates raw anomaly scores.
    """
    # Extract only the features for modeling
    X = features_df[feature_cols].copy()
    
    # Initialize Isolation Forest
    model = IsolationForest(
        contamination=0.05,
        random_state=42
    )
    
    # Train the model
    model.fit(X)
    
    # Generate raw anomaly scores
    # score_samples() returns negative values where lower/more negative means more anomalous.
    raw_scores = model.score_samples(X)
    
    # Invert score direction so that:
    # Higher value = more anomalous
    # Lower value = more normal
    anomaly_scores = -raw_scores
    
    # Return scores as a pandas Series to align with original dataframe
    return pd.Series(anomaly_scores, index=features_df.index)
