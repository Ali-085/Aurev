/**
 * Server Leaderboard Page
 * 
 * Displays servers ranked by comprehensive scoring algorithm:
 * - Performance Score (20%): Log-scaled verified payout volume + percentage growth
 * - Engagement Score (20%): Active traders, submission frequency, consistency, approval rate
 * - Verification Quality (20%): Low fake rates, screenshot clarity, approval accuracy
 * - Diversity Score (20%): Market variety, trader count, instrument spread, multi-category
 * 
 * SECURITY:
 * - Public view for all servers
 * - Protected actions for authenticated users
 * - Server owner verification for edits
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

import './Servers.css';

const Servers = () => {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [availablePlatforms, setAvailablePlatforms] = useState([]);
  const [sortBy, setSortBy] = useState('rank'); // rank, performance, engagement, quality, diversity

  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchServers();
    fetchPlatforms();
  }, [sortBy]); // Refetch when sort changes

  const fetchPlatforms = async () => {
    try {
      const response = await api.get('/platform-admin/platforms/?active_only=true');
      setAvailablePlatforms(response.data.map(p => p.name));
    } catch (err) {
      console.error('Failed to fetch platforms:', err);
    }
  };

  const fetchServers = async () => {
    try {
      setLoading(true);
      // Fetch from analytics endpoint: returns GLOBAL rankings
      // sort_by matches backend keys: rank, performance, engagement, quality, diversity
      let sortParam = 'score'; // default to rank
      if (sortBy === 'performance') sortParam = 'performance';
      if (sortBy === 'engagement') sortParam = 'engagement';
      if (sortBy === 'quality') sortParam = 'quality';
      if (sortBy === 'diversity') sortParam = 'diversity';

      const response = await api.get(`/analytics/top-servers/?sort_by=${sortParam}&limit=100`);

      // The endpoint returns array directly, not wrapped in 'leaderboard'
      const data = Array.isArray(response.data) ? response.data : [];

      // Map analytics structure to ServerCard expected structure
      const mappedServers = data.map(item => ({
        ...item.server, // id, name, description, platform, etc.
        id: item.server.id,
        is_verified: true,
        member_count: item.metrics?.member_count || item.metrics?.active_submitters_30d || 0,
        total_verified_payouts: item.metrics?.total_volume || 0,
        total_submissions: item.metrics?.total_payouts || 0,
        scores: {
          ...item.scores,
          total: item.total_score // Add total score from root level
        },
        rank_val: item.rank
      }));

      setServers(mappedServers);
      setError('');
    } catch (err) {
      setError('Failed to load servers');
      console.error('Error fetching servers:', err);
    } finally {
      setLoading(false);
    }
  };



  const filteredServers = servers.filter(server => {
    const matchesSearch = server.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (server.description && server.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesPlatform = filterPlatform === 'all' || server.platform === filterPlatform;

    return matchesSearch && matchesPlatform;
  });

  // Backend already sorts, but we keep the list as is (mappedServers) which respects the requested sort.
  const sortedServers = filteredServers;

  const getRankBadge = (index) => {
    if (index === 0) return '';
    if (index === 1) return '';
    if (index === 2) return '';
    return `#${index + 1}`;
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#28a745'; // Green
    if (score >= 60) return '#ffc107'; // Yellow
    if (score >= 40) return '#fd7e14'; // Orange
    return '#dc3545'; // Red
  };

  if (loading) {
    return <div className="servers-loading">Loading servers...</div>;
  }

  return (
    <div className="servers-page">

      {error && (
        <div className="servers-error">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="servers-filters">
        <input
          type="text"
          placeholder="Search servers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <select
          value={filterPlatform}
          onChange={(e) => setFilterPlatform(e.target.value)}
        >
          <option value="all">All Platforms</option>
          {availablePlatforms.map(platform => (
            <option key={platform} value={platform}>{platform}</option>
          ))}
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="rank">Overall Rank</option>
          <option value="performance">Performance Score</option>
          <option value="engagement">Engagement Score</option>
          <option value="quality">Quality Score</option>
          <option value="diversity">Diversity Score</option>
        </select>
      </div>

      {/* Scoring Legend */}
      <div className="servers-legend">
        <h3>Ranking Formula</h3>
        <div className="servers-legend-grid">
          <div><strong>Performance (100):</strong> Log-scaled volume + growth</div>
          <div><strong>Growth (100):</strong> Percentage increase over time</div>
          <div><strong>Engagement (100):</strong> Active traders, frequency, approval rate</div>
          <div><strong>Quality (100):</strong> Low fake rates, clean approvals</div>
          <div><strong>Diversity (100):</strong> Markets, traders, instruments</div>
        </div>
      </div>

      {/* Server List */}
      <div className="servers-list">
        {sortedServers.length === 0 ? (
          <div className="no-servers">
            No servers found
          </div>
        ) : (
          sortedServers.map((server, index) => (
            <ServerCard
              key={server.id}
              server={server}
              rank={getRankBadge(index)}
              getScoreColor={getScoreColor}
              navigate={navigate}
            />
          ))
        )}
      </div>
    </div>
  );
};

const ServerCard = ({ server, rank, getScoreColor, navigate }) => {
  const scores = server.scores;

  // Create unique chart data with server ID to force re-render
  const chartData = [
    { subject: 'Performance', value: Number((scores?.performance || 0).toFixed(2)), id: `${server.id}-perf` },
    { subject: 'Growth', value: Number((scores?.growth || 0).toFixed(2)), id: `${server.id}-grow` },
    { subject: 'Engagement', value: Number((scores?.engagement || 0).toFixed(2)), id: `${server.id}-eng` },
    { subject: 'Quality', value: Number((scores?.quality || 0).toFixed(2)), id: `${server.id}-qual` },
    { subject: 'Diversity', value: Number((scores?.diversity || 0).toFixed(2)), id: `${server.id}-div` }
  ];

  return (
    <div
      className="server-card"
      onClick={() => navigate(`/servers/${server.id}/public`)}
    >
      <div className="server-card-header">
        <div className="server-card-info">
          <div className="server-card-title-row">
            <span className="server-card-rank">{rank}</span>
            <h3>
              {server.name}
              {server.is_verified && <span className="server-card-verified"></span>}
            </h3>
          </div>
          <p className="server-card-description">
            {server.description}
          </p>
          <div className="server-card-meta">
            <span>{server.platform}</span>
            <span>{server.member_count || 0} members</span>
            <span>${server.total_verified_payouts?.toLocaleString() || 0} verified</span>
          </div>
        </div>

        {/* Overall Score */}
        <div className="server-card-score">
          <div className="server-card-score-value" style={{ color: getScoreColor(scores?.total || 0) }}>
            {(scores?.total || 0).toFixed(1)}
          </div>
          <div className="server-card-score-label">Overall Score</div>
        </div>
      </div>

      {/* Score Breakdown - Radar Chart */}
      <div className="server-card-breakdown" onClick={(e) => e.stopPropagation()}>
        <ResponsiveContainer width="100%" height={280} key={`container-${server.id}-${JSON.stringify(chartData)}`}>
          <RadarChart
            cx="50%"
            cy="50%"
            outerRadius="70%"
            data={chartData}
          >
            <PolarGrid
              stroke="rgba(0, 102, 255, 0.2)"
              strokeWidth={1}
            />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: 'rgba(100, 149, 237, 0.9)', fontSize: 13, fontWeight: 500 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: 'rgba(100, 149, 237, 0.6)', fontSize: 10 }}
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
              name={server.name}
              dataKey="value"
              stroke="#0066ff"
              strokeWidth={2}
              fill="#0066ff"
              fillOpacity={0.5}
              dot={{ fill: '#0066ff', r: 4 }}
              isAnimationActive={false}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Servers;
