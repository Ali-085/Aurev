import { useState, useEffect } from 'react';
import api from '../config/api';
import './RoleSubscriptionModal.css';

/**
 * RoleSubscriptionModal
 * 
 * Modal for changing user roles with integrated subscription management.
 * When assigning ServerCreator role, requires subscription tier, duration, and reason.
 * 
 * Props:
 * - isOpen: boolean - show/hide modal
 * - onClose: function - callback when modal closes
 * - onSubmit: function(roleData) - callback with {role, subscription: {tier, duration_days, reason, override_existing}}
 * - user: object - {id, username, email, roles}
 * - currentSubscription: object | null - {has_subscription, tier, status, is_paid, grant_info}
 */
const RoleSubscriptionModal = ({ isOpen, onClose, onSubmit, user, currentSubscription }) => {
  const [selectedRole, setSelectedRole] = useState('Trader');
  const [tier, setTier] = useState('standard');
  const [durationType, setDurationType] = useState('30d');
  const [customDuration, setCustomDuration] = useState('');
  const [reason, setReason] = useState('');
  const [overrideConfirmed, setOverrideConfirmed] = useState(false);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [availableTiers, setAvailableTiers] = useState([]);
  const [loadingTiers, setLoadingTiers] = useState(true);

  // Fetch available subscription tiers from API
  useEffect(() => {
    const fetchTiers = async () => {
      try {
        const response = await api.get('/subscriptions/plans/');
        const plans = response.data.results || response.data;
        const tiers = plans.map(plan => ({
          value: plan.tier,
          label: plan.name,
          price: `$${parseFloat(plan.price_per_month).toFixed(2)}/mo`
        }));
        setAvailableTiers(tiers);
        // Set default tier to first available
        if (tiers.length > 0) {
          setTier(tiers[0].value);
        }
      } catch (error) {
        console.error('Failed to fetch subscription plans:', error);
        // Fallback to standard if API fails
        setAvailableTiers([{ value: 'standard', label: 'Standard', price: 'Contact Admin' }]);
        setTier('standard');
      } finally {
        setLoadingTiers(false);
      }
    };
    fetchTiers();
  }, []);

  // Reset form when modal opens/user changes
  useEffect(() => {
    if (isOpen && user) {
      setSelectedRole('Trader');
      if (availableTiers.length > 0) {
        setTier(availableTiers[0].value);
      }
      setDurationType('30d');
      setCustomDuration('');
      setReason('');
      setOverrideConfirmed(false);
      setErrors({});
    }
  }, [isOpen, user, availableTiers]);

  if (!isOpen || !user) return null;

  const roles = [
    { value: 'ServerCreator', label: 'Server Creator', description: 'Can create and manage servers (requires subscription)' },
    { value: 'Admin', label: 'Admin', description: 'Platform-level admin permissions' },
    { value: 'Moderator', label: 'Moderator', description: 'Can moderate content' },
    { value: 'Trader', label: 'Trader', description: 'Regular platform user' }
  ];

  // Tiers are now fetched from API in useEffect above

  const durationPresets = [
    { value: '30d', label: '30 days' },
    { value: '90d', label: '90 days' },
    { value: '365d', label: '1 year' },
    { value: 'permanent', label: 'Permanent' },
    { value: 'custom', label: 'Custom (days)' }
  ];

  const hasPaidSubscription = currentSubscription?.has_subscription && currentSubscription?.is_paid;
  const requiresOverride = selectedRole === 'ServerCreator' && hasPaidSubscription;

  const getDurationDays = () => {
    if (durationType === 'permanent') return null;
    if (durationType === 'custom') {
      const days = parseInt(customDuration, 10);
      return isNaN(days) || days <= 0 ? null : days;
    }
    return parseInt(durationType.replace('d', ''), 10);
  };

  const validate = () => {
    const newErrors = {};

    if (selectedRole === 'ServerCreator') {
      if (!tier) {
        newErrors.tier = 'Tier is required for ServerCreator role';
      }

      if (durationType === 'custom') {
        const days = parseInt(customDuration, 10);
        if (isNaN(days) || days <= 0) {
          newErrors.duration = 'Custom duration must be a positive number';
        }
      }

      if (!reason.trim()) {
        newErrors.reason = 'Reason is required for manual subscription grants';
      }

      if (requiresOverride && !overrideConfirmed) {
        newErrors.override = 'You must confirm override to replace paid Stripe subscription';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    const roleData = {
      role: selectedRole
    };

    // Add subscription data only for ServerCreator
    if (selectedRole === 'ServerCreator') {
      roleData.subscription = {
        tier,
        duration_days: getDurationDays(),
        reason: reason.trim(),
        override_existing: overrideConfirmed
      };
    }

    try {
      await onSubmit(roleData);
      onClose();
    } catch (error) {
      setErrors({ submit: error.message || 'Failed to update role' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Change User Role</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <div className="user-info">
            <p><strong>User:</strong> {user.username} ({user.email})</p>
          </div>

          {/* Existing Subscription Warning */}
          {currentSubscription?.has_subscription && (
            <div className={`subscription-warning ${currentSubscription.is_paid ? 'danger' : 'info'}`}>
              <h4>Existing Subscription Detected</h4>
              <p>
                <strong>Type:</strong> {currentSubscription.subscription_type === 'stripe' ? 'Paid (Stripe)' : 'Manual Grant'}
                <br />
                <strong>Tier:</strong> {currentSubscription.tier}
                <br />
                <strong>Status:</strong> {currentSubscription.status}
                <br />
                <strong>Expires:</strong> {new Date(currentSubscription.current_period_end).toLocaleDateString()}
              </p>
              {currentSubscription.grant_info && (
                <p style={{ fontSize: '13px', marginTop: '8px' }}>
                  <strong>Grant Reason:</strong> {currentSubscription.grant_info.grant_reason}
                  <br />
                  <strong>Granted By:</strong> {currentSubscription.grant_info.granted_by}
                </p>
              )}
              {currentSubscription.is_paid && (
                <p style={{ color: '#d9534f', fontWeight: 'bold', marginTop: '10px' }}>
                  This is a PAID Stripe subscription. Overriding will cancel their payment and may cause billing issues.
                </p>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Role Selection */}
            <div className="form-group">
              <label><strong>Select Role</strong></label>
              <div className="role-options">
                {roles.map((role) => (
                  <label key={role.value} className={`role-option ${selectedRole === role.value ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="role"
                      value={role.value}
                      checked={selectedRole === role.value}
                      onChange={(e) => setSelectedRole(e.target.value)}
                      disabled={isSubmitting}
                    />
                    <div className="role-info">
                      <strong>{role.label}</strong>
                      <p>{role.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Subscription Configuration (only for ServerCreator) */}
            {selectedRole === 'ServerCreator' && (
              <div className="subscription-config">
                <h3>Subscription Configuration</h3>

                {/* Tier Selection */}
                <div className="form-group">
                  <label htmlFor="tier"><strong>Subscription Tier</strong></label>
                  {loadingTiers ? (
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Loading subscription plans...</p>
                  ) : availableTiers.length === 0 ? (
                    <p className="error-message">No subscription plans available. Contact administrator.</p>
                  ) : (
                    <select
                      id="tier"
                      value={tier}
                      onChange={(e) => setTier(e.target.value)}
                      disabled={isSubmitting}
                      className={errors.tier ? 'error' : ''}
                    >
                      {availableTiers.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label} - {t.price}
                        </option>
                      ))}
                    </select>
                  )}
                  {errors.tier && <span className="error-message">{errors.tier}</span>}
                </div>

                {/* Duration Selection */}
                <div className="form-group">
                  <label htmlFor="duration"><strong>Subscription Duration</strong></label>
                  <select
                    id="duration"
                    value={durationType}
                    onChange={(e) => setDurationType(e.target.value)}
                    disabled={isSubmitting}
                  >
                    {durationPresets.map((d) => (
                      <option key={d.value} value={d.value}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                  {durationType === 'custom' && (
                    <div style={{ marginTop: '10px' }}>
                      <input
                        type="number"
                        placeholder="Enter days"
                        value={customDuration}
                        onChange={(e) => setCustomDuration(e.target.value)}
                        disabled={isSubmitting}
                        min="1"
                        className={errors.duration ? 'error' : ''}
                      />
                      {errors.duration && <span className="error-message">{errors.duration}</span>}
                    </div>
                  )}
                </div>

                {/* Reason */}
                <div className="form-group">
                  <label htmlFor="reason"><strong>Reason for Manual Grant</strong></label>
                  <textarea
                    id="reason"
                    placeholder="e.g., Beta tester, Partnership agreement, Promotional offer..."
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    disabled={isSubmitting}
                    rows={3}
                    className={errors.reason ? 'error' : ''}
                  />
                  {errors.reason && <span className="error-message">{errors.reason}</span>}
                  <small>This will be logged for audit purposes</small>
                </div>

                {/* Override Confirmation (only if paid subscription exists) */}
                {requiresOverride && (
                  <div className="form-group">
                    <label className={`override-checkbox ${errors.override ? 'error' : ''}`}>
                      <input
                        type="checkbox"
                        checked={overrideConfirmed}
                        onChange={(e) => setOverrideConfirmed(e.target.checked)}
                        disabled={isSubmitting}
                      />
                      <strong>I understand this will cancel their paid Stripe subscription</strong>
                    </label>
                    {errors.override && <span className="error-message">{errors.override}</span>}
                  </div>
                )}
              </div>
            )}

            {/* Submit Error */}
            {errors.submit && (
              <div className="submit-error">
                {errors.submit}
              </div>
            )}

            {/* Modal Footer */}
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Updating...' : 'Update Role'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RoleSubscriptionModal;
