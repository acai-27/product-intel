"""
Schema definitions for NL2SQL prompt injection.

Describes queryable tables and columns so the LLM can generate valid SQL.
"""

from typing import Any

# Tables the NL2SQL engine is allowed to query
ALLOWED_TABLES: frozenset[str] = frozenset({
    "product_performance",
})

TABLE_SCHEMAS: dict[str, dict[str, Any]] = {
    "product_performance": {
        "description": "Daily product KPIs and business drivers. Primary table for revenue, profit, orders, marketing, inventory.",
        "columns": {
            "date": "DATE — record date",
            "product_id": "VARCHAR — product identifier (e.g. P001)",
            "category": "VARCHAR — product category",
            "subcategory": "VARCHAR",
            "brand": "VARCHAR",
            "revenue": "FLOAT — daily revenue",
            "profit": "FLOAT — daily profit",
            "orders": "FLOAT — daily order count",
            "conversion_rate": "FLOAT",
            "retention_rate": "FLOAT",
            "marketing_spend": "FLOAT",
            "discount_pct": "FLOAT",
            "shipping_fee": "FLOAT",
            "avg_selling_price": "FLOAT",
            "inventory_available": "INTEGER",
            "traffic": "FLOAT",
            "active_users": "FLOAT",
            "current_ctr": "FLOAT",
            "current_roas": "FLOAT",
            "avg_ltv": "FLOAT",
            "dominant_age_group": "VARCHAR",
            "amazon_sales_pct": "FLOAT",
            "website_sales_pct": "FLOAT",
            "nykaa_sales_pct": "FLOAT",
            "mobile_app_sales_pct": "FLOAT",
        },
    },
}


def get_schema_prompt(dialect: str = "postgresql", date_context: str = "") -> str:
    """Format table schemas for LLM SQL generation."""
    lines = [
        f"Database dialect: {dialect}",
        "Rules: SELECT-only queries. Use only the tables and columns listed below.",
        "Do NOT query JSON columns. Always include LIMIT (max 100).",
        "CRITICAL: There is NO column named total_revenue, total_profit, or total_orders.",
        "Always aggregate raw columns: SUM(revenue) AS total_revenue, SUM(profit) AS total_profit, SUM(orders) AS total_orders.",
        "Only use column names exactly as listed below — never invent column names.",
        "For monthly ranges use: date >= 'YYYY-MM-01' AND date < first day of next month.",
    ]
    if date_context:
        lines.append(date_context)
    lines.append("")
    for table, spec in TABLE_SCHEMAS.items():
        lines.append(f"TABLE {table}: {spec['description']}")
        for col, desc in spec["columns"].items():
            lines.append(f"  - {col}: {desc}")
        lines.append("")
    return "\n".join(lines)


def get_allowed_tables() -> frozenset[str]:
    return ALLOWED_TABLES
