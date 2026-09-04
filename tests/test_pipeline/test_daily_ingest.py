"""
Tests for the daily ingest pipeline's two-step upsert.

Uses an in-memory SQLite engine with PRAGMA foreign_keys=ON so FK
constraints are actually enforced — without this, SQLite silently
ignores FK violations and the tests prove nothing about the two-step
product-registration logic being load-bearing.
"""

import os
import sys
import datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, text

# Ensure project root is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Must set NEON_URL before importing models (database.py reads it at import time)
os.environ.setdefault("NEON_URL", "sqlite:///:memory:")

from src.core.database import Base
from src.core.models import Product, ProductMetricsDaily
from src.pipeline.daily_ingest import upsert_daily_metrics


def _enable_sqlite_fk(dbapi_connection, connection_record):
    """Enable FK enforcement on every SQLite connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def test_engine():
    """In-memory SQLite engine with FK enforcement and fresh schema per test."""
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", _enable_sqlite_fk)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _make_sample_df(
    product_id="P001",
    category="Skincare",
    date=None,
    revenue=31500.0,
):
    """Build a minimal single-row DataFrame with all required columns."""
    return pd.DataFrame([{
        "product_id": product_id,
        "date": date or datetime.date(2025, 6, 15),
        "category": category,
        "subcategory": "Moisturizer",
        "brand": "BrandX",
        "avg_ltv": 1200.0,
        "dominant_age_group": "25-34",
        "inventory_available": 500,
        "avg_selling_price": 700.0,
        "discount_pct": 15.0,
        "shipping_fee": 69.0,
        "sales_channel_mix": None,
        "campaign_mix": None,
        "acquisition_mix": None,
        "amazon_sales_pct": 30.0,
        "website_sales_pct": 40.0,
        "nykaa_sales_pct": 20.0,
        "mobile_app_sales_pct": 10.0,
        "search_campaign_pct": 25.0,
        "social_campaign_pct": 35.0,
        "email_campaign_pct": 20.0,
        "affiliate_campaign_pct": 20.0,
        "google_source_pct": 30.0,
        "instagram_source_pct": 25.0,
        "facebook_source_pct": 15.0,
        "email_source_pct": 10.0,
        "organic_source_pct": 10.0,
        "referral_source_pct": 10.0,
        "marketing_spend": 5000.0,
        "traffic": 3000.0,
        "active_users": 1500.0,
        "current_ctr": 0.05,
        "current_roas": 3.2,
        "orders": 45.0,
        "revenue": revenue,
        "profit": 12000.0,
        "conversion_rate": 0.05,
        "retention_rate": 0.40,
    }])


class TestUpsertDailyMetrics:
    def test_upsert_inserts_new_row(self, test_engine):
        df = _make_sample_df()
        upsert_daily_metrics(df, test_engine)

        with test_engine.connect() as conn:
            row_count = conn.execute(text("SELECT count(*) FROM product_metrics_daily")).scalar()
            assert row_count == 1

            product_count = conn.execute(text("SELECT count(*) FROM products")).scalar()
            assert product_count == 1

            revenue = conn.execute(
                text("SELECT revenue FROM product_metrics_daily WHERE product_id = 'P001'")
            ).scalar()
            assert revenue == 31500.0

    def test_upsert_corrects_existing_row(self, test_engine):
        df = _make_sample_df(revenue=31500.0)
        upsert_daily_metrics(df, test_engine)

        # Second upsert with corrected revenue
        corrected = _make_sample_df(revenue=32000.0)
        upsert_daily_metrics(corrected, test_engine)

        with test_engine.connect() as conn:
            # Row count unchanged — update, not insert
            row_count = conn.execute(text("SELECT count(*) FROM product_metrics_daily")).scalar()
            assert row_count == 1

            # Revenue reflects the correction
            revenue = conn.execute(
                text("SELECT revenue FROM product_metrics_daily WHERE product_id = 'P001'")
            ).scalar()
            assert revenue == 32000.0

    def test_upsert_registers_new_product_without_fk_violation(self, test_engine):
        """
        A metrics row for a never-seen product_id should NOT cause an FK
        violation, because Step 1 of the upsert registers the product first.

        With PRAGMA foreign_keys=ON, this test would genuinely fail if the
        product-registration step were removed — SQLite would reject the
        metrics insert due to the FK constraint.
        """
        df = _make_sample_df(product_id="P_NEW", category="Haircare")
        # Should not raise
        upsert_daily_metrics(df, test_engine)

        with test_engine.connect() as conn:
            product = conn.execute(
                text("SELECT product_id, category FROM products WHERE product_id = 'P_NEW'")
            ).mappings().one()
            assert product["product_id"] == "P_NEW"
            assert product["category"] == "Haircare"

            metric_count = conn.execute(
                text("SELECT count(*) FROM product_metrics_daily WHERE product_id = 'P_NEW'")
            ).scalar()
            assert metric_count == 1

    def test_fk_violation_without_product_registration(self, test_engine):
        """
        Prove that the FK constraint is actually enforced: inserting a
        metrics row for a product_id that doesn't exist in `products`
        must raise an IntegrityError.  This validates that the test
        engine's PRAGMA foreign_keys=ON is working.
        """
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.dialects.sqlite import insert

        with pytest.raises(IntegrityError):
            with test_engine.begin() as conn:
                conn.execute(
                    insert(ProductMetricsDaily.__table__).values({
                        "product_id": "P_GHOST",
                        "date": datetime.date(2025, 1, 1),
                        "revenue": 100.0,
                    })
                )
