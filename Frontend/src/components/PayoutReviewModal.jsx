import { useState } from 'react';
import { Link } from 'react-router-dom';
import { payoutService } from '../services';
import api from '../config/api';
import './PayoutReviewModal.css';

const PayoutReviewModal = ({ submission, onClose, onReviewComplete }) => {
  const [action, setAction] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [privateImageUrl, setPrivateImageUrl] = useState(null);
  const [loadingPrivateImage, setLoadingPrivateImage] = useState(false);
  
  const loadPrivateImage = async () => {
    if (!sub.has_private_verification_image || privateImageUrl) return;
    
    try {
      setLoadingPrivateImage(true);
      const response = await api.get(`/payouts/submissions/${sub.id}/verification_image/`, {
        responseType: 'blob'
      });
      
      const imageUrl = URL.createObjectURL(response.data);
      setPrivateImageUrl(imageUrl);
    } catch (error) {
      console.error('Error loading private verification image:', error);
      alert('Failed to load private verification image');
    } finally {
      setLoadingPrivateImage(false);
    }
  };
  
  const handleSubmit = async () => {
    if (!action) {
      alert('Please select an action (Approve, Reject, or Mark Suspicious)');
      return;
    }
    
    if ((action === 'Rejected' || action === 'MarkedSuspicious') && !reason.trim()) {
      alert('Please provide a reason for rejection or marking as suspicious');
      return;
    }
    
    try {
      setSubmitting(true);
      
      await payoutService.reviewSubmission(
        submission.submission.id,
        { action, reason: reason.trim() || 'No reason provided' }
      );
      
      alert(`Payout ${action === 'Approved' ? 'approved' : action === 'Rejected' ? 'rejected' : 'marked as suspicious'} successfully!`);
      onReviewComplete();
    } catch (error) {
      console.error('Error submitting review:', error);
      alert(`Failed to submit review: ${error.response?.data?.error || error.message}`);
    } finally {
      setSubmitting(false);
    }
  };
  
  const sub = submission.submission;
  const userStats = submission.user_stats;
  const serverStats = submission.server_stats;
  
  return (
    <div className="review-modal-overlay">
      <div className="review-modal">
        <div className="modal-header">
          <h2>Review Payout Submission #{sub.id}</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        
        <div className="modal-body">
          {/* Screenshot Section */}
          <div className="screenshot-section">
            <h3>Proof Screenshot</h3>
            {sub.screenshot ? (
              <div className="screenshot-viewer">
                <img src={sub.screenshot} alt="Payout proof" style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px' }} />
                <button 
                  onClick={() => window.open(sub.screenshot, '_blank', 'noopener,noreferrer')}
                  className="btn btn-sm btn-secondary"
                  style={{ marginTop: '10px' }}
                >
                  Open Full Size ↗
                </button>
              </div>
            ) : (
              <div className="no-screenshot">No screenshot provided</div>
            )}
          </div>
          
          {/* Private Verification Image Section */}
          {sub.has_private_verification_image && (
            <div className="screenshot-section">
              <h3>🔒 Private Verification Image</h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                Bank invoice / transaction screenshot (staff only)
              </p>
              {!privateImageUrl ? (
                <button 
                  onClick={loadPrivateImage}
                  className="btn btn-sm btn-primary"
                  disabled={loadingPrivateImage}
                >
                  {loadingPrivateImage ? 'Loading...' : 'View Private Verification Image'}
                </button>
              ) : (
                <div className="screenshot-viewer">
                  <img src={privateImageUrl} alt="Private verification" style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px' }} />
                  <button 
                    onClick={() => window.open(privateImageUrl, '_blank', 'noopener,noreferrer')}
                    className="btn btn-sm btn-secondary"
                    style={{ marginTop: '10px' }}
                  >
                    Open Full Size ↗
                  </button>
                </div>
              )}
            </div>
          )}
          
          {/* Submission Details */}
          <div className="details-section">
            <h3>Submission Details</h3>
            <div className="details-grid">
              <div className="detail-item">
                <span className="detail-label">Amount:</span>
                <span className="detail-value amount">${parseFloat(sub.amount).toLocaleString()} {sub.currency}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Market:</span>
                <span className="detail-value"><span className="badge">{sub.market_category}</span></span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Instrument:</span>
                <span className="detail-value">{sub.instrument}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Payout Date:</span>
                <span className="detail-value">{new Date(sub.payout_date).toLocaleDateString()}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Discord Contact:</span>
                <span className="detail-value">{sub.discord_contact_info || 'Not provided'}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">User:</span>
                <Link 
                  to={`/trader/${sub.user.id}/public`}
                  className="detail-value"
                  style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  {sub.user.username} ↗
                </Link>
              </div>
              <div className="detail-row">
                <span className="detail-label">Server:</span>
                <Link 
                  to={`/servers/${sub.server.id}/public`}
                  className="detail-value"
                  style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  {sub.server.name} ↗
                </Link>
              </div>
              <div className="detail-item">
                <span className="detail-label">Submitted:</span>
                <span className="detail-value">{new Date(sub.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
          
          {/* Verification Context */}
          <div className="context-section">
            <h3>Verification Context</h3>
            
            <div className="context-grid">
              {/* User Stats */}
              <div className="context-box">
                <h4>User Stats</h4>
                <div className="context-stats">
                  <div className="stat">
                    <span className="stat-label">Total Submissions:</span>
                    <span className="stat-value">{userStats.total_submissions}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Approved:</span>
                    <span className="stat-value green">{userStats.approved}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Rejected:</span>
                    <span className="stat-value red">{userStats.rejected}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Approval Rate:</span>
                    <span className="stat-value">{userStats.approval_rate}%</span>
                  </div>
                </div>
              </div>
              
              {/* Server Stats */}
              <div className="context-box">
                <h4>Server Stats</h4>
                <div className="context-stats">
                  <div className="stat">
                    <span className="stat-label">Total Submissions:</span>
                    <span className="stat-value">{serverStats.total_submissions}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Approved:</span>
                    <span className="stat-value green">{serverStats.approved}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Rejected:</span>
                    <span className="stat-value red">{serverStats.rejected}</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* User History */}
            {submission.user_history && submission.user_history.length > 0 && (
              <div className="history-box">
                <h4>User's Recent Submissions</h4>
                <div className="history-list">
                  {submission.user_history.slice(0, 5).map(h => (
                    <div key={h.id} className="history-item">
                      <span className="history-amount">${parseFloat(h.amount).toLocaleString()}</span>
                      <span className="history-market">{h.market_category}</span>
                      <span className={`history-status ${h.status.toLowerCase()}`}>{h.status}</span>
                      <span className="history-date">{new Date(h.created_at).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Review History */}
            {submission.review_history && submission.review_history.length > 0 && (
              <div className="review-history-box">
                <h4>Review History</h4>
                <div className="review-history-list">
                  {submission.review_history.map((log, idx) => (
                    <div key={idx} className="review-history-item">
                      <div className="review-log-header">
                        <span className="reviewer">{log.reviewer}</span>
                        <span className={`action ${log.action.toLowerCase()}`}>{log.action}</span>
                        <span className="date">{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                      {log.reason && (
                        <div className="review-log-reason">{log.reason}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Review Actions */}
          <div className="review-actions-section">
            <h3>Your Decision</h3>
            
            <div className="action-buttons">
              <button 
                onClick={() => setAction('Approved')}
                className={`action-btn approve ${action === 'Approved' ? 'selected' : ''}`}
                disabled={submitting}
              >
                Approve
              </button>
              <button 
                onClick={() => setAction('Rejected')}
                className={`action-btn reject ${action === 'Rejected' ? 'selected' : ''}`}
                disabled={submitting}
              >
                ✗ Reject
              </button>
              <button 
                onClick={() => setAction('MarkedSuspicious')}
                className={`action-btn suspicious ${action === 'MarkedSuspicious' ? 'selected' : ''}`}
                disabled={submitting}
              >
                ⚠ Mark Suspicious
              </button>
            </div>
            
            {(action === 'Rejected' || action === 'MarkedSuspicious') && (
              <div className="reason-input">
                <label>Reason *</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={action === 'Rejected' 
                    ? 'Why are you rejecting this submission? (e.g., Screenshot unclear, Amount mismatch, Duplicate submission)'
                    : 'Why is this submission suspicious? (e.g., Edited screenshot, Unusual pattern, Possible fraud)'
                  }
                  rows="3"
                  disabled={submitting}
                />
              </div>
            )}
            
            {action === 'Approved' && (
              <div className="approval-note">
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Optional note (e.g., Verified with broker statement)"
                  rows="2"
                  disabled={submitting}
                />
              </div>
            )}
          </div>
        </div>
        
        <div className="modal-footer">
          <button onClick={onClose} className="btn btn-secondary" disabled={submitting}>
            Cancel
          </button>
          <button 
            onClick={handleSubmit} 
            className="btn btn-primary" 
            disabled={!action || submitting}
          >
            {submitting ? 'Submitting...' : 'Submit Review'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PayoutReviewModal;
