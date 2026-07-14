import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Only allow Neon
DATABASE_URL = os.getenv("NEON_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "NEON_URL environment variable is not set. "
        "Application requires a Neon PostgreSQL database."
    )

# SQLAlchemy expects postgresql:// instead of postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

engine_kwargs = {
    "pool_pre_ping": True,      # Checks connection before using it
    "pool_recycle": 300,        # Refresh stale connections
}

# Neon requires TLS; make SSL explicit for every Postgres connection.
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"sslmode": "require"}

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_neon_connection():
    """
    Create a direct psycopg2 connection for Neon operations that need
    to bypass the SQLAlchemy session pool.
    """
    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=30,
    )
    conn.autocommit = False
    return conn

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
