/**
 * Joined Servers Page
 * 
 * Displays all servers the authenticated user is a member of.
 * Shows server details with quick actions for dashboard access and payout submission.
 * 
 * SECURITY:
 * - Requires authentication
 * - Only shows user's own server memberships
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './JoinedServers.css';

const JoinedServers = () => {
  const [servers, setServers] = useState([]);
  const [filteredServers, setFilteredServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchJoinedServers();
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    // Filter servers based on search term
    if (searchTerm.trim() === '') {
      setFilteredServers(servers);
    } else {
      const filtered = servers.filter(server =>
        server.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredServers(filtered);
    }
  }, [searchTerm, servers]);

  const fetchJoinedServers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/servers/members/my_servers/');
      setServers(response.data);
      setFilteredServers(response.data);
      setError('');
    } catch (err) {
      setError('Failed to load your servers');
      console.error('Error fetching joined servers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDashboard = (serverId) => {
    navigate(`/servers/${serverId}/dashboard`);
  };

  const handleSubmitPayout = (serverId) => {
    navigate('/payouts', { state: { selectedServer: serverId } });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="joined-servers-loading">
        <div className="spinner"></div>
        <h2>Loading your servers...</h2>
      </div>
    );
  }

  return (
    <div className="joined-servers-page">
      {/* Header */}
      <div className="joined-servers-header">
        <div className="header-content">
          <h1>My Servers</h1>
          <p className="subtitle">Servers you are a member of</p>
        </div>
      </div>

      {/* Search Bar */}
      {servers.length > 0 && (
        <div className="search-section">
          <input
            type="text"
            placeholder="Search servers by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredServers.length === 0 && !error && (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
              <circle cx="60" cy="60" r="50" stroke="rgba(0, 102, 255, 0.2)" strokeWidth="2" />
              <path d="M40 60h40M60 40v40" stroke="rgba(0, 102, 255, 0.4)" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
          <h2>No Servers Found</h2>
          <p>
            {searchTerm 
              ? `No servers match "${searchTerm}"`
              : "You haven't joined any servers yet. Browse the server leaderboard to discover and join trading servers!"}
          </p>
          {!searchTerm && (
            <button 
              className="browse-button"
              onClick={() => navigate('/servers')}
            >
              Browse Servers
            </button>
          )}
        </div>
      )}

      {/* Server Cards Grid */}
      {filteredServers.length > 0 && (
        <div className="servers-grid">
          {filteredServers.map((server) => (
            <div key={server.id} className="server-card">
              {/* Card Header with Logo */}
              <div className="card-header">
                <div className="server-logo">
                  {server.logo_url ? (
                    <img src={server.logo_url} alt={server.name} />
                  ) : (
                    <div className="logo-placeholder">
                      {server.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
                <div className="server-info">
                  <h3 className="server-name">{server.name}</h3>
                  <div className="server-meta">
                    <span className="platform-badge">{server.platform}</span>
                    {server.is_verified && (
                      <span className="verified-badge">Verified</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Description */}
              {server.description && (
                <p className="server-description">
                  {server.description.length > 120
                    ? `${server.description.substring(0, 120)}...`
                    : server.description}
                </p>
              )}

              {/* Membership Stats */}
              <div className="membership-stats">
                <div className="stat-item">
                  <span className="stat-label">Joined</span>
                  <span className="stat-value">
                    {formatDate(server.membership.joined_at)}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Your Payouts</span>
                  <span className="stat-value">
                    {formatAmount(server.membership.total_verified_payouts)}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Submissions</span>
                  <span className="stat-value">
                    {server.membership.total_submissions}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="card-actions">
                <button
                  className="btn-dashboard"
                  onClick={() => handleViewDashboard(server.id)}
                >
                  View Dashboard
                </button>
                <button
                  className="btn-submit"
                  onClick={() => handleSubmitPayout(server.id)}
                >
                  Submit Payout
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JoinedServers;
