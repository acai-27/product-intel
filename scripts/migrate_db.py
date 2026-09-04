"""
One-shot database migration: normalise product_performance into
products + product_metrics_daily, expose a view, drop dead tables.

Runs inside a single transaction — any failure (including the two hard-abort
pre-flight checks) rolls everything back automatically.

Usage:
    python -m scripts.migrate_db          # uses NEON_URL from env
    python -m scripts.migrate_db --url <DATABASE_URL>
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ── Column lists (kept in sync with the target schema DDL) ────────────────

_METRICS_COLS = [
    "product_id", "date",
    "avg_ltv", "dominant_age_group", "inventory_available",
    "avg_selling_price", "discount_pct", "shipping_fee",
    "sales_channel_mix", "campaign_mix", "acquisition_mix",
    "amazon_sales_pct", "website_sales_pct", "nykaa_sales_pct", "mobile_app_sales_pct",
    "search_campaign_pct", "social_campaign_pct", "email_campaign_pct", "affiliate_campaign_pct",
    "google_source_pct", "instagram_source_pct", "facebook_source_pct",
    "email_source_pct", "organic_source_pct", "referral_source_pct",
    "marketing_spend", "traffic", "active_users", "current_ctr", "current_roas",
    "orders", "revenue", "profit", "conversion_rate", "retention_rate",
]

_VIEW_COLS = (
    "pmd.product_id, pmd.date, p.category, p.subcategory, p.brand, "
    "pmd.avg_ltv, pmd.dominant_age_group, pmd.inventory_available, "
    "pmd.avg_selling_price, pmd.discount_pct, pmd.shipping_fee, "
    "pmd.sales_channel_mix, pmd.campaign_mix, pmd.acquisition_mix, "
    "pmd.amazon_sales_pct, pmd.website_sales_pct, pmd.nykaa_sales_pct, pmd.mobile_app_sales_pct, "
    "pmd.search_campaign_pct, pmd.social_campaign_pct, pmd.email_campaign_pct, pmd.affiliate_campaign_pct, "
    "pmd.google_source_pct, pmd.instagram_source_pct, pmd.facebook_source_pct, "
    "pmd.email_source_pct, pmd.organic_source_pct, pmd.referral_source_pct, "
    "pmd.marketing_spend, pmd.traffic, pmd.active_users, pmd.current_ctr, pmd.current_roas, "
    "pmd.orders, pmd.revenue, pmd.profit, pmd.conversion_rate, pmd.retention_rate"
)


def run_migration(engine) -> None:
    """Execute the full migration inside one transaction."""
    with engine.begin() as conn:
        # ── Step 1: pre-flight — abort if any product_id → >1 category ──
        bad_rows = conn.execute(text(
            "SELECT product_id, COUNT(DISTINCT category) AS n "
            "FROM product_performance GROUP BY product_id "
            "HAVING COUNT(DISTINCT category) > 1"
        )).fetchall()
        if bad_rows:
            raise RuntimeError(
                f"Aborting migration: {len(bad_rows)} product_id(s) have inconsistent "
                f"category values, cannot backfill products table safely: {bad_rows}"
            )
        print("[1/5] Pre-flight category check passed.")

        # ── Step 2: create + backfill products ───────────────────────────
        conn.execute(text("""
            CREATE TABLE products (
                product_id   VARCHAR(50) PRIMARY KEY,
                category     VARCHAR(100) NOT NULL,
                subcategory  VARCHAR(100),
                brand        VARCHAR(100),
                created_at   DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """))
        conn.execute(text("""
            INSERT INTO products (product_id, category, subcategory, brand)
            SELECT DISTINCT product_id, category, subcategory, brand
            FROM product_performance
        """))
        prod_count = conn.execute(text("SELECT count(*) FROM products")).scalar()
        print(f"[2/5] Created 'products' table and backfilled {prod_count} rows.")

        # ── Step 3: create + backfill product_metrics_daily ──────────────
        cols_csv = ", ".join(_METRICS_COLS)
        conn.execute(text(f"""
            CREATE TABLE product_metrics_daily (
                product_id             VARCHAR(50) NOT NULL
                                        REFERENCES products(product_id)
                                        ON UPDATE CASCADE ON DELETE RESTRICT,
                date                   DATE NOT NULL,
                avg_ltv                FLOAT,
                dominant_age_group     VARCHAR(50),
                inventory_available    INTEGER,
                avg_selling_price      FLOAT,
                discount_pct           FLOAT CHECK (discount_pct BETWEEN 0 AND 100),
                shipping_fee           FLOAT,
                sales_channel_mix      JSONB,
                campaign_mix           JSONB,
                acquisition_mix        JSONB,
                amazon_sales_pct       FLOAT,
                website_sales_pct      FLOAT,
                nykaa_sales_pct        FLOAT,
                mobile_app_sales_pct   FLOAT,
                search_campaign_pct    FLOAT,
                social_campaign_pct    FLOAT,
                email_campaign_pct     FLOAT,
                affiliate_campaign_pct FLOAT,
                google_source_pct      FLOAT,
                instagram_source_pct   FLOAT,
                facebook_source_pct    FLOAT,
                email_source_pct       FLOAT,
                organic_source_pct     FLOAT,
                referral_source_pct    FLOAT,
                marketing_spend        FLOAT,
                traffic                FLOAT,
                active_users           FLOAT,
                current_ctr            FLOAT,
                current_roas           FLOAT,
                orders                 FLOAT,
                revenue                FLOAT,
                profit                 FLOAT,
                conversion_rate        FLOAT,
                retention_rate         FLOAT,
                PRIMARY KEY (product_id, date)
            )
        """))
        conn.execute(text("CREATE INDEX ix_pmd_date ON product_metrics_daily(date)"))
        conn.execute(text(f"""
            INSERT INTO product_metrics_daily ({cols_csv})
            SELECT {cols_csv} FROM product_performance
        """))
        metrics_count = conn.execute(text("SELECT count(*) FROM product_metrics_daily")).scalar()
        print(f"[3/5] Created 'product_metrics_daily' table and backfilled {metrics_count} rows.")

        # ── Step 4: cutover — rename table, create view ──────────────────
        conn.execute(text("ALTER TABLE product_performance RENAME TO product_performance_legacy"))
        conn.execute(text(f"""
            CREATE VIEW product_performance AS
            SELECT {_VIEW_COLS}
            FROM product_metrics_daily pmd
            JOIN products p ON p.product_id = pmd.product_id
        """))
        print("[4/5] Renamed old table to 'product_performance_legacy', created view.")

        # ── Step 5: pre-flight + drop unused tables ──────────────────────
        for tbl in ("events", "snapshots", "knowledge_base"):
            count = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            if count > 0:
                raise RuntimeError(
                    f"Aborting migration: '{tbl}' has {count} row(s), expected 0. "
                    f"Investigate before dropping — this data isn't accounted for "
                    f"anywhere in this plan."
                )
        conn.execute(text("DROP TABLE events"))
        conn.execute(text("DROP TABLE snapshots"))
        conn.execute(text("DROP TABLE knowledge_base"))
        print("[5/5] Dropped empty tables: events, snapshots, knowledge_base.")

    print("\n✓ Migration completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Run the product-intel DB migration.")
    parser.add_argument("--url", default=None, help="Database URL (overrides NEON_URL env var)")
    args = parser.parse_args()

    db_url = args.url or os.getenv("NEON_URL")
    if not db_url:
        print("Error: no database URL. Set NEON_URL or pass --url.", file=sys.stderr)
        sys.exit(1)

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    run_migration(engine)


if __name__ == "__main__":
    main()
