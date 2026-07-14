export interface FilterState {
  selectedProduct: string;
  selectedCategory: string;
  startDate: string;
  endDate: string;
}

export interface FilterContextType extends FilterState {
  setSelectedProduct: (val: string) => void;
  setSelectedCategory: (val: string) => void;
  setStartDate: (val: string) => void;
  setEndDate: (val: string) => void;
}

export interface TrendData {
  history?: { date: string; value: number }[];
  direction?: 'increasing' | 'decreasing' | 'flat';
  growth_rate_pct?: number;
  r_squared?: number;
  p_value?: number;
}

export interface KpiData {
  revenue?: { sum: number; daily_avg: number };
  orders?: { sum: number; daily_avg: number };
  average_order_value?: number;
  conversion_rate?: { mean: number };
  retention_rate?: { mean: number };
}

export interface ChartDataConfig {
  labels: string[];
  datasets: any[];
}

export type VizStatus = 'loading' | 'ready' | 'error';

export interface ChatVisualization {
  id: string;
  title: string;
  subtitle?: string;
  chart_type: 'line' | 'bar' | 'doughnut';
  index_axis?: 'x' | 'y' | null;
  status: VizStatus;
  data?: ChartDataConfig;
}

export interface Message {
  sender: 'user' | 'assistant';
  text: string;
  meta?: {
    route?: string;
    raw?: any;
  };
  visualizations?: ChatVisualization[];
}

// Data Layer Responses
export interface DashboardResponse {
  kpis: KpiData;
  channelData: any;
  campaignData: any;
  inventoryData: any;
}

export interface PredictionResponse {
  data: TrendData;
}

export interface ChatResponse {
  response: string;
  routed_to: string;
}
