import pytest
from unittest.mock import patch

def test_anomaly_detect_endpoint_v2(client):
    payload = {
        "product_id": "P001",
        "target_date": "2025-06-15",
        "kpi": "revenue"
    }
    mock_data = {
        "product_id": "P001",
        "kpi": "revenue",
        "summary": {
            "total_points": 180,
            "anomaly_count": 2,
            "positive_opportunities": 1,
            "negative_risks": 1,
        },
        "graph_data": [
            {
                "date": "2025-06-15",
                "value": 15000.0,
                "is_anomaly": True,
                "classification": "Opportunity",
                "deviation_pct": 25.5
            }
        ],
        "anomalies": [
            {
                "date": "2025-06-15",
                "value": 15000.0,
                "is_anomaly": True,
                "classification": "Opportunity",
                "deviation_pct": 25.5
            }
        ]
    }
    
    with patch("src.core.new_anomaly.engine.AnomalyDetectionEngineV2.run_detection", return_value=mock_data):
        response = client.post("/api/v1/anomaly/detect", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_id"] == "P001"
        assert "summary" in data
        assert "graph_data" in data
        assert "anomalies" in data

def test_anomaly_scan_endpoint_v2(client):
    payload = {
        "product_id": "P001",
        "lookback_days": 14,
        "kpi": "revenue"
    }
    mock_data = {
        "product_id": "P001",
        "lookback_days": 14,
        "kpi": "revenue",
        "anomalous_dates": [
            {"date": "2025-06-15", "percentage_change": -15.0, "severity_score": 85.0, "status": "Risk", "details": "negative_drop"}
        ]
    }
    with patch("src.core.new_anomaly.engine.AnomalyDetectionEngineV2.scan_anomalies", return_value=mock_data):
        response = client.post("/api/v1/anomaly/scan", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["product_id"] == "P001"
        assert "anomalous_dates" in data

def test_anomaly_top_products_endpoint_v2(client):
    mock_data = {
        "top_10_critical_products": [
            {"product_id": "P001", "kpi": "revenue", "severity_score": 85.0, "status": "Critical", "revenue_loss": 0.0, "profit_loss": 0.0, "percent_change": 0.0}
        ]
    }
    with patch("src.core.new_anomaly.engine.AnomalyDetectionEngineV2.get_top_products", return_value=mock_data):
        payload = {
            "target_date": "2025-06-15",
            "kpi": "revenue"
        }
        response = client.post("/api/v1/anomaly/top-products", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["target_date"] == "2025-06-15"
        assert "top_10_critical_products" in data
        assert "top_revenue_risk" not in data
