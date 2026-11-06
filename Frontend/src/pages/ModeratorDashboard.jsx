import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { adminService } from '../services';
import PayoutReviewModal from '../components/PayoutReviewModal';
import { useAuth } from '../context/AuthContext';
import { canAdmin } from '../utils/permissions';
import './ModeratorDashboard.css';

const ModeratorDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('queue');
  const [overview, setOverview] = useState(null);
  const [queue, setQueue] = useState([]);
  const [myReviews, setMyReviews] = useState([]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [submissionDetail, setSubmissionDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Redirect admins to admin dashboard
  useEffect(() => {
    if (user && canAdmin(user)) {
      navigate('/dashboard/admin', { replace: true });
    }
  }, [user, navigate]);
  
  useEffect(() => {
    fetchOverview();
  }, []);
  
  useEffect(() => {
    if (activeTab === 'queue') {
      fetchQueue();
    } else if (activeTab === 'my-reviews') {
      fetchMyReviews();
    }
  }, [activeTab]);
  
  const fetchOverview = async () => {
    try {
      const data = await adminService.getModeratorOverview();
      setOverview(data);
    } catch (error) {
      console.error('Error fetching overview:', error);
    }
  };
  
  const fetchQueue = async () => {
    try {
      setLoading(true);
      const data = await adminService.getModeratorReviewQueue();
      setQueue(data);
    } catch (error) {
      console.error('Error fetching queue:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchMyReviews = async () => {
    try {
      setLoading(true);
      const data = await adminService.getModeratorMyReviews();
      setMyReviews(data);
    } catch (error) {
      console.error('Error fetching my reviews:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchSubmissionDetail = async (submissionId) => {
    try {
      const data = await adminService.getModeratorSubmissionDetail(submissionId);
      setSubmissionDetail(data);
      setSelectedSubmission(submissionId);
    } catch (error) {
      console.error('Error fetching submission detail:', error);
      alert('Failed to load submission details');
    }
  };
  
  const handleReviewComplete = () => {
    // Close modal and refresh queue
    setSelectedSubmission(null);
    setSubmissionDetail(null);
    fetchOverview();
    fetchQueue();
  };
  
  const renderOverview = () => (
    <div className="mod-overview">
      <div className="stats-grid">
        <div className="stat-card pending">
          <div className="stat-value">{overview?.pending_queue || 0}</div>
          <div className="stat-label">Pending Queue</div>
        </div>
        <div className="stat-card today">
          <div className="stat-value">{overview?.my_reviews_today || 0}</div>
          <div className="stat-label">Reviewed Today</div>
        </div>
        <div className="stat-card total">
          <div className="stat-value">{overview?.my_total_reviews || 0}</div>
          <div className="stat-label">Lifetime Reviews</div>
        </div>
        <div className="stat-card rate">
          <div className="stat-value">{overview?.my_approval_rate || 0}%</div>
          <div className="stat-label">Approval Rate</div>
        </div>
      </div>
      
      <div className="detailed-stats">
        <div className="stat-row">
          <div className="stat-item">
            <span className="label">Approved:</span>
            <span className="value green">{overview?.my_approvals || 0}</span>
          </div>
          <div className="stat-item">
            <span className="label">Rejected:</span>
            <span className="value red">{overview?.my_rejections || 0}</span>
          </div>
        </div>
      </div>
      
      <div className="mod-info-box">
        <h3>Moderator Role</h3>
        <p>You are a <strong>verification worker</strong>. Your job is to review payout submissions quickly and accurately.</p>
        
        <div className="permissions-grid">
          <div className="permission-col">
            <h4>You CAN:</h4>
            <ul>
              <li>Review pending payouts</li>
              <li>Approve submissions</li>
              <li>Reject submissions</li>
              <li>Mark as fraudulent</li>
              <li>Add rejection reasons</li>
              <li>View verification context</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
  
  const renderQueue = () => (
    <div className="mod-section">
      <div className="section-header">
        <h2>Review Queue ({queue.length})</h2>
        <button onClick={fetchQueue} className="btn btn-secondary">
          Refresh Queue
        </button>
      </div>
      
      <div className="queue-list">
        {queue.map(submission => (
          <div key={submission.id} className="queue-item">
            <div className="queue-item-header">
              <div className="submission-id">#{submission.id}</div>
              <div className="submission-badge">{submission.market_category}</div>
            </div>
            
            <div className="queue-item-body">
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">User:</span>
                  <Link 
                    to={`/trader/${submission.user.id}/public`}
                    className="info-value"
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {submission.user.username}
                  </Link>
                </div>
                <div className="info-item">
                  <span className="info-label">Server:</span>
                  <Link 
                    to={`/servers/${submission.server.id}/public`}
                    className="info-value"
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {submission.server.name}
                  </Link>
                </div>
                <div className="info-item">
                  <span className="info-label">Amount:</span>
                  <span className="info-value amount">${parseFloat(submission.amount).toLocaleString()}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Instrument:</span>
                  <span className="info-value">{submission.instrument}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Date:</span>
                  <span className="info-value">{new Date(submission.payout_date).toLocaleDateString()}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Submitted:</span>
                  <span className="info-value">{new Date(submission.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>
            
            <div className="queue-item-footer">
              <button 
                onClick={() => fetchSubmissionDetail(submission.id)}
                className="btn btn-primary"
              >
                Review Now
              </button>
            </div>
          </div>
        ))}
        
        {queue.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon"></div>
            <div className="empty-text">No pending submissions!</div>
            <div className="empty-subtext">Queue is empty - great work!</div>
          </div>
        )}
      </div>
    </div>
  );
  
  const renderMyReviews = () => (
    <div className="mod-section">
      <div className="section-header">
        <h2>My Reviews ({myReviews.length})</h2>
        <div className="filter-buttons">
          <button onClick={() => fetchMyReviews()} className="btn btn-sm">All</button>
          <button onClick={() => fetchMyReviews('Approved')} className="btn btn-sm btn-success">Approved</button>
          <button onClick={() => fetchMyReviews('Rejected')} className="btn btn-sm btn-danger">Rejected</button>
        </div>
      </div>
      
      <div className="reviews-table">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Server</th>
              <th>Amount</th>
              <th>Market</th>
              <th>Status</th>
              <th>Reviewed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {myReviews.map(review => (
              <tr key={review.id}>
                <td>#{review.id}</td>
                <td>
                  <Link 
                    to={`/trader/${review.user.id}/public`}
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {review.user.username}
                  </Link>
                </td>
                <td>
                  <Link 
                    to={`/servers/${review.server.id}/public`}
                    style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  >
                    {review.server.name}
                  </Link>
                </td>
                <td className="amount">${parseFloat(review.amount).toLocaleString()}</td>
                <td><span className="badge">{review.market_category}</span></td>
                <td>
                  <span className={`status-badge ${review.status.toLowerCase()}`}>
                    {review.status}
                  </span>
                </td>
                <td>{new Date(review.reviewed_at).toLocaleDateString()}</td>
                <td>
                  <button 
                    onClick={() => fetchSubmissionDetail(review.id)}
                    className="btn btn-sm btn-secondary"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {myReviews.length === 0 && (
          <div className="empty-state">No reviews yet</div>
        )}
      </div>
    </div>
  );
  
  return (
    <div className="moderator-dashboard">
      <div className="mod-header">
        <h1>Moderator Dashboard</h1>
        <p className="mod-subtitle">Payout Verification</p>
      </div>
      
      {overview && renderOverview()}
      
      <div className="mod-tabs">
        <button 
          className={`tab ${activeTab === 'queue' ? 'active' : ''}`}
          onClick={() => setActiveTab('queue')}
        >
          Review Queue ({overview?.pending_queue || 0})
        </button>
        <button 
          className={`tab ${activeTab === 'my-reviews' ? 'active' : ''}`}
          onClick={() => setActiveTab('my-reviews')}
        >
          My Reviews ({overview?.my_total_reviews || 0})
        </button>
      </div>
      
      <div className="mod-content">
        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <>
            {activeTab === 'queue' && renderQueue()}
            {activeTab === 'my-reviews' && renderMyReviews()}
          </>
        )}
      </div>
      
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

export default ModeratorDashboard;
