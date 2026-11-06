/**
 * Server Public View
 * 
 * Public analytics page with restricted data to drive subscriptions.
 * Accessed via: /servers/:serverId/public
 * 
 * Shows LIMITED analytics:
 * - Top 3 traders only (vs 5-15 in subscriptions)
 * - Momentum icon + status only (no timeline)
 * - Health score only (no breakdown)
 * - Payout count only (no event list)
 * - All-time metrics only (no 7d/30d/90d)
 * - Health score: Overall score ONLY (no breakdown)
 * - Payout timeline: Count ONLY (no event list)
 * - Rank: Current rank ONLY (no progression)
 * - Extra stats: Basic (approval rate, monthly change %, time between)
 * - Bonus metrics: All-time stats ONLY (no 7d/30d/90d breakdowns)
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { serverService, analyticsService } from '../services';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import UpgradePrompt from '../components/UpgradePrompt';
import { useAuth } from '../context/AuthContext';
import './ServerPublicView.css';

const ServerPublicView = () => {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const { user, checkAuth } = useAuth();

  const [analytics, setAnalytics] = useState(null);
  const [server, setServer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedView, setSelectedView] = useState('overview');
  const [isMember, setIsMember] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [checkingMembership, setCheckingMembership] = useState(false);
  const [joiningServer, setJoiningServer] = useState(false);
  const [imageModal, setImageModal] = useState({ isOpen: false, imageUrl: null });

  useEffect(() => {
    if (serverId) {
      fetchPublicAnalytics();
      if (user) {
        checkMembershipStatus();
      }
    }
  }, [serverId, user]);

  const fetchPublicAnalytics = async () => {
    try {
      // Get public server dashboard data (no auth required)
      const dashboardData = await analyticsService.getPublicServerDashboard(serverId);
      setServer(dashboardData.server);
      setAnalytics(dashboardData);

      // Check if current user is the server owner
      if (user && dashboardData.server) {
        setIsOwner(dashboardData.server.owner_id === user.id);
      }
    } catch (error) {
      console.error('Error fetching public analytics:', error);
      setError('Failed to load server data');
    } finally {
      setLoading(false);
    }
  };

  const checkMembershipStatus = async () => {
    if (!user || !serverId) return;

    setCheckingMembership(true);
    try {
      console.log('🔍 Checking membership for server:', serverId, 'user:', user?.username);
      const response = await serverService.checkMembership(serverId);
      console.log('✅ Membership response:', response);
      setIsMember(response.is_member || false);
    } catch (error) {
      console.error('❌ Error checking membership:', error);
      setIsMember(false);
    } finally {
      setCheckingMembership(false);
    }
  };

  const handleJoinServer = async () => {
    if (!user) {
      return; // Button should be hidden if no user, but just in case
    }

    setJoiningServer(true);
    try {
      await serverService.joinServer(serverId);

      // Refresh user data to update permissions (is_member capability)
      await checkAuth();

      // Redirect to server dashboard after successful join
      navigate(`/servers/${serverId}`);
    } catch (error) {
      console.error('Error joining server:', error);

      // Show error message
      const errorMessage = error.response?.data?.error || 'Failed to join server. Please try again.';
      alert(errorMessage);

      setJoiningServer(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return 'rgba(0, 102, 255, 0.9)';
    if (score >= 40) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="server-view-loading">
        <div className="spinner"></div>
        <p>Loading server data...</p>
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="server-view-error">
        <h2>No Data Available</h2>
        <p>{error || 'Failed to load server data'}</p>
        <button onClick={() => navigate('/servers')} className="btn btn-secondary">
          ← Back to Servers
        </button>
      </div>
    );
  }

  const {
    server: serverData,
    stats,
    metrics_overview,
    graphs,
    breakdowns,
    rankings
  } = analytics;

  // Use backend-provided scores from rankings (same source as /servers page)
  // This ensures consistency across the platform
  const scores = rankings?.scores ? {
    ...rankings.scores,
    total: rankings.total_score || 0  // total_score is at root level of rankings
  } : null;

  // Prepare radar chart data (only if scores are available)
  const chartData = scores ? [
    { subject: 'Performance', value: Number((scores.performance || 0).toFixed(2)) },
    { subject: 'Growth', value: Number((scores.growth || 0).toFixed(2)) },
    { subject: 'Engagement', value: Number((scores.engagement || 0).toFixed(2)) },
    { subject: 'Quality', value: Number((scores.quality || 0).toFixed(2)) },
    { subject: 'Diversity', value: Number((scores.diversity || 0).toFixed(2)) }
  ] : [];

  // Compute badges based on server metrics
  const computeBadges = () => {
    const badges = {
      performance: [],
      consistency: [],
      community: []
    };

    // Performance Badges
    if (rankings?.global_rank) {
      if (rankings.global_rank <= 10) {
        badges.performance.push({ name: 'Top 10 Global', tier: 'legendary' });
      } else if (rankings.global_rank <= 50) {
        badges.performance.push({ name: 'Top 50 Global', tier: 'epic' });
      }
    }

    if (metrics_overview?.total_verified_volume) {
      const volume = metrics_overview.total_verified_volume;
      if (volume >= 1000000) {
        badges.performance.push({ name: '7-Figure Club', tier: 'legendary' });
      } else if (volume >= 500000) {
        badges.performance.push({ name: '500k Club', tier: 'epic' });
      } else if (volume >= 250000) {
        badges.performance.push({ name: '250k Club', tier: 'rare' });
      } else if (volume >= 100000) {
        badges.performance.push({ name: '100k Club', tier: 'uncommon', });
      }
    }

    // Consistency Badges
    if (metrics_overview?.active_submitters_30d >= 5) {
      badges.consistency.push({ name: '30-Day Activity', tier: 'rare' });
    }

    if (metrics_overview?.approval_rate_3m >= 80) {
      badges.consistency.push({ name: 'High Accuracy', tier: 'epic' });
    }

    if (metrics_overview?.growth_rate_30d >= 50) {
      badges.consistency.push({ name: 'Fastest Growing Server', tier: 'legendary' });
    }

    // Community Badges
    if (metrics_overview?.active_submitters_30d >= 10) {
      badges.community.push({ name: 'Active Trader Base', tier: 'rare' });
    }

    // Emerging Server: Created within last 6 months and has growth
    const serverCreatedDate = new Date(serverData.created_at);
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

    if (serverCreatedDate > sixMonthsAgo && metrics_overview?.growth_rate_30d > 0) {
      badges.community.push({ name: 'Emerging Server', tier: 'uncommon' });
    }

    return badges;
  };

  const badges = computeBadges();

  return (
    <div className="server-public-view">
      {/* Pokemon Card and Radar Chart Container */}
      <div className="pokemon-card-radar-container">
        {/* Pokemon Card Style Header */}
        <div className="pokemon-card-header">
          {/* Card Border Effect */}
          <div className="pokemon-card-border">
            <div className="pokemon-card-content">
              {/* Top Section: Logo, Title, and Metadata */}
              <div className="pokemon-card-top">
                <div className="pokemon-card-title-section">
                  <div className="server-logo-wrapper">
                    {serverData.logo_url ? (
                      <img src={serverData.logo_url} alt={serverData.name} className="pokemon-server-logo" />
                    ) : (
                      <div className="pokemon-logo-placeholder">
                        {serverData.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>

                  <div className="pokemon-card-title-info">
                    <div className="pokemon-title-row">
                      <h1 className="pokemon-server-name">{serverData.name}</h1>
                      {serverData.is_verified && (
                        <span className="pokemon-verified-badge">Verified</span>
                      )}
                    </div>

                    <div className="pokemon-metadata">
                      <span className="pokemon-platform">{serverData.platform}</span>
                      <span className="pokemon-meta-divider">•</span>
                      <span className="pokemon-established">
                        Est. {new Date(serverData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })}
                      </span>
                      {rankings?.global_rank && (
                        <>
                          <span className="pokemon-meta-divider">•</span>
                          <span className="pokemon-rank">Rank #{rankings.global_rank}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Overall Score Badge */}
                {scores && scores.total !== undefined && (
                  <div className="pokemon-score-badge">
                    <div className="pokemon-score-circle" style={{ borderColor: getScoreColor(scores.total) }}>
                      <div className="pokemon-score-value" style={{ color: getScoreColor(scores.total) }}>
                        {scores.total.toFixed(1)}
                      </div>
                      <div className="pokemon-score-label">Overall</div>
                    </div>
                  </div>
                )}
              </div>

              {/* Description */}
              {serverData.description && (
                <p className="pokemon-description">{serverData.description}</p>
              )}

              {/* Middle Section: Badges */}
              <div className="pokemon-badges-section">
                {(badges.performance.length > 0 || badges.consistency.length > 0 || badges.community.length > 0) ? (
                  <div className="badges-grid">
                    {badges.performance.map((badge, idx) => (
                      <div key={`perf-${idx}`} className={`server-badge badge-${badge.tier}`}>
                        {badge.name}
                      </div>
                    ))}
                    {badges.consistency.map((badge, idx) => (
                      <div key={`cons-${idx}`} className={`server-badge badge-${badge.tier}`}>
                        {badge.name}
                      </div>
                    ))}
                    {badges.community.map((badge, idx) => (
                      <div key={`comm-${idx}`} className={`server-badge badge-${badge.tier}`}>
                        {badge.name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-badges-message">
                    <span className="no-badges-text">No badges earned yet</span>
                  </div>
                )}
              </div>

              {/* Bottom Section: Market Categories and Stats */}
              <div className="pokemon-bottom-section">
                {serverData.market_categories && serverData.market_categories.length > 0 && (
                  <div className="pokemon-markets">
                    <span className="pokemon-markets-label">Markets:</span>
                    <div className="pokemon-market-tags">
                      {serverData.market_categories.map(cat => (
                        <span key={cat} className="pokemon-market-tag">{cat}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Quick Stats Bar */}
                {metrics_overview && (
                  <div className="pokemon-quick-stats">
                    <div className="pokemon-stat">
                      <span className="pokemon-stat-value">
                        ${metrics_overview.total_verified_volume.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                      </span>
                      <span className="pokemon-stat-label">Total Volume</span>
                    </div>
                    <div className="pokemon-stat">
                      <span className="pokemon-stat-value">{metrics_overview.verified_payout_count.toLocaleString()}</span>
                      <span className="pokemon-stat-label">Payouts</span>
                    </div>
                    <div className="pokemon-stat">
                      <span className="pokemon-stat-value">{metrics_overview.active_submitters_30d}</span>
                      <span className="pokemon-stat-label">Active Traders</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Holographic Shine Effect */}
              <div className="pokemon-card-shine"></div>
            </div>
          </div>
        </div>

        {/* Join Server Button Section */}
        {user && !isOwner && !isMember && (
          <div className="join-server-section">
            <button
              className="join-server-button"
              onClick={handleJoinServer}
              disabled={joiningServer || checkingMembership}
            >
              {joiningServer ? (
                <>
                  <span className="button-spinner"></span>
                  Joining...
                </>
              ) : (
                <>
                  <span className="join-icon">+</span>
                  Join Server
                </>
              )}
            </button>
            <p className="join-server-description">
              Join {serverData.name} to submit payouts and appear on the leaderboard
            </p>
          </div>
        )}

        {/* Radar Chart Section */}
        {scores && chartData.length > 0 && (
          <div className="pokemon-radar-chart-standalone">
            <div className="radar-chart-border">
              <div className="radar-chart-content">
                <h3 className="radar-chart-title">Server Metrics</h3>
                <ResponsiveContainer width="100%" height={320}>
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
                    <defs>
                      <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="rgba(0, 102, 255, 0.8)" />
                        <stop offset="100%" stopColor="rgba(0, 102, 255, 0.3)" />
                      </linearGradient>
                    </defs>
                    <PolarGrid stroke="rgba(0, 102, 255, 0.2)" strokeWidth={1.5} />
                    <PolarAngleAxis
                      dataKey="subject"
                      tick={{ fill: 'rgba(0, 102, 255, 0.9)', fontSize: 11, fontWeight: 600 }}
                    />
                    <PolarRadiusAxis
                      angle={90}
                      domain={[0, 100]}
                      tick={{ fill: 'rgba(0, 102, 255, 0.6)', fontSize: 9 }}
                      tickCount={6}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgba(0, 0, 0, 0.9)',
                        border: '1px solid rgba(0, 102, 255, 0.5)',
                        borderRadius: '8px',
                        color: 'white'
                      }}
                    />
                    <Radar
                      name={serverData.name}
                      dataKey="value"
                      stroke="rgba(0, 102, 255, 1)"
                      strokeWidth={2.5}
                      fill="url(#radarGradient)"
                      fillOpacity={0.6}
                      dot={{ fill: 'rgba(0, 102, 255, 1)', r: 4, strokeWidth: 2, stroke: '#fff' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* View Selector */}
      <div className="analytics-view-selector">
        <button
          className={`view-tab ${selectedView === 'overview' ? 'active' : ''}`}
          onClick={() => setSelectedView('overview')}
        >
          Overview
        </button>
        <button
          className={`view-tab ${selectedView === 'performance' ? 'active' : ''}`}
          onClick={() => setSelectedView('performance')}
        >
          Performance
        </button>
        <button
          className={`view-tab ${selectedView === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setSelectedView('leaderboard')}
        >
          Leaderboard
        </button>
        <button
          className={`view-tab ${selectedView === 'activity' ? 'active' : ''}`}
          onClick={() => setSelectedView('activity')}
        >
          Recent Activity
        </button>
        <button
          className={`view-tab ${selectedView === 'badges' ? 'active' : ''}`}
          onClick={() => setSelectedView('badges')}
        >
          Badges
        </button>
        <button
          className={`view-tab ${selectedView === 'historical' ? 'active' : ''}`}
          onClick={() => setSelectedView('historical')}
        >
          Historical Stats
        </button>
        <button
          className={`view-tab ${selectedView === 'contact' ? 'active' : ''}`}
          onClick={() => setSelectedView('contact')}
        >
          Contact
        </button>
        <button
          className={`view-tab ${selectedView === 'stats' ? 'active' : ''}`}
          onClick={() => setSelectedView('stats')}
        >
          Additional Stats
        </button>
      </div>

      {/* Overview Tab */}
      {selectedView === 'overview' && metrics_overview && (
        <>
          {/* Overview Actions */}
          <div className="overview-actions">
            {rankings?.global_rank && (
              <div className="ranking-badge-large">
                <div className="ranking-icon">🏆</div>
                <div className="ranking-content">
                  <div className="ranking-label">Global Ranking</div>
                  <div className="ranking-value">#{rankings.global_rank}</div>
                </div>
              </div>
            )}
          </div>

          <div className="metrics-overview-section">
            <h2 className="section-title">Server Performance Metrics</h2>
            <p className="section-subtitle">Key performance indicators and server health analytics</p>          <div className="metrics-grid">
              <div className="metric-card primary">
                <div className="metric-content">
                  <div className="metric-value">
                    ${metrics_overview.total_verified_volume.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="metric-label">Total Verified Volume</div>
                  <div className="metric-description">Lifetime verified payout volume</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <div className="metric-value">
                    {metrics_overview.verified_payout_count.toLocaleString()}
                  </div>
                  <div className="metric-label">Verified Payouts</div>
                  <div className="metric-description">Total approved submissions</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <div className="metric-value">
                    {metrics_overview.active_submitters_30d}
                  </div>
                  <div className="metric-label">Active Submitters</div>
                  <div className="metric-description">Unique traders (last 30 days)</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <div className="metric-value">
                    {metrics_overview.approval_rate_3m.toFixed(1)}%
                  </div>
                  <div className="metric-label">Approval Rate</div>
                  <div className="metric-description">Last 3 months</div>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-content">
                  <div className="metric-value" style={{ color: metrics_overview.growth_rate_30d >= 0 ? '#10b981' : '#ef4444' }}>
                    {metrics_overview.growth_rate_30d >= 0 ? '+' : ''}{metrics_overview.growth_rate_30d.toFixed(1)}%
                  </div>
                  <div className="metric-label">Growth Rate</div>
                  <div className="metric-description">30-day payout change</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Badges Tab */}
      {selectedView === 'badges' && (badges.performance.length > 0 || badges.consistency.length > 0 || badges.community.length > 0) && (
        <div className="badges-section">
          <h2 className="section-title">Badges & Achievements</h2>
          <p className="section-subtitle">Earned accomplishments based on verified performance metrics</p>

          {/* Performance Badges */}
          {badges.performance.length > 0 && (
            <div className="badge-category">
              <h3 className="badge-category-title">Performance Badges</h3>
              <div className="badges-grid">
                {badges.performance.map((badge, idx) => (
                  <div key={idx} className={`badge-card badge-${badge.tier}`}>
                    <div className="badge-header">
                      <span className="badge-tier-label">{badge.tier.toUpperCase()}</span>
                    </div>
                    <div className="badge-content">
                      <div className="badge-name">{badge.name}</div>
                      <div className="badge-description">
                        {badge.name === 'Top 10 Global' && 'Ranked in the top 10 servers globally'}
                        {badge.name === 'Top 50 Global' && 'Ranked in the top 50 servers globally'}
                        {badge.name === '7-Figure Club' && 'Over $1,000,000 in verified volume'}
                        {badge.name === '500k Club' && 'Over $500,000 in verified volume'}
                        {badge.name === '250k Club' && 'Over $250,000 in verified volume'}
                        {badge.name === '100k Club' && 'Over $100,000 in verified volume'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Consistency Badges */}
          {badges.consistency.length > 0 && (
            <div className="badge-category">
              <h3 className="badge-category-title">Consistency Badges</h3>
              <div className="badges-grid">
                {badges.consistency.map((badge, idx) => (
                  <div key={idx} className={`badge-card badge-${badge.tier}`}>
                    <div className="badge-header">
                      <span className="badge-tier-label">{badge.tier.toUpperCase()}</span>
                    </div>
                    <div className="badge-content">
                      <div className="badge-name">{badge.name}</div>
                      <div className="badge-description">
                        {badge.name === '30-Day Activity' && 'Consistent activity with 5+ traders in the last 30 days'}
                        {badge.name === 'High Accuracy' && '80%+ verification rate over last 3 months'}
                        {badge.name === 'Fastest Growing Server' && '50%+ growth rate in the last 30 days'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Community Badges */}
          {badges.community.length > 0 && (
            <div className="badge-category">
              <h3 className="badge-category-title">Community Badges</h3>
              <div className="badges-grid">
                {badges.community.map((badge, idx) => (
                  <div key={idx} className={`badge-card badge-${badge.tier}`}>
                    <div className="badge-header">
                      <span className="badge-tier-label">{badge.tier.toUpperCase()}</span>
                    </div>
                    <div className="badge-content">
                      <div className="badge-name">{badge.name}</div>
                      <div className="badge-description">
                        {badge.name === 'Active Trader Base' && 'Strong community with 10+ active traders'}
                        {badge.name === 'Emerging Server' && 'New server with positive growth momentum'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Performance Tab */}
      {selectedView === 'performance' && (
        <div className="analytics-section">
          <h2 className="section-title">Performance Analytics</h2>
          <p className="section-subtitle">Comprehensive data visualization and trend analysis</p>

          {/* Monthly Payout Volume Chart */}
          {graphs?.monthly && graphs.monthly.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">Monthly Payout Volume</h3>
                <p className="chart-subtitle">Total verified payout volume by month (Last 12 months)</p>
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <LineChart data={graphs.monthly} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <defs>
                    <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#0066ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                  <XAxis
                    dataKey="month"
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
                    }}
                  />
                  <YAxis
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(0, 0, 0, 0.9)',
                      border: '1px solid rgba(0, 102, 255, 0.5)',
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => [`$${value.toLocaleString()}`, 'Volume']}
                    labelFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="volume"
                    stroke="#0066ff"
                    fillOpacity={1}
                    fill="url(#volumeGradient)"
                    strokeWidth={3}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Payout Count Over Time */}
          {graphs?.monthly && graphs.monthly.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">Payout Count Over Time</h3>
                <p className="chart-subtitle">Number of verified payouts by month</p>
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <BarChart data={graphs.monthly} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                  <XAxis
                    dataKey="month"
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
                    }}
                  />
                  <YAxis
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(0, 0, 0, 0.9)',
                      border: '1px solid rgba(0, 102, 255, 0.5)',
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => [value, 'Payouts']}
                    labelFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    }}
                    cursor={false}
                  />
                  <Bar
                    dataKey="count"
                    fill="#0066ff"
                    radius={[8, 8, 0, 0]}
                    name="Payouts"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Active Submitters Trend */}
          {graphs?.submitter_trend && graphs.submitter_trend.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">Active Submitters Trend</h3>
                <p className="chart-subtitle">Unique active traders per week (Last 12 weeks)</p>
              </div>
              <ResponsiveContainer width="100%" height={380}>
                <AreaChart data={graphs.submitter_trend} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <defs>
                    <linearGradient id="submitterGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0066ff" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#0066ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                  <XAxis
                    dataKey="week_start"
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(0, 0, 0, 0.9)',
                      border: '1px solid rgba(0, 102, 255, 0.5)',
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value) => [value, 'Active Traders']}
                    labelFormatter={(date) => `Week of ${new Date(date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`}
                    cursor={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="active_submitters"
                    stroke="#0066ff"
                    fillOpacity={1}
                    fill="url(#submitterGradient)"
                    strokeWidth={3}
                    name="Active Traders"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Market Distribution Pie Chart */}
          {breakdowns?.markets && breakdowns.markets.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <h3 className="chart-title">Market Distribution</h3>
                <p className="chart-subtitle">Verified payout volume by market category</p>
              </div>
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={breakdowns.markets}
                    dataKey="volume"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={120}
                    labelLine={false}
                    label={({ category, percentage }) => percentage > 5 ? `${category} ${percentage.toFixed(1)}%` : ''}
                  >
                    {breakdowns.markets.map((entry, index) => {
                      const colors = ['#0066ff', '#00b4d8', '#90e0ef', '#caf0f8', '#48cae4'];
                      return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />;
                    })}
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
            </div>
          )}
        </div>
      )}

      {/* Leaderboard Tab */}
      {selectedView === 'leaderboard' && analytics.top_traders && analytics.top_traders.length > 0 && (
        <div className="leaderboard-section">
          <div className="chart-card">
            <div className="chart-header">
              <h3 className="chart-title">Top 5 Trader Contributions</h3>
              <p className="chart-subtitle">Leading contributors to server verified volume</p>
            </div>
            <div className="leaderboard-table">
              <div className="leaderboard-header">
                <div className="rank-col">Rank</div>
                <div className="trader-col">Trader</div>
                <div className="volume-col">Total Volume</div>
                <div className="count-col">Payouts</div>
                <div className="contribution-col">Contribution</div>
              </div>
              {analytics.top_traders.map((trader) => (
                <div key={trader.user_id} className={`leaderboard-row rank-${trader.rank} ${trader.is_private ? 'private-trader' : ''}`}>
                  <div className="rank-col">
                    <span className="rank-badge">#{trader.rank}</span>
                  </div>
                  <div className="trader-col">
                    <div className="trader-name-wrapper">
                      <Link
                        to={trader.profile_url || `/trader/${trader.user_id}/public`}
                        className="trader-name"
                        style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                      >
                        {trader.username}
                      </Link>
                      {trader.is_private && (
                        <span className="privacy-badge" title="This trader has privacy settings enabled">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        </span>
                      )}
                    </div>
                    {trader.best_market && (
                      <span className="trader-market">{trader.best_market}</span>
                    )}
                  </div>
                  <div className="volume-col">
                    <span className="volume-amount">${trader.total_volume.toLocaleString()}</span>
                  </div>
                  <div className="count-col">
                    <span className="payout-count">{trader.submission_count}</span>
                  </div>
                  <div className="contribution-col">
                    <div className="contribution-bar-container">
                      <div
                        className="contribution-bar"
                        style={{ width: `${trader.contribution_percentage}%` }}
                      ></div>
                      <span className="contribution-text">{trader.contribution_percentage.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="privacy-notice">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <p>Traders with privacy settings enabled appear with anonymized usernames. Performance metrics remain visible to respect community transparency while protecting individual privacy preferences.</p>
            </div>
          </div>
        </div>
      )}

      {/* Activity Tab - Recent Payouts */}
      {selectedView === 'activity' && analytics.recent_payouts && analytics.recent_payouts.length > 0 && (
        <div className="payout-feed-section">
          <div className="feed-header">
            <div>
              <h2 className="section-title">Recent Verified Payouts</h2>
              <p className="section-subtitle">Real-time payout activity from this community</p>
            </div>
            <div className="live-indicator">
              <span className="pulse-dot"></span>
              <span className="live-text">Live</span>
            </div>
          </div>

          <div className="payout-feed-container">
            {analytics.recent_payouts.map((payout) => (
              <div key={payout.id} className="payout-feed-item">
                <div className="payout-screenshot">
                  {payout.screenshot_url ? (
                    <div className="screenshot-preview">
                      <img
                        src={payout.screenshot_url}
                        alt="Payout verification"
                        className="blurred-screenshot"
                        onClick={(e) => {
                          e.currentTarget.classList.toggle('blurred-screenshot');
                          e.currentTarget.classList.toggle('unblurred-screenshot');
                        }}
                      />
                      <div 
                        className="screenshot-overlay"
                        onClick={(e) => {
                          const img = e.currentTarget.previousElementSibling;
                          img.classList.toggle('blurred-screenshot');
                          img.classList.toggle('unblurred-screenshot');
                        }}
                      >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        <span>Click to view</span>
                      </div>
                    </div>
                  ) : (
                    <div className="screenshot-placeholder">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                      </svg>
                    </div>
                  )}
                  <div className="verification-badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                    </svg>
                    Verified
                  </div>
                </div>

                <div className="payout-details">
                  <div className="payout-header-row">
                    <div className="payout-amount">${payout.amount.toLocaleString()}</div>
                    <div className="payout-date">
                      {new Date(payout.payout_date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </div>
                  </div>

                  <div className="payout-meta">
                    <div className="meta-item">
                      <span className="meta-label">Trader</span>
                      <Link
                        to={payout.trader.profile_url || `/trader/${payout.trader.user_id}/public`}
                        className={`meta-value ${payout.trader.is_private ? 'private-trader-name' : ''}`}
                        style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                      >
                        {payout.trader.username}
                        {payout.trader.is_private && (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                          </svg>
                        )}
                      </Link>
                    </div>

                    <div className="meta-item">
                      <span className="meta-label">Market</span>
                      <span className="meta-value market-badge">{payout.market_category}</span>
                    </div>

                    {payout.prop_firm && (
                      <div className="meta-item">
                        <span className="meta-label">Prop Firm</span>
                        <span className="meta-value firm-name">{payout.prop_firm.name}</span>
                      </div>
                    )}

                    <div className="meta-item">
                      <span className="meta-label">Instrument</span>
                      <span className="meta-value">{payout.instrument}</span>
                    </div>
                  </div>

                  {payout.verified_at && (
                    <div className="verification-info">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      Verified {new Date(payout.verified_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric'
                      })}
                    </div>
                  )}

                  {payout.screenshot_url && (
                    <button
                      className="view-image-button"
                      onClick={() => setImageModal({ isOpen: true, imageUrl: payout.screenshot_url })}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                        <polyline points="10,17 15,12 20,17" />
                        <line x1="23" y1="7" x2="17" y2="7" />
                        <polyline points="9,7 4,12 1,9" />
                      </svg>
                      View Image
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical Stats Tab */}
      {selectedView === 'historical' && analytics.historical_stats && (
        <div className="historical-stats-section">
          <h2 className="section-title">Historical Performance</h2>
          <p className="section-subtitle">Long-term analytics and growth trajectory</p>

          <div className="historical-stats-grid">
            {/* Lifetime Volume Card */}
            <div className="historical-card primary-card">
              <div className="card-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <div className="card-content">
                <div className="card-label">Lifetime Volume</div>
                <div className="card-value">${analytics.historical_stats.lifetime_volume.toLocaleString()}</div>
                <div className="card-subtitle">{analytics.historical_stats.lifetime_count} total payouts</div>
              </div>
            </div>

            {/* Monthly Averages Card */}
            <div className="historical-card">
              <div className="card-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <div className="card-content">
                <div className="card-label">Monthly Average</div>
                <div className="card-value">${analytics.historical_stats.avg_monthly_volume.toLocaleString()}</div>
                <div className="card-subtitle">{analytics.historical_stats.avg_monthly_count} payouts/month</div>
              </div>
            </div>

            {/* Peak Month Card */}
            {analytics.historical_stats.peak_month && (
              <div className="historical-card success-card">
                <div className="card-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
                    <polyline points="16 7 22 7 22 13" />
                  </svg>
                </div>
                <div className="card-content">
                  <div className="card-label">Peak Month</div>
                  <div className="card-value">${analytics.historical_stats.peak_month.volume.toLocaleString()}</div>
                  <div className="card-subtitle">
                    {new Date(analytics.historical_stats.peak_month.month + '-01').toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                  </div>
                </div>
              </div>
            )}

            {/* Lowest Month Card */}
            {analytics.historical_stats.lowest_month && (
              <div className="historical-card warning-card">
                <div className="card-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
                    <polyline points="16 17 22 17 22 11" />
                  </svg>
                </div>
                <div className="card-content">
                  <div className="card-label">Lowest Month</div>
                  <div className="card-value">${analytics.historical_stats.lowest_month.volume.toLocaleString()}</div>
                  <div className="card-subtitle">
                    {new Date(analytics.historical_stats.lowest_month.month + '-01').toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                  </div>
                </div>
              </div>
            )}

            {/* Growth Trajectory Card */}
            <div className={`historical-card ${analytics.historical_stats.growth_trajectory === 'growing' ? 'success-card' : analytics.historical_stats.growth_trajectory === 'declining' ? 'danger-card' : ''}`}>
              <div className="card-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 3v18h18" />
                  <path d="M18 17V9" />
                  <path d="M13 17V5" />
                  <path d="M8 17v-3" />
                </svg>
              </div>
              <div className="card-content">
                <div className="card-label">Growth Trajectory</div>
                <div className="card-value trajectory-value">
                  {analytics.historical_stats.trajectory_percentage >= 0 ? '+' : ''}
                  {analytics.historical_stats.trajectory_percentage.toFixed(1)}%
                </div>
                <div className="card-subtitle">{analytics.historical_stats.growth_trajectory.charAt(0).toUpperCase() + analytics.historical_stats.growth_trajectory.slice(1)}</div>
              </div>
            </div>

            {/* Stability Rating Card */}
            <div className="historical-card">
              <div className="card-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <div className="card-content">
                <div className="card-label">Stability Rating</div>
                <div className="card-value">{analytics.historical_stats.stability_score}/100</div>
                <div className="card-subtitle">{analytics.historical_stats.stability_rating}</div>
              </div>
            </div>
          </div>

          {/* Submission Accuracy History Chart */}
          {analytics.historical_stats.accuracy_history && analytics.historical_stats.accuracy_history.length > 0 && (
            <div className="accuracy-chart-card">
              <h3 className="chart-title">Submission Accuracy History</h3>
              <p className="chart-subtitle">Approval rate over the last 6 months</p>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={analytics.historical_stats.accuracy_history} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                  <defs>
                    <linearGradient id="accuracyGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#0066ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                  <XAxis
                    dataKey="month"
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'short' });
                    }}
                  />
                  <YAxis
                    stroke="rgba(100, 149, 237, 0.7)"
                    tick={{ fontSize: 12 }}
                    domain={[0, 100]}
                    tickFormatter={(value) => `${value}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(0, 0, 0, 0.9)',
                      border: '1px solid rgba(0, 102, 255, 0.5)',
                      borderRadius: '8px',
                      color: 'white'
                    }}
                    formatter={(value, name, props) => {
                      if (name === 'accuracy') {
                        return [`${value}% (${props.payload.approved_submissions}/${props.payload.total_submissions})`, 'Approval Rate'];
                      }
                      return [value, name];
                    }}
                    labelFormatter={(month) => {
                      const [year, m] = month.split('-');
                      const date = new Date(year, parseInt(m) - 1);
                      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="accuracy"
                    stroke="#0066ff"
                    fillOpacity={1}
                    fill="url(#accuracyGradient)"
                    strokeWidth={3}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Contact Tab */}
      {selectedView === 'contact' && server && (
        <div className="contact-section">
          <h2 className="section-title">Contact & Links</h2>
          <p className="section-subtitle">Connect with this trading community</p>

          <div className="contact-links-grid">
            {/* Discord Invite - Always present */}
            <a
              href={server.invite_link}
              target="_blank"
              rel="noopener noreferrer"
              className="contact-link primary-link"
            >
              <div className="link-icon discord-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
              </div>
              <div className="link-content">
                <div className="link-label">Discord Server</div>
                <div className="link-url">Join Community</div>
              </div>
              <div className="link-arrow">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M7 17L17 7M17 7H7M17 7V17" />
                </svg>
              </div>
            </a>

            {/* Website */}
            {server.website && (
              <a
                href={server.website}
                target="_blank"
                rel="noopener noreferrer"
                className="contact-link"
              >
                <div className="link-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                </div>
                <div className="link-content">
                  <div className="link-label">Website</div>
                  <div className="link-url">{new URL(server.website).hostname}</div>
                </div>
                <div className="link-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 17L17 7M17 7H7M17 7V17" />
                  </svg>
                </div>
              </a>
            )}

            {/* Twitter */}
            {server.twitter_url && (
              <a
                href={server.twitter_url}
                target="_blank"
                rel="noopener noreferrer"
                className="contact-link"
              >
                <div className="link-icon twitter-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                </div>
                <div className="link-content">
                  <div className="link-label">Twitter / X</div>
                  <div className="link-url">Follow Updates</div>
                </div>
                <div className="link-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 17L17 7M17 7H7M17 7V17" />
                  </svg>
                </div>
              </a>
            )}

            {/* YouTube */}
            {server.youtube_url && (
              <a
                href={server.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
                className="contact-link"
              >
                <div className="link-icon youtube-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                  </svg>
                </div>
                <div className="link-content">
                  <div className="link-label">YouTube</div>
                  <div className="link-url">Watch Videos</div>
                </div>
                <div className="link-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 17L17 7M17 7H7M17 7V17" />
                  </svg>
                </div>
              </a>
            )}

            {/* Instagram */}
            {server.instagram_url && (
              <a
                href={server.instagram_url}
                target="_blank"
                rel="noopener noreferrer"
                className="contact-link"
              >
                <div className="link-icon instagram-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                  </svg>
                </div>
                <div className="link-content">
                  <div className="link-label">Instagram</div>
                  <div className="link-url">Follow Profile</div>
                </div>
                <div className="link-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 17L17 7M17 7H7M17 7V17" />
                  </svg>
                </div>
              </a>
            )}

            {/* Support Email */}
            {server.support_email && (
              <a
                href={`mailto:${server.support_email}`}
                className="contact-link"
              >
                <div className="link-icon email-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                </div>
                <div className="link-content">
                  <div className="link-label">Support Contact</div>
                  <div className="link-url">{server.support_email}</div>
                </div>
                <div className="link-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 17L17 7M17 7H7M17 7V17" />
                  </svg>
                </div>
              </a>
            )}
          </div>

          {/* Disclaimer */}
          <div className="contact-disclaimer">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p>
              <strong>Important:</strong> Aurevia does not endorse trading groups. Data shown is verified payout performance only.
              Always conduct your own research before joining any trading community.
            </p>
          </div>
        </div>
      )}

      {/* Additional Stats Tab */}
      {selectedView === 'stats' && stats && (
        <div className="chart-section">
          <h2>Additional Statistics</h2>
          <p className="chart-description">Extended server analytics and insights</p>
          <div className="stats-grid-extended">
            <div className="stat-card">
              <div className="stat-content">
                <div className="stat-label">Established</div>
                <div className="stat-value">{server.established_date ? new Date(server.established_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-content">
                <div className="stat-label">Platform</div>
                <div className="stat-value">{server.platform || 'Not specified'}</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-content">
                <div className="stat-label">Verification Status</div>
                <div className="stat-value">{server.is_verified ? 'Verified' : 'Unverified'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Image Modal */}
      {imageModal.isOpen && (
        <div className="modal-overlay" onClick={() => setImageModal({ isOpen: false, imageUrl: null })}>
          <div className="modal-content image-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Payout Screenshot</h2>
              <button
                className="modal-close"
                onClick={() => setImageModal({ isOpen: false, imageUrl: null })}
              >
                ×
              </button>
            </div>
            <div className="modal-body image-modal-body">
              <img
                src={imageModal.imageUrl}
                alt="Payout verification"
                className="modal-image"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServerPublicView;
