from types import SimpleNamespace
from unittest.mock import patch

from src.core.new_anomaly.engine import AnomalyDetectionEngineV2


def _result(product_id: str, deviations: list[float]):
    return SimpleNamespace(
        product_id=product_id,
        kpi="revenue",
        anomalies=[
            SimpleNamespace(
                status="Risk",
                deviation_pct=deviation,
                
            )
            for deviation in deviations
        ],
    )


def test_anomaly_rank_uses_canonical_detector_and_sorts_by_risk() -> None:
    engine = AnomalyDetectionEngineV2(data_path="temporal_dataset.csv")
    engine._catalog = ["P001", "P002", "P003"]

    def fake_detect(data_path, product_id, kpi, date_range, target_date=None):
        assert data_path == "temporal_dataset.csv"
        assert kpi == "revenue"
        assert date_range == "30 Days"
        assert target_date == "2025-12-31"
        scores = {
            "P001": [-10.0],
            "P002": [-25.0, -5.0],
            "P003": [],
        }
        return _result(product_id, scores[product_id])

    with patch("src.core.new_anomaly.engine.detect_anomalies", side_effect=fake_detect) as detect:
        result = engine.get_top_products(date="2025-12-31", kpi="revenue")

    assert detect.call_count == 3
    ranked = result["top_10_critical_products"]
    assert [item["product_id"] for item in ranked] == ["P002", "P001"]
    assert ranked[0]["severity_score"] == 30.0