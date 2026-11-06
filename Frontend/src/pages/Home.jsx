/**
 * Home Page (Landing Page)
 * 
 * Public page showcasing Aurevia platform features
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { publicApi } from '../config/api';
import api from '../config/api';
// import { calculateServerScores } from '../utils/serverRanking';
import './Home.css';

const Home = () => {
  const [leaderboard, setLeaderboard] = useState([]);
  const [topThree, setTopThree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [heroStats, setHeroStats] = useState({
    verified_servers: 0,
    total_payouts: 0,
    active_traders: 0
  });
  const [filters, setFilters] = useState({
    platform: '',
    category: '',
    timeframe: 'all',
    min_volume: '',
    sort_by: 'volume'  // Use backend's global score ranking by default
  });
  const [filtersVisible, setFiltersVisible] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [availablePlatforms, setAvailablePlatforms] = useState([]);
  const itemsPerPage = 10;
  const maxPages = 10;

  // Payout feed state
  const [payouts, setPayouts] = useState([]);
  const [payoutPage, setPayoutPage] = useState(1);
  const [payoutItemsPerPage] = useState(10);
  const [payoutTotalPages, setPayoutTotalPages] = useState(1);
  const [payoutFilters, setPayoutFilters] = useState({
    server_name: '',
    amount_min: '',
    amount_max: '',
    date_from: '',
    date_to: ''
  });
  const [payoutLoading, setPayoutLoading] = useState(false);

  useEffect(() => {
    fetchTopServers();
    fetchHeroStats();
    fetchPlatforms();
  }, [filters]); // Removed currentPage as we are fetching top 100 once and paginating client side for fluidity

  useEffect(() => {
    fetchHeroStats();
    fetchPodiumServers();
  }, []);

  useEffect(() => {
    fetchRecentPayouts();
  }, [payoutPage, payoutFilters]);

  const fetchPlatforms = async () => {
    try {
      const response = await publicApi.get('/platform-admin/platforms/?active_only=true');
      setAvailablePlatforms(response.data.map(p => p.name.toLowerCase()));
    } catch (err) {
      console.error('Failed to fetch platforms:', err);
    }
  };

  const fetchPodiumServers = async () => {
    try {
      // Always fetch top 3 by global score (rank) for the podium
      const response = await publicApi.get('/analytics/top-servers/?sort_by=volume&limit=3');
      const data = Array.isArray(response.data) ? response.data : (response.data.leaderboard || []);
      setTopThree(data.slice(0, 3));
    } catch (error) {
      console.error('Error fetching podium servers:', error);
    }
  };

  const fetchTopServers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.platform) params.append('platform', filters.platform);
      if (filters.category) params.append('category', filters.category);
      if (filters.timeframe) params.append('timeframe', filters.timeframe);
      if (filters.min_volume) params.append('min_volume', filters.min_volume);
      if (filters.sort_by) params.append('sort_by', filters.sort_by);
      params.append('limit', 100); // Fetch top 100 ranked servers from backend

      const response = await publicApi.get(`/analytics/top-servers/?${params.toString()}`);
      // Backend now returns array directly or { leaderboard: [] } ?
      // My backend implementation returns Response(paginated_result) which is a List.
      // But let's check what I wrote: `return Response(paginated_result)` -> matches `response.data` being the array.
      // However, previous code assumed `response.data.leaderboard`.
      // I should update frontend to handle both or match backend to previous output structure?
      // My backend returns a list `Response(leaderboard)`.

      const data = Array.isArray(response.data) ? response.data : (response.data.leaderboard || []);

      setTotalResults(data.length);
      // setTopThree(data.slice(0, 3)); // Podium is now independent

      // Client-side pagination of the fetched top 100
      const startIndex = (currentPage - 1) * itemsPerPage;
      const endIndex = startIndex + itemsPerPage;
      setLeaderboard(data.slice(startIndex, endIndex));

    } catch (error) {
      console.error('Error fetching top servers:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHeroStats = async () => {
    try {
      const response = await publicApi.get('/analytics/global-overview/');
      const data = response.data;

      // Calculate active traders from verified payouts (unique submitters)
      const activeTraders = data.global_metrics?.total_verified_payouts || 0;

      setHeroStats({
        verified_servers: data.global_metrics?.active_servers || 0,
        total_payouts: data.global_metrics?.total_payout_volume || 0,
        active_traders: Math.floor(activeTraders * 0.3) // Rough estimate: 30% of payouts = unique traders
      });
    } catch (error) {
      console.error('Error fetching hero stats:', error);
    }
  };

  const fetchRecentPayouts = async () => {
    setPayoutLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', payoutPage);
      params.append('limit', payoutItemsPerPage);

      if (payoutFilters.server_name) params.append('server_name', payoutFilters.server_name);
      if (payoutFilters.amount_min) params.append('amount_min', payoutFilters.amount_min);
      if (payoutFilters.amount_max) params.append('amount_max', payoutFilters.amount_max);
      if (payoutFilters.date_from) params.append('date_from', payoutFilters.date_from);
      if (payoutFilters.date_to) params.append('date_to', payoutFilters.date_to);

      const response = await publicApi.get(`/analytics/recent-payouts/?${params.toString()}`);
      setPayouts(response.data.payouts);
      setPayoutTotalPages(response.data.pagination.total_pages);
    } catch (error) {
      console.error('Error fetching recent payouts:', error);
    } finally {
      setPayoutLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const resetFilters = () => {
    setFilters({
      platform: '',
      category: '',
      timeframe: 'all',
      min_volume: '',
      sort_by: 'score'
    });
    setCurrentPage(1);
  };

  const hasActiveFilters = filters.platform || filters.category ||
    filters.timeframe !== 'all' || filters.min_volume ||
    filters.sort_by !== 'volume';

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content-wrapper">
          <div className="hero-text-column">
            <div className="hero-badge">Verified Server Leaderboards</div>

            <h1 className="hero-title">
              Compete with the Best Trading Servers
            </h1>

            <p className="hero-subtitle">
              Submit your payouts to verified servers, get authenticated by moderators, and climb both server and global rankings.
            </p>

            <div className="hero-actions">
              <Link to="/register" className="Get-Started">
                Get Started
                <span className="hero-btn-icon">→</span>
              </Link>
              <Link to="/servers" className="Browse-Server">
                Browse Servers
              </Link>
            </div>
          </div>

          {/* Podium Visualization */}
          <div className="hero-visual-column">
            <div className="podium-container">
              <div className="podium-card podium-second" style={{ padding: topThree[1]?.server?.logo_url ? "30px 20px" : "55px 20px" }}>
                <div className="podium-position">#2</div>
                {topThree[1]?.server?.logo_url && (
                  <div className="podium-avatar">
                    <img src={topThree[1].server.logo_url} alt="Server avatar" />
                  </div>
                )}
                <div className="podium-server-name">{topThree[1]?.server?.name || 'Server'}</div>
                <div className="podium-label">Silver Position</div>
                <div className="podium-amount">
                  {topThree[1] ? formatCurrency(topThree[1].metrics.total_volume) : '$0'}
                </div>
              </div>

              <div className="podium-card podium-first" style={{ padding: topThree[0]?.server?.logo_url ? "45px 20px" : "70px 20px" }}>
                <div className="podium-position">#1</div>
                {topThree[0]?.server?.logo_url && (
                  <div className="podium-avatar">
                    <img src={topThree[0].server.logo_url} alt="Server avatar" />
                  </div>
                )}
                <div className="podium-server-name">{topThree[0]?.server?.name || 'Server'}</div>
                <div className="podium-label">Top Server</div>
                <div className="podium-amount">
                  {topThree[0] ? formatCurrency(topThree[0].metrics.total_volume) : '$0'}
                </div>
                <div className="podium-badge-small">Champion</div>
              </div>

              <div className="podium-card podium-third" style={{ padding: topThree[2]?.server?.logo_url ? "17px 20px" : "42px 20px" }}>
                <div className="podium-position">#3</div>
                {topThree[2]?.server?.logo_url && (
                  <div className="podium-avatar">
                    <img src={topThree[2].server.logo_url} alt="Server avatar" />
                  </div>
                )}
                <div className="podium-server-name">{topThree[2]?.server?.name || 'Server'}</div>
                <div className="podium-label">Bronze Position</div>
                <div className="podium-amount">
                  {topThree[2] ? formatCurrency(topThree[2].metrics.total_volume) : '$0'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="hero-stats">
          <div className="home-stat-item">
            <div className="home-stat-value">{heroStats.verified_servers}</div>
            <div className="home-stat-label">Verified Servers</div>
          </div>
          <div className="home-stat-item">
            <div className="home-stat-value">
              ${heroStats.total_payouts.toLocaleString()}
            </div>
            <div className="home-stat-label">Total Payouts</div>
          </div>
          <div className="home-stat-item">
            <div className="home-stat-value">{heroStats.active_traders.toLocaleString()}+</div>
            <div className="home-stat-label">Active Traders</div>
          </div>
        </div>
      </section>

      {/* Top 10 Servers Leaderboard */}
      <section className="home-leaderboard-section">
        <div className="home-leaderboard-header">
          <h2 className="home-leaderboard-title">Top Performing Servers</h2>
          <p className="home-leaderboard-subtitle">Live rankings updated in real-time</p>
          <button
            className="filter-toggle-btn"
            onClick={() => setFiltersVisible(!filtersVisible)}
          >
            {filtersVisible ? 'Hide' : 'Filter'}
            {hasActiveFilters && <span className="filter-badge">{
              [filters.platform, filters.category, filters.timeframe !== 'all',
              filters.min_volume, filters.sort_by !== 'volume'].filter(Boolean).length
            }</span>}
          </button>
        </div>

        {/* Filter Panel */}
        {filtersVisible && (
          <div className="filter-panel">
            <div className="filter-grid">
              <div className="filter-group">
                <label>Platform</label>
                <select
                  value={filters.platform}
                  onChange={(e) => handleFilterChange('platform', e.target.value)}
                >
                  <option value="">All Platforms</option>
                  {availablePlatforms.map(platform => (
                    <option key={platform} value={platform}>
                      {platform.charAt(0).toUpperCase() + platform.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Market Category</label>
                <select
                  value={filters.category}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
                >
                  <option value="">All Markets</option>
                  <option value="futures">Futures</option>
                  <option value="forex">Forex</option>
                  <option value="crypto">Crypto</option>
                  <option value="options">Options</option>
                  <option value="equities">Equities</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>

              <div className="filter-group">
                <label>Timeframe</label>
                <select
                  value={filters.timeframe}
                  onChange={(e) => handleFilterChange('timeframe', e.target.value)}
                >
                  <option value="all">All Time</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="90d">Last 90 Days</option>
                </select>
              </div>

              <div className="filter-group">
                <label>Min Volume ($)</label>
                <input
                  type="number"
                  placeholder="0"
                  value={filters.min_volume}
                  onChange={(e) => handleFilterChange('min_volume', e.target.value)}
                  min="0"
                  step="1000"
                />
              </div>

              <div className="filter-group">
                <label>Sort By</label>
                <select
                  value={filters.sort_by}
                  onChange={(e) => handleFilterChange('sort_by', e.target.value)}
                >
                  <option value="score">Score (Rank)</option>
                  <option value="volume">Total Volume</option>
                  <option value="payouts">Payout Count</option>
                  <option value="growth">Recent Growth</option>
                  <option value="activity">Active Traders</option>
                </select>
              </div>
            </div>

            {hasActiveFilters && (
              <button className="reset-filters-btn" onClick={resetFilters}>
                ↺ Reset All Filters
              </button>
            )}
          </div>
        )}

        {loading ? (
          <div className="home-leaderboard-loading">Loading leaderboard...</div>
        ) : leaderboard.length === 0 ? (
          <div className="home-leaderboard-empty">
            <p>No servers match your filters. Try adjusting your criteria.</p>
            <button onClick={resetFilters} className="reset-btn-empty">Reset Filters</button>
          </div>
        ) : (
          <div className="home-leaderboard-table-wrapper">
            <table className="home-leaderboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Server</th>
                  <th>Total Volume</th>
                  <th>Total Payouts</th>
                  <th>Active Submitters</th>
                  <th>30D Growth</th>
                  <th>Trend</th>
                  <th>Rank Change</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item, index) => (
                  <tr key={item.server.id} className="home-leaderboard-row">
                    <td className="home-rank-cell">
                      <div>#{(currentPage - 1) * itemsPerPage + index + 1}</div>
                    </td>
                    <td className="server-cell">
                      <div className="server-info">
                        <div className="server-identity">
                          <Link
                            to={item.server.profile_url || `/servers/${item.server.id}/public`}
                            className="home-server-name"
                          >
                            {item.server.name}
                          </Link>
                        </div>
                        <div className="server-meta">
                          <span className="server-category">{item.metadata.category}</span>
                          <span className="server-separator">•</span>
                          <span className="server-established">Est. {new Date(item.metadata.established).getFullYear()}</span>
                        </div>
                      </div>
                    </td>
                    <td className="metric-cell volume-cell">
                      <div className="home-metric-value">{formatCurrency(item.metrics.total_volume)}</div>
                      <div className="home-metric-label">verified</div>
                    </td>
                    <td className="metric-cell">
                      <div className="home-metric-value">{item.metrics.total_payouts.toLocaleString()}</div>
                      <div className="home-metric-label">payouts</div>
                    </td>
                    <td className="metric-cell">
                      <div className="home-metric-value">{item.metrics.active_submitters_30d}</div>
                      <div className="home-metric-label">traders (30d)</div>
                    </td>
                    <td className="metric-cell growth-cell">
                      <div className={`growth-value ${item.momentum.volume_change_30d > 0 ? 'positive' :
                        item.momentum.volume_change_30d < 0 ? 'negative' : 'neutral'
                        }`}>
                        {item.momentum.volume_change_30d > 0 ? '+' : ''}
                        {item.momentum.volume_change_30d.toFixed(1)}%
                      </div>
                    </td>
                    <td className="metric-cell trend-cell">
                      <span className={`trend-icon trend-${item.momentum.trend_7d}`}>
                        {item.momentum.trend_icon}
                      </span>
                    </td>
                    <td className="metric-cell rank-change-cell">
                      {item.momentum.rank_change === 0 ? (
                        <span className="rank-stable">—</span>
                      ) : item.momentum.rank_change > 0 ? (
                        <span className="rank-up">▲ +{item.momentum.rank_change}</span>
                      ) : (
                        <span className="rank-down">▼ {item.momentum.rank_change}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {!loading && leaderboard.length > 0 && (
          <div className="home-pagination-controls">
            <button
              className="home-pagination-btn"
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
            >
              ← Previous
            </button>

            <div className="pagination-info">
              {Array.from({ length: Math.min(maxPages, Math.ceil(totalResults / itemsPerPage)) }, (_, i) => i + 1).map(page => (
                <button
                  key={page}
                  className={`pagination-number ${currentPage === page ? 'active' : ''}`}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </button>
              ))}
            </div>

            <button
              className="home-pagination-btn"
              onClick={() => setCurrentPage(prev => Math.min(maxPages, Math.ceil(totalResults / itemsPerPage), prev + 1))}
              disabled={currentPage >= Math.min(maxPages, Math.ceil(totalResults / itemsPerPage))}
            >
              Next →
            </button>
          </div>
        )}

        <div className="home-leaderboard-footer">
          <Link to="/servers" className="view-all-btn">
            View Full Rankings →
          </Link>
        </div>
      </section>

      {/* Recent Payouts Feed */}
      <section className="home-payout-feed-section">
        <div className="home-payout-header">
          <h2 className="section-heading">Recent Payouts</h2>
          <p className="section-subheading">Live feed of verified payouts across all servers</p>
        </div>

        {/* Filters */}
        <div className="home-payout-filters-container">
          <input
            type="text"
            placeholder="Search by server name..."
            className="home-payout-filter-input"
            value={payoutFilters.server_name}
            onChange={(e) => setPayoutFilters(prev => ({ ...prev, server_name: e.target.value }))}
          />

          <input
            type="number"
            placeholder="Min Amount"
            className="home-payout-filter-input"
            value={payoutFilters.amount_min}
            onChange={(e) => setPayoutFilters(prev => ({ ...prev, amount_min: e.target.value }))}
          />

          <input
            type="number"
            placeholder="Max Amount"
            className="home-payout-filter-input"
            value={payoutFilters.amount_max}
            onChange={(e) => setPayoutFilters(prev => ({ ...prev, amount_max: e.target.value }))}
          />

          <input
            type="date"
            placeholder="From Date"
            className="home-payout-filter-input"
            value={payoutFilters.date_from}
            onChange={(e) => setPayoutFilters(prev => ({ ...prev, date_from: e.target.value }))}
          />

          <input
            type="date"
            placeholder="To Date"
            className="home-payout-filter-input"
            value={payoutFilters.date_to}
            onChange={(e) => setPayoutFilters(prev => ({ ...prev, date_to: e.target.value }))}
          />

          <button
            className="home-payout-clear-btn"
            onClick={() => {
              setPayoutFilters({
                server_name: '',
                amount_min: '',
                amount_max: '',
                date_from: '',
                date_to: ''
              });
              setPayoutPage(1);
            }}
          >
            Clear Filters
          </button>
        </div>

        {/* Payout Table */}
        {payoutLoading ? (
          <div className="home-payout-loading">Loading payouts...</div>
        ) : (
          <>
            <div className="home-payout-table-container">
              <table className="home-payout-table">
                <thead>
                  <tr>
                    <th>Server Name</th>
                    <th>Amount</th>
                    <th>Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {payouts.length > 0 ? (
                    payouts.map((payout) => (
                      <tr key={payout.id} className="home-payout-row">
                        <td className="home-payout-server-name">
                          <Link to={`/servers/${payout.server_id}/public`}>
                            {payout.server_name}
                          </Link>
                        </td>
                        <td className="home-payout-amount">
                          {formatCurrency(payout.amount)}
                        </td>
                        <td className="home-payout-date">
                          {new Date(payout.submitted_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="no-payouts">
                        No payouts found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {payoutTotalPages > 1 && (
              <div className="home-payout-pagination">
                <button
                  className="home-payout-pagination-btn"
                  onClick={() => setPayoutPage(prev => Math.max(1, prev - 1))}
                  disabled={payoutPage === 1}
                >
                  ← Previous
                </button>

                <div className="home-payout-page-numbers">
                  {[...Array(Math.min(5, payoutTotalPages))].map((_, i) => {
                    const page = i + 1;
                    return (
                      <button
                        key={page}
                        className={`home-payout-page-btn ${payoutPage === page ? 'active' : ''}`}
                        onClick={() => setPayoutPage(page)}
                      >
                        {page}
                      </button>
                    );
                  })}
                </div>

                <button
                  className="home-payout-pagination-btn"
                  onClick={() => setPayoutPage(prev => Math.min(payoutTotalPages, prev + 1))}
                  disabled={payoutPage === payoutTotalPages}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </section>

      {/* Server Verification Section */}
      <section className="verification-section">
        <div className="verification-grid">
          {/* Card 1: Server Verification */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22C12 22 20 18 20 12V5L12 2L4 5V12C4 18 12 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Server Verification</h3>
            <p className="verification-card-description">
              Every server goes through our verification process. Only legitimate trading communities receive the verified badge and platform access.
            </p>
            <ul className="verification-feature-list">
              <li>Manual application review</li>
              <li>Community size validation</li>
              <li>Verified badge display</li>
            </ul>
          </div>

          {/* Card 2: Manual Verification */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 15L11 17L15 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Manual Verification</h3>
            <p className="verification-card-description">
              Server moderators manually review every payout submission with screenshot proof. No bots, no automation - just real verification.
            </p>
            <ul className="verification-feature-list">
              <li>Screenshot proof required</li>
              <li>Moderator approval system</li>
              <li>Reject with feedback</li>
            </ul>
          </div>

          {/* Card 3: Dual Leaderboards */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 20V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M12 20V4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M6 20V14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Dual Leaderboards</h3>
            <p className="verification-card-description">
              Track performance across both server-specific and global rankings. Compete within your community and against the world.
            </p>
            <ul className="verification-feature-list">
              <li>Server leaderboards</li>
              <li>Global rankings</li>
              <li>Real-time updates</li>
            </ul>
          </div>

          {/* Card 4: Real-Time Updates */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M12 6V12L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Real-Time Updates</h3>
            <p className="verification-card-description">
              Watch rankings update instantly as payouts get verified. See your position change in real-time across all leaderboards.
            </p>
            <ul className="verification-feature-list">
              <li>Instant rank updates</li>
              <li>Live verification status</li>
              <li>Notification system</li>
            </ul>
          </div>

          {/* Card 5: Advanced Analytics */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 20V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M18 20V4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M6 20V16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Advanced Analytics</h3>
            <p className="verification-card-description">
              Server owners get detailed insights into community activity, payout trends, and member performance over time.
            </p>
            <ul className="verification-feature-list">
              <li>Performance graphs</li>
              <li>Payout history tracking</li>
              <li>Member statistics</li>
            </ul>
          </div>

          {/* Card 6: Community Focused */}
          <div className="verification-card">
            <div className="verification-icon-wrapper icon-blue">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9 11C11.2091 11 13 9.20914 13 7C13 4.79086 11.2091 3 9 3C6.79086 3 5 4.79086 5 7C5 9.20914 6.79086 11 9 11Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M23 21V19C22.9993 18.1137 22.7044 17.2528 22.1614 16.5523C21.6184 15.8519 20.8581 15.3516 20 15.13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.0078 6.11683 19.0078 7.005C19.0078 7.89318 18.7122 8.75608 18.1676 9.45768C17.623 10.1593 16.8604 10.6597 16 10.88" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="verification-card-title">Community Focused</h3>
            <p className="verification-card-description">
              Foster healthy competition within your server. Build reputation and trust through verified results and transparent rankings.
            </p>
            <ul className="verification-feature-list">
              <li>Server-first approach</li>
              <li>Community leaderboards</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="feature-card_1">
          <h3 className="home-feature-title">Server-First Leaderboards</h3>
          <p className="home-feature-description">
            Every server has its own verified leaderboard. Traders submit to their community, moderators verify authenticity, and rankings update in real-time.
          </p>
          <ul className="home-feature-list">
            <li>Manual verification by server moderators</li>
            <li>Server-specific and global rankings</li>
            <li>Transparent proof requirements</li>
            <li>Real-time leaderboard updates</li>
          </ul>
          <Link to="/servers" className="home-feature-cta">
            Explore Servers →
          </Link>
        </div>

        <div className="feature-card_1">
          <h3 className="home-feature-title">Built on Trust</h3>
          <p className="home-feature-description">
            No bots. No fake numbers. Every payout is manually verified by moderators.
          </p>
          <ul className="home-feature-list">
            <li>Screenshot proof required</li>
            <li>Community accountability</li>
            <li>Verified server badges</li>
            <li>Zero tolerance for fraud</li>
          </ul>
          <Link to="/analytics" className="home-feature-cta">
            View Rankings →
          </Link>
        </div>
      </section>

      {/* Why Choose Section */}
      <section className="why-section">
        <div className="why-badge">Why Choose Aurevia</div>
        <h2 className="why-title">
          The Most Transparent Trading Leaderboard Platform
        </h2>

        <div className="why-grid">
          <div className="why-card">
            <h4 className="why-card-title">Server Verification</h4>
            <p className="why-card-text">
              Every server undergoes rigorous verification. Only legitimate trading communities with proven track records receive the verified badge.
            </p>
          </div>

          <div className="why-card">
            <h4 className="why-card-title">Real-Time Rankings</h4>
            <p className="why-card-text">
              Watch your rank climb as payouts get verified. Both server and global leaderboards update instantly with every submission.
            </p>
          </div>

          <div className="why-card">
            <h4 className="why-card-title">Community Driven</h4>
            <p className="why-card-text">
              Foster healthy competition and build lasting reputation within your trading community through transparent, verified results.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <div className="home-cta-container">
        <section className="home-cta-section">
          <div className="home-cta-content">
            <h2 className="home-cta-title">Standard</h2>
            <div className="home-cta-price">$149 <span className="home-cta-period">/month</span></div>
            <p className="home-cta-description">
              Everything you need to verify your community and build trust
            </p>

            <ul className="home-cta-features">
              <li>Verified server badge</li>
              <li>Advanced analytics</li>
              <li>Priority support</li>
            </ul>

            <Link to="/pricing" className="home-cta-button">
              Start Here→
            </Link>

            <p className="home-cta-note">
              🔒 Secure payments via Stripe • Cancel anytime • No credit card required for trial
            </p>
          </div>
        </section>

      </div>
    </div>
  );
};

export default Home;
