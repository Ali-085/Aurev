import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { adminService } from '../services';
import PayoutReviewModal from '../components/PayoutReviewModal';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [pendingSubmissions, setPendingSubmissions] = useState([]);
  const [suspiciousSubmissions, setSuspiciousSubmissions] = useState([]);
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [serverAnalytics, setServerAnalytics] = useState(null);
  const [memberProfile, setMemberProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Review modal state
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [submissionDetail, setSubmissionDetail] = useState(null);
  
  // Filters
  const [serverFilter, setServerFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [amountFilter, setAmountFilter] = useState('all');
  
  // Pause modal state
  const [pauseModal, setPauseModal] = useState({ show: false, serverId: null, serverName: '' });
  const [pauseReason, setPauseReason] = useState('');
  const [notification, setNotification] = useState({ show: false, message: '', type: '' });
  
  useEffect(() => {
    if (activeTab === 'overview') {
      fetchOverview();
    } else if (activeTab === 'pending') {
      fetchPendingSubmissions();
    } else if (activeTab === 'suspicious') {
      fetchSuspiciousSubmissions();
    } else if (activeTab === 'servers') {
      fetchServers();
    }
  }, [activeTab]);
  
  const fetchOverview = async () => {
    try {
      setLoading(true);
      const data = await adminService.getAdminOverview();
      setOverview(data);
    } catch (error) {
      console.error('Error fetching overview:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchPendingSubmissions = async () => {
    try {
      setLoading(true);
      const data = await adminService.getAdminPendingSubmissions();
      setPendingSubmissions(data);
    } catch (error) {
      console.error('Error fetching pending submissions:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchSuspiciousSubmissions = async () => {
    try {
      setLoading(true);
      const data = await adminService.getAdminSuspiciousSubmissions();
      setSuspiciousSubmissions(data);
    } catch (error) {
      console.error('Error fetching suspicious submissions:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchServers = async () => {
    try {
      setLoading(true);
      const data = await adminService.getAdminServerList();
      setServers(data);
    } catch (error) {
      console.error('Error fetching servers:', error);
      console.error('Error details:', error.response?.data);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchServerAnalytics = async (serverId) => {
    try {
      const data = await adminService.getAdminServerAnalytics(serverId);
      setServerAnalytics(data);
      setSelectedServer(serverId);
    } catch (error) {
      console.error('Error fetching server analytics:', error);
    }
  };
  
  const pauseServer = async (serverId, serverName) => {
    setPauseModal({ show: true, serverId, serverName });
    setPauseReason('');
  };
  
  const confirmPauseServer = async () => {
    if (!pauseReason.trim()) {
      setNotification({ show: true, message: 'Please provide a reason for pausing', type: 'error' });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
      return;
    }
    
    try {
      await adminService.pauseServerSubmissions(pauseModal.serverId, { reason: pauseReason });
      setNotification({ show: true, message: 'Server submissions paused successfully', type: 'success' });
      setPauseModal({ show: false, serverId: null, serverName: '' });
      setPauseReason('');
      fetchServers();
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
    } catch (error) {
      console.error('Error pausing server:', error);
      setNotification({ show: true, message: 'Failed to pause server', type: 'error' });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
    }
  };
  
  const fetchSubmissionDetail = async (submissionId) => {
    try {
      const data = await adminService.getModeratorSubmissionDetail(submissionId);
      setSubmissionDetail(data);
      setSelectedSubmission(submissionId);
    } catch (error) {
      console.error('Error fetching submission detail:', error);
      setNotification({ show: true, message: 'Failed to load submission details', type: 'error' });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
    }
  };
  
  const handleReviewComplete = () => {
    // Close modal and refresh
    setSelectedSubmission(null);
    setSubmissionDetail(null);
    fetchOverview();
    fetchPendingSubmissions();
  };

  const resumeServer = async (serverId) => {
    try {
      await adminService.resumeServerSubmissions(serverId);
      setNotification({ show: true, message: 'Server submissions resumed successfully', type: 'success' });
      fetchServers();
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
    } catch (error) {
      console.error('Error resuming server:', error);
      setNotification({ show: true, message: 'Failed to resume server', type: 'error' });
      setTimeout(() => setNotification({ show: false, message: '', type: '' }), 3000);
    }
  };
  
  const downloadReport = async (reportType) => {
    try {
      const blob = await adminService.downloadReport(reportType);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `admin_report_${reportType}_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading report:', error);
      alert('Failed to download report');
    }
  };
  
  const renderOverview = () => (
    <div className="admin-overview">
      <h2>Admin Dashboard Overview</h2>
      
      {overview && (
        <>
          <div className="stats-grid">
            <div className="stat-card pending">
              <div className="stat-value">{overview.pending_submissions}</div>
              <div className="stat-label">Pending Submissions</div>
            </div>
            <div className="stat-card suspicious">
              <div className="stat-value">{overview.suspicious_submissions}</div>
              <div className="stat-label">Suspicious</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{overview.my_reviews_today}</div>
              <div className="stat-label">My Reviews Today</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{overview.paused_servers}</div>
              <div className="stat-label">Paused Servers</div>
            </div>
          </div>
          
          <div className="weekly-stats">
            <h3>Last 7 Days</h3>
            <div className="stats-row">
              <div className="stat-item">
                <span className="label">Submissions:</span>
                <span className="value">{overview.weekly_stats.submissions}</span>
              </div>
              <div className="stat-item">
                <span className="label">Approvals:</span>
                <span className="value green">{overview.weekly_stats.approvals}</span>
              </div>
              <div className="stat-item">
                <span className="label">Rejections:</span>
                <span className="value red">{overview.weekly_stats.rejections}</span>
              </div>
            </div>
          </div>
        </>
      )}
      
      <div className="admin-info-box">
        <h3>🛡️ Admin Permissions</h3>
        <div className="permissions-grid">
          <div className="permission-col">
            <h4>You CAN:</h4>
            <ul>
              <li>Review & approve payouts</li>
              <li>Mark suspicious submissions</li>
              <li>Edit payout categories</li>
              <li>Pause server submissions</li>
              <li>View server analytics</li>
              <li>Download moderation reports</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
  
  const renderPendingSubmissions = () => {
    // Apply filters
    let filtered = [...pendingSubmissions];
    
    if (serverFilter !== 'all') {
      filtered = filtered.filter(sub => sub.server.id === serverFilter);
    }
    
    if (dateFilter !== 'all') {
      const now = new Date();
      filtered = filtered.filter(sub => {
        const subDate = new Date(sub.created_at);
        const daysDiff = (now - subDate) / (1000 * 60 * 60 * 24);
        if (dateFilter === '7days') return daysDiff <= 7;
        if (dateFilter === '30days') return daysDiff <= 30;
        return true;
      });
    }
    
    if (amountFilter !== 'all') {
      filtered = filtered.filter(sub => {
        const amount = parseFloat(sub.amount);
        if (amountFilter === 'under1k') return amount < 1000;
        if (amountFilter === '1k-5k') return amount >= 1000 && amount < 5000;
        if (amountFilter === '5k-10k') return amount >= 5000 && amount < 10000;
        if (amountFilter === 'over10k') return amount >= 10000;
        return true;
      });
    }
    
    // Get unique servers for filter
    const uniqueServers = [...new Map(pendingSubmissions.map(s => [s.server.id, s.server])).values()];
    
    return (
      <div>
        <h2>Pending Payout Submissions ({filtered.length})</h2>
        
        <div className="filters-bar">
          <div className="filter-group">
            <label>Server</label>
            <select value={serverFilter} onChange={(e) => setServerFilter(e.target.value)}>
              <option value="all">All Servers</option>
              {uniqueServers.map(server => (
                <option key={server.id} value={server.id}>{server.name}</option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>Date Range</label>
            <select value={dateFilter} onChange={(e) => setDateFilter(e.target.value)}>
              <option value="all">All Time</option>
              <option value="7days">Last 7 Days</option>
              <option value="30days">Last 30 Days</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Amount</label>
            <select value={amountFilter} onChange={(e) => setAmountFilter(e.target.value)}>
              <option value="all">All Amounts</option>
              <option value="under1k">Under $1,000</option>
              <option value="1k-5k">$1,000 - $5,000</option>
              <option value="5k-10k">$5,000 - $10,000</option>
              <option value="over10k">Over $10,000</option>
            </select>
          </div>
        </div>
        
        <div className="submissions-list">
          {filtered.map(sub => (
            <div key={sub.id} className="submission-card">
              <div className="submission-header">
                <div className="submission-info">
                  <h3>Payout #{sub.id}</h3>
                  <p>
                    <Link to={`/trader/${sub.user.id}/public`}>{sub.user.username}</Link>
                    {' '} from{' '}
                    <Link to={`/servers/${sub.server.id}/public`}>{sub.server.name}</Link>
                  </p>
                </div>
              </div>
              
              {sub.screenshot && (
                <div className="screenshot-display">
                  <img src={sub.screenshot} alt="Payout screenshot" />
                </div>
              )}
              
              <div className="submission-meta">
                <div className="meta-item">
                  <span className="meta-label">Amount</span>
                  <span className="meta-value">${parseFloat(sub.amount).toLocaleString()}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Market</span>
                  <span className="meta-value">{sub.market_category}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Instrument</span>
                  <span className="meta-value">{sub.instrument}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Payout Date</span>
                  <span className="meta-value">{new Date(sub.payout_date).toLocaleDateString()}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Submitted</span>
                  <span className="meta-value">{new Date(sub.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              
              <div className="submission-actions">
                <button 
                  onClick={() => fetchSubmissionDetail(sub.id)}
                  className="action-btn approve"
                >
                  Review & Approve
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {filtered.length === 0 && (
          <div className="empty-state">
            <h3>No pending submissions</h3>
            <p>All caught up! No payouts to review.</p>
          </div>
        )}
      </div>
    );
  };
  
  const renderSuspiciousSubmissions = () => {
    // Apply filters
    let filtered = [...suspiciousSubmissions];
    
    if (serverFilter !== 'all') {
      filtered = filtered.filter(sub => sub.server.id === serverFilter);
    }
    
    if (dateFilter !== 'all') {
      const now = new Date();
      filtered = filtered.filter(sub => {
        const subDate = new Date(sub.created_at);
        const daysDiff = (now - subDate) / (1000 * 60 * 60 * 24);
        if (dateFilter === '7days') return daysDiff <= 7;
        if (dateFilter === '30days') return daysDiff <= 30;
        return true;
      });
    }
    
    if (amountFilter !== 'all') {
      filtered = filtered.filter(sub => {
        const amount = parseFloat(sub.amount);
        if (amountFilter === 'under1k') return amount < 1000;
        if (amountFilter === '1k-5k') return amount >= 1000 && amount < 5000;
        if (amountFilter === '5k-10k') return amount >= 5000 && amount < 10000;
        if (amountFilter === 'over10k') return amount >= 10000;
        return true;
      });
    }
    
    const uniqueServers = [...new Map(suspiciousSubmissions.map(s => [s.server.id, s.server])).values()];
    
    return (
      <div>
        <h2>Suspicious Submissions ({filtered.length})</h2>
        
        <div className="filters-bar">
          <div className="filter-group">
            <label>Server</label>
            <select value={serverFilter} onChange={(e) => setServerFilter(e.target.value)}>
              <option value="all">All Servers</option>
              {uniqueServers.map(server => (
                <option key={server.id} value={server.id}>{server.name}</option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label>Date Range</label>
            <select value={dateFilter} onChange={(e) => setDateFilter(e.target.value)}>
              <option value="all">All Time</option>
              <option value="7days">Last 7 Days</option>
              <option value="30days">Last 30 Days</option>
            </select>
          </div>
          
          <div className="filter-group">
            <label>Amount</label>
            <select value={amountFilter} onChange={(e) => setAmountFilter(e.target.value)}>
              <option value="all">All Amounts</option>
              <option value="under1k">Under $1,000</option>
              <option value="1k-5k">$1,000 - $5,000</option>
              <option value="5k-10k">$5,000 - $10,000</option>
              <option value="over10k">Over $10,000</option>
            </select>
          </div>
        </div>
        
        <div className="submissions-list">
          {filtered.map(sub => (
            <div key={sub.id} className="submission-card suspicious">
              <div className="submission-header">
                <div className="submission-info">
                  <h3>🚨 Suspicious Payout #{sub.id}</h3>
                  <p>
                    <Link to={`/trader/${sub.user.id}/public`}>{sub.user.username}</Link>
                    {' '} from{' '}
                    <Link to={`/servers/${sub.server.id}/public`}>{sub.server.name}</Link>
                  </p>
                  <p style={{ color: '#ff4466', fontSize: '0.85rem' }}>
                    Flagged by {sub.reviewer?.username || 'System'}
                  </p>
                </div>
              </div>
              
              {sub.screenshot && (
                <div className="screenshot-display">
                  <img src={sub.screenshot} alt="Payout screenshot" />
                </div>
              )}
              
              <div className="submission-meta">
                <div className="meta-item">
                  <span className="meta-label">Amount</span>
                  <span className="meta-value">${parseFloat(sub.amount).toLocaleString()}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Market</span>
                  <span className="meta-value">{sub.market_category}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Instrument</span>
                  <span className="meta-value">{sub.instrument}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Reviewed</span>
                  <span className="meta-value">{new Date(sub.reviewed_at).toLocaleDateString()}</span>
                </div>
              </div>
              
              <div className="submission-actions">
                <button 
                  onClick={() => fetchSubmissionDetail(sub.id)}
                  className="action-btn reject"
                >
                  Investigate
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {filtered.length === 0 && (
          <div className="empty-state">
            <h3>No suspicious submissions</h3>
            <p>No flagged payouts at this time.</p>
          </div>
        )}
      </div>
    );
  };
  
  const renderServers = () => (
    <div>
      <h2>Server Moderation ({servers.length})</h2>
      
      <div className="servers-grid">
        {servers.map(server => (
          <div key={server.id} className={`server-card ${server.payout_submissions_paused ? 'paused' : ''}`}>
            <div className="server-header">
              <h3>
                <Link to={`/servers/${server.id}/public`}>
                  {server.name}
                </Link>
              </h3>
              {server.payout_submissions_paused ? (
                <span className="server-badge paused">Paused</span>
              ) : (
                <span className="server-badge active">Active</span>
              )}
            </div>
            
            <div className="server-stats">
              <div className="server-stat-item">
                <span className="server-stat-label">Owner</span>
                <span className="server-stat-value">{server.owner}</span>
              </div>
              <div className="server-stat-item">
                <span className="server-stat-label">Platform</span>
                <span className="server-stat-value">{server.platform}</span>
              </div>
              <div className="server-stat-item">
                <span className="server-stat-label">Members</span>
                <span className="server-stat-value">{server.total_members}</span>
              </div>
              <div className="server-stat-item">
                <span className="server-stat-label">Pending</span>
                <span className="server-stat-value" style={{ color: server.pending_submissions > 0 ? '#ff4466' : '#00ff88' }}>
                  {server.pending_submissions}
                </span>
              </div>
            </div>
            
            <div className="server-actions">
              <button 
                onClick={() => fetchServerAnalytics(server.id)}
                className="server-action-btn view"
              >
                Analytics
              </button>
              
              {server.payout_submissions_paused ? (
                <button 
                  onClick={() => resumeServer(server.id)}
                  className="server-action-btn resume"
                >
                 Resume
                </button>
              ) : (
                <button 
                  onClick={() => pauseServer(server.id, server.name)}
                  className="server-action-btn pause"
                >
                  Pause
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {servers.length === 0 && (
        <div className="empty-state">
          <h3>No servers found</h3>
          <p>No servers to moderate.</p>
        </div>
      )}
      
      {serverAnalytics && selectedServer && (
        <div className="server-analytics-modal" onClick={() => setServerAnalytics(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Server Analytics: {serverAnalytics.server.name}</h2>
              <button onClick={() => setServerAnalytics(null)} className="close-btn">×</button>
            </div>
            
            <div className="stats-grid" style={{ marginBottom: '2rem' }}>
              <div className="stat-card">
                <div className="stat-value">{serverAnalytics.stats.total_submissions}</div>
                <div className="stat-label">Total Submissions</div>
              </div>
              <div className="stat-card" style={{ borderColor: 'rgba(0, 255, 136, 0.5)' }}>
                <div className="stat-value" style={{ color: '#00ff88' }}>{serverAnalytics.stats.approved}</div>
                <div className="stat-label">Approved</div>
              </div>
              <div className="stat-card" style={{ borderColor: 'rgba(255, 68, 102, 0.5)' }}>
                <div className="stat-value" style={{ color: '#ff4466' }}>{serverAnalytics.stats.rejected}</div>
                <div className="stat-label">Rejected</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{serverAnalytics.stats.rejection_rate}%</div>
                <div className="stat-label">Rejection Rate</div>
              </div>
            </div>
            
            <h3 style={{ marginBottom: '1rem', color: '#fff' }}>Top Submitters</h3>
            <div style={{ background: 'rgba(0, 102, 255, 0.05)', border: '1px solid rgba(0, 102, 255, 0.2)', borderRadius: '12px', padding: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '0.75rem', textAlign: 'left', color: '#888', fontSize: '0.85rem', textTransform: 'uppercase' }}>User</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', color: '#888', fontSize: '0.85rem', textTransform: 'uppercase' }}>Submissions</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', color: '#888', fontSize: '0.85rem', textTransform: 'uppercase' }}>Verified Payouts</th>
                  </tr>
                </thead>
                <tbody>
                  {serverAnalytics.top_submitters.map(sub => (
                    <tr key={sub.user_id} style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                      <td style={{ padding: '0.75rem' }}>
                        <Link to={`/trader/${sub.user_id}/public`} style={{ color: '#0066ff', textDecoration: 'none' }}>
                          {sub.username}
                        </Link>
                      </td>
                      <td style={{ padding: '0.75rem', color: '#fff' }}>{sub.total_submissions}</td>
                      <td style={{ padding: '0.75rem', color: '#00ff88', fontWeight: '600' }}>
                        ${parseFloat(sub.total_verified_payouts).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
  
  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
      </div>
      
      <div className="admin-tabs">
        <button 
          className={`admin-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`admin-tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          Pending ({overview?.pending_submissions || 0})
        </button>
        <button 
          className={`admin-tab ${activeTab === 'suspicious' ? 'active' : ''}`}
          onClick={() => setActiveTab('suspicious')}
        >
          Suspicious ({overview?.suspicious_submissions || 0})
        </button>
        <button 
          className={`admin-tab ${activeTab === 'servers' ? 'active' : ''}`}
          onClick={() => setActiveTab('servers')}
        >
          Servers
        </button>
      </div>
      
      {loading ? (
        <div className="loading-state">
          <h3>Loading...</h3>
        </div>
      ) : (
        <>
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'pending' && renderPendingSubmissions()}
          {activeTab === 'suspicious' && renderSuspiciousSubmissions()}
          {activeTab === 'servers' && renderServers()}
        </>
      )}

      {/* Pause Server Modal */}
      {pauseModal.show && (
        <div className="modal-overlay" onClick={() => setPauseModal({ show: false, serverId: null, serverName: '' })}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-dialog-header">
              <h3>Pause Server Submissions</h3>
              <button onClick={() => setPauseModal({ show: false, serverId: null, serverName: '' })} className="modal-close-btn">×</button>
            </div>
            <div className="modal-dialog-body">
              <p className="modal-server-name">{pauseModal.serverName}</p>
              <p className="modal-description">This will prevent users from submitting new payouts to this server. Existing submissions will remain in the queue.</p>
              <label className="modal-label">
                Reason for pausing:
                <textarea
                  className="modal-textarea"
                  value={pauseReason}
                  onChange={(e) => setPauseReason(e.target.value)}
                  placeholder="Enter reason for pausing submissions..."
                  rows="4"
                  autoFocus
                />
              </label>
            </div>
            <div className="modal-dialog-footer">
              <button onClick={() => setPauseModal({ show: false, serverId: null, serverName: '' })} className="modal-btn modal-btn-cancel">
                Cancel
              </button>
              <button onClick={confirmPauseServer} className="modal-btn modal-btn-confirm">
                Pause Submissions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Notification Toast */}
      {notification.show && (
        <div className={`notification-toast ${notification.type}`}>
          {notification.type === 'success' ? '✓ ' : '✗ '}
          {notification.message}
        </div>
      )}
      
      {/* Payout Review Modal */}
      {selectedSubmission && submissionDetail && (
        <PayoutReviewModal
          submission={submissionDetail}
          onClose={() => {
            setSelectedSubmission(null);
            setSubmissionDetail(null);
          }}
          onReviewComplete={handleReviewComplete}
        />
      )}
    </div>
  );
};

export default AdminDashboard;
