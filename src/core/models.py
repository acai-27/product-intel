import json
import math
import datetime
from typing import Any
from sqlalchemy import Column, Integer, Float, String, Date, Text, JSON, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from src.core.database import Base

def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_json_value(item) for item in value]
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value
    for attr in ("item",):
        try:
            value = value.item()
            break
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    try:
        json.dumps(value)
    except Exception:
        return str(value)
    return value

class SafeJSON(JSON):
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _sanitize_json_value(value)


class Product(Base):
    __tablename__ = 'products'
    product_id = Column(String(50), primary_key=True)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    created_at = Column(Date, nullable=False, default=datetime.date.today)

    metrics = relationship("ProductMetricsDaily", back_populates="product")


class ProductMetricsDaily(Base):
    __tablename__ = 'product_metrics_daily'
    __table_args__ = (
        CheckConstraint('discount_pct BETWEEN 0 AND 100', name='ck_discount_pct_range'),
    )

    product_id = Column(
        String(50),
        ForeignKey('products.product_id', onupdate='CASCADE', ondelete='RESTRICT'),
        primary_key=True,
        nullable=False,
    )
    date = Column(Date, primary_key=True, nullable=False, index=True)
    avg_ltv = Column(Float, nullable=True)
    dominant_age_group = Column(String(50), nullable=True)
    inventory_available = Column(Integer, nullable=True)
    avg_selling_price = Column(Float, nullable=True)
    discount_pct = Column(Float, nullable=True)
    shipping_fee = Column(Float, nullable=True)
    sales_channel_mix = Column(SafeJSON, nullable=True)
    campaign_mix = Column(SafeJSON, nullable=True)
    acquisition_mix = Column(SafeJSON, nullable=True)
    amazon_sales_pct = Column(Float, nullable=True)
    website_sales_pct = Column(Float, nullable=True)
    nykaa_sales_pct = Column(Float, nullable=True)
    mobile_app_sales_pct = Column(Float, nullable=True)
    search_campaign_pct = Column(Float, nullable=True)
    social_campaign_pct = Column(Float, nullable=True)
    email_campaign_pct = Column(Float, nullable=True)
    affiliate_campaign_pct = Column(Float, nullable=True)
    google_source_pct = Column(Float, nullable=True)
    instagram_source_pct = Column(Float, nullable=True)
    facebook_source_pct = Column(Float, nullable=True)
    email_source_pct = Column(Float, nullable=True)
    organic_source_pct = Column(Float, nullable=True)
    referral_source_pct = Column(Float, nullable=True)
    marketing_spend = Column(Float, nullable=True)
    traffic = Column(Float, nullable=True)
    active_users = Column(Float, nullable=True)
    current_ctr = Column(Float, nullable=True)
    current_roas = Column(Float, nullable=True)
    orders = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    conversion_rate = Column(Float, nullable=True)
    retention_rate = Column(Float, nullable=True)

    product = relationship("Product", back_populates="metrics")
