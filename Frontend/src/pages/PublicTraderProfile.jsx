import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { publicApi } from '../config/api';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadialBarChart, RadialBar } from 'recharts';
import { useScrollAnimation } from '../hooks/useScrollAnimation';
import './Analytics.css'; // Use Analytics CSS for consistent styling

/**
 * Public Trader Profile - PROFESSIONAL PERFORMANCE CARD
 * 
 * STRICT PRIVACY RULES:
 * - NO personal data displayed (no real names, emails, contact info)
 * - NO sensitive trading details (deposits, balances, detailed history)
 * - Shows ONLY: alias/handle, server context, lifetime volume, rank, payout feed
 * 
 * Privacy Modes:
 * - privacy=true: Shows minimal anonymized version (unless valid token provided)
 * - privacy=false: Shows professional performance card with allowed public stats
 */
const PublicTraderProfile = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const token = searchParams.get('token'); // Private analytics token

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(null);
  const [selectedView, setSelectedView] = useState(searchParams.get('view') || 'overview');

  useEffect(() => {
    fetchProfile();
  }, [userId, token]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      
      // Build URL with optional token and server_id
      const params = new URLSearchParams();
      if (token) params.append('token', token);
      
      const url = `/auth/trader/${userId}/public/${params.toString() ? '?' + params.toString() : ''}`;
      
      const response = await publicApi.get(url);
      setProfile(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching public profile:', err);
      if (err.response?.status === 404) {
        setError('Trader not found');
      } else {
        setError('Failed to load profile');
      }
    } finally {
      setLoading(false);
    }
  };

  const changeView = (view) => {
    setSelectedView(view);
    setSearchParams({ view, ...(token && { token }) });
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <h2>Loading trader profile...</h2>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="analytics-page">
        <div className="analytics-header">
          <h2>Profile Unavailable</h2>
          <p>{error || 'Unable to load trader profile'}</p>
          <button onClick={() => navigate('/')} className="btn btn-secondary" style={{ marginTop: '20px' }}>
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      {/* Pokemon Card Style Header */}
      <div className="public-trader-pokemon-card-header">
        <div className="public-trader-pokemon-card-border">
          <div className="public-trader-pokemon-card-content">
            {/* Top Section: Avatar, Name, and Status */}
            <div className="public-trader-pokemon-card-top">
              <div className="public-trader-pokemon-title-section">
                <div className="public-trader-avatar-wrapper">
                  {profile.avatar_url ? (
                    <img src={profile.avatar_url} alt={profile.alias} className="public-trader-avatar" />
                  ) : (
                    <div className="public-trader-avatar-placeholder">
                      {profile.alias.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
                
                <div className="public-trader-info">
                  <h1 className="public-trader-pokemon-name">{profile.alias}</h1>
                  <p className="public-trader-pokemon-subtitle">Trader Performance Card</p>
                  
                  <div className="public-trader-badges">
                    {profile.is_private && (
                      <span className="public-trader-badge private">Private Profile</span>
                    )}
                    {token && !profile.is_private && (
                      <span className="public-trader-badge granted">Full Access</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Rank Badge */}
              {profile.server_rank && (
                <div className="public-trader-rank-badge">
                  <div className="public-trader-rank-circle">
                    <div className="public-trader-rank-value">#{profile.server_rank}</div>
                    <div className="public-trader-rank-label">Server Rank</div>
                  </div>
                </div>
              )}
            </div>

            {/* Server Info */}
            {profile.server_name && (
              <div className="public-trader-server-info">
                <span className="public-trader-server-name">{profile.server_name}</span>
                {profile.contribution_percentage !== null && (
                  <>
                    <span className="public-trader-meta-divider">•</span>
                    <span className="public-trader-contribution">{profile.contribution_percentage.toFixed(1)}% contribution</span>
                  </>
                )}
                {profile.active_period && (
                  <>
                    <span className="public-trader-meta-divider">•</span>
                    <span className="public-trader-status">{profile.active_period}</span>
                  </>
                )}
              </div>
            )}

            {/* Radial Progress Chart - Approval Rate */}
            {profile.approval_rate !== null && profile.approval_rate !== undefined && (
              <div className="public-trader-radial-chart-section">
                <ResponsiveContainer width="100%" height={200}>
                  <RadialBarChart
                    cx="50%"
                    cy="50%"
                    innerRadius="60%"
                    outerRadius="90%"
                    barSize={16}
                    data={[
                      {
                        name: 'Approval Rate',
                        value: profile.approval_rate,
                        fill: profile.approval_rate >= 90 ? '#4caf50' : profile.approval_rate >= 70 ? '#0066ff' : '#ff9800'
                      }
                    ]}
                    startAngle={90}
                    endAngle={-270}
                  >
                    <RadialBar
                      minAngle={15}
                      background={{ fill: 'rgba(255, 255, 255, 0.1)' }}
                      clockWise
                      dataKey="value"
                      cornerRadius={10}
                    />
                    <text
                      x="50%"
                      y="45%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      style={{
                        fontSize: '32px',
                        fontWeight: 'bold',
                        fill: '#fff'
                      }}
                    >
                      {profile.approval_rate}%
                    </text>
                    <text
                      x="50%"
                      y="60%"
                      textAnchor="middle"
                      dominantBaseline="middle"
                      style={{
                        fontSize: '12px',
                        fill: 'rgba(255, 255, 255, 0.7)'
                      }}
                    >
                      Approval Rate
                    </text>
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Key Stats */}
            {(profile.lifetime_volume !== null || profile.total_verified_payout_count !== null) && (
              <div className="public-trader-pokemon-stats-section">
                <div className="public-trader-pokemon-stat-row">
                  <div className="public-trader-pokemon-stat">
                    <span className="public-trader-stat-label">Total Volume</span>
                    <span className="public-trader-stat-value">
                      {profile.lifetime_volume !== null && profile.lifetime_volume !== undefined
                        ? `$${profile.lifetime_volume.toLocaleString()}`
                        : profile.lifetime_volume_range || 'Private'}
                    </span>
                  </div>
                  <div className="public-trader-pokemon-stat">
                    <span className="public-trader-stat-label">Total Payouts</span>
                    <span className="public-trader-stat-value">
                      {profile.total_verified_payout_count !== null && profile.total_verified_payout_count !== undefined
                        ? profile.total_verified_payout_count
                        : 'Private'}
                    </span>
                  </div>
                </div>
                <div className="public-trader-pokemon-stat-row">
                  <div className="public-trader-pokemon-stat">
                    <span className="public-trader-stat-label">Largest Win</span>
                    <span className="public-trader-stat-value">
                      {profile.largest_verified_payout !== null && profile.largest_verified_payout !== undefined
                        ? `$${profile.largest_verified_payout.toLocaleString()}`
                        : 'Private'}
                    </span>
                  </div>
                  <div className="public-trader-pokemon-stat">
                    <span className="public-trader-stat-label">Activity</span>
                    <span className="public-trader-stat-value" style={{ fontSize: '14px' }}>
                      {profile.active_period ? profile.active_period.replace('Active in last ', '').replace(' days', 'd') : 'Unknown'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Action Button */}
            <div className="public-trader-pokemon-actions">
              <button className="public-trader-btn-back" onClick={() => navigate(-1)}>
                Back
              </button>
            </div>

            {/* Holographic Shine Effect */}
            <div className="public-trader-pokemon-card-shine"></div>
          </div>
        </div>
      </div>

      {/* View Selector Tabs */}
      <div className="analytics-view-selector">
        <ViewTab
          active={selectedView === 'overview'}
          onClick={() => changeView('overview')}
          label="Overview"
        />
        <ViewTab
          active={selectedView === 'performance'}
          onClick={() => changeView('performance')}
          label="Performance"
        />
        <ViewTab
          active={selectedView === 'payouts'}
          onClick={() => changeView('payouts')}
          label="Payout Feed"
        />
        <ViewTab
          active={selectedView === 'achievements'}
          onClick={() => changeView('achievements')}
          label="Achievements"
        />
      </div>

      {/* Content */}
      {selectedView === 'overview' && (
        <TraderOverview profile={profile} token={token} />
      )}
      {selectedView === 'performance' && (
        <TraderPerformance profile={profile} token={token} />
      )}
      {selectedView === 'payouts' && (
        <TraderPayouts profile={profile} token={token} />
      )}
      {selectedView === 'achievements' && (
        <TraderAchievements profile={profile} token={token} />
      )}
    </div>
  );
};

// ViewTab Component - Simple button matching Analytics
const ViewTab = ({ active, onClick, label }) => (
  <button
    className={`view-tab ${active ? 'active' : ''}`}
    onClick={onClick}
  >
    {label}
  </button>
);

// Section Component - Matches Analytics Section wrapper
const Section = ({ title, children }) => {
  const [ref, isVisible] = useScrollAnimation();
  
  return (
    <div ref={ref} className={`analytics-section scroll-animate ${isVisible ? 'visible' : ''}`}>
      {title && <h3 className="section-title">{title}</h3>}
      {children}
    </div>
  );
};

// MetricCard Component - Matches Analytics MetricCard exactly
const MetricCard = ({ icon, title, value, subtitle, index = 0 }) => {
  const [ref, isVisible] = useScrollAnimation();
  
  return (
    <div
      ref={ref}
      className={`analytics-stat-card scroll-animate ${isVisible ? 'visible' : ''}`}
      style={{ 
        animationDelay: `${index * 100}ms`,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '20px'
      }}
    >
      {icon && <div className="stat-icon">{icon}</div>}
      <div className="stat-content" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <h4 style={{ margin: 0, fontSize: '14px', color: '#fff', fontWeight: '500' }}>{title}</h4>
        <p className="stat-value" style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', color: '#fff' }}>{value}</p>
        {subtitle && <p className="stat-subtitle" style={{ margin: 0, fontSize: '12px', color: '#fff', opacity: 0.7 }}>{subtitle}</p>}
      </div>
    </div>
  );
};

// TraderOverview Component
const TraderOverview = ({ profile, token }) => {
  return (
    <div>
      {/* Key Metrics */}
      <Section title="Performance Overview">
        <div className="analytics-stats-grid">
          <MetricCard
            title="Total Volume"
            value={profile.lifetime_volume !== null && profile.lifetime_volume !== undefined
              ? `$${profile.lifetime_volume.toLocaleString()}`
              : (profile.lifetime_volume_range || 'Private')}
            subtitle={`${profile.total_verified_payout_count || 0} verified payouts`}
            index={0}
          />
          <MetricCard
            title="Largest Singular Payout"
            value={profile.largest_verified_payout !== null && profile.largest_verified_payout !== undefined
              ? `$${profile.largest_verified_payout.toLocaleString()}`
              : 'Private'}
            subtitle="Best single payout"
            index={1}
          />
          <MetricCard
            title="Approval Rate"
            value={profile.approval_rate !== null && profile.approval_rate !== undefined
              ? `${profile.approval_rate}%`
              : 'Private'}
            subtitle="Submission success rate"
            index={2}
          />
          <MetricCard
            title="Activity Status"
            value={profile.active_period || 'Unknown'}
            subtitle="Recent activity"
            index={3}
          />
        </div>
      </Section>

      {/* Activity Status */}
      {profile.active_period && (
        <Section title="Activity Status">
          <div style={{
            background: 'rgba(0, 102, 255, 0.05)',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid rgba(0, 102, 255, 0.1)'
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              <div>
                <p style={{ color: '#999', marginBottom: '8px' }}>Status</p>
                <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#0066ff' }}>
                  {profile.active_period}
                </p>
              </div>
              {profile.public_achievements && profile.public_achievements.length > 0 && (
                <div>
                  <p style={{ color: '#999', marginBottom: '8px' }}>Achievements</p>
                  <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#4caf50' }}>
                    {profile.public_achievements.length} Unlocked
                  </p>
                </div>
              )}
            </div>
          </div>
        </Section>
      )}
    </div>
  );
};

// TraderPerformance Component
const TraderPerformance = ({ profile }) => {
  const chartData = profile.chart_data || {};
  const payoutTimeline = chartData.payout_timeline || [];
  const marketBreakdown = Object.entries(chartData.market_breakdown || {}).map(([category, data]) => ({
    market_category: category,
    ...data
  }));
  const accuracyHistory = chartData.submission_accuracy_history || [];

  return (
    <div>
      {/* Payout Timeline Chart */}
      {payoutTimeline.length > 0 && (
        <Section title="Payout Timeline">
          <div style={{
            background: 'rgba(0, 102, 255, 0.05)',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid rgba(0, 102, 255, 0.1)'
          }}>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={payoutTimeline}>
                <defs>
                  <linearGradient id="payoutGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0066ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                <XAxis dataKey="date" stroke="#999" />
                <YAxis stroke="#999" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    border: '1px solid rgba(0, 102, 255, 0.5)',
                    borderRadius: '8px',
                    color: '#fff'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#0066ff"
                  strokeWidth={2}
                  fill="url(#payoutGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}

      {/* Market Breakdown */}
      {marketBreakdown.length > 0 && (
        <Section title="Market Breakdown">
          <div style={{
            background: 'rgba(0, 102, 255, 0.05)',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid rgba(0, 102, 255, 0.1)'
          }}>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={marketBreakdown}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ market_category, percentage }) => percentage > 5 ? `${market_category} ${percentage.toFixed(1)}%` : ''}
                  outerRadius={120}
                  innerRadius={60}
                  fill="#8884d8"
                  dataKey="volume"
                  nameKey="market_category"
                >
                  {marketBreakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={['#0066ff', '#00b4d8', '#90e0ef', '#caf0f8', '#48cae4'][index % 5]} />
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
                          <p style={{ color: 'white', margin: '0 0 8px 0', fontWeight: 'bold' }}>{data.market_category}</p>
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
          </div>
        </Section>
      )}

      {/* Submission Accuracy History */}
      {accuracyHistory.length > 0 && (
        <Section title="Submission Accuracy">
          <div style={{
            background: 'rgba(0, 102, 255, 0.05)',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid rgba(0, 102, 255, 0.1)'
          }}>
            <ResponsiveContainer width="100%" height={400}>
              <AreaChart data={accuracyHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                <XAxis dataKey="month" stroke="#999" />
                <YAxis stroke="#999" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    border: '1px solid rgba(0, 102, 255, 0.5)',
                    borderRadius: '8px',
                    color: '#fff'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="accuracy_rate"
                  stroke="#4caf50"
                  strokeWidth={2}
                  fill="rgba(76, 175, 80, 0.1)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Section>
      )}
    </div>
  );
};

// TraderPayouts Component
const TraderPayouts = ({ profile }) => {
  const payouts = profile.recent_payouts || [];
  const [expandedScreenshots, setExpandedScreenshots] = useState({});

  const toggleScreenshot = (payoutId) => {
    setExpandedScreenshots(prev => ({
      ...prev,
      [payoutId]: !prev[payoutId]
    }));
  };

  if (payouts.length === 0) {
    return (
      <Section title="Payout Feed">
        <div style={{
          background: 'rgba(0, 102, 255, 0.05)',
          borderRadius: '12px',
          padding: '40px',
          textAlign: 'center',
          border: '1px solid rgba(0, 102, 255, 0.1)'
        }}>
          <p style={{ color: '#fff', fontSize: '16px' }}>No payouts yet</p>
        </div>
      </Section>
    );
  }

  return (
    <Section title="Payout Feed">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {payouts.map((payout, idx) => (
          <div
            key={payout.id || idx}
            className="scroll-animate"
            style={{
              background: 'rgba(0, 102, 255, 0.05)',
              borderRadius: '12px',
              padding: '20px',
              border: '1px solid rgba(0, 102, 255, 0.1)',
              animationDelay: `${idx * 50}ms`
            }}
          >
            <div style={{ 
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: payout.screenshot_url ? '16px' : '0'
            }}>
              <div>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '18px' }}>{payout.firm_name || 'Unknown Firm'}</h4>
                <p style={{ margin: 0, color: '#fff', fontSize: '14px' }}>
                  {new Date(payout.payout_date).toLocaleDateString()} • {payout.instrument} • {payout.market_category}
                </p>
                {payout.server_name && (
                  <p style={{ margin: '4px 0 0 0', color: '#fff', fontSize: '12px' }}>
                    Server: {payout.server_name}
                  </p>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <p style={{ 
                  margin: '0 0 4px 0', 
                  fontSize: '24px', 
                  fontWeight: 'bold',
                  color: '#fff'
                }}>
                  ${payout.amount?.toLocaleString() || '0'}
                </p>
                <span style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  color: '#fff',
                  padding: '4px 12px',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}>
                  Verified
                </span>
              </div>
            </div>
            
            {/* Screenshot Preview */}
            {payout.screenshot_url && (
              <div 
                onClick={() => toggleScreenshot(payout.id)}
                style={{
                  cursor: 'pointer',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: '1px solid rgba(0, 102, 255, 0.2)',
                  position: 'relative'
                }}
              >
                <img 
                  src={payout.screenshot_url} 
                  alt="Payout proof" 
                  style={{
                    width: '100%',
                    height: expandedScreenshots[payout.id] ? 'auto' : '200px',
                    objectFit: expandedScreenshots[payout.id] ? 'contain' : 'cover',
                    filter: expandedScreenshots[payout.id] ? 'none' : 'blur(8px)',
                    transition: 'all 0.3s ease'
                  }}
                />
                {!expandedScreenshots[payout.id] && (
                  <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    background: 'rgba(0, 0, 0, 0.7)',
                    padding: '12px 24px',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px',
                    fontWeight: '500',
                    pointerEvents: 'none'
                  }}>
                    Click to view proof
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
};

// TraderAchievements Component
const TraderAchievements = ({ profile }) => {
  const achievements = profile.public_achievements || [];

  return (
    <div>
      <Section title="Achievements & Milestones">
        <div className="analytics-stats-grid">
          <MetricCard
            title="Total Achievements"
            value={achievements.length}
            subtitle="Milestones unlocked"
            index={0}
          />
          <MetricCard
            title="Server Rank"
            value={profile.server_rank ? `#${profile.server_rank}` : 'N/A'}
            subtitle="Position in server"
            index={1}
          />
          <MetricCard
            title="Activity Status"
            value={profile.active_period || 'N/A'}
            subtitle="Recent activity"
            index={2}
          />
          <MetricCard
            title="Approval Rate"
            value={`${profile.approval_rate || 0}%`}
            subtitle="Verification accuracy"
            index={3}
          />
        </div>
      </Section>

      {achievements.length > 0 && (
        <Section title="Achievements">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
            {achievements.map((achievement, idx) => (
              <div
                key={idx}
                className="scroll-animate"
                style={{
                  background: 'rgba(0, 102, 255, 0.05)',
                  borderRadius: '12px',
                  padding: '24px',
                  border: '1px solid rgba(0, 102, 255, 0.1)',
                  textAlign: 'center',
                  animationDelay: `${idx * 100}ms`,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                <div style={{ 
                  fontSize: '48px', 
                  lineHeight: '1',
                  marginBottom: '8px'
                }}>
                  🏆
                </div>
                <h4 style={{ 
                  margin: '0', 
                  fontSize: '16px', 
                  color: '#fff',
                  fontWeight: '600'
                }}>
                  {achievement}
                </h4>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
};

export default PublicTraderProfile;
