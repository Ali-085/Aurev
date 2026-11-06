/**
 * ServerCreatorCancel - Payment cancellation page
 * 
 * Security:
 * - No authentication required (public page)
 * - Retry button redirects to authenticated checkout endpoint
 * - Registration expiration handled server-side
 */

import { useNavigate } from 'react-router-dom';
import './ServerCreatorCancel.css';

export default function ServerCreatorCancel() {
  const navigate = useNavigate();

  return (
    <div className="cancel-container">
      <div className="cancel-card">
        <div className="cancel-icon"></div>
        
        <h1>Payment Cancelled</h1>
        
        <p className="message">
          Your payment was not completed. Your account is not yet activated.
        </p>

        <div className="info-box">
          <p>Your registration will expire in 24 hours</p>
          <p>You can retry payment at any time before expiration</p>
        </div>
        
        <div className="action-buttons">
          <button 
            onClick={() => navigate('/server-creator/checkout')}
            className="retry-button"
          >
            Try Payment Again
          </button>
          
          <button 
            onClick={() => navigate('/dashboard')} 
            className="dashboard-button"
          >
            Return to Dashboard
          </button>
        </div>

        <div className="help-section">
          <p className="help-title">Need help?</p>
          <p className="help-text">
            If you're experiencing issues with payment, please contact our support team.
          </p>
        </div>
      </div>
    </div>
  );
}
