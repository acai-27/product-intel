from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AnomalyPoint:
    date: str
    value: float
    score: float
    is_anomaly: bool
    anomaly_type: Optional[str]
    deviation_pct: Optional[float]
    status: str

@dataclass
class AnomalySummary:
    total_points: int
    anomaly_count: int
    positive_anomalies: int
    negative_anomalies: int
    threshold_method: str
    threshold_percentile: int
    threshold_value: float

@dataclass
class AnomalyResult:
    product_id: str
    kpi: str
    summary: AnomalySummary
    graph_data: List[AnomalyPoint]
    anomalies: List[AnomalyPoint]
