import pytest
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set dummy env vars for tests so database checks don't crash
os.environ["NEON_URL"] = "sqlite:///data/test.db"

@pytest.fixture(scope="module")
def client():
    from src.api.main import app

    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def test_dataset():
    # Load actual temporal dataset to run integration checks
    csv_path = "temporal_dataset.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    
    # Fallback to dummy data if not found
    dates = pd.date_range(start="2025-01-01", periods=100)
    rows = []
    for d in dates:
        for p in ["P001", "P002"]:
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "product_id": p,
                "category": "Skincare",
                "avg_selling_price": 700.0,
                "discount_pct": 15,
                "shipping_fee": 69,
                "marketing_spend": 5000,
                "traffic": 3000,
                "orders": 45,
                "revenue": 31500.0,
                "profit": 12000.0,
                "conversion_rate": 0.05,
                "retention_rate": 0.40
            })
    return pd.DataFrame(rows)
