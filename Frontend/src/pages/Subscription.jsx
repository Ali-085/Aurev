/**
 * Subscription Management Page
 * 
 * Allows users to view and manage their subscription
 * 
 * SECURITY:
 * - Protected route (authentication required)
 * - All subscription changes through secure Stripe API
 * - Proration calculations from backend
 * - Cancel confirmation to prevent accidental cancellation
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './Subscription.css';

const Subscription = () => {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [showUpgradeOptions, setShowUpgradeOptions] = useState(false);

  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchSubscriptionStatus();
  }, []);

  const fetchSubscriptionStatus = async () => {
    try {
      const response = await api.get('/subscriptions/status/');
      setSubscription(response.data);
      setError('');
    } catch (err) {
      setError('Failed to load subscription information');
      console.error('Error fetching subscription:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    setCanceling(true);
    try {
      await api.post('/subscriptions/cancel/');
      await fetchSubscriptionStatus();
      await checkAuth(); // Refresh user data
      setShowCancelModal(false);
      setError('');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to cancel subscription');
      console.error('Error canceling subscription:', err);
    } finally {
      setCanceling(false);
    }
  };

  const handleUpgrade = () => {
    navigate('/pricing');
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getTierBadgeColor = (tier) => {
    switch(tier) {
      case 'standard': return '#007bff';
      case 'premium': return '#6f42c1';
      case 'elite': return '#ffc107';
      default: return '#6c757d';
    }
  };

  if (loading) {
    return (
      <div className="subscription-page">
        <div className="subscription-loading">
          <div className="spinner"></div>
          <p>Loading subscription details...</p>
        </div>
      </div>
    );
  }

  const hasActiveSubscription = subscription?.has_subscription;
  const isManualGrant = subscription?.subscription_type === 'manual_grant';
  const tier = subscription?.tier || 'free';

  return (
    <div className="subscription-page">
      <div className="subscription-header">
        <h1>Subscription Management</h1>
        <p>Manage your Aurevia subscription and billing</p>
      </div>

      {error && (
        <div className="subscription-error">
          <span className="error-icon"></span>
          {error}
        </div>
      )}

      {/* Current Plan Card */}
      <div className="subscription-current-plan">
        <div className="plan-header">
          <div>
            <h2>Current Plan</h2>
            <div 
              className="plan-tier-badge"
              style={{ backgroundColor: getTierBadgeColor(tier) }}
            >
              {tier.charAt(0).toUpperCase() + tier.slice(1)}
            </div>
          </div>
          {!hasActiveSubscription && (
            <button 
              className="btn-upgrade"
              onClick={handleUpgrade}
            >
              Upgrade Now
            </button>
          )}
        </div>

        {hasActiveSubscription ? (
          <div className="plan-details">
            <div className="plan-detail-item">
              <span className="detail-label">Status</span>
              <span className={`detail-value status-${subscription.status}`}>
                {subscription.status === 'active' && 'Active'}
                {subscription.status === 'trialing' && 'Trial'}
                {subscription.status === 'past_due' && 'Past Due'}
                {subscription.status === 'canceled' && 'Canceled'}
              </span>
            </div>

            <div className="plan-detail-item">
              <span className="detail-label">Type</span>
              <span className="detail-value">
                {isManualGrant ? (
                  <>
                    <span className="manual-grant-badge">Manual Grant</span>
                    {subscription.grant_info && (
                      <span className="grant-info">
                        Granted by {subscription.grant_info.granted_by}
                      </span>
                    )}
                  </>
                ) : (
                  'Stripe Subscription'
                )}
              </span>
            </div>

            {subscription.current_period_end && (
              <div className="plan-detail-item">
                <span className="detail-label">
                  {subscription.status === 'canceled' ? 'Access Until' : 'Renews On'}
                </span>
                <span className="detail-value">
                  {formatDate(subscription.current_period_end)}
                </span>
              </div>
            )}

            {isManualGrant && subscription.grant_info && (
              <div className="plan-detail-item">
                <span className="detail-label">Grant Duration</span>
                <span className="detail-value">
                  {subscription.grant_info.is_permanent 
                    ? 'Permanent' 
                    : `${subscription.grant_info.duration_days} days`}
                </span>
              </div>
            )}

            {subscription.grant_info?.grant_reason && (
              <div className="plan-detail-item">
                <span className="detail-label">Grant Reason</span>
                <span className="detail-value">
                  {subscription.grant_info.grant_reason}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="no-subscription">
            <p className="no-subscription-icon"></p>
            <h3>No Active Subscription</h3>
            <p>You're currently on the free plan with limited features.</p>
            <button 
              className="btn-upgrade-large"
              onClick={handleUpgrade}
            >
              View Premium Plans
            </button>
          </div>
        )}
      </div>

      {/* Actions Card */}
      {hasActiveSubscription && !isManualGrant && (
        <div className="subscription-actions">
          <h3>Subscription Actions</h3>
          
          <div className="action-buttons">
            {tier !== 'elite' && subscription.status === 'active' && (
              <button 
                className="action-btn upgrade"
                onClick={handleUpgrade}
              >
                <span className="action-icon">⬆️</span>
                <div>
                  <div className="action-title">Upgrade Plan</div>
                  <div className="action-desc">Get more features and benefits</div>
                </div>
              </button>
            )}

            {subscription.status !== 'canceled' && (
              <button 
                className="action-btn cancel"
                onClick={() => setShowCancelModal(true)}
              >
                <span className="action-icon"></span>
                <div>
                  <div className="action-title">Cancel Subscription</div>
                  <div className="action-desc">Cancel at end of billing period</div>
                </div>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Features Overview */}
      <div className="subscription-features">
        <h3>Your Plan Features</h3>
        <div className="features-grid">
          <FeatureItem 
            icon=""
            title="Servers"
            value={tier === 'elite' ? 'Unlimited' : tier === 'premium' ? '10' : tier === 'standard' ? '3' : '1'}
            available={hasActiveSubscription || tier === 'free'}
          />
          <FeatureItem 
            icon=""
            title="Analytics"
            value={tier === 'elite' ? 'Advanced' : tier === 'premium' ? 'Enhanced' : 'Basic'}
            available={true}
          />
          <FeatureItem 
            icon=""
            title="Custom Branding"
            value={tier === 'elite' ? 'Full' : 'Limited'}
            available={tier === 'elite'}
          />
          <FeatureItem 
            icon=""
            title="Priority Support"
            value={tier === 'elite' || tier === 'premium' ? 'Yes' : 'No'}
            available={tier === 'elite' || tier === 'premium'}
          />
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelModal && (
        <div className="modal-overlay" onClick={() => setShowCancelModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Cancel Subscription?</h2>
              <button 
                className="modal-close"
                onClick={() => setShowCancelModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p>Are you sure you want to cancel your subscription?</p>
              <ul className="cancel-warning-list">
                <li>You'll lose access to premium features</li>
                <li>Your subscription will remain active until {formatDate(subscription?.current_period_end)}</li>
                <li>You can resubscribe anytime</li>
              </ul>
            </div>
            <div className="modal-actions">
              <button 
                className="btn-secondary"
                onClick={() => setShowCancelModal(false)}
                disabled={canceling}
              >
                Keep Subscription
              </button>
              <button 
                className="btn-danger"
                onClick={handleCancelSubscription}
                disabled={canceling}
              >
                {canceling ? 'Canceling...' : 'Yes, Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const FeatureItem = ({ icon, title, value, available }) => (
  <div className={`feature-item ${available ? 'available' : 'unavailable'}`}>
    <span className="feature-icon">{icon}</span>
    <div className="feature-info">
      <div className="feature-title">{title}</div>
      <div className="feature-value">{value}</div>
    </div>
    {!available && <span className="feature-lock"></span>}
  </div>
);

export default Subscription;
