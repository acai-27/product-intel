import os
import pandas as pd
from functools import lru_cache
from typing import Generator, Optional, Any
from sqlalchemy import Engine

from src.core.forecaster import ProductForecaster
from src.core.explainer import PredictionExplainer
from src.core.new_anomaly.engine import AnomalyDetectionEngineV2
from src.core.simulator import ScenarioSimulator
from src.utils.logger import setup_logger

logger = setup_logger("dependencies")


def _safe_date(value: Any) -> Optional[pd.Timestamp]:
    """Parse absolute or relative dates without raising. Returns None if invalid."""
    try:
        from src.core.nl2sql.dates import safe_parse_date
        return safe_parse_date(value)
    except Exception:
        try:
            return pd.to_datetime(value)
        except Exception:
            return None


# In-memory global cache for files that should load only once
class AppState:
    """Singleton holding initialized core engines to avoid reloading models/datasets."""
    db_engine: Optional[Engine] = None
    df_historical: Optional[pd.DataFrame] = None
    
    # Core Engines
    forecaster: Optional[ProductForecaster] = None
    explainer: Optional[PredictionExplainer] = None
    anomaly_engine: Optional[AnomalyDetectionEngineV2] = None
    simulator: Optional[ScenarioSimulator] = None
    planner_agent: Optional[Any] = None
    llm_client: Optional[Any] = None
    nl2sql_engine: Optional[Any] = None

def get_historical_df_from_csv(
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    csv_path: str = "temporal_dataset.csv"
) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        logger.error(f"CSV path {csv_path} does not exist.")
        return pd.DataFrame()
        
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    
    if product_id:
        df = df[df["product_id"] == product_id]
    if category:
        df = df[df["category"] == category]
    if start_date:
        parsed_start = _safe_date(start_date)
        if parsed_start is not None:
            df = df[df["date"] >= parsed_start]
    if end_date:
        parsed_end = _safe_date(end_date)
        if parsed_end is not None:
            df = df[df["date"] <= parsed_end]
        
    df = df.sort_values(by=["product_id", "date"]).reset_index(drop=True)
    return df

def get_historical_df_from_db(
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None
) -> pd.DataFrame:
    db_url = os.getenv("NEON_URL") or os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("sqlite"):
        try:
            from src.core.database import get_neon_connection

            query = "SELECT * FROM product_performance WHERE 1=1"
            params = []

            if product_id:
                query += " AND product_id = %s"
                params.append(product_id)

            if category:
                query += " AND category = %s"
                params.append(category)

            if start_date:
                parsed_start = _safe_date(start_date)
                if parsed_start is not None:
                    query += " AND date >= %s"
                    params.append(parsed_start.strftime("%Y-%m-%d"))

            if end_date:
                parsed_end = _safe_date(end_date)
                if parsed_end is not None:
                    query += " AND date <= %s"
                    params.append(parsed_end.strftime("%Y-%m-%d"))

            logger.info(f"Executing dynamic query on Neon DB: {query} with params: {params}")

            conn = get_neon_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    rows = cur.fetchall()

                df = pd.DataFrame(rows, columns=columns)

                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"])
                    if "id" in df.columns:
                        df = df.drop(columns=["id"])
                    df = df.sort_values(by=["product_id", "date"]).reset_index(drop=True)
                    return df
                else:
                    logger.warning("Database query returned empty DataFrame. Falling back to CSV...")
                    return get_historical_df_from_csv(start_date, end_date, product_id, category)
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Database dynamic query failed: {e}. Falling back to CSV...")
            return get_historical_df_from_csv(start_date, end_date, product_id, category)
    else:
        # Try SQLite first, otherwise CSV
        try:
            from src.core.database import engine
            from sqlalchemy import text
            query = "SELECT * FROM product_performance WHERE 1=1"
            params = {}
            if product_id:
                query += " AND product_id = :product_id"
                params["product_id"] = product_id
            if category:
                query += " AND category = :category"
                params["category"] = category
            if start_date:
                parsed_start = _safe_date(start_date)
                if parsed_start is not None:
                    query += " AND date >= :start_date"
                    params["start_date"] = parsed_start.strftime("%Y-%m-%d")
            if end_date:
                parsed_end = _safe_date(end_date)
                if parsed_end is not None:
                    query += " AND date <= :end_date"
                    params["end_date"] = parsed_end.strftime("%Y-%m-%d")
            
            df = pd.read_sql(text(query), con=engine, params=params)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                if "id" in df.columns:
                    df = df.drop(columns=["id"])
                df = df.sort_values(by=["product_id", "date"]).reset_index(drop=True)
                return df
            else:
                logger.info("SQLite query returned empty DataFrame. Using CSV...")
                return get_historical_df_from_csv(start_date, end_date, product_id, category)
        except Exception as e:
            logger.info(f"SQLite/DB query failed or SQLite not initialized: {e}. Using CSV...")
            return get_historical_df_from_csv(start_date, end_date, product_id, category)

def get_max_date_from_db() -> pd.Timestamp:
    db_url = os.getenv("NEON_URL") or os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("sqlite"):
        try:
            from src.core.database import get_neon_connection
            conn = get_neon_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT MAX(date) FROM product_performance")
                    res = cur.fetchone()
                if res and res[0] is not None:
                    return pd.to_datetime(res[0])
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to get max date from db: {e}")
    try:
        from src.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            res = conn.execute(text("SELECT MAX(date) FROM product_performance")).scalar()
            if res:
                return pd.to_datetime(res)
    except Exception:
        pass
    try:
        df = pd.read_csv("temporal_dataset.csv", usecols=["date"])
        return pd.to_datetime(df["date"].max())
    except Exception:
        return pd.Timestamp.now()

def load_app_state(models_dir: str = "models", preprocessor_path: str = "models/preprocessor.joblib", csv_path: str = "temporal_dataset.csv"):
    # Startup preloading of the entire dataset is disabled to prevent latency.
    AppState.df_historical = None

    if AppState.forecaster is None:
        logger.info(f"Loading Forecaster from {models_dir}...")
        AppState.forecaster = ProductForecaster(models_dir, preprocessor_path)
        
    if AppState.explainer is None:
        logger.info("Loading SHAP Explainer...")
        AppState.explainer = PredictionExplainer(AppState.forecaster)
        
    if AppState.simulator is None:
        logger.info("Initializing Scenario Simulator...")
        AppState.simulator = ScenarioSimulator(AppState.forecaster)
        
    if AppState.planner_agent is None:
        logger.info("Initializing LLM Planner Agent...")
        from src.core.agent.planner import LLMPlannerAgent
        AppState.planner_agent = LLMPlannerAgent(
            forecaster=AppState.forecaster,
            explainer=AppState.explainer,
            simulator=AppState.simulator,
            df_historical=AppState.df_historical
        )

    if AppState.anomaly_engine is None:
        logger.info("Initializing Anomaly Detection Engine...")
        AppState.anomaly_engine = AnomalyDetectionEngineV2(
            data_path="temporal_dataset.csv"
        )

    # ── LangGraph Pipeline ───────────────────────────────────────────
    if AppState.llm_client is None:
        logger.info("Initializing LLM Client...")
        from src.core.llm import LLMClient
        AppState.llm_client = LLMClient()

    if AppState.nl2sql_engine is None:
        logger.info("Initializing NL2SQL Engine...")
        from src.core.database import engine as db_engine
        from src.core.nl2sql import NL2SQLEngine
        AppState.nl2sql_engine = NL2SQLEngine(
            llm_client=AppState.llm_client,
            db_engine=db_engine,
        )

    try:
        from src.core.agent.graph import init_graph, _compiled_graph
        if _compiled_graph is None:
            logger.info("Compiling LangGraph agent pipeline...")
            init_graph(
                llm_client=AppState.llm_client,
                engines={
                    "forecaster": AppState.forecaster,
                    "explainer": AppState.explainer,
                    "simulator": AppState.simulator,
                    "anomaly_engine": AppState.anomaly_engine,
                    "nl2sql_engine": AppState.nl2sql_engine,
                    "llm_client": AppState.llm_client,
                },
            )
    except Exception as e:
        logger.warning(f"LangGraph initialization failed (legacy mode will be used): {e}")

def get_historical_data() -> pd.DataFrame:
    # Query database dynamically on demand if called by legacy functions or tests
    return get_historical_df_from_db()

def get_forecaster() -> ProductForecaster:
    if AppState.forecaster is None:
        load_app_state()
    return AppState.forecaster

def get_explainer() -> PredictionExplainer:
    if AppState.explainer is None:
        load_app_state()
    return AppState.explainer

def get_simulator() -> ScenarioSimulator:
    if AppState.simulator is None:
        load_app_state()
    return AppState.simulator

def get_planner_agent():
    if AppState.planner_agent is None:
        load_app_state()
    return AppState.planner_agent

def get_anomaly_engine():
    if AppState.anomaly_engine is None:
        load_app_state()
    return AppState.anomaly_engine
