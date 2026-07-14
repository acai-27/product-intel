import apiClient from '../api/client';
import { DashboardResponse, KpiData } from '../types';

export interface DashboardPayload {
  start_date: string | null;
  end_date: string | null;
  product_id: string | null;
  category: string | null;
}

interface ForecastPoint {
  date: string;
  value: number;
  confidence_lower: number;
  confidence_upper: number;
}

interface ForecastAllResponse {
  product_id: string;
  horizon_days: number;
  revenue: ForecastPoint[];
  profit: ForecastPoint[];
  orders: ForecastPoint[];
  conversion_rate: ForecastPoint[];
  retention_rate: ForecastPoint[];
}

const sum = (points: ForecastPoint[]) => points.reduce((total, pt) => total + pt.value, 0);
const average = (points: ForecastPoint[]) => points.length ? sum(points) / points.length : 0;

export const getDashboardData = async (payload: DashboardPayload): Promise<DashboardResponse> => {
  const productId = payload.product_id || 'P001';
  const forecast = await apiClient<ForecastAllResponse>('/forecast/predict_all', {
    method: 'POST',
    body: JSON.stringify({
      product_id: productId,
      horizon_days: 30,
    }),
  });

  const kpis: KpiData = {
    revenue: { sum: sum(forecast.revenue), daily_avg: average(forecast.revenue) },
    orders: { sum: sum(forecast.orders), daily_avg: average(forecast.orders) },
    conversion_rate: { mean: average(forecast.conversion_rate) },
    retention_rate: { mean: average(forecast.retention_rate) },
    average_order_value: sum(forecast.orders) ? sum(forecast.revenue) / sum(forecast.orders) : 0,
  };

  return {
    kpis,
    channelData: null,
    campaignData: null,
    inventoryData: null,
  };
};