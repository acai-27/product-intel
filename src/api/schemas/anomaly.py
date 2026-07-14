from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class AnomalyRequest(BaseModel):
    product_id: str = Field(..., example="P001")
    target_date: Optional[str] = Field(None, example="2025-06-15")
    kpi: str = Field("revenue", example="revenue")

class CategoryAnomalyRequest(BaseModel):
    category: str = Field(..., example="Skincare")
    target_date: Optional[str] = Field(None, example="2025-06-15")
    kpi: str = Field("revenue", example="revenue")

class GlobalAnomalyRequest(BaseModel):
    target_date: Optional[str] = Field(None, example="2025-06-15")
    kpi: str = Field("revenue", example="revenue")

class AnomalySummary(BaseModel):
    total_points: int
    anomaly_count: int
    positive_opportunities: int
    negative_risks: int

class AnomalyPoint(BaseModel):
    date: str
    value: float
    is_anomaly: bool
    classification: Optional[str] = None
    deviation_pct: float

class AnomalyResponse(BaseModel):
    product_id: str
    kpi: str
    summary: AnomalySummary
    graph_data: List[AnomalyPoint]
    anomalies: List[AnomalyPoint]

class CategoryAnomalyResponse(BaseModel):
    category: str
    target_date: str
    kpi: str
    anomalies: List[AnomalyResponse]

class ProductRankingDetail(BaseModel):
    product_id: str
    kpi: str
    severity_score: float
    status: str
    revenue_loss: float
    profit_loss: float
    percent_change: float

class GlobalRankingResponse(BaseModel):
    target_date: Optional[str] = None
    kpi: Optional[str] = None
    top_10_critical_products: List[ProductRankingDetail]

class AnomalyScanRequest(BaseModel):
    product_id: str = Field(..., example="P001")
    lookback_days: int = Field(14, example=14, description="Lookback window size (e.g. 14 or 30 days)")
    kpi: str = Field("revenue", example="revenue")

class AnomalyScanResponse(BaseModel):
    product_id: str
    lookback_days: int
    kpi: str
    anomalous_dates: List[Dict[str, Any]] = Field(
        ...,
        description="List of detected anomalies with their date, severity, and details"
    )
