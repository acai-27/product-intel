import json
import math
import datetime
from typing import Any
from sqlalchemy import Column, Integer, Float, String, Date, Text, JSON
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

class Snapshot(Base):
    __tablename__ = 'snapshots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, unique=True, nullable=False, index=True)
    total_revenue = Column(Float, nullable=False)
    total_profit = Column(Float, nullable=False)
    total_orders = Column(Integer, nullable=False)
    mean_conversion_rate = Column(Float, nullable=False)
    mean_retention_rate = Column(Float, nullable=False)
    total_marketing_spend = Column(Float, nullable=False)
    total_inventory = Column(Integer, nullable=False)
    avg_discount_pct = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    top_products = Column(SafeJSON)
    worst_products = Column(SafeJSON)
    largest_growth = Column(SafeJSON)
    largest_decline = Column(SafeJSON)
    inventory_alerts = Column(SafeJSON)
    channel_mix = Column(SafeJSON)
    campaign_mix = Column(SafeJSON)
    traffic_mix = Column(SafeJSON)
    summary = Column(Text)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(50), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    kpis_affected = Column(String(200))
    reason = Column(Text)
    business_impact = Column(Text)
    confidence = Column(Float, default=1.0)

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(100), nullable=False, index=True)
    query_context = Column(Text)
    synthesized_rules = Column(SafeJSON)
    confidence_score = Column(Float)
    created_at = Column(Date, default=datetime.date.today)
    driver = Column(String(100), index=True)
    segment = Column(String(100), index=True)
    season = Column(String(50), index=True)
    outcome_score = Column(Float)
    confidence = Column(Float)

class ProductPerformance(Base):
    __tablename__ = 'product_performance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    product_id = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
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


