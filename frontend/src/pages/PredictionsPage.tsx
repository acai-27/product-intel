import React, { useState } from 'react';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';
import { ArrowUpRight, ArrowDownRight, RefreshCw, TrendingUp, LineChart } from 'lucide-react';
import { useFilters } from '../components/FilterContext';
import { GlobalFilterBar } from '../components/GlobalFilterBar';
import { usePredictions } from '../hooks/usePredictions';
import { LoadingState, ErrorState } from '../components/LoadingErrorState';
import { Button } from '../components/ui/Button';
import { CardHeader } from '../components/ui/Card';
import { Table } from '../components/ui/Table';
import { useTheme } from '../context/ThemeContext';
import { getChartScales } from '../utils/chartTheme';
import { themeConfig } from '../theme.config';

export default function PredictionsPage() {
  const { selectedProduct, selectedCategory, startDate, endDate } = useFilters();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [trendMetric, setTrendMetric] = useState('revenue');
  const [trendGranularity, setTrendGranularity] = useState('daily');

  const { data, isLoading, isError, error, refetch, isFetching } = usePredictions({
    product_id: selectedProduct || null,
    category: selectedCategory || null,
    start_date: startDate || null,
    end_date: endDate || null,
    metric: trendMetric,
    granularity: trendGranularity,
  });

  const trendData = data?.data;
  const scales = getChartScales(isDark);

  const metricLabel = trendMetric.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const growth = trendData?.growth_rate_pct || 0;
  const growthPositive = growth > 0;
  const growthNegative = growth < 0;

  const trendChartConfig = trendData?.history
    ? {
      labels: trendData.history.map((pt) => pt.date),
      datasets: [
        {
          label: trendMetric.replace('_', ' '),
          data: trendData.history.map((pt) => pt.value),
          borderColor: '#7A7268',
          backgroundColor: 'rgba(122, 114, 104, 0.12)',
          borderWidth: 2.5,
          tension: 0.45,
          fill: true,
          pointRadius: trendData.history.length > 30 ? 0 : 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#7A7268',
          pointBorderColor: isDark ? themeConfig.palette.cashmere : themeConfig.palette.cashmereLightMode,
          pointBorderWidth: 2,
        },
      ],
    }
    : null;

  const tableData =
    trendData?.history?.slice(-8).map((pt) => ({
      date: pt.date,
      value: typeof pt.value === 'number' ? pt.value.toFixed(2) : pt.value,
      metric: trendMetric.replace('_', ' '),
    })) ?? [];

  return (
    <>
      <header className="pin-hero animate-fade-in">
        <div>
          <div className="pin-hero-eyebrow">
            <LineChart size={14} />
            Analytics studio
          </div>
          <h1>Watch your metrics breathe</h1>
          <p className="pin-hero-desc">
            Long-term trajectories, regression fits, and the quiet story behind the numbers — all in one cozy view.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon={<RefreshCw size={14} className={isFetching ? 'spin' : ''} />}
          onClick={() => refetch()}
          disabled={isFetching}
        >
          Refresh
        </Button>
      </header>

      <GlobalFilterBar />

      <div className="animate-fade-in">
        {isLoading ? (
          <LoadingState message="Tracing your trends…" />
        ) : isError ? (
          <ErrorState
            message={error instanceof Error ? error.message : 'Unknown error'}
            onRetry={() => refetch()}
          />
        ) : (
          <>
            {trendData && (
              <div className="analytics-studio-hero animate-fade-in-scale">
                <div>
                  <span
                    style={{
                      fontSize: 11,
                      textTransform: 'uppercase',
                      letterSpacing: '0.12em',
                      color: 'var(--cozy-rose)',
                      fontWeight: 600,
                    }}
                  >
                    {trendGranularity} · {metricLabel}
                  </span>
                  <h2 style={{ marginTop: 'var(--space-3)', fontFamily: 'var(--font-display)', fontSize: 'var(--text-2xl)' }}>
                    {metricLabel} trajectory
                  </h2>
                  <p style={{ color: 'var(--text-muted)', marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)' }}>
                    Regression over your selected window
                  </p>
                </div>
                <div
                  className="analytics-growth-ring"
                  style={{
                    borderColor: growthPositive ? 'var(--success)' : growthNegative ? 'var(--danger)' : 'var(--cozy-rose)',
                  }}
                >
                  <strong style={{ color: growthPositive ? 'var(--success)' : growthNegative ? 'var(--danger)' : undefined }}>
                    {growthPositive ? '+' : ''}
                    {growth}%
                  </strong>
                  <span>Growth</span>
                </div>
              </div>
            )}

            <div className="pin-card pin-card--pad-lg" style={{ marginBottom: 'var(--space-8)' }}>
              <div className="analytics-controls">
                <CardHeader
                  title="Metric trajectory"
                  subtitle={metricLabel}
                  icon={<TrendingUp size={18} />}
                />
                <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', alignItems: 'center' }}>
                  <select
                    className="filter-select"
                    value={trendMetric}
                    onChange={(e) => setTrendMetric(e.target.value)}
                    style={{ minWidth: 160, borderRadius: 14 }}
                  >
                    <option value="revenue">Revenue</option>
                    <option value="orders">Orders</option>
                    <option value="conversion_rate">Conversion rate</option>
                    <option value="retention_rate">Retention rate</option>
                  </select>
                  <div className="granularity-selector granularity-selector--cozy">
                    {['daily', 'weekly', 'monthly', 'quarterly'].map((gran) => (
                      <button
                        key={gran}
                        type="button"
                        className={`granularity-btn ${trendGranularity === gran ? 'active' : ''}`}
                        onClick={() => setTrendGranularity(gran)}
                      >
                        {gran.charAt(0).toUpperCase() + gran.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div style={{ height: 380, position: 'relative' }}>
                {trendChartConfig ? (
                  <Line
                    data={trendChartConfig}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales,
                      interaction: { intersect: false, mode: 'index' },
                    }}
                  />
                ) : (
                  <div className="empty-state">
                    <div className="empty-state-icon">
                      <TrendingUp size={28} />
                    </div>
                    <h3>No trend data yet</h3>
                    <p>Adjust filters or widen your date range</p>
                  </div>
                )}
              </div>

              {trendData && (
                <div className="analytics-pin-stats animate-fade-in">
                  <div className="analytics-stat-pin">
                    <label>Direction</label>
                    <p
                      style={{
                        color:
                          trendData.direction === 'increasing'
                            ? 'var(--success)'
                            : trendData.direction === 'decreasing'
                              ? 'var(--danger)'
                              : undefined,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 4,
                      }}
                    >
                      {trendData.direction === 'increasing' && <ArrowUpRight size={16} />}
                      {trendData.direction === 'decreasing' && <ArrowDownRight size={16} />}
                      {trendData.direction}
                    </p>
                  </div>
                  <div className="analytics-stat-pin">
                    <label>Growth rate</label>
                    <p style={{ color: growthPositive ? 'var(--success)' : growthNegative ? 'var(--danger)' : undefined }}>
                      {growthPositive ? '+' : ''}
                      {growth}%
                    </p>
                  </div>
                  <div className="analytics-stat-pin">
                    <label>R² fit</label>
                    <p>{((trendData.r_squared || 0) * 100).toFixed(1)}%</p>
                  </div>
                  <div className="analytics-stat-pin">
                    <label>Significance</label>
                    <p>{(trendData.p_value || 1) < 0.05 ? 'Significant' : 'Weak'}</p>
                  </div>
                </div>
              )}
            </div>

            {tableData.length > 0 && (
              <div className="pin-card pin-card--pad-lg">
                <CardHeader title="Recent data points" subtitle="Latest values in view" />
                <Table
                  columns={[
                    { key: 'date', header: 'Date', sortable: true },
                    { key: 'metric', header: 'Metric' },
                    { key: 'value', header: 'Value', sortable: true },
                  ]}
                  data={tableData}
                />
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
