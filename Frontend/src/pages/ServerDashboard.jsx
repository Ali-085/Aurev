/**
 * Server Dashboard
 * 
 * Interactive member/owner dashboard for joined servers.
 * Accessed via: /servers/:serverId/dashboard
 * 
 * Features:
 * - Real-time leaderboard and rankings
 * - Activity heatmaps and statistics
 * - Gallery and community highlights  
 * - Moderation stats
 * - Global server comparisons
 * - Join/leave server functionality
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { analyticsService, serverService } from '../services';
import { useAuth } from '../context/AuthContext';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './ServerDashboard.css';

const ServerDashboard = () => {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  
  const [activeTab, setActiveTab] = useState('overview');
  const [dashboardData, setDashboardData] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [heatmapData, setHeatmapData] = useState([]);
  const [gallery, setGallery] = useState([]);
  const [moderationStats, setModerationStats] = useState(null);
  const [globalComparison, setGlobalComparison] = useState(null);
  const [membership, setMembership] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [joiningServer, setJoiningServer] = useState(false);
  const [leavingServer, setLeavingServer] = useState(false);
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  
  // Fetch dashboard data
  const fetchDashboard = async () => {
    try {
      const data = await analyticsService.getServerDashboard(serverId);
      setDashboardData(data);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
      setError('Failed to load server data');
    }
  };
  
  // Fetch leaderboard
  const fetchLeaderboard = async () => {
    try {
      const data = await analyticsService.getServerLeaderboard(serverId);
      setLeaderboard(data.leaderboard);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };
  
  // Fetch heatmap
  const fetchHeatmap = async () => {
    try {
      const data = await analyticsService.getServerHeatmap(serverId);
      setHeatmapData(data.heatmap);
    } catch (error) {
      console.error('Error fetching heatmap:', error);
    }
  };
  
  // Fetch gallery
  const fetchGallery = async () => {
    try {
      const data = await analyticsService.getServerGallery(serverId);
      setGallery(data.gallery);
    } catch (error) {
      console.error('Error fetching gallery:', error);
    }
  };
  
  // Fetch moderation stats
  const fetchModerationStats = async () => {
    try {
      const data = await analyticsService.getServerModerationStats(serverId);
      setModerationStats(data);
    } catch (error) {
      console.error('Error fetching moderation stats:', error);
    }
  };
  
  // Fetch global comparison
  const fetchGlobalComparison = async () => {
    try {
      const data = await analyticsService.getGlobalComparison(serverId);
      setGlobalComparison(data);
    } catch (error) {
      console.error('Error fetching global comparison:', error);
    }
  };
  
  // Check membership status
  const checkMembership = async () => {
    try {
      const membershipData = await serverService.checkMembership(serverId);
      
      // Check if user is owner and Elite subscription status
      if (isAuthenticated && dashboardData?.server && user) {
        membershipData.is_owner = dashboardData.server.owner_user?.id === user.id;
        
        // Check Elite subscription
        try {
          const subscriptionData = await analyticsService.getUserSubscription(dashboardData.server.id);
          membershipData.is_elite = subscriptionData.is_elite;
        } catch (subError) {
          membershipData.is_elite = false;
        }
      }
      
      setMembership(membershipData);
    } catch (error) {
      console.error('Error checking membership:', error);
    }
  };
  
  // Join server
  const handleJoinServer = async () => {
    if (!isAuthenticated) {
      alert('Please login to join this server');
      navigate('/login');
      return;
    }
    
    setJoiningServer(true);
    try {
      const data = await serverService.joinServer(serverId);
      alert(data.message);
      checkMembership(); // Refresh membership status
    } catch (error) {
      console.error('Error joining server:', error);
      alert(error.response?.data?.error || 'Failed to join server');
    } finally {
      setJoiningServer(false);
    }
  };
  
  // Navigate to payout submission page with this server pre-selected
  const handleSubmitPayout = () => {
    navigate('/payouts', { state: { preselectedServer: dashboardData?.server.id } });
  };
  
  // Leave server handler
  const handleLeaveServer = async () => {
    if (!isAuthenticated) {
      alert('Please login to leave this server');
      navigate('/login');
      return;
    }
    
    setLeavingServer(true);
    try {
      const data = await serverService.leaveServer(serverId);
      
      // Show success message
      alert(data.message || 'Successfully left the server');
      
      // Close modal
      setShowLeaveModal(false);
      
      // Redirect to joined servers page or home
      navigate('/joined-servers');
      
    } catch (error) {
      console.error('Error leaving server:', error);
      
      // Show error message
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.detail || 
                       'Failed to leave server. Please try again.';
      alert(errorMsg);
      
      setLeavingServer(false);
      setShowLeaveModal(false);
    }
  };
  
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchDashboard();
      await fetchLeaderboard();
      await checkMembership();
      setLoading(false);
    };
    
    loadData();
  }, [serverId]);
  
  useEffect(() => {
    // Load additional data based on active tab
    if (activeTab === 'heatmap' && heatmapData.length === 0) {
      fetchHeatmap();
    } else if (activeTab === 'gallery' && gallery.length === 0) {
      fetchGallery();
    } else if (activeTab === 'moderation' && !moderationStats) {
      fetchModerationStats();
    } else if (activeTab === 'comparison' && !globalComparison) {
      fetchGlobalComparison();
    }
  }, [activeTab]);
  
  if (loading) {
    return (
      <div className="server-view-loading">
        <div className="spinner"></div>
        <p>Loading server data...</p>
      </div>
    );
  }
  
  if (error || !dashboardData) {
    return (
      <div className="server-view-error">
        <h2>Error</h2>
        <p>{error || 'Server not found'}</p>
      </div>
    );
  }
  
  // Redirect non-members to public view
 /* if (membership !== null && !membership.is_member && !membership.is_owner) {
    navigate(`/servers/${serverId}/public`, { replace: true });
    return null;
  }
  */
  const { server, stats, graphs, breakdowns, top_day, rankings } = dashboardData;
  
  // Colors for pie chart - matching Analytics
  const COLORS = ['#0066ff', '#00b4d8', '#90e0ef', '#caf0f8', '#48cae4'];
  
  // Custom tooltip styling to match Analytics
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
    <div className="server-view">
      {/* Header */}
      <div className="server-header">
        <div className="server-info">
          <h1>
            <Link 
              to={server.profile_url || `/servers/${server.id}/public`}
              style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              {server.name}
            </Link>
          </h1>
          {server.is_verified && <span className="ser-dash-verified-badge">Verified</span>}
          <p className="server-description">{server.description}</p>
          <div className="server-meta">
            <span className="ser-dash-platform-badge">{server.platform}</span>
            <span className="created-date">Created {new Date(server.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        
        {/* Owner Action Buttons */}
        {membership?.is_owner && (
          <div className="owner-actions">
            <button 
              className="btn-settings"
              onClick={() => navigate(`/servers/${serverId}/settings`)}
            >
              ⚙️ Server Settings
            </button>
            {membership?.is_elite && (
              <button 
                className="btn-elite-settings"
                onClick={() => navigate(`/servers/${serverId}/branding`)}
              >
                ✨ Elite Branding
              </button>
            )}
          </div>
        )}
      </div>

      {/* Key Stats */}
      <div className="key-stats">
          <div className="stat-card">
            <div className="stat-value">${stats.total_volume.toLocaleString()}</div>
            <div className="stat-label">Total Payout Volume</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.total_submissions}</div>
            <div className="stat-label">Total Payouts</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.unique_traders}</div>
            <div className="stat-label">Total Traders</div>
          </div>
          {rankings.global_rank && (
            <div className="stat-card rank-card">
              <div className="stat-value">#{rankings.global_rank}</div>
              <div className="stat-label">Global Rank</div>
            </div>
          )}
      </div>
      
      {/* Member Actions */}
      {membership && (
        <div className="member-actions">
          {!membership.is_member ? (
            <button onClick={handleJoinServer} className="btn btn-join" disabled={joiningServer}>
              {joiningServer ? 'Joining...' : '+ Join Server'}
            </button>
          ) : (
            <>
              {membership.can_submit && (
                <button onClick={handleSubmitPayout} className="server-dashboard-btn ser-das-btn-submit">
                  Submit Payout
                </button>
              )}
              {/* Leave Server button - only shown to members who are not owners */}
              {!membership.is_owner && (
                <button 
                  onClick={() => setShowLeaveModal(true)} 
                  className="server-dashboard-btn ser-das-btn-leave"
                  disabled={leavingServer}
                >
                  {leavingServer ? 'Leaving...' : 'Leave Server'}
                </button>
              )}
              {!membership.can_submit && (
                <div className="info-message">
                  {membership.message}
                </div>
              )}
            </>
          )}
        </div>
      )}
      
      {/* Navigation Tabs */}
      <div className="server-tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
        >
          Leaderboard
        </button>
        <button
          className={`tab ${activeTab === 'heatmap' ? 'active' : ''}`}
          onClick={() => setActiveTab('heatmap')}
        >
          Activity Heatmap
        </button>
        <button
          className={`tab ${activeTab === 'gallery' ? 'active' : ''}`}
          onClick={() => setActiveTab('gallery')}
        >
          Screenshot Gallery
        </button>
        <button
          className={`tab ${activeTab === 'moderation' ? 'active' : ''}`}
          onClick={() => setActiveTab('moderation')}
        >
          Moderation Stats
        </button>
        <button
          className={`tab ${activeTab === 'comparison' ? 'active' : ''}`}
          onClick={() => setActiveTab('comparison')}
        >
          Global Comparison
        </button>
      </div>
      
      {/* Tab Content */}
      <div className="tab-content">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="overview-tab">
            {/* Recent Activity */}
            <div className="recent-activity">
              <h2>Recent Activity (Last 7 Days)</h2>
              <div className="activity-cards">
                <div className="activity-card">
                  <div className="activity-value">${stats.recent_volume_7d.toLocaleString()}</div>
                  <div className="activity-label">Volume</div>
                </div>
                <div className="activity-card">
                  <div className="activity-value">{stats.recent_count_7d}</div>
                  <div className="activity-label">Submissions</div>
                </div>
              </div>
            </div>
            
            {/* Graphs */}
            <div className="graphs-section">
              {/* Daily Graph */}
              <div className="graph-container">
                <h3>Daily Volume (Last 30 Days)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={graphs.daily}>
                    <defs>
                      <linearGradient id="colorDailyVolume" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0066ff" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#0066ff" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                    <XAxis 
                      dataKey="date" 
                      tickFormatter={(date) => new Date(date).toLocaleDateString()}
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
                      fill="url(#colorDailyVolume)"
                      name="Volume" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              
              {/* Weekly Graph */}
              <div className="graph-container">
                <h3>Weekly Volume (Last 12 Weeks)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={graphs.weekly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 102, 255, 0.1)" />
                    <XAxis 
                      dataKey="week_start" 
                      tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      stroke="rgba(100, 149, 237, 0.7)" 
                      style={{ fontSize: '12px' }}
                    />
                    <YAxis 
                      stroke="rgba(100, 149, 237, 0.7)" 
                      style={{ fontSize: '12px' }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={false} />
                    <Bar 
                      dataKey="volume" 
                      fill="#0066ff" 
                      name="Volume" 
                      radius={[8, 8, 0, 0]}
                      activeBar={false}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              
              {/* Monthly Graph */}
              <div className="graph-container">
                <h3>Monthly Volume (Last 12 Months)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={graphs.monthly}>
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
                    <Tooltip content={<CustomTooltip />} cursor={false} />
                    <Bar 
                      dataKey="volume" 
                      fill="#0066ff" 
                      name="Volume" 
                      radius={[8, 8, 0, 0]}
                      activeBar={false}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            {/* Market Breakdown */}
            <div className="breakdowns-section">
              <div className="breakdown-container">
                <h3>Market Breakdown</h3>
                {breakdowns.markets.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={350}>
                      <PieChart>
                        <Pie
                          data={breakdowns.markets}
                          dataKey="volume"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          outerRadius={120}
                          innerRadius={60}
                          labelLine={false}
                          label={({ category, percentage }) => percentage > 5 ? `${category} ${percentage.toFixed(1)}%` : ''}
                        >
                          {breakdowns.markets.map((entry, index) => (
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
                    <div className="market-legend">
                      {breakdowns.markets.map((market, index) => (
                        <div key={index} className="legend-item">
                          <span className="legend-color" style={{ backgroundColor: COLORS[index % COLORS.length] }}></span>
                          <span className="legend-label">{market.category}</span>
                          <span className="legend-value">${market.volume.toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="no-data">No market data available</div>
                )}
              </div>
              
              {/* Top Instruments */}
              <div className="breakdown-container">
                <h3>Top Instruments</h3>
                {breakdowns.instruments.length > 0 ? (
                  <div className="instruments-list">
                    {breakdowns.instruments.map((instrument, index) => (
                      <div key={index} className="instrument-item">
                        <div className="instrument-rank">#{index + 1}</div>
                        <div className="instrument-name">{instrument.instrument}</div>
                        <div className="instrument-stats">
                          <span className="instrument-volume">${instrument.volume.toLocaleString()}</span>
                          <span className="instrument-count">{instrument.count} payouts</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-data">No instrument data available</div>
                )}
              </div>
            </div>
            
            {/* Top Day */}
            {top_day && (
              <div className="top-day-section">
                <h3>Best Performance Day</h3>
                <div className="top-day-card">
                  <div className="top-day-date">{new Date(top_day.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
                  <div className="top-day-volume">${top_day.volume.toLocaleString()}</div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <div className="leaderboard-tab">
            <h2>Top Traders</h2>
            <div className="leaderboard-table">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Trader</th>
                    <th>Total Volume</th>
                    <th>Submissions</th>
                    <th>Best Market</th>
                    <th>Best Instrument</th>
                    <th>Recent Activity</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((trader) => (
                    <tr key={trader.rank} className={trader.rank <= 3 ? `top-${trader.rank}` : ''}>
                      <td className="rank-cell">
                        {trader.rank <= 3 && <span className="medal"></span>}
                        #{trader.rank}
                      </td>
                      <td className="username-cell">
                        <Link 
                          to={trader.profile_url || `/trader/${trader.user_id}/public`}
                          style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                        >
                          {trader.username}
                        </Link>
                      </td>
                      <td className="volume-cell">${trader.total_volume.toLocaleString()}</td>
                      <td>{trader.total_submissions}</td>
                      <td><span className="badge">{trader.best_market || 'N/A'}</span></td>
                      <td>{trader.best_instrument || 'N/A'}</td>
                      <td>{trader.recent_submissions_30d} (30d)</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {/* Heatmap Tab */}
        {activeTab === 'heatmap' && (
          <div className="heatmap-tab">
            <h2>Submission Activity Heatmap</h2>
            <p className="heatmap-description">Shows when traders are most active (last 90 days)</p>
            <div className="heatmap-container">
              {heatmapData.length > 0 ? (
                <div className="heatmap-grid">
                  <div className="heatmap-hours">
                    {[...Array(24)].map((_, hour) => (
                      <div key={hour} className="hour-label">{hour}:00</div>
                    ))}
                  </div>
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => (
                    <div key={day} className="heatmap-row">
                      <div className="day-label">{day}</div>
                      <div className="hour-cells">
                        {[...Array(24)].map((_, hour) => {
                          const cell = heatmapData.find(d => d.day === day && d.hour === hour);
                          const count = cell ? cell.count : 0;
                          const intensity = Math.min(count / 5, 1); // Normalize to 0-1
                          return (
                            <div
                              key={hour}
                              className="heatmap-cell"
                              style={{
                                backgroundColor: `rgba(76, 175, 80, ${intensity})`,
                                border: '1px solid #e5e5e5'
                              }}
                              title={`${day} ${hour}:00 - ${count} submissions`}
                            >
                              {count > 0 && <span className="cell-count">{count}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-data">Loading heatmap...</div>
              )}
            </div>
          </div>
        )}
        
        {/* Gallery Tab */}
        {activeTab === 'gallery' && (
          <div className="gallery-tab">
            <h2>Screenshot Gallery</h2>
            <div className="gallery-grid">
              {gallery.map((item) => (
                <div key={item.id} className="gallery-item">
                  <div className="payout-screenshot">
                    {item.screenshot ? (
                      <div className="screenshot-preview">
                        <img 
                          src={item.screenshot} 
                          alt={`Payout ${item.id}`}
                          className="blurred-screenshot"
                          onClick={(e) => {
                            e.currentTarget.classList.toggle('blurred-screenshot');
                            e.currentTarget.classList.toggle('unblurred-screenshot');
                          }}
                        />
                        <div className="screenshot-overlay">
                          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                            <circle cx="12" cy="12" r="3"/>
                          </svg>
                          <span>Click to view</span>
                        </div>
                      </div>
                    ) : (
                      <div className="screenshot-placeholder">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                          <circle cx="8.5" cy="8.5" r="1.5"/>
                          <polyline points="21 15 16 10 5 21"/>
                        </svg>
                      </div>
                    )}
                    <div className="verification-badge">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                      </svg>
                      Verified
                    </div>
                  </div>
                  <div className="gallery-overlay">
                    <div className="gallery-amount">${item.amount.toLocaleString()} {item.currency}</div>
                    <div className="gallery-details">
                      <span className="gallery-market">{item.market}</span>
                      <span className="gallery-instrument">{item.instrument}</span>
                    </div>
                    <div className="gallery-user">
                      <Link 
                        to={item.profile_url || `/trader/${item.user_id}/public`}
                        style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                      >
                        {item.username}
                      </Link>
                    </div>
                    <div className="gallery-date">{new Date(item.payout_date).toLocaleDateString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Moderation Tab */}
        {activeTab === 'moderation' && moderationStats && (
          <div className="moderation-tab">
            <h2>Moderation Transparency</h2>
            
            <div className="moderation-stats">
              <div className="mod-stat-card">
                <div className="mod-stat-value">{moderationStats.stats.approval_rate}%</div>
                <div className="mod-stat-label">Approval Rate</div>
              </div>
              <div className="mod-stat-card">
                <div className="mod-stat-value">{moderationStats.stats.avg_review_time_hours.toFixed(1)}h</div>
                <div className="mod-stat-label">Avg Review Time</div>
              </div>
              <div className="mod-stat-card">
                <div className="mod-stat-value">{moderationStats.stats.approved}</div>
                <div className="mod-stat-label">Approved</div>
              </div>
              <div className="mod-stat-card">
                <div className="mod-stat-value">{moderationStats.stats.rejected}</div>
                <div className="mod-stat-label">Rejected</div>
              </div>
            </div>
            
            {moderationStats.top_rejection_reasons.length > 0 && (
              <div className="rejection-reasons">
                <h3>Top Rejection Reasons</h3>
                {moderationStats.top_rejection_reasons.map((reason, index) => (
                  <div key={index} className="reason-item">
                    <span className="reason-text">{reason.reason}</span>
                    <span className="reason-count">{reason.count} times</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Comparison Tab */}
        {activeTab === 'comparison' && globalComparison && (
          <div className="comparison-tab">
            <h2>Global Comparison</h2>
            
            <div className="comparison-stats">
              <div className="comparison-card">
                <h3>Volume Ranking</h3>
                <div className="comparison-value">Top {globalComparison.comparison.volume_percentile.toFixed(0)}%</div>
                <div className="comparison-detail">
                  ${Math.abs(globalComparison.comparison.volume_vs_avg).toLocaleString()} 
                  {globalComparison.comparison.volume_vs_avg >= 0 ? ' above' : ' below'} average
                </div>
              </div>
              
              <div className="comparison-card">
                <h3>Payout Count Ranking</h3>
                <div className="comparison-value">Top {globalComparison.comparison.payouts_percentile.toFixed(0)}%</div>
                <div className="comparison-detail">
                  {Math.abs(globalComparison.comparison.payouts_vs_avg).toFixed(0)} 
                  {globalComparison.comparison.payouts_vs_avg >= 0 ? ' above' : ' below'} average
                </div>
              </div>
            </div>
            
            <div className="top-10-section">
              <h3>Top 10 Servers</h3>
              <div className="top-10-list">
                {globalComparison.top_10.map((server) => (
                  <div key={server.rank} className="top-10-item">
                    <span className="top-10-rank">#{server.rank}</span>
                    <span className="top-10-name">{server.name}</span>
                    <span className="top-10-volume">${server.volume.toLocaleString()}</span>
                    <span className="top-10-payouts">{server.payouts} payouts</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Leave Server Confirmation Modal */}
      {showLeaveModal && (
        <div className="modal-overlay" onClick={() => !leavingServer && setShowLeaveModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Leave Server?</h2>
              <button 
                className="modal-close" 
                onClick={() => setShowLeaveModal(false)}
                disabled={leavingServer}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p>Are you sure you want to leave <strong>{server?.name}</strong>?</p>
              <p className="modal-warning">You will lose access immediately and will need to rejoin to submit payouts or view member content.</p>
            </div>
            <div className="modal-actions">
              <button 
                className="btn-modal-cancel" 
                onClick={() => setShowLeaveModal(false)}
                disabled={leavingServer}
              >
                Cancel
              </button>
              <button 
                className="btn-modal-confirm" 
                onClick={handleLeaveServer}
                disabled={leavingServer}
              >
                {leavingServer ? 'Leaving...' : 'Leave Server'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServerDashboard;
