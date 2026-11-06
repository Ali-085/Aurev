/**
 * Server Owner Analytics
 * 
 * Deep analytics dashboard for server owners only.
 * Shows comprehensive metrics with tier-based feature access:
 * - Total payout insights
 * - Server activity metrics  
 * - Trader performance breakdown
 * - Market category analytics
 * - Submission quality metrics
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../config/api';
import { getTierFeatures, getTierInfo, formatTierName } from '../utils/tierUtils';
import UpgradePrompt from '../components/UpgradePrompt';
import './ServerOwnerAnalytics.css';

const ServerOwnerAnalytics = () => {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedTab, setSelectedTab] = useState('overview');
  const [userTier, setUserTier] = useState(null);
  const [tierFeatures, setTierFeatures] = useState(null);

  useEffect(() => {
    fetchServerAnalytics();
    fetchUserSubscription();
  }, [serverId]);

  const fetchServerAnalytics = async () => {
    try {
      const response = await api.get(`/analytics/server-owner/dashboard/${serverId}/`);
      setData(response.data);
      
      // Extract tier from response if available
      if (response.data.user_tier) {
        setUserTier(response.data.user_tier);
        setTierFeatures(getTierFeatures(response.data.user_tier));
      }
    } catch (error) {
      console.error('Error fetching server analytics:', error);
      if (error.response?.status === 403) {
        setError('not_owner');
      } else if (error.response?.status === 404) {
        setError('not_found');
      } else {
        setError('general');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const fetchUserSubscription = async () => {
    try {
      const response = await api.get('/subscriptions/status/');
      if (response.data.tier) {
        setUserTier(response.data.tier);
        setTierFeatures(getTierFeatures(response.data.tier));
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
      // User might not have subscription, set as free
      setUserTier('free');
      setTierFeatures(getTierFeatures('free'));
    }
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <h2>Loading server analytics...</h2>
      </div>
    );
  }

  if (error === 'not_owner') {
    return (
      <div className="analytics-access-denied">
        <h2>Access Denied</h2>
        <p>You do not own this server.</p>
        <button onClick={() => navigate('/server-dashboard')} className="analytics-back-button">
          Back to My Servers
        </button>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="analytics-not-found">
        <h2>Server Not Found</h2>
        <button onClick={() => navigate('/server-dashboard')} className="analytics-back-button">
          Back to My Servers
        </button>
      </div>
    );
  }

  // Allow settings access even if analytics data is unavailable
  const hasServerData = data && data.server;
  const serverIdForSettings = serverId || data?.server?.id;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '' },
    { id: 'traders', label: 'Traders', icon: '' },
    { id: 'markets', label: 'Markets', icon: '' },
    { id: 'quality', label: 'Quality', icon: '' },
    { id: 'settings', label: 'Settings', }
  ];

  return (
    <div className="analytics-page">
      {/* Header */}
      <div className="analytics-header">
        <div className="analytics-header-info">
          <div className="analytics-header-title">
            <h1>
              {hasServerData ? (
                <Link 
                  to={data.server.profile_url || `/servers/${data.server.id}/public`}
                  style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                >
                  {data.server.name}
                </Link>
              ) : (
                'Server Analytics'
              )}
            </h1>
            {userTier && userTier !== 'free' && (
              <span className="analytics-tier-badge" style={{ background: getTierInfo(userTier).color }}>
                {getTierInfo(userTier).icon} {formatTierName(userTier)} Tier
              </span>
            )}
          </div>
          {hasServerData && <p className="analytics-header-members">{data.server.total_members} members</p>}
        </div>
        <div className="analytics-header-actions">
          <button onClick={() => navigate(`/servers/${serverIdForSettings}/settings`)} className="primary">
            Settings
          </button>
          <button onClick={() => navigate('/pricing')} className="secondary">
            {userTier && userTier !== 'free' && userTier !== 'elite' ? 'Upgrade' : 'View Plans'}
          </button>
          <button onClick={() => navigate('/my-servers')} className="secondary">
            Back to Servers
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="analytics-tabs">
        <div className="analytics-tabs-list">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id)}
              className={`analytics-tab-button ${selectedTab === tab.id ? 'active' : ''}`}
            >
              {tab.icon} {tab.label.split(' ')[1]}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {selectedTab === 'overview' && (
        hasServerData ? (
          <OverviewTab data={data} userTier={userTier} tierFeatures={tierFeatures} />
        ) : (
          <div className="analytics-error">
            <h2>Server data not available</h2>
            <p>Unable to load analytics. Please try the Settings tab to configure your server.</p>
          </div>
        )
      )}
      {selectedTab === 'traders' && (
        hasServerData ? (
          <TradersTab data={data} userTier={userTier} tierFeatures={tierFeatures} />
        ) : (
          <div className="analytics-error">
            <h2>Server data not available</h2>
            <p>Unable to load analytics. Please try the Settings tab to configure your server.</p>
          </div>
        )
      )}
      {selectedTab === 'markets' && (
        hasServerData ? (
          <MarketsTab data={data} userTier={userTier} tierFeatures={tierFeatures} />
        ) : (
          <div className="analytics-error">
            <h2>Server data not available</h2>
            <p>Unable to load analytics. Please try the Settings tab to configure your server.</p>
          </div>
        )
      )}
      {selectedTab === 'quality' && (
        hasServerData ? (
          <QualityTab data={data} userTier={userTier} tierFeatures={tierFeatures} />
        ) : (
          <div className="analytics-error">
            <h2>Server data not available</h2>
            <p>Unable to load analytics. Please try the Settings tab to configure your server.</p>
          </div>
        )
      )}
      {selectedTab === 'settings' && <SettingsTab serverId={serverIdForSettings} navigate={navigate} />}
    </div>
  );
};

// Server Info Pokemon Card Component
const ServerInfoCard = ({ server, payout_insights, activity_metrics }) => {
  if (!server) return null;

  const overallScore = activity_metrics?.approval_rate || 0;
  const getScoreColor = (score) => {
    return 'rgba(0, 102, 255, 0.8)';
  };

  return (
    <div className="pokemon-card-container">
      <div className="pokemon-card-border">
        <div className="pokemon-card-content">
          <div className="pokemon-card-top">
            <div className="pokemon-card-title-section">
              <div className="server-logo-wrapper">
                {server.logo_url ? (
                  <img src={server.logo_url} alt={server.name} className="pokemon-server-logo" />
                ) : (
                  <div className="pokemon-logo-placeholder">
                    {server.name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
              
              <div className="pokemon-card-title-info">
                <div className="pokemon-title-row">
                  <h1 className="pokemon-server-name">{server.name}</h1>
                  {server.is_verified && (
                    <span className="pokemon-verified-badge">Verified</span>
                  )}
                </div>
                
                <div className="pokemon-metadata">
                  <span className="pokemon-platform">{server.platform}</span>
                  <span className="pokemon-meta-divider">•</span>
                  <span className="pokemon-established">
                    {server.total_members} members
                  </span>
                </div>
              </div>
            </div>

            <div className="pokemon-score-badge">
              <div className="pokemon-score-circle" style={{ borderColor: getScoreColor(overallScore) }}>
                <div className="pokemon-score-value" style={{ color: getScoreColor(overallScore) }}>
                  {overallScore.toFixed(1)}%
                </div>
                <div className="pokemon-score-label">Approval</div>
              </div>
            </div>
          </div>

          {server.description && (
            <p className="pokemon-description">{server.description}</p>
          )}

          <div className="pokemon-stats-grid">
            <div className="pokemon-stat">
              <div className="pokemon-stat-label">Total Verified</div>
              <div className="pokemon-stat-value">${(payout_insights?.total_verified || 0).toLocaleString()}</div>
            </div>
            <div className="pokemon-stat">
              <div className="pokemon-stat-label">Total Submissions</div>
              <div className="pokemon-stat-value">{payout_insights?.total_submissions || 0}</div>
            </div>
            <div className="pokemon-stat">
              <div className="pokemon-stat-label">Active Traders (30d)</div>
              <div className="pokemon-stat-value">{activity_metrics?.active_traders_30d || 0}</div>
            </div>
            <div className="pokemon-stat">
              <div className="pokemon-stat-label">Submissions/Day</div>
              <div className="pokemon-stat-value">{(activity_metrics?.submissions_per_day || 0).toFixed(1)}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Overview Tab Component
const OverviewTab = ({ data, userTier, tierFeatures }) => {
  const { payout_insights, activity_metrics } = data;

  return (
    <div>
      <ServerInfoCard server={data.server} payout_insights={payout_insights} activity_metrics={activity_metrics} />
      {/* Payout Overview Cards */}
      <h2 className="analytics-section-heading">Payout Insights</h2>
      <div className="analytics-metrics-grid">
        <MetricCard title="Total Verified" value={`$${(payout_insights?.total_verified || 0).toLocaleString()}`} />
        <MetricCard title="Monthly Growth" value={`${(payout_insights?.monthly_growth || 0) > 0 ? '+' : ''}${payout_insights?.monthly_growth || 0}%`} />
        <MetricCard title="Average Payout" value={`$${(payout_insights?.average_payout || 0).toFixed(2)}`} />
        <MetricCard title="Largest Payout" value={`$${(payout_insights?.largest_payout || 0).toLocaleString()}`} />
        <MetricCard title="Total Submissions" value={payout_insights?.total_submissions || 0} />
      </div>

      {/* Activity Metrics */}
      <h2 className="analytics-section-heading">Activity Metrics</h2>
      <div className="analytics-metrics-grid">
        <MetricCard title="Active Traders (7d)" value={activity_metrics?.active_traders_7d || 0} />
        <MetricCard title="Active Traders (30d)" value={activity_metrics?.active_traders_30d || 0} />
        <MetricCard title="Submissions/Day" value={(activity_metrics?.submissions_per_day || 0).toFixed(1)} />
        <MetricCard title="Approval Rate" value={`${activity_metrics?.approval_rate || 0}%`} />
        <MetricCard title="Suspicious Rate" value={`${activity_metrics?.suspicious_rate || 0}%`} />
        <MetricCard title="Pending Reviews" value={activity_metrics?.pending_submissions || 0} />
      </div>

      {/* Most Consistent Traders */}
      {tierFeatures?.consistencyScores && payout_insights.most_consistent_traders?.length > 0 && (
        <>
          <h2 className="analytics-section-heading">Most Consistent Traders</h2>
          <div className="analytics-table-container">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Trader</th>
                  <th className="text-right">Consistency Score</th>
                  <th className="text-right">Total Payouts</th>
                  <th className="text-right">Submissions</th>
                </tr>
              </thead>
              <tbody>
                {payout_insights.most_consistent_traders.map((trader, idx) => (
                  <tr key={idx}>
                    <td>
                      <Link 
                        to={trader.profile_url || `/trader/${trader.user_id}/public`}
                        style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                      >
                        {trader.username}
                      </Link>
                    </td>
                    <td className="text-right">
                      {trader.consistency_score.toFixed(1)}
                    </td>
                    <td className="text-right">${trader.total_payouts.toLocaleString()}</td>
                    <td className="text-right">{trader.submission_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      
      {/* Locked Feature: Consistency Scores (Premium+) */}
      {!tierFeatures?.consistencyScores && (
        <div className="upgrade-prompt-container">
          <UpgradePrompt requiredTier="premium" featureName="Trader Consistency Analysis" />
        </div>
      )}
    </div>
  );
};

// Traders Tab Component
const TradersTab = ({ data, userTier, tierFeatures }) => {
  const { trader_performance } = data;
  
  // Limit top traders based on tier
  const topTradersLimit = tierFeatures?.topTradersTop10 ? 10 : 5;

  return (
    <div>
      {/* Top Traders All Time */}
      <h2 className="analytics-section-heading">Top Traders (All Time)</h2>
      <div className="analytics-table-container">
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Trader</th>
              <th className="text-right">Total Verified</th>
              <th className="text-right">Submissions</th>
            </tr>
          </thead>
          <tbody>
              {(trader_performance?.top_traders_alltime || []).slice(0, topTradersLimit).map((trader, idx) => (
              <tr key={idx}>
                <td className="bold">
                  #{idx + 1}
                </td>
                <td className="bold">
                  <Link 
                    to={trader.profile_url || `/trader/${trader.user_id}/public`}
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {trader.username}
                  </Link>
                </td>
                <td className="text-right">
                  ${(trader.total || 0).toLocaleString()}
                </td>
                <td className="text-right">{trader.submissions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!tierFeatures?.topTradersTop10 && (trader_performance?.top_traders_alltime || []).length > 5 && (
        <div style={{ marginTop: '15px', textAlign: 'center' }}>
          <UpgradePrompt requiredTier="premium" featureName="Top 10+ Traders" inline />
        </div>
      )}

      {/* Top Traders Monthly */}
      <h2 className="analytics-section-heading">Top Traders (Last 30 Days)</h2>
      <div className="analytics-table-container">
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Trader</th>
              <th className="text-right">Total Verified</th>
              <th className="text-right">Submissions</th>
            </tr>
          </thead>
          <tbody>
            {(trader_performance?.top_traders_monthly || []).map((trader, idx) => (
              <tr key={idx}>
                <td className="bold">#{idx + 1}</td>
                <td className="bold">
                  <Link 
                    to={trader.profile_url || `/trader/${trader.user_id}/public`}
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {trader.username}
                  </Link>
                </td>
                <td className="text-right">
                  ${(trader.total || 0).toLocaleString()}
                </td>
                <td className="text-right">{trader.submissions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Most Improved & Highest Single */}
      <div className="highlight-cards-grid">
        {trader_performance.most_improved && (
          <div className="highlight-card">
            <h3>Most Improved Trader</h3>
            <p className="trader-name">
              <Link 
                to={trader_performance.most_improved.profile_url || `/trader/${trader_performance.most_improved.user_id}/public`}
                style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
              >
                {trader_performance.most_improved.username}
              </Link>
            </p>
            <p className="amount">
              +{(trader_performance.most_improved.growth_percentage || 0).toFixed(1)}%
            </p>
            <p className="details">
              Recent: ${(trader_performance.most_improved.recent_total || 0).toLocaleString()} | 
              Previous: ${(trader_performance.most_improved.previous_total || 0).toLocaleString()}
            </p>
          </div>
        )}
        
        {trader_performance.highest_single_payout && (
          <div className="highlight-card">
            <h3>Highest Single Payout</h3>
            <p className="trader-name">
              <Link 
                to={trader_performance.highest_single_payout.profile_url || `/trader/${trader_performance.highest_single_payout.user_id}/public`}
                style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
              >
                {trader_performance.highest_single_payout.username}
              </Link>
            </p>
            <p className="amount">
              ${(trader_performance.highest_single_payout.amount || 0).toLocaleString()}
            </p>
            <p className="details">
              {trader_performance.highest_single_payout.market_category} - {trader_performance.highest_single_payout.instrument}
            </p>
            <p className="date">
              {trader_performance.highest_single_payout.date}
            </p>
          </div>
        )}
      </div>

      {/* Trader Categories */}
      {tierFeatures?.traderCategorization && trader_performance.trader_categories?.length > 0 && (
        <>
          <h2 className="analytics-section-heading">Trader Style Analysis</h2>
          <div className="analytics-table-container">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Trader</th>
                  <th>Style</th>
                  <th className="text-right">Avg Payout</th>
                  <th className="text-right">Frequency</th>
                </tr>
              </thead>
              <tbody>
                {trader_performance.trader_categories.slice(0, 20).map((trader, idx) => (
                  <tr key={idx}>
                    <td className="bold">
                      <Link 
                        to={trader.profile_url || `/trader/${trader.user_id}/public`}
                        style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                      >
                        {trader.username}
                      </Link>
                    </td>
                    <td>
                      <span className="trader-category-badge">
                        {trader.category}
                      </span>
                    </td>
                    <td className="text-right">${trader.avg_payout.toFixed(2)}</td>
                    <td className="text-right">{trader.frequency}/day</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      
      {/* Locked Feature: Trader Categorization (Premium+) */}
      {!tierFeatures?.traderCategorization && (
        <div style={{ marginTop: '30px' }}>
          <UpgradePrompt requiredTier="premium" featureName="Trader Style Analysis (Scalper, Day Trader, etc.)" />
        </div>
      )}
    </div>
  );
};

// Markets Tab Component
const MarketsTab = ({ data, userTier, tierFeatures }) => {
  const { market_analytics } = data;

  return (
    <div>
      <h2 className="analytics-section-heading">Market Category Analytics</h2>
      
      {(market_analytics || []).map((market, idx) => (
        <div key={idx} className="market-category-card">
          <div className="market-category-header">
            <h3>{market.category}</h3>
            <span className={`market-trend-badge ${market.trend || 'stable'}`}>
              {market.trend === 'growing' ? 'Growing' : market.trend === 'declining' ? 'Declining' : 'Stable'}
            </span>
          </div>
          
          <div className="market-stats-grid">
            <div className="market-stat">
              <p className="market-stat-label">Total Verified</p>
              <p className="market-stat-value">${(market.total || 0).toLocaleString()}</p>
            </div>
            <div className="market-stat">
              <p className="market-stat-label">Average</p>
              <p className="market-stat-value">${(market.average || 0).toFixed(2)}</p>
            </div>
            <div className="market-stat">
              <p className="market-stat-label">Submissions</p>
              <p className="market-stat-value">{market.submissions}</p>
            </div>
            <div className="market-stat">
              <p className="market-stat-label">Share of Total</p>
              <p className="market-stat-value primary">{market.percentage_share}%</p>
            </div>
          </div>
          
          {(market.top_instruments || []).length > 0 && (
            <div className="market-instruments-section">
              <h4>Top Instruments</h4>
              <div className="market-instruments-list">
                {(market.top_instruments || []).map((inst, instIdx) => (
                  <div key={instIdx} className="market-instrument-chip">
                    <strong>{inst.name}</strong>: ${(inst.total || 0).toLocaleString()} ({inst.count || 0} trades)
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Quality Tab Component
const QualityTab = ({ data, userTier, tierFeatures }) => {
  const { quality_metrics } = data;

  return (
    <div>
      <h2 className="analytics-section-heading">Submission Quality Metrics</h2>
      
      {/* Overview Cards */}
      <div className="analytics-metrics-grid">
        <MetricCard title="Avg Approval Time" value={`${(quality_metrics?.avg_approval_time_hours || 0).toFixed(1)} hrs`} />
        <MetricCard title="Pending Reviews" value={quality_metrics?.total_pending || 0} />
        <MetricCard title="Total Rejected" value={quality_metrics?.total_rejected || 0} />
      </div>

      {/* Rejection Reasons */}
      {(quality_metrics?.rejection_reasons || []).length > 0 && (
        <>
          <h2 className="analytics-section-heading">Rejection Reasons Breakdown</h2>
          <div className="analytics-table-container">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Reason</th>
                  <th className="text-right">Count</th>
                </tr>
              </thead>
              <tbody>
                {(quality_metrics?.rejection_reasons || []).map((reason, idx) => (
                  <tr key={idx}>
                    <td>{reason.reason}</td>
                    <td className="text-right bold">{reason.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Common Mistakes */}
      {(quality_metrics?.common_mistakes || []).length > 0 && (
        <>
          <h2 className="analytics-section-heading">Most Common Submission Mistakes</h2>
          <div className="rejection-list">
            {(quality_metrics?.common_mistakes || []).map((mistake, idx) => (
              <div key={idx} className="rejection-item">
                <span>{mistake.reason}</span>
                <span className="rejection-count">
                  {mistake.count}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

// Settings Tab Component
const SettingsTab = ({ serverId, navigate }) => {
  useEffect(() => {
    // Redirect to the actual settings page
    navigate(`/servers/${serverId}/settings`, { replace: true });
  }, [serverId, navigate]);

  return (
    <div className="analytics-loading">
      <h2>Redirecting to settings...</h2>
    </div>
  );
};

// Reusable Metric Card Component
const MetricCard = ({ title, value }) => (
  <div className="metric-card">
    <p className="metric-card-title">{title}</p>
    <p className="metric-card-value">{value}</p>
  </div>
);

export default ServerOwnerAnalytics;
