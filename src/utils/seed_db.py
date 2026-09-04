"""
Seed the database from the temporal CSV dataset.

This script now delegates to the same upsert function used by the daily
ingest pipeline, ensuring the seed path and the recurring write path
exercise identical logic.

Usage:
    python -m src.utils.seed_db
    python -m src.utils.seed_db --csv temporal_dataset.csv
"""

import os
import json
import argparse
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.core.database import engine, Base
from src.core.models import Product, ProductMetricsDaily
from src.pipeline.daily_ingest import upsert_daily_metrics


def seed_database(csv_path: str = "temporal_dataset.csv"):
    print(f"Connecting to database to seed data...")

    # Create all tables defined in Base metadata
    print("Creating tables if they do not exist...")
    Base.metadata.create_all(bind=engine)

    # Check if data already exists to avoid duplicate seeding
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(ProductMetricsDaily).count()
        if count > 0:
            print(f"Database already contains {count} records. Skipping seeding to prevent duplication.")
            return
    except Exception as e:
        print(f"Query check failed (perhaps table doesn't exist yet): {e}")
    finally:
        session.close()

    print(f"Reading dataset from {csv_path}...")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)

    # Parse date column to actual date objects
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Deserialize JSON string columns back to dicts/objects so they map to SQL JSON types
    json_cols = ["sales_channel_mix", "campaign_mix", "acquisition_mix"]
    for col in json_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

    print(f"Upserting {len(df)} records via daily_ingest pipeline...")
    upsert_daily_metrics(df, engine)

    print("Data seeding completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the product-intel database from CSV.")
    parser.add_argument("--csv", default="temporal_dataset.csv", help="Path to the CSV file")
    args = parser.parse_args()
    seed_database(args.csv)
