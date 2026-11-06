/**
 * Market Analytics Dashboard
 * 
 * Comprehensive market analytics including:
 * - Market-wide heatmaps (Futures vs Forex vs Crypto vs Options vs Equities)
 * - Global submission insights
 * - Monthly awards
 * - Deep category statistics per market
 * 
 * Public access for marketing and traders
 */

import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { publicApi } from '../config/api';
import { fetchMarketCategories, getMarketColor as getColor } from '../services/marketService';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useScrollAnimation } from '../hooks/useScrollAnimation';
import './Analytics.css';

const Analytics = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedView, setSelectedView] = useState(searchParams.get('view') || 'overview');
  const [selectedMarket, setSelectedMarket] = useState(searchParams.get('market') || '');
  const [loading, setLoading] = useState(true);
  const [globalData, setGlobalData] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [awardsData, setAwardsData] = useState(null);
  const [marketCategories, setMarketCategories] = useState([]);

  useEffect(() => {
    loadMarketCategories();
  }, []);

  useEffect(() => {
    if (marketCategories.length > 0 && !selectedMarket) {
      // Set first active market as default
      const firstMarket = marketCategories.find(m => m.is_active);
      if (firstMarket) {
        setSelectedMarket(firstMarket.name);
      }
    }
  }, [marketCategories]);

  useEffect(() => {
    if (selectedMarket || selectedView === 'overview' || selectedView === 'trends' || selectedView === 'highlights' || selectedView === 'awards') {
      fetchData();
    }
  }, [selectedView, selectedMarket]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (selectedView === 'overview' || selectedView === 'trends' || selectedView === 'highlights') {
        await fetchGlobalOverview();
      } else if (selectedView === 'market') {
        await fetchMarketAnalytics();
      } else if (selectedView === 'awards') {
        await fetchMonthlyAwards();
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMarketCategories = async () => {
    const markets = await fetchMarketCategories();
    setMarketCategories(markets);
  };

  const fetchGlobalOverview = async (period = 'month', scatterPeriod = '90d', scatterGranularity = 'day') => {
    const response = await publicApi.get('/analytics/global-overview/', {
      params: { 
        period,
        scatter_period: scatterPeriod,
        scatter_granularity: scatterGranularity
      }
    });
    setGlobalData(response.data);
  };

  const fetchMarketAnalytics = async () => {
    const response = await publicApi.get('/analytics/market-detail/', {
      params: { market_category: selectedMarket }
    });
    setMarketData(response.data);
  };

  const fetchMonthlyAwards = async () => {
    const response = await publicApi.get('/analytics/monthly-awards/');
    setAwardsData(response.data);
  };

  const changeView = (view) => {
    setSelectedView(view);
    setSearchParams({ view, market: selectedMarket });
  };

  const changeMarket = (market) => {
    setSelectedMarket(market);
    setSearchParams({ view: selectedView, market });
  };

  return (
    <div className="analytics-page">
      {/* Header */}
      <div className="analytics-header">
        <h1>Market Analytics Dashboard</h1>
        <p>
          Comprehensive trading analytics across all verified servers
        </p>
      </div>

      {/* View Selector */}
      <div className="analytics-view-selector">
        <ViewTab
          active={selectedView === 'overview'}
          onClick={() => changeView('overview')}
          icon=""
          label="Global Overview"
        />
        <ViewTab
          active={selectedView === 'trends'}
          onClick={() => changeView('trends')}
          icon=""
          label="Global Ecosystem Trends"
        />
        <ViewTab
          active={selectedView === 'highlights'}
          onClick={() => changeView('highlights')}
          icon=""
          label="Highlights & Records"
        />
        <ViewTab
          active={selectedView === 'market'}
          onClick={() => changeView('market')}
          icon=""
          label="Market Deep Dive"
        />
        <ViewTab
          active={selectedView === 'awards'}
          onClick={() => changeView('awards')}
          icon=""
          label="Monthly Rankings"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="analytics-loading">
          <h2>Loading analytics...</h2>
        </div>
      ) : (
        <>
          {selectedView === 'overview' && globalData && (
            <GlobalOverview data={globalData} marketCategories={marketCategories} />
          )}
          {selectedView === 'trends' && globalData && globalData.ecosystem_trends && (
            <EcosystemTrends
              trends={globalData.ecosystem_trends}
              marketCategories={marketCategories}
              onPeriodChange={(period, scatterPeriod, scatterGranularity) => fetchGlobalOverview(period, scatterPeriod, scatterGranularity)}
            />
          )}
          {selectedView === 'highlights' && globalData && globalData.highlights_and_records && (
            <GlobalHighlights highlights={globalData.highlights_and_records} />
          )}
          {selectedView === 'market' && (
            <>
              <MarketSelector
                markets={marketCategories.filter(m => m.is_active)}
                selected={selectedMarket}
                getColor={getColor}
                onSelect={changeMarket}
              />
              {marketData && <MarketDeepDive data={marketData} market={selectedMarket} marketCategories={marketCategories} />}
            </>
          )}
          {selectedView === 'awards' && awardsData && (
            <MonthlyAwards data={awardsData} />
          )}
        </>
      )}
    </div>
  );
};

const ViewTab = ({ active, onClick, label }) => (
  <button
    className={`view-tab ${active ? 'active' : ''}`}
    onClick={onClick}
  >
    {label}
  </button>
);

const MarketSelector = ({ markets, selected, onSelect, getColor }) => (
  <div className="market-selector">
    {markets.map((market) => {
      const isSelected = selected === market.name;
      const color = 'rgba(0, 102, 255, 0.3)';

      return (
        <button
          key={market.id || market.name}
          className={`market-chip ${isSelected ? 'active' : ''}`}
          onClick={() => onSelect(market.name)}
          style={{
            backgroundColor: isSelected ? color : undefined,
            borderColor: isSelected ? color : undefined,
          }}
        >
          {market.name}
        </button>
      );
    })}
  </div>
);

// GLOBAL OVERVIEW COMPONENT
const GlobalOverview = ({ data, marketCategories }) => {
  // Use new global_metrics object if available, fall back to legacy fields
  const metrics = data.global_metrics || {
    total_verified_payouts: data.total_verified_payouts,
    total_payout_volume: data.total_volume,
    active_servers: data.active_servers,
    active_submissions_today: data.active_submissions_today,
    system_uptime: data.system_uptime
  };

  // Line chart controls and state
  const [chartMetric, setChartMetric] = useState('total_verified_payouts');
  const [chartPeriod, setChartPeriod] = useState('month');
  const [chartMarket, setChartMarket] = useState('all');
  const [timeseries, setTimeseries] = useState(null);
  const [timeseriesLoading, setTimeseriesLoading] = useState(false);
  const [timeseriesError, setTimeseriesError] = useState(null);
  const [chartRef, chartVisible] = useScrollAnimation({ threshold: 0.2 });

  useEffect(() => {
    const fetchTimeseries = async () => {
      setTimeseriesLoading(true);
      setTimeseriesError(null);
      try {
        const params = { metric: chartMetric, period: chartPeriod };
        if (chartMarket && chartMarket !== 'all') params.market = chartMarket;
        const resp = await publicApi.get('/analytics/global-timeseries/', { params });
        // Expecting an array of { date, value }
        setTimeseries(resp.data.timeseries || resp.data || []);
      } catch (err) {
        console.error('Timeseries fetch error', err);
        setTimeseriesError('Unable to load data for the selected options.');
        setTimeseries([]);
      } finally {
        setTimeseriesLoading(false);
      }
    };

    if (chartVisible) {
      fetchTimeseries();
    }
  }, [chartMetric, chartPeriod, chartMarket, chartVisible]);

  return (
    <div>
      {/* SECTION 1 — Global Performance Metrics (Top Header) */}
      {/* These are the "headline stats" that instantly establish scale and legitimacy */}
      <Section title="Global Performance Metrics">
        <div className="analytics-stats-grid">
          <MetricCard
            index={0}
            icon=""
            title="Total Verified Payouts"
            value={metrics.total_verified_payouts?.toLocaleString() || '0'}
            subtitle="All-time approved submissions"
          />
          <MetricCard
            index={1}
            icon=""
            title="Total Payout Volume"
            value={`${metrics.total_payout_volume >= 1000000 ? `$${(metrics.total_payout_volume / 1000000).toFixed(1)}M+` : metrics.total_payout_volume?.toLocaleString() || '0'}`}
            subtitle="Cumulative processed volume"
          />
          <MetricCard
            index={2}
            icon=""
            title="Active Servers"
            value={metrics.active_servers?.toLocaleString() || '0'}
            subtitle="With payouts in last 30 days"
          />
          <MetricCard
            index={3}
            icon=""
            title="Active Submissions Today"
            value={metrics.active_submissions_today?.toLocaleString() || '0'}
            subtitle="Live ecosystem activity"
          />
          <MetricCard
            index={4}
            icon=""
            title="Aurevia System Uptime"
            value={`${metrics.system_uptime?.toFixed(2) || '99.99'}%`}
            subtitle="Institutional-grade reliability"
          />
        </div>
      </Section>

      {/* Market-Wide Heatmaps */}
      <Section title="Market Performance Heatmap">
        <MarketHeatmap markets={data.market_comparison} marketCategories={marketCategories} />
      </Section>

      {/* Global Submission Insights */}
      <Section title="Platform-Wide Insights">
        <div className="analytics-stats-grid">
          <MetricCard
            index={0}
            icon=""
            title="Daily Volume"
            value={`$${data.daily_volume?.toLocaleString() || '0'}`}
            subtitle="Last 24 hours"
          />
          <MetricCard
            index={1}
            icon=""
            title="Total Submissions"
            value={data.total_submissions?.toLocaleString() || '0'}
            subtitle={`${data.daily_submissions || 0} today`}
          />
          <MetricCard
            index={2}
            icon=""
            title="Approval Rate"
            value={`${data.approval_rate?.toFixed(1) || '0'}%`}
            subtitle={`${data.rejection_rate?.toFixed(1) || '0'}% rejected`}
          />
        </div>

        {/* Submission Status Breakdown */}
        <div className="analytics-stats-grid">
          <StatusCard
            label="Approved"
            count={data.approved_count || 0}
            percentage={data.approval_rate || 0}
          />
          <StatusCard
            label="Pending"
            count={data.pending_count || 0}
            percentage={data.pending_rate || 0}
          />
          <StatusCard
            label="Rejected"
            count={data.rejected_count || 0}
            percentage={data.rejection_rate || 0}
          />
          <StatusCard
            label="Suspicious"
            count={data.suspicious_count || 0}
            percentage={data.suspicious_rate || 0}
          />
        </div>
      </Section>

      {/* Metric Over Time - line chart with card-like filters */}
      <Section title="Metric Over Time">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ color: 'white', marginBottom: '8px' }}>Metric Over Time</h3>
            <p style={{ color: 'rgba(100, 149, 237, 0.8)', fontSize: '14px' }}>
              Choose a metric, period and market to visualize its trend.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              {[{ label: 'Payouts', value: 'total_verified_payouts' }, { label: 'Volume', value: 'total_payout_volume' }, { label: 'Servers', value: 'active_servers' }, { label: 'Submissions', value: 'active_submissions_today' }, { label: 'Uptime', value: 'system_uptime' }].map(m => (
                <button
                  key={m.value}
                  onClick={() => setChartMetric(m.value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: chartMetric === m.value ? '2px solid #0066ff' : '1px solid rgba(0, 102, 255, 0.2)',
                    backgroundColor: chartMetric === m.value ? 'rgba(0, 102, 255, 0.12)' : 'transparent',
                    color: chartMetric === m.value ? '#0066ff' : 'rgba(100,149,237,0.85)',
                    cursor: 'pointer',
                    fontSize: '13px'
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              {['week', 'month', 'year'].map(p => (
                <button
                  key={p}
                  onClick={() => setChartPeriod(p)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: chartPeriod === p ? '2px solid #0066ff' : '1px solid rgba(0, 102, 255, 0.2)',
                    backgroundColor: chartPeriod === p ? 'rgba(0, 102, 255, 0.12)' : 'transparent',
                    color: chartPeriod === p ? '#0066ff' : 'rgba(100,149,237,0.85)',
                    cursor: 'pointer',
                    fontSize: '13px',
                    textTransform: 'capitalize'
                  }}
                >
                  {p}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => setChartMarket('all')}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  border: chartMarket === 'all' ? '2px solid #0066ff' : '1px solid rgba(0, 102, 255, 0.2)',
                  backgroundColor: chartMarket === 'all' ? 'rgba(0, 102, 255, 0.12)' : 'transparent',
                  color: chartMarket === 'all' ? '#0066ff' : 'rgba(100,149,237,0.85)',
                  cursor: 'pointer',
                  fontSize: '13px'
                }}
              >
                All Markets
              </button>
              <MarketSelector
                markets={marketCategories.filter(m => m.is_active)}
                selected={chartMarket}
                getColor={() => 'rgba(0,102,255,0.3)'}
                onSelect={(m) => setChartMarket(m)}
              />
            </div>
          </div>
        </div>

        <div ref={chartRef} style={{ backgroundColor: 'rgba(0, 102, 255, 0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(0, 102, 255, 0.2)' }}>
          { !chartVisible ? (
            <div style={{ height: 350 }} />
          ) : timeseriesLoading ? (
            <div style={{ padding: '40px', color: 'rgba(100,149,237,0.8)' }}>Loading chart...</div>
          ) : timeseries && timeseries.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={timeseries}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                <XAxis dataKey="date" stroke="rgba(100, 149, 237, 0.7)" style={{ fontSize: '12px' }} />
                <YAxis stroke="rgba(100, 149, 237, 0.7)" style={{ fontSize: '12px' }} tickFormatter={(v) => {
                  if (chartMetric && chartMetric.toLowerCase().includes('volume')) {
                    if (v >= 1000) return `$${(v / 1000).toFixed(0)}k`;
                    return `$${v}`;
                  }
                  if (typeof v === 'number') return v.toLocaleString();
                  return v;
                }} />
                <Tooltip content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div style={{ backgroundColor: 'rgba(0,0,0,0.9)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(0,102,255,0.5)' }}>
                        <p style={{ color: 'white', margin: 0, fontWeight: 'bold' }}>{label}</p>
                        <p style={{ color: '#0066ff', margin: '6px 0' }}>{chartMetric.includes('volume') ? `$${d.value?.toLocaleString()}` : d.value?.toLocaleString()}</p>
                      </div>
                    );
                  }
                  return null;
                }} />
                <Line type="monotone" dataKey="value" stroke="#0066ff" strokeWidth={3} dot={{ r: 3 }} name={chartMetric} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ padding: '40px', color: 'rgba(100,149,237,0.8)' }}>No data available for the selected options.</div>
          )}
        </div>
      </Section>

      </div>
  );
};

// MARKET DEEP DIVE COMPONENT
const MarketDeepDive = ({ data, market, marketCategories }) => {
  const marketInfo = marketCategories.find(m => m.name === market) || {};
  const marketColor = getColor(market);

  return (
    <div>
      {/* Market Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '20px',
        marginBottom: '30px',
      }}>
        <MetricCard
          icon=''
          title={`${marketInfo.name || market} Total Volume`}
          value={`$${data.total_payouts?.toLocaleString() || '0'}`}
          subtitle={`${data.total_submissions || 0} submissions`}
        />
        <MetricCard
          icon=""
          title="Average Payout"
          value={`$${data.avg_payout?.toFixed(2) || '0'}`}
          subtitle={`${data.median_payout ? `Median: $${data.median_payout.toFixed(2)}` : ''}`}
        />
        <MetricCard
          icon=""
          title="Active Traders"
          value={data.unique_traders?.toLocaleString() || '0'}
          subtitle={`${data.unique_servers || 0} servers`}
        />
        <MetricCard
          icon=""
          title="Instruments"
          value={data.unique_instruments?.toLocaleString() || '0'}
          subtitle="Different instruments traded"
        />
      </div>

      {/* Instrument Heatmap */}
      <Section title={`${marketInfo.name} Instrument Performance`}>
        <InstrumentHeatmap instruments={data.instruments || []} />
      </Section>

      {/* Top Instruments Table */}
      <Section title="Top Instruments by Volume">
        <InstrumentTable instruments={data.instruments || []} />
      </Section>

      {/* Server Rankings for this Market */}
      <Section title={`Top Servers in ${marketInfo.name}`}>
        <ServerRankingTable servers={data.top_servers || []} />
      </Section>

      {/* Trader Rankings for this Market */}
      <Section title={`Top Traders in ${marketInfo.name}`}>
        <TraderRankingTable traders={data.top_traders || []} />
      </Section>

    </div>
  );
};

// MONTHLY AWARDS COMPONENT
const MonthlyAwards = ({ data }) => (
  <div>
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '30px',
    }}>
      <AwardCard
        icon=""
        title="Server of the Month"
        winner={data.server_of_month}
        metric="Total Volume"
        value={data.server_of_month?.value}
      />
      <AwardCard
        icon=""
        title="Trader of the Month"
        winner={data.trader_of_month}
        metric="Total Payouts"
        value={data.trader_of_month?.value}
      />
      <AwardCard
        icon=""
        title="Rising Star"
        winner={data.rising_star}
        metric="Growth Rate"
        value={data.rising_star?.value}
      />
      <AwardCard
        icon=""
        title="Most Active Community"
        winner={data.most_active}
        metric="Submissions"
        value={data.most_active?.value}
      />
    </div>

    {/* Historical Winners */}
    <Section title="Previous Winners">
      <HistoricalAwards data={data.historical || []} />
    </Section>
  </div>
);

// UTILITY COMPONENTS

// Animated Section wrapper using Intersection Observer
const Section = ({ title, children, delay = 0 }) => {
  const [ref, isVisible] = useScrollAnimation({ threshold: 0.1 });

  return (
    <div 
      ref={ref}
      className={`analytics-section ${isVisible ? 'animate-in' : 'animate-out'}`}
      style={{ 
        animationDelay: `${delay}ms`,
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'translateY(0)' : 'translateY(30px)',
        transition: `opacity 0.6s ease ${delay}ms, transform 0.6s ease ${delay}ms`
      }}
    >
      <h2>{title}</h2>
      {children}
    </div>
  );
};

const MetricCard = ({ icon, title, value, subtitle, index = 0 }) => {
  const [ref, isVisible] = useScrollAnimation({ threshold: 0.2 });

  return (
    <div 
      ref={ref}
      className="analytics-stat-card"
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'scale(1) translateY(0)' : 'scale(0.9) translateY(20px)',
        transition: `all 0.5s ease ${index * 100}ms`
      }}
    >
      <div className="icon">{icon}</div>
      <div className="title">{title}</div>
      <div className="value">{value}</div>
      {subtitle && <div className="subtitle">{subtitle}</div>}
    </div>
  );
};

const StatusCard = ({ label, count, percentage }) => (
  <div className="analytics-stat-card">
    <div className="title">{label}</div>
    <div className="value">
      {count.toLocaleString()}
    </div>
    <div className="subtitle">{percentage.toFixed(1)}%</div>
  </div>
);

// Separate component for animated market card
const MarketHeatmapCard = ({ market, marketInfo, index }) => {
  const [ref, isVisible] = useScrollAnimation({ threshold: 0.2 });
  
  return (
    <div
      key={market.category}
      ref={ref}
      className="market-heatmap-card"
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? 'scale(1) translateY(0)' : 'scale(0.95) translateY(20px)',
        transition: `all 0.5s ease ${index * 80}ms`
      }}
    >
      <div className="icon">{marketInfo.icon || ''}</div>
      <div className="name">{marketInfo.name || market.category}</div>
      <div className="volume">${market.volume.toLocaleString()}</div>
      <div className="count">{market.submissions} submissions</div>
      <div className="count">
        {market.growth > 0 ? '▴' : '▾'} {market.growth.toFixed(1)}% vs last month
      </div>
    </div>
  );
};

const MarketHeatmap = ({ markets, marketCategories }) => {
  if (!markets || markets.length === 0) {
    return <div className="no-data">No data available</div>;
  }

  const maxVolume = Math.max(...markets.map(m => m.volume));

  return (
    <div className="market-heatmap">
      {markets.map((market, index) => {
        const marketInfo = marketCategories.find(m => m.name === market.category) || {};
        return (
          <MarketHeatmapCard 
            key={market.category}
            market={market}
            marketInfo={marketInfo}
            index={index}
          />
        );
      })}
    </div>
  );
};

const InstrumentHeatmap = ({ instruments }) => {
  if (!instruments || instruments.length === 0) {
    return <div className="no-data">No data available</div>;
  }

  const maxPayout = Math.max(...instruments.map(i => i.total_payout));

  return (
    <div className="instrument-heatmap">
      {instruments.slice(0, 30).map((instrument) => {
        const intensity = (instrument.total_payout / maxPayout) * 100;
        const color = getHeatmapColor(intensity);

        return (
          <div
            key={instrument.instrument}
            className="instrument-heatmap-card"
          >
            <div className="name">
              {instrument.instrument}
            </div>
            <div className="volume">
              ${instrument.total_payout.toLocaleString()}
            </div>
            <div className="count">
              {instrument.submission_count} payouts
            </div>
          </div>
        );
      })}
    </div>
  );
};

const getHeatmapColor = (intensity) => {
  if (intensity > 80) return '#d32f2f';
  if (intensity > 60) return '#f57c00';
  if (intensity > 40) return '#fbc02d';
  if (intensity > 20) return '#8bc34a';
  return '#e0e0e0';
};

const InstrumentTable = ({ instruments }) => {
  if (!instruments || instruments.length === 0) return null;

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Instrument</th>
            <th className="text-right">Total Volume</th>
            <th className="text-right">Submissions</th>
            <th className="text-right">Avg Payout</th>
            <th className="text-right">Traders</th>
          </tr>
        </thead>
        <tbody>
          {instruments.slice(0, 15).map((instrument, index) => (
            <tr key={instrument.instrument}>
              <td>
                #{index + 1}
              </td>
              <td className="bold">{instrument.instrument}</td>
              <td className="text-right">
                ${instrument.total_payout.toLocaleString()}
              </td>
              <td className="text-right">
                {instrument.submission_count}
              </td>
              <td className="text-right">
                ${instrument.avg_payout.toFixed(2)}
              </td>
              <td className="text-right">
                {instrument.unique_traders}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ServerRankingTable = ({ servers }) => {
  if (!servers || servers.length === 0) return null;

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Server</th>
            <th className="text-right">Volume</th>
            <th className="text-right">Submissions</th>
          </tr>
        </thead>
        <tbody>
          {servers.slice(0, 10).map((server, index) => (
            <tr key={server.server_id}>
              <td>
                #{index + 1}
              </td>
              <td className="bold">
                <Link 
                  to={server.profile_url || `/servers/${server.server_id}/public`}
                  style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  {server.server_name}
                </Link>
              </td>
              <td className="text-right">
                ${server.total_payout.toLocaleString()}
              </td>
              <td className="text-right">
                {server.submission_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TraderRankingTable = ({ traders }) => {
  if (!traders || traders.length === 0) return null;

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Trader</th>
            <th className="text-right">Volume</th>
            <th className="text-right">Submissions</th>
          </tr>
        </thead>
        <tbody>
          {traders.slice(0, 10).map((trader, index) => (
            <tr key={trader.user_id || index}>
              <td>
                #{index + 1}
              </td>
              <td className="bold">
                <Link 
                  to={trader.profile_url || `/trader/${trader.user_id}/public`}
                  style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  {trader.username || trader.user_name || 'Anonymous'}
                </Link>
              </td>
              <td className="text-right">
                ${(trader.total_payout || trader.total_volume || 0).toLocaleString()}
              </td>
              <td className="text-right">
                {trader.submission_count || trader.count || 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const TimeframeChart = ({ timeframes }) => {
  const maxCount = Math.max(...timeframes.map(t => t.count));

  return (
    <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '12px' }}>
      {timeframes.map((tf) => {
        const percentage = (tf.count / maxCount) * 100;

        return (
          <div key={tf.timeframe} style={{ marginBottom: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 'bold', fontSize: '15px' }}>{tf.timeframe}</span>
              <span style={{ color: 'rgba(100, 149, 237, 0.8)', fontSize: '14px' }}>{tf.count} trades</span>
            </div>
            <div style={{
              width: '100%',
              height: '35px',
              backgroundColor: 'rgba(0, 102, 255, 0.1)',
              borderRadius: '6px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${percentage}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #007bff 0%, #0056b3 100%)',
                transition: 'width 0.4s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                paddingRight: '12px',
                color: 'white',
                fontWeight: 'bold',
                fontSize: '13px',
              }}>
                {percentage > 10 && `${percentage.toFixed(1)}%`}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const TrendChart = ({ data }) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '300px' }}>
        {data.map((day, index) => {
          const height = (day.value / maxValue) * 100;

          return (
            <div
              key={index}
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                height: '100%',
              }}
            >
              <div
                style={{
                  height: `${height}%`,
                  backgroundColor: 'rgba(0, 102, 255, 0.5)',
                  borderRadius: '4px 4px 0 0',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(0, 102, 255, 0.4)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(0, 102, 255, 0.3)'}
                title={`${day.date}: $${day.value.toLocaleString()}`}
              />
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '12px', color: 'rgba(100, 149, 237, 0.8)' }}>
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
};

// SECTION 2 — Global Ecosystem Trends Component
const EcosystemTrends = ({ trends, marketCategories, onPeriodChange }) => {
  const COLORS = ['#0066ff', '#00b4d8', '#90e0ef', '#caf0f8', '#48cae4'];
  const [growthPeriod, setGrowthPeriod] = useState('month');
  const [scatterPeriod, setScatterPeriod] = useState('90d');
  const [scatterGranularity, setScatterGranularity] = useState('day');

  // Scroll animation hooks for each chart
  const [volumeChartRef, volumeChartVisible] = useScrollAnimation({ threshold: 0.2 });
  const [countChartRef, countChartVisible] = useScrollAnimation({ threshold: 0.2 });
  const [scatterChartRef, scatterChartVisible] = useScrollAnimation({ threshold: 0.2 });
  const [pieChartRef, pieChartVisible] = useScrollAnimation({ threshold: 0.2 });
  const [growthChartRef, growthChartVisible] = useScrollAnimation({ threshold: 0.2 });

  // Custom tooltip styling to match Aurevia theme
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          padding: '12px',
          borderRadius: '8px',
          border: '1px solid rgba(0, 102, 255, 0.5)',
          backdropFilter: 'blur(10px)',
        }}>
          <p style={{ color: 'white', margin: '0 0 8px 0', fontWeight: 'bold' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, margin: '4px 0', fontSize: '14px' }}>
              {entry.name}: {typeof entry.value === 'number' && entry.name.includes('Volume')
                ? `$${entry.value.toLocaleString()}`
                : entry.value.toLocaleString()}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div>
      <Section title="Global Ecosystem Trends">
        <p style={{ color: 'rgba(100, 149, 237, 0.9)', marginBottom: '30px', fontSize: '16px' }}>
          Interactive visualizations showing Aurevia's growth trajector
        </p>

        {/* Monthly Verified Payout Volume - Line Chart */}
        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ color: 'white', marginBottom: '20px' }}>Monthly Verified Payout Volume</h3>
          <p style={{ color: 'rgba(100, 149, 237, 0.8)', marginBottom: '15px', fontSize: '14px' }}>
            Growth over time (0 risk to server privacy)
          </p>
          <div 
            ref={volumeChartRef}
            style={{ 
              backgroundColor: 'rgba(0, 102, 255, 0.05)', 
              padding: '20px', 
              borderRadius: '12px', 
              border: '1px solid rgba(0, 102, 255, 0.2)'
            }}
          >
            {volumeChartVisible && (
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={trends.monthly_volume}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0066ff" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#0066ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                <XAxis
                  dataKey="month"
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="volume"
                  stroke="#0066ff"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorVolume)"
                  name="Volume"
                />
              </AreaChart>
            </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Monthly Verified Payout Count - Bar Chart */}
        <div style={{ marginBottom: '40px' }}>
          <h3 style={{ color: 'white', marginBottom: '20px' }}>Monthly Verified Payout Count</h3>
          <p style={{ color: 'rgba(100, 149, 237, 0.8)', marginBottom: '15px', fontSize: '14px' }}>
            Ecosystem usage and activity levels
          </p>
          <div 
            ref={countChartRef}
            style={{ 
              backgroundColor: 'rgba(0, 102, 255, 0.05)', 
              padding: '20px', 
              borderRadius: '12px', 
              border: '1px solid rgba(0, 102, 255, 0.2)'
            }}
          >
            {countChartVisible && (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={trends.monthly_count}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                <XAxis
                  dataKey="month"
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                />
                <Tooltip content={<CustomTooltip />} cursor={false} />
                <Bar
                  dataKey="count"
                  fill="#0066ff"
                  name="Payouts"
                  radius={[8, 8, 0, 0]}
                  activeBar={false}
                />
              </BarChart>
            </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Payout Distribution Scatter Plot */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ color: 'white', marginBottom: '8px' }}>Payout Distribution Over Time</h3>
              <p style={{ color: 'rgba(100, 149, 237, 0.8)', fontSize: '14px' }}>
                Individual payout amounts (up to 1000 most recent payouts shown)
              </p>
            </div>
            {/* Scatter Plot Filters */}
            <div style={{ display: 'flex', gap: '15px' }}>
              {/* Time Period Filter */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: 'rgba(100, 149, 237, 0.8)', textTransform: 'uppercase', letterSpacing: '1px' }}>Time Period</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {[{label: '7D', value: '7d'}, {label: '30D', value: '30d'}, {label: '90D', value: '90d'}, {label: '180D', value: '180d'}, {label: '1Y', value: '365d'}, {label: 'All', value: 'all'}].map(period => (
                    <button
                      key={period.value}
                      onClick={() => {
                        setScatterPeriod(period.value);
                        if (onPeriodChange) onPeriodChange(growthPeriod, period.value, scatterGranularity);
                      }}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '6px',
                        border: scatterPeriod === period.value
                          ? '2px solid #0066ff'
                          : '1px solid rgba(0, 102, 255, 0.3)',
                        backgroundColor: scatterPeriod === period.value
                          ? 'rgba(0, 102, 255, 0.2)'
                          : 'rgba(0, 102, 255, 0.05)',
                        color: scatterPeriod === period.value ? '#0066ff' : 'rgba(100, 149, 237, 0.8)',
                        cursor: 'pointer',
                        fontWeight: scatterPeriod === period.value ? 'bold' : 'normal',
                        fontSize: '13px',
                        transition: 'all 0.2s ease',
                        backdropFilter: 'blur(10px)'
                      }}
                      onMouseEnter={(e) => {
                        if (scatterPeriod !== period.value) {
                          e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.1)';
                          e.target.style.borderColor = 'rgba(0, 102, 255, 0.5)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (scatterPeriod !== period.value) {
                          e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.05)';
                          e.target.style.borderColor = 'rgba(0, 102, 255, 0.3)';
                        }
                      }}
                    >
                      {period.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Granularity Filter */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ fontSize: '12px', color: 'rgba(100, 149, 237, 0.8)', textTransform: 'uppercase', letterSpacing: '1px' }}>Granularity</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {['day', 'week', 'month', 'year'].map(gran => (
                    <button
                      key={gran}
                      onClick={() => {
                        setScatterGranularity(gran);
                        if (onPeriodChange) onPeriodChange(growthPeriod, scatterPeriod, gran);
                      }}
                      style={{
                        padding: '8px 16px',
                        borderRadius: '6px',
                        border: scatterGranularity === gran
                          ? '2px solid #0066ff'
                          : '1px solid rgba(0, 102, 255, 0.3)',
                        backgroundColor: scatterGranularity === gran
                          ? 'rgba(0, 102, 255, 0.2)'
                          : 'rgba(0, 102, 255, 0.05)',
                        color: scatterGranularity === gran ? '#0066ff' : 'rgba(100, 149, 237, 0.8)',
                        cursor: 'pointer',
                        fontWeight: scatterGranularity === gran ? 'bold' : 'normal',
                        textTransform: 'capitalize',
                        fontSize: '13px',
                        transition: 'all 0.2s ease',
                        backdropFilter: 'blur(10px)'
                      }}
                      onMouseEnter={(e) => {
                        if (scatterGranularity !== gran) {
                          e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.1)';
                          e.target.style.borderColor = 'rgba(0, 102, 255, 0.5)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (scatterGranularity !== gran) {
                          e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.05)';
                          e.target.style.borderColor = 'rgba(0, 102, 255, 0.3)';
                        }
                      }}
                    >
                      {gran}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div 
            ref={scatterChartRef}
            style={{ 
              backgroundColor: 'rgba(0, 102, 255, 0.05)', 
              padding: '20px', 
              borderRadius: '12px', 
              border: '1px solid rgba(0, 102, 255, 0.2)'
            }}
          >
            {scatterChartVisible && (
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart
                margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                <XAxis
                  dataKey="date"
                  name="Date"
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                />
                <YAxis
                  dataKey="amount"
                  name="Payout"
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => {
                    if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
                    return `$${value}`;
                  }}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div style={{
                          backgroundColor: 'rgba(0, 0, 0, 0.9)',
                          padding: '12px',
                          borderRadius: '8px',
                          border: '1px solid rgba(0, 102, 255, 0.5)',
                          backdropFilter: 'blur(10px)'
                        }}>
                          <p style={{ color: 'white', margin: '0 0 8px 0', fontWeight: 'bold' }}>
                            {new Date(data.date).toLocaleDateString()}
                          </p>
                          <p style={{ color: '#0066ff', margin: '4px 0', fontSize: '14px' }}>
                            Amount: ${data.amount.toLocaleString()}
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter
                  name="Payouts"
                  data={trends.payout_scatter}
                  fill="#0066ff"
                  fillOpacity={0.6}
                />
              </ScatterChart>
            </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Two Column Layout for Category Breakdown and Growth Curve */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '40px' }}>

          {/* Category Breakdown - Pie/Donut Chart */}
          <div>
            <h3 style={{ color: 'white', marginBottom: '20px' }}>Market Category Distribution</h3>
            <p style={{ color: 'rgba(100, 149, 237, 0.8)', marginBottom: '15px', fontSize: '14px' }}>
              Trading activity by market type
            </p>
            <div 
              ref={pieChartRef}
              style={{ 
                backgroundColor: 'rgba(0, 102, 255, 0.05)', 
                padding: '20px', 
                borderRadius: '12px', 
                border: '1px solid rgba(0, 102, 255, 0.2)'
              }}
            >
              {pieChartVisible && (
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={trends.category_breakdown}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ category, percentage }) => percentage > 5 ? `${category} ${percentage.toFixed(1)}%` : ''}
                    outerRadius={120}
                    innerRadius={60}
                    fill="#8884d8"
                    dataKey="volume"
                    nameKey="category"
                  >
                    {trends.category_breakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div style={{
                            backgroundColor: 'rgba(0, 0, 0, 0.9)',
                            padding: '12px',
                            borderRadius: '8px',
                            border: '1px solid rgba(0, 102, 255, 0.5)'
                          }}>
                            <p style={{ color: 'white', margin: '0 0 8px 0', fontWeight: 'bold' }}>{data.category}</p>
                            <p style={{ color: '#0066ff', margin: '4px 0', fontSize: '14px' }}>
                              Volume: ${data.volume.toLocaleString()}
                            </p>
                            <p style={{ color: '#00b4d8', margin: '4px 0', fontSize: '14px' }}>
                              Count: {data.count.toLocaleString()}
                            </p>
                            <p style={{ color: '#90e0ef', margin: '4px 0', fontSize: '14px' }}>
                              Share: {data.percentage.toFixed(1)}%
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Legend for Pie Chart */}
          <div>
            <h3 style={{ color: 'white', marginBottom: '20px' }}>Market Breakdown</h3>
            <p style={{ color: 'rgba(100, 149, 237, 0.8)', marginBottom: '15px', fontSize: '14px' }}>
              Detailed statistics by category
            </p>
            <div style={{ backgroundColor: 'rgba(0, 102, 255, 0.05)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(0, 102, 255, 0.2)' }}>
              {trends.category_breakdown.map((cat, index) => (
                <div
                  key={cat.category}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '12px',
                    marginBottom: '8px',
                    backgroundColor: 'rgba(0, 102, 255, 0.05)',
                    borderRadius: '8px',
                    border: '1px solid rgba(0, 102, 255, 0.1)'
                  }}
                >
                  <div
                    style={{
                      width: '16px',
                      height: '16px',
                      backgroundColor: COLORS[index % COLORS.length],
                      borderRadius: '4px',
                      marginRight: '12px'
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ color: 'white', fontWeight: 'bold', marginBottom: '4px' }}>
                      {cat.category}
                    </div>
                    <div style={{ color: 'rgba(100, 149, 237, 0.8)', fontSize: '13px' }}>
                      ${cat.volume.toLocaleString()} • {cat.count.toLocaleString()} payouts • {cat.percentage.toFixed(1)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Ecosystem Growth Curve - Combined Metric Line Chart */}
        <div style={{ marginBottom: '40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ color: 'white', marginBottom: '8px' }}>Ecosystem Growth Curve</h3>
              <p style={{ color: 'rgba(100, 149, 237, 0.8)', fontSize: '14px' }}>
                Combined payouts count + volume over time
              </p>
            </div>
            {/* Time Period Selector */}
            <div style={{ display: 'flex', gap: '10px' }}>
              {['week', 'month', 'year'].map(period => (
                <button
                  key={period}
                  onClick={() => {
                    setGrowthPeriod(period);
                    if (onPeriodChange) onPeriodChange(period);
                  }}
                  style={{
                    padding: '10px 20px',
                    borderRadius: '8px',
                    border: growthPeriod === period
                      ? '2px solid #0066ff'
                      : '1px solid rgba(0, 102, 255, 0.3)',
                    backgroundColor: growthPeriod === period
                      ? 'rgba(0, 102, 255, 0.2)'
                      : 'rgba(0, 102, 255, 0.05)',
                    color: growthPeriod === period ? '#0066ff' : 'rgba(100, 149, 237, 0.8)',
                    cursor: 'pointer',
                    fontWeight: growthPeriod === period ? 'bold' : 'normal',
                    textTransform: 'capitalize',
                    transition: 'all 0.2s ease',
                    backdropFilter: 'blur(10px)'
                  }}
                  onMouseEnter={(e) => {
                    if (growthPeriod !== period) {
                      e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.1)';
                      e.target.style.borderColor = 'rgba(0, 102, 255, 0.5)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (growthPeriod !== period) {
                      e.target.style.backgroundColor = 'rgba(0, 102, 255, 0.05)';
                      e.target.style.borderColor = 'rgba(0, 102, 255, 0.3)';
                    }
                  }}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>
          <div 
            ref={growthChartRef}
            style={{ 
              backgroundColor: 'rgba(0, 102, 255, 0.05)', 
              padding: '20px', 
              borderRadius: '12px', 
              border: '1px solid rgba(0, 102, 255, 0.2)'
            }}
          >
            {growthChartVisible && (
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={trends.growth_curve}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                <XAxis
                  dataKey={growthPeriod}
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  stroke="rgba(100, 149, 237, 0.7)"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => {
                    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                    if (value >= 1000) return `${(value / 1000).toFixed(0)}k`;
                    return value.toFixed(0);
                  }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div style={{
                          backgroundColor: 'rgba(0, 0, 0, 0.9)',
                          padding: '12px',
                          borderRadius: '8px',
                          border: '1px solid rgba(0, 102, 255, 0.5)',
                          backdropFilter: 'blur(10px)'
                        }}>
                          <p style={{ color: 'white', margin: '0 0 8px 0', fontWeight: 'bold' }}>{label}</p>
                          <p style={{ color: '#0066ff', margin: '4px 0', fontSize: '14px' }}>
                            Combined Metric: {payload[0].value.toLocaleString()}
                          </p>
                          <p style={{ color: '#00b4d8', margin: '4px 0', fontSize: '13px' }}>
                            (Count: {data.cumulative_count?.toLocaleString() || 'N/A'})
                          </p>
                          <p style={{ color: '#90e0ef', margin: '4px 0', fontSize: '13px' }}>
                            (Volume: ${data.cumulative_volume?.toLocaleString() || 'N/A'})
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend
                  wrapperStyle={{
                    paddingTop: '20px',
                    color: 'rgba(100, 149, 237, 0.9)'
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="combined"
                  stroke="#0066ff"
                  strokeWidth={3}
                  dot={{ fill: '#0066ff', r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Combined Growth (Count + Volume)"
                />
              </LineChart>
            </ResponsiveContainer>
            )}
          </div>
        </div>
      </Section>
    </div>
  );
};

// SECTION 3: Global Highlights & Records Component
const GlobalHighlights = ({ highlights }) => {
  if (!highlights) return null;

  const {
    largest_payout_this_month,
    fastest_growing_server,
    milestone_message,
    seven_day_trends,
    submission_heat_score
  } = highlights;

  // Helper to get color based on percentage change
  const getChangeColor = (percent) => {
    if (percent > 0) return '#00ff88'; // Green
    if (percent < 0) return '#ff4444'; // Red
    return '#90e0ef'; // Blue (neutral)
  };

  // Helper to get heat score color
  const getHeatColor = (score) => {
    if (score === 'High Activity') return '#00ff88';
    if (score === 'Cooling') return '#ff4444';
    return '#90e0ef';
  };

  return (
    <div>
      <Section title="Global Highlights & Records">
        <p style={{ color: 'rgba(100, 149, 237, 0.9)', marginBottom: '30px', fontSize: '16px' }}>
          Stats that tell the Aurevia story
        </p>

        {/* Top Row: Largest Payout, Fastest Growing Server, Milestone */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '30px' }}>

          {/* Largest Payout This Month */}
          <div style={{
            backgroundColor: 'rgba(0, 102, 255, 0.05)',
            padding: '30px',
            borderRadius: '12px',
            border: '2px solid rgba(0, 102, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            textAlign: 'center',
            transition: 'all 0.3s ease',
            cursor: 'pointer'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 102, 255, 0.6)';
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'none';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.3)';
            }}>
            <div style={{ fontSize: '14px', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Largest Payout This Month
            </div>
            <div style={{ fontSize: '48px', fontWeight: 'bold', marginBottom: '10px' }}>
              ${largest_payout_this_month.toLocaleString()}
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(100, 149, 237, 0.6)' }}>
              Single transaction record
            </div>
          </div>

          {/* Fastest Growing Server */}
          <div style={{
            backgroundColor: 'rgba(0, 102, 255, 0.05)',
            padding: '30px',
            borderRadius: '12px',
            border: '2px solid rgba(0, 102, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            textAlign: 'center',
            transition: 'all 0.3s ease',
            cursor: 'pointer'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 102, 255, 0.6)';
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'none';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.3)';
            }}>
            <div style={{ fontSize: '14px', color: 'rgba(100, 149, 237, 0.8)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Fastest Growing Server
            </div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '10px', wordBreak: 'break-word' }}>
              {fastest_growing_server}
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(100, 149, 237, 0.6)' }}>
              Most new payouts this month
            </div>
          </div>

          {/* Milestone Badge */}
          <div style={{
            backgroundColor: milestone_message ? 'rgba(0, 255, 136, 0.1)' : 'rgba(0, 102, 255, 0.05)',
            padding: '30px',
            borderRadius: '12px',
            border: milestone_message ? '2px solid rgba(0, 255, 136, 0.5)' : '2px solid rgba(0, 102, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            cursor: 'pointer'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = 'rgba(0, 102, 255, 0.6)';
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'none';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.6)';
            }}>
            {milestone_message ? (
              <>
                <div style={{ fontSize: '16px', fontWeight: 'bold', lineHeight: '1.5' }}>
                  {milestone_message}
                </div>
              </>
            ) : (
              <div style={{ fontSize: '14px', color: 'rgba(100, 149, 237, 0.6)' }}>
                No new milestones reached yet
              </div>
            )}
          </div>
        </div>

        {/* Bottom Row: 7-Day Trends & Heat Score */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>

          {/* 7-Day Trend Summary */}
          <div style={{
            backgroundColor: 'rgba(0, 102, 255, 0.05)',
            padding: '30px',
            borderRadius: '12px',
            border: '2px solid rgba(0, 102, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.3s ease',
            cursor: 'pointer'
          }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 102, 255, 0.6)';
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'none';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.3)';
            }}>
            <h3 style={{ color: 'white', marginBottom: '20px', fontSize: '20px' }}>7-Day Trend Summary</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

              {/* Payouts This Week */}
              <div>
                <div style={{ fontSize: '14px', color: 'rgba(100, 149, 237, 0.8)', marginBottom: '8px' }}>
                  Total Payouts This Week
                </div>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginBottom: '5px' }}>
                  {seven_day_trends.this_week_payouts.toLocaleString()}
                </div>
                <div style={{
                  fontSize: '14px',
                  color: getChangeColor(seven_day_trends.payouts_change_percent),
                  fontWeight: 'bold'
                }}>
                  {seven_day_trends.payouts_change_percent > 0 ? '↑' : seven_day_trends.payouts_change_percent < 0 ? '↓' : '→'}
                  {' '}
                  {Math.abs(seven_day_trends.payouts_change_percent).toFixed(1)}% vs last week
                </div>
              </div>

              {/* Volume This Week */}
              <div>
                <div style={{ fontSize: '14px', color: 'rgba(100, 149, 237, 0.8)', marginBottom: '8px' }}>
                  Volume This Week
                </div>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'white', marginBottom: '5px' }}>
                  ${seven_day_trends.this_week_volume.toLocaleString()}
                </div>
                <div style={{
                  fontSize: '14px',
                  color: getChangeColor(seven_day_trends.volume_change_percent),
                  fontWeight: 'bold'
                }}>
                  {seven_day_trends.volume_change_percent > 0 ? '↑' : seven_day_trends.volume_change_percent < 0 ? '↓' : '→'}
                  {' '}
                  {Math.abs(seven_day_trends.volume_change_percent).toFixed(1)}% vs last week
                </div>
              </div>
            </div>
          </div>

          {/* Submission Heat Score */}
          <div style={{
            backgroundColor: 'rgba(0, 102, 255, 0.05)',
            padding: '30px',
            borderRadius: '12px',
            border: '2px solid rgba(0, 102, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            cursor: 'pointer'
          }}
            onMouseEnter={(e) => {
              const color = submission_heat_score === 'High Activity' ? 'rgba(0, 255, 136, 0.6)' :
                submission_heat_score === 'Cooling' ? 'rgba(255, 68, 68, 0.6)' :
                  'rgba(144, 224, 239, 0.6)';
              e.currentTarget.style.boxShadow = `0 0 30px ${color}`;
              e.currentTarget.style.transform = 'translateY(-5px)';
              e.currentTarget.style.borderColor = color.replace('0.6', '0.8');
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'none';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.borderColor = 'rgba(0, 102, 255, 0.3)';
            }}>
            <div style={{ fontSize: '14px', color: 'rgba(100, 149, 237, 0.8)', marginBottom: '15px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Submission Activity
            </div>
            <div style={{
              fontSize: '24px',
              fontWeight: 'bold',
              color: getHeatColor(submission_heat_score),
              marginBottom: '10px'
            }}>
              {submission_heat_score}
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(100, 149, 237, 0.6)' }}>
              Platform heat indicator
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
};

const AwardCard = ({ icon, title, winner, metric, value }) => (
  <div className="award-card">
    <div className="trophy">{icon}</div>
    <h3 className="category">{title}</h3>
    {winner ? (
      <>
        <div className="winner">
          {winner.profile_url ? (
            <Link 
              to={winner.profile_url}
              style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              {winner.name}
            </Link>
          ) : (
            winner.name
          )}
        </div>
        <div className="details">{metric}</div>
        <div className="winner">
          {typeof value === 'number' ? `$${value.toLocaleString()}` : value}
        </div>
      </>
    ) : (
      <div style={{ fontSize: '16px', color: 'rgba(100, 149, 237, 0.7)' }}>No data available</div>
    )}
  </div>
);

const HistoricalAwards = ({ data }) => {
  if (!data || data.length === 0) {
    return <div style={{ padding: '20px', textAlign: 'center', color: 'rgba(100, 149, 237, 0.8)' }}>No historical data available</div>;
  }

  return (
    <div style={{ overflowX: 'auto', backgroundColor: 'rgba(0, 102, 255, 0.002)', borderRadius: '8px', backdropFilter: 'blur(10px)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: 'rgba(0, 102, 255, 0.002)', backdropFilter: 'blur(10px)' }}>
        <thead>
          <tr style={{ backgroundColor: 'rgba(0, 102, 255, 0.05)', backdropFilter: 'blur(10px)' }}>
            <th style={{ padding: '12px', textAlign: 'left' }}>Month</th>
            <th style={{ padding: '12px', textAlign: 'left' }}>Server of Month</th>
            <th style={{ padding: '12px', textAlign: 'left' }}>Trader of Month</th>
            <th style={{ padding: '12px', textAlign: 'left' }}>Rising Star</th>
          </tr>
        </thead>
        <tbody>
          {data.map((entry, index) => (
            <tr key={`${entry.month}-${index}`} style={{ backgroundColor: 'rgba(0, 102, 255, 0.005)', transition: 'all 0.3s ease', backdropFilter: 'blur(10px)', borderRadius: '8px' }}>
              <td style={{ padding: '12px', fontWeight: 'bold' }}>{entry.month}</td>
              <td style={{ padding: '12px' }}>{entry.server}</td>
              <td style={{ padding: '12px' }}>{entry.trader}</td>
              <td style={{ padding: '12px' }}>{entry.rising_star}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Analytics;
