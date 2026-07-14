import apiClient from '../api/client';
import { PredictionResponse, TrendData } from '../types';

export interface TrendPayload {
  start_date: string | null;
  end_date: string | null;
  product_id: string | null;
  category: string | null;
  metric: string;
  granularity: string;
}

interface ForecastPoint {
  date: string;
  value: number;
  confidence_lower: number;
  confidence_upper: number;
}

interface ForecastResponse {
  target_metric: string;
  product_id: string;
  horizon_days: number;
  forecast: ForecastPoint[];
  aggregated_sum: number;
  aggregated_mean: number;
}

const calculateGrowth = (history: { date: string; value: number }[]): number => {
  if (history.length < 2) return 0;
  const first = history[0].value;
  const last = history[history.length - 1].value;
  if (!first) return 0;
  return Number((((last - first) / Math.abs(first)) * 100).toFixed(2));
};

export const getPredictionsData = async (payload: TrendPayload): Promise<PredictionResponse> => {
  const productId = payload.product_id || 'P001';
  const metric = payload.metric || 'revenue';
  const forecast = await apiClient<ForecastResponse>('/forecast/predict', {
    method: 'POST',
    body: JSON.stringify({
      product_id: productId,
      target_metric: metric,
      horizon_days: 30,
    }),
  });

  const history = forecast.forecast.map((pt) => ({ date: pt.date, value: pt.value }));
  const growth = calculateGrowth(history);
  const data: TrendData = {
    history,
    direction: growth > 0 ? 'increasing' : growth < 0 ? 'decreasing' : 'flat',
    growth_rate_pct: growth,
    r_squared: undefined,
    p_value: undefined,
  };

  return { data };
};