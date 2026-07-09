import pandas as pd
from typing import Optional

def load_product_data(
    file_path: str,
    product_id: str,
    kpi: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    Loads historical data from the CSV dataset, filters by product_id,
    and returns a DataFrame containing 'date' and the specified 'kpi'.
    """
    # Load dataset
    df = pd.read_csv(file_path)
    
    # Filter by product_id
    product_df = df[df["product_id"] == product_id].copy()
    
    if product_df.empty:
        raise ValueError(f"No data found for product_id: {product_id}")
        
    if kpi not in product_df.columns:
        raise ValueError(f"KPI '{kpi}' not found in dataset columns.")
        
    # Ensure date is datetime
    product_df["date"] = pd.to_datetime(product_df["date"])
    
    # Apply date filters if provided
    if start_date:
        product_df = product_df[product_df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        product_df = product_df[product_df["date"] <= pd.to_datetime(end_date)]
        
    # Sort chronologically
    product_df = product_df.sort_values("date").reset_index(drop=True)
    
    # Select only required columns
    result_df = product_df[["date", kpi]].copy()
    
    # Ensure there's data left
    if result_df.empty:
        raise ValueError("No data left after applying date filters.")
        
    return result_df
