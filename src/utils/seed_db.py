import os
import json
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import JSON, Date
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

from src.core.database import engine, Base
from src.core.models import ProductPerformance

def seed_database(csv_path: str = "temporal_dataset.csv"):
    db_url = os.getenv("NEON_URL") or os.getenv("DATABASE_URL")
    print(f"Connecting to database to migrate data...")
    
    # Create all tables defined in Base metadata
    print("Creating tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    
    # Check if data already exists to avoid duplicate seeding
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(ProductPerformance).count()
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
            
    print(f"Migrating {len(df)} records to database in chunks...")
    
    # Use Pandas to_sql to write to database
    df.to_sql(
        name="product_performance",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        dtype={
            "date": Date(),
            "sales_channel_mix": JSON,
            "campaign_mix": JSON,
            "acquisition_mix": JSON
        }
    )
    
    print("Data migration completed successfully!")

if __name__ == "__main__":
    seed_database()
