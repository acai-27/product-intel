import logging
from typing import Dict, Any, Optional
from dataclasses import asdict
import pandas as pd

from .service import detect_anomalies

logger = logging.getLogger(__name__)

class AnomalyDetectionEngineV2:
    def __init__(self, data_path: str = "temporal_dataset.csv"):
        self.data_path = data_path
        self._catalog = None

    @property
    def catalog(self):
        if self._catalog is None:
            try:
                df = pd.read_csv(self.data_path, usecols=["product_id"])
                self._catalog = df["product_id"].unique().tolist()
            except Exception as e:
                logger.error(f"Failed to load dynamic catalog from {self.data_path}: {e}")
                self._catalog = ["P001", "P002", "P003", "P004", "P005"] # Fallback
        return self._catalog

    def run_detection(self, product_id: str, target_date: Optional[str] = None, kpi: str = "revenue") -> Dict[str, Any]:
        date_range = "180 Days"
        # detect_anomalies now supports target_date
        res = detect_anomalies(self.data_path, product_id, kpi, date_range, target_date)
        
        # Explicit mapping to AnomalyResponse schema
        return {
            "product_id": res.product_id,
            "kpi": res.kpi,
            "summary": {
                "total_points": res.summary.total_points,
                "anomaly_count": res.summary.anomaly_count,
                "positive_opportunities": res.summary.positive_anomalies,
                "negative_risks": res.summary.negative_anomalies,
            },
            "graph_data": [
                {
                    "date": pt.date,
                    "value": pt.value,
                    "is_anomaly": pt.is_anomaly,
                    "classification": pt.status,
                    "deviation_pct": pt.deviation_pct or 0.0
                } for pt in res.graph_data
            ],
            "anomalies": [
                {
                    "date": a.date,
                    "value": a.value,
                    "is_anomaly": a.is_anomaly,
                    "classification": a.status,
                    "deviation_pct": a.deviation_pct or 0.0
                } for a in res.anomalies
            ]
        }

    def scan_anomalies(self, product_id: str, lookback_days: int = 14, kpi: str = "revenue") -> Dict[str, Any]:
        date_range = "30 Days" if lookback_days <= 30 else "90 Days" if lookback_days <= 90 else "180 Days"
        res = detect_anomalies(self.data_path, product_id, kpi, date_range)
        
        # AnomalyScanResponse expects anomalous_dates
        anomalous_dates = []
        for anomaly in res.anomalies:
            anomalous_dates.append({
                "date": anomaly.date,
                "percentage_change": anomaly.deviation_pct or 0.0,
                "severity_score": anomaly.score * 100,  # Normalize or just pass the score
                "status": anomaly.status or "Risk",
                "details": anomaly.anomaly_type
            })
            
        return {
            "product_id": product_id,
            "lookback_days": lookback_days,
            "kpi": kpi,
            "anomalous_dates": anomalous_dates
        }

    def get_top_products(self, date: Optional[str] = None, kpi: str = "revenue") -> Dict[str, Any]:
        """
        Calculates Criticality Score = Σ abs(deviation_pct) for all Risk anomalies.
        Returns top_10_critical_products.
        """
        product_scores = []
        
        for pid in self.catalog:
            try:
                res = detect_anomalies(self.data_path, pid, kpi, "30 Days", date)
                
                # Calculate criticality score
                criticality = 0.0
                risk_count = 0
                for anomaly in res.anomalies:
                    if anomaly.status in {"Risk", "Attention Required"}:
                        criticality += abs(anomaly.deviation_pct or 0.0)
                        risk_count += 1
                        
                if risk_count > 0:
                    product_scores.append({
                        "product_id": pid,
                        "kpi": kpi,
                        "severity_score": criticality, # raw criticality, do not cap
                        "status": "Critical" if criticality > 50 else "High",
                        "revenue_loss": 0.0,
                        "profit_loss": 0.0,
                        "percent_change": 0.0
                    })
            except Exception as e:
                logger.warning(f"Ranking anomaly detection failed for product {pid}: {str(e)}")
                continue
                
        # Sort descending by severity score
        sorted_products = sorted(product_scores, key=lambda x: x["severity_score"], reverse=True)
        
        return {
            "top_10_critical_products": sorted_products[:10]
        }
