/**
 * Trader Profile Analytics
 * 
 * Individual trader statistics including:
 * - Payout overview (total, growth, averages)
 * - Consistency metrics (Aurevia score, streaks, volatility)
 * - Market-specific performance stats
 * - Rankings (global & server)
 * - Earned badges
 * 
 * Requires authentication
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isTrader } from '../utils/permissions';
import api from '../config/api';
import './TraderProfile.css';

const TraderProfile = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedMarket, setSelectedMarket] = useState('all');
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is a trader before fetching
    if (!isTrader(user)) {
      setError('not_trader');
      setLoading(false);
      return;
    }
    fetchTraderAnalytics();
  }, [user]);

  const fetchTraderAnalytics = async () => {
    try {
      const response = await api.get('/analytics/trader/profile/');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching trader analytics:', error);
      if (error.response?.status === 403) {
        setError('not_trader');
      } else {
        setError('general');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="trader-profile-loading">
        <h2>Loading your analytics...</h2>
      </div>
    );
  }

  if (error === 'not_trader') {
    // Check if user is a ServerCreator
    const isServerCreator = user?.role === 'ServerCreator';
    
    return (
      <div className="trader-profile-not-available">
        <div className="icon"></div>
        {isServerCreator ? (
          <>
            <h2>Server Creator Account</h2>
            <p>
              You have a Server Creator account. This page is for traders to view their payout analytics.
            </p>
            <p style={{ marginTop: '16px', color: 'var(--primary-blue)' }}>
              <strong>Ready to create your trading server?</strong>
            </p>
            <div className="button-group">
              <button className="primary" onClick={() => navigate('/servers/create')}>
                Create Your Server
              </button>
              <button className="secondary" onClick={() => navigate('/dashboard')}>
                Back to Dashboard
              </button>
            </div>
          </>
        ) : (
          <>
            <h2>Trader Analytics Not Available</h2>
            <p>
              Analytics are only available for traders who are members of at least one server. 
              Join a trading server to start tracking your payout performance, consistency scores, and rankings!
            </p>
            <div className="button-group">
              <button className="primary" onClick={() => navigate('/servers')}>
                Browse Servers
              </button>
              <button className="secondary" onClick={() => navigate('/dashboard')}>
                Back to Dashboard
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  if (!data || error === 'general') {
    return (
      <div className="trader-profile-error">
        <h2>Unable to load analytics</h2>
        <p>Please try again later.</p>
      </div>
    );
  }

  const { payout_overview, consistency_metrics, market_stats, rankings, badges } = data;

  // Get risk rating color
  const getRiskColor = (rating) => {
    return 'rgba(0, 102, 255, 0.5)';
  };

  // Get consistency score color
  const getConsistencyColor = (score) => {
    return 'rgba(0, 102, 255, 0.5)';
  };

  // Get growth trend icon
  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'Increasing': return '';
      case 'Stable': return '';
      case 'Decreasing': return '';
      default: return '';
    }
  };

  // Format hour to AM/PM
  const formatHour = (hour) => {
    if (hour === null) return 'N/A';
    const period = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}:00 ${period}`;
  };

  // Filter market stats
  const displayedMarkets = selectedMarket === 'all' 
    ? market_stats 
    : market_stats.filter(m => m.category === selectedMarket);

  return (
    <div className="trader-profile">
      {/* Pokemon Card Style Header */}
      <div className="trader-pokemon-card-header">
        <div className="trader-pokemon-card-border">
          <div className="trader-pokemon-card-content">
            {/* Top Section: Username and Score */}
            <div className="trader-pokemon-card-top">
              <div className="trader-pokemon-title-section">
                <div className="trader-info">
                  <h1 className="trader-pokemon-name">{user?.username}</h1>
                  <p className="trader-pokemon-subtitle">Trading Performance Card</p>
                  {rankings && (
                    <div className="trader-pokemon-ranks">
                      <span className="trader-rank-badge">Global #{rankings.global_rank}</span>
                      {rankings.server_ranks && rankings.server_ranks.length > 0 && (
                        <span className="trader-rank-badge">Server #{rankings.server_ranks[0].rank}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Consistency Score Circle */}
              {consistency_metrics && (
                <div className="trader-pokemon-score-badge">
                  <div className="trader-pokemon-score-circle" style={{ borderColor: getConsistencyColor(consistency_metrics.consistency_score) }}>
                    <div className="trader-pokemon-score-value" style={{ color: getConsistencyColor(consistency_metrics.consistency_score) }}>
                      {consistency_metrics.consistency_score}
                    </div>
                    <div className="trader-pokemon-score-label">Consistency</div>
                  </div>
                </div>
              )}
            </div>

            {/* Middle Section: Key Stats */}
            {payout_overview && (
              <div className="trader-pokemon-stats-section">
                <div className="trader-pokemon-stat-row">
                  <div className="trader-pokemon-stat">
                    <span className="trader-stat-label">Total Verified</span>
                    <span className="trader-stat-value">${payout_overview.total_verified.toLocaleString()}</span>
                  </div>
                  <div className="trader-pokemon-stat">
                    <span className="trader-stat-label">Avg Payout</span>
                    <span className="trader-stat-value">${payout_overview.avg_payout.toFixed(2)}</span>
                  </div>
                </div>
                <div className="trader-pokemon-stat-row">
                  <div className="trader-pokemon-stat">
                    <span className="trader-stat-label">Monthly Growth</span>
                    <span className="trader-stat-value" style={{ color: payout_overview.monthly_growth >= 0 ? '#10b981' : '#ef4444' }}>
                      {payout_overview.monthly_growth >= 0 ? '+' : ''}{payout_overview.monthly_growth.toFixed(1)}%
                    </span>
                  </div>
                  <div className="trader-pokemon-stat">
                    <span className="trader-stat-label">Largest Win</span>
                    <span className="trader-stat-value">${payout_overview.largest_payout.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Section: Badges Preview */}
            {badges && badges.length > 0 && (
              <div className="trader-pokemon-badges-preview">
                <span className="trader-badges-label">Achievements:</span>
                <div className="trader-badges-mini">
                  {badges.slice(0, 4).map((badge, idx) => (
                    <div key={idx} className="trader-badge-mini" title={badge.name}>
                      <span>{badge.icon}</span>
                    </div>
                  ))}
                  {badges.length > 4 && (
                    <div className="trader-badge-mini more">+{badges.length - 4}</div>
                  )}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="trader-pokemon-actions">
              <button className="trader-btn-primary" onClick={() => navigate('/payouts')}>
                Submit Payout
              </button>
              <button className="trader-btn-secondary" onClick={() => navigate('/dashboard')}>
                Dashboard
              </button>
            </div>

            {/* Holographic Shine Effect */}
            <div className="trader-pokemon-card-shine"></div>
          </div>
        </div>
      </div>

      {/* Badges Section */}
      {badges.length > 0 && (
        <div className="badges-section">
          <h2>Your Badges</h2>
          <div className="badges-grid">
            {badges.map((badge, idx) => (
              <div key={idx} className="badge-card">
                <span className="icon">{badge.icon}</span>
                <div>
                  <div className="name" style={{ color: badge.color }}>{badge.name}</div>
                  <div className="description">{badge.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Payout Overview */}
      <Section title="Payout Overview">
        <div className="stats-overview-section">
          <MetricCard
            label="Total Verified Payouts"
            value={`$${payout_overview.total_verified.toLocaleString()}`}
          />
          <MetricCard
            label="Monthly Growth"
            value={`${payout_overview.monthly_growth >= 0 ? '+' : ''}${payout_overview.monthly_growth.toFixed(1)}%`}
            subtext={`$${payout_overview.current_month_total.toLocaleString()} this month`}
          />
          <MetricCard
            label="Average Payout"
            value={`$${payout_overview.avg_payout.toFixed(2)}`}
          />
          <MetricCard
            label="Largest Single Payout"
            value={`$${payout_overview.largest_payout.toLocaleString()}`}
          />
          <MetricCard
            label="Submission Frequency"
            value={`${payout_overview.weekly_frequency.toFixed(1)} / week`}
            subtext={`${payout_overview.daily_frequency.toFixed(2)} / day`}
          />
          <MetricCard
            label="Most Active Time"
            value={formatHour(payout_overview.most_active_hour)}
            subtext="Peak trading hour"
          />
        </div>
      </Section>

      {/* Consistency Metrics */}
      <Section title="Consistency Metrics">
        <div className="consistency-grid">
          {/* Consistency Score - Large */}
          <div className="consistency-card" style={{ borderColor: getConsistencyColor(consistency_metrics.consistency_score) }}>
            <div className="icon"></div>
            <div className="label">Aurevia Consistency Score™</div>
            <div className="value" style={{ color: getConsistencyColor(consistency_metrics.consistency_score) }}>
              {consistency_metrics.consistency_score}
            </div>
            <div className="max">out of 100</div>
            <div className="description">
              Based on submission regularity, payout stability, and growth trend
            </div>
          </div>

          {/* Streaks */}
          <div className="consistency-card">
            <div className="icon"></div>
            <div className="label">Submission Streaks</div>
            <div className="value">
              {consistency_metrics.current_streak}
            </div>
            <div className="subtext">Current streak (days)</div>
            <div className="divider">
              <div className="secondary-value">{consistency_metrics.longest_streak}</div>
              <div className="secondary-label">Longest streak</div>
            </div>
          </div>

          {/* Volatility */}
          <MetricCard
            icon=""
            label="Volatility Score"
            value={`${consistency_metrics.volatility_score.toFixed(1)}%`}
            subtext="Lower is more stable"
          />

          {/* Growth Trend */}
          <div className="consistency-card">
            <div className="icon">
              {getTrendIcon(consistency_metrics.growth_trend)}
            </div>
            <div className="label">Growth Trend</div>
            <div className="value">
              {consistency_metrics.growth_trend}
            </div>
            <div className="subtext">Based on recent activity</div>
          </div>

          {/* Risk Rating */}
          <div className="consistency-card" style={{ borderColor: getRiskColor(consistency_metrics.risk_rating) }}>
            <div className="icon">
              {consistency_metrics.risk_rating === 'Stable' ? '' : 
               consistency_metrics.risk_rating === 'Moderate' ? '' :
               consistency_metrics.risk_rating === 'Inconsistent' ? '' : ''}
            </div>
            <div className="label">Risk Rating</div>
            <div className="value" style={{ color: getRiskColor(consistency_metrics.risk_rating) }}>
              {consistency_metrics.risk_rating}
            </div>
            <div className="subtext">Trading style classification</div>
          </div>
        </div>
      </Section>

      {/* Market-Specific Stats */}
      <Section title="Market Performance">
        {market_stats.length === 0 ? (
          <div className="no-data">
            No market data available yet. Start submitting payouts to see your stats!
          </div>
        ) : (
          <div className="stats-grid">
            {market_stats.map((market) => (
              <MarketCard key={market.category} market={market} />
            ))}
          </div>
        )}
      </Section>

      {/* Rankings */}
      <Section title="Rankings">
        <div className="rankings-grid">
          {/* Global Rank */}
          <div 
            className="ranking-card global"
            onClick={() => navigate('/analytics?view=market&market=futures')}
          >
            <div className="icon"></div>
            <div className="label">Global Rank</div>
            <div className="rank">#{rankings.global_rank}</div>
            <div className="subtext">Worldwide leaderboard</div>
            <div className="link">View global leaderboard →</div>
          </div>

          {/* Server Ranks */}
          {rankings.server_ranks.map((server, idx) => (
            <div
              key={idx}
              className="ranking-card server"
              onClick={() => navigate(server.profile_url || `/servers/${server.server_id}/public`)}
            >
              <div className="icon"></div>
              <div className="label">{server.server_name}</div>
              <div className="rank">#{server.rank}</div>
              <div className="subtext">of {server.total_members} members</div>
              <div className="link">Click to view profile →</div>
            </div>
          ))}

          {rankings.server_ranks.length === 0 && (
            <div className="ranking-card no-servers">
              <div className="icon"></div>
              <div className="label">Not a member of any servers yet</div>
              <div className="subtext">
                Join a trading community to compete on server leaderboards!
              </div>
              <button
                className="btn-primary"
                onClick={() => navigate('/servers')}
              >
                Browse Servers
              </button>
            </div>
          )}
        </div>
      </Section>
    </div>
  );
};

// Helper Components
const Section = ({ title, children }) => (
  <div className="section">
    <h2>{title}</h2>
    {children}
  </div>
);

const MetricCard = ({ icon, label, value, subtext, color }) => (
  <div className="stat-card" style={{ borderColor: color }}>
    <div className="icon">{icon}</div>
    <div className="label">{label}</div>
    <div className="value" style={{ color }}>{value}</div>
    {subtext && <div className="subtext">{subtext}</div>}
  </div>
);

const MarketCard = ({ market }) => {
  const getMarketIcon = (category) => {
    switch (category) {
      case 'futures': return '';
      case 'forex': return '';
      case 'crypto': return '';
      case 'options': return '';
      case 'equities': return '';
      default: return '';
    }
  };

  const getMarketColor = (category) => {
    switch (category) {
      case 'futures': return '#007bff';
      case 'forex': return '#28a745';
      case 'crypto': return '#ffc107';
      case 'options': return '#17a2b8';
      case 'equities': return '#6c757d';
      default: return '#6c757d';
    }
  };

  return (
    <div className="market-card" style={{ borderColor: getMarketColor(market.category) }}>
      <div className="market-card-header">
        <span className="icon">{getMarketIcon(market.category)}</span>
        <span className="title" style={{ color: getMarketColor(market.category) }}>
          {market.category.charAt(0).toUpperCase() + market.category.slice(1)}
        </span>
      </div>
      
      <div className="market-card-payout">
        <div className="label">Total Payout</div>
        <div className="value" style={{ color: getMarketColor(market.category) }}>
          ${market.total_payout.toLocaleString()}
        </div>
      </div>

      <div className="market-card-stats">
        <div>
          <div className="label">Avg Payout</div>
          <div className="value">
            ${market.avg_payout.toFixed(0)}
          </div>
        </div>
      </div>

      <div className="market-card-best">
        <div className="label">Most Profitable</div>
        <div className="instrument" style={{ color: getMarketColor(market.category) }}>
          {market.most_profitable_instrument}
        </div>
        <div className="amount">
          ${market.most_profitable_amount.toLocaleString()}
        </div>
      </div>

      <div className="market-card-footer">
        {market.submission_count} submission{market.submission_count !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

export default TraderProfile;
