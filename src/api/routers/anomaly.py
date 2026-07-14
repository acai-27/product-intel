from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any

from src.api.schemas.anomaly import (
    AnomalyRequest, GlobalAnomalyRequest,
    AnomalyResponse, GlobalRankingResponse,
    AnomalyScanRequest, AnomalyScanResponse
)

from src.api.dependencies import get_anomaly_engine
from src.core.new_anomaly.engine import AnomalyDetectionEngineV2

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection Engine"])

@router.post("/detect", response_model=AnomalyResponse)
async def detect_anomaly_endpoint(
    payload: AnomalyRequest,
    engine: AnomalyDetectionEngineV2 = Depends(get_anomaly_engine)
):
    try:
        res = engine.run_detection(
            product_id=payload.product_id,
            target_date=payload.target_date,
            kpi=payload.kpi
        )
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection error: {str(e)}")

@router.post("/scan", response_model=AnomalyScanResponse)
async def scan_anomalies_endpoint(
    payload: AnomalyScanRequest,
    engine: AnomalyDetectionEngineV2 = Depends(get_anomaly_engine)
):
    try:
        res = engine.scan_anomalies(
            product_id=payload.product_id,
            lookback_days=payload.lookback_days,
            kpi=payload.kpi
        )
        if "error" in res:
            raise HTTPException(status_code=400, detail=res["error"])
        return res
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly scanning error: {str(e)}")

@router.post("/top-products", response_model=GlobalRankingResponse)
async def get_top_products_endpoint(
    payload: GlobalAnomalyRequest,
    engine: AnomalyDetectionEngineV2 = Depends(get_anomaly_engine)
):
    try:
        res = engine.get_top_products(
            date=payload.target_date,
            kpi=payload.kpi
        )
        return GlobalRankingResponse(
            target_date=payload.target_date,
            kpi=payload.kpi,
            top_10_critical_products=res["top_10_critical_products"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global ranking error: {str(e)}")

@router.get("/top-products", response_model=GlobalRankingResponse)
async def get_top_products_get_endpoint(
    target_date: str = Query(..., description="Target date for global anomaly ranking"),
    kpi: str = Query("revenue", description="KPI metric"),
    engine: AnomalyDetectionEngineV2 = Depends(get_anomaly_engine)
):
    try:
        res = engine.get_top_products(
            date=target_date,
            kpi=kpi
        )
        return GlobalRankingResponse(
            target_date=target_date,
            kpi=kpi,
            top_10_critical_products=res["top_10_critical_products"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global ranking error: {str(e)}")
