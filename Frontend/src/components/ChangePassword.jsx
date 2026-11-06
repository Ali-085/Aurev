import { useState, useEffect } from 'react';
import authService from '../services/authService';
import './ChangePassword.css';

const ChangePassword = () => {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, feedback: [] });

  // Calculate password strength
  useEffect(() => {
    if (!formData.newPassword) {
      setPasswordStrength({ score: 0, feedback: [] });
      return;
    }

    const password = formData.newPassword;
    let score = 0;
    const feedback = [];

    if (password.length >= 8) score += 1;
    else feedback.push('At least 8 characters');

    if (/[A-Z]/.test(password)) score += 1;
    else feedback.push('One uppercase letter');

    if (/[a-z]/.test(password)) score += 1;
    else feedback.push('One lowercase letter');

    if (/[0-9]/.test(password)) score += 1;
    else feedback.push('One number');

    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    else feedback.push('One special character');

    setPasswordStrength({ score, feedback });
  }, [formData.newPassword]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear errors when user types
    if (error) setError('');
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
    if (success) setSuccess(false);
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.currentPassword) {
      errors.currentPassword = 'Current password is required';
    }

    if (!formData.newPassword) {
      errors.newPassword = 'New password is required';
    } else if (formData.newPassword.length < 8) {
      errors.newPassword = 'Password must be at least 8 characters';
    } else if (formData.currentPassword === formData.newPassword) {
      errors.newPassword = 'New password must be different from current password';
    }

    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (formData.newPassword !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      await authService.changePassword(
        formData.currentPassword,
        formData.newPassword,
        formData.confirmPassword
      );
      
      setSuccess(true);
      
      // Clear form
      setFormData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(false), 5000);
    } catch (err) {
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.response?.data) {
        // Handle validation errors
        const errors = {};
        Object.keys(err.response.data).forEach(key => {
          const snakeToCamel = key.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
          if (Array.isArray(err.response.data[key])) {
            errors[snakeToCamel] = err.response.data[key][0];
          } else {
            errors[snakeToCamel] = err.response.data[key];
          }
        });
        setValidationErrors(errors);
        setError('Please fix the errors below');
      } else {
        setError('Failed to change password. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStrengthColor = () => {
    if (passwordStrength.score <= 1) return '#e53e3e';
    if (passwordStrength.score <= 2) return '#dd6b20';
    if (passwordStrength.score <= 3) return '#d69e2e';
    if (passwordStrength.score <= 4) return '#38a169';
    return '#22543d';
  };

  const getStrengthLabel = () => {
    if (passwordStrength.score <= 1) return 'Weak';
    if (passwordStrength.score <= 2) return 'Fair';
    if (passwordStrength.score <= 3) return 'Good';
    if (passwordStrength.score <= 4) return 'Strong';
    return 'Excellent';
  };

  return (
    <div className="change-password-section">
      <h2>Change Password</h2>
      <p className="section-description">
        Update your password to keep your account secure. You'll be logged out of other devices.
      </p>

      <form onSubmit={handleSubmit} className="change-password-form">
        {success && (
          <div className="success-message">
            ✓ Password changed successfully! Other sessions have been logged out.
          </div>
        )}

        {error && <div className="error-message">{error}</div>}

        <div className="form-group">
          <label htmlFor="currentPassword">Current Password</label>
          <input
            id="currentPassword"
            type="password"
            name="currentPassword"
            value={formData.currentPassword}
            onChange={handleChange}
            placeholder="Enter current password"
            disabled={loading}
            autoComplete="current-password"
          />
          {validationErrors.currentPassword && (
            <span className="field-error">{validationErrors.currentPassword}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="newPassword">New Password</label>
          <input
            id="newPassword"
            type="password"
            name="newPassword"
            value={formData.newPassword}
            onChange={handleChange}
            placeholder="Enter new password"
            disabled={loading}
            autoComplete="new-password"
          />
          {validationErrors.newPassword && (
            <span className="field-error">{validationErrors.newPassword}</span>
          )}
          
          {formData.newPassword && (
            <div className="password-strength">
              <div className="strength-bar">
                <div 
                  className="strength-fill" 
                  style={{ 
                    width: `${(passwordStrength.score / 5) * 100}%`,
                    backgroundColor: getStrengthColor()
                  }}
                />
              </div>
              <div className="strength-info">
                <span 
                  className="strength-label" 
                  style={{ color: getStrengthColor() }}
                >
                  {getStrengthLabel()}
                </span>
                {passwordStrength.feedback.length > 0 && (
                  <span className="strength-feedback">
                    Missing: {passwordStrength.feedback.join(', ')}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm New Password</label>
          <input
            id="confirmPassword"
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            placeholder="Confirm new password"
            disabled={loading}
            autoComplete="new-password"
          />
          {validationErrors.confirmPassword && (
            <span className="field-error">{validationErrors.confirmPassword}</span>
          )}
          {formData.confirmPassword && formData.newPassword === formData.confirmPassword && (
            <span className="field-success">✓ Passwords match</span>
          )}
        </div>

        <div className="form-actions">
          <button 
            type="submit" 
            className="btn-primary"
            disabled={loading || passwordStrength.score < 3}
          >
            {loading ? 'Changing Password...' : 'Change Password'}
          </button>
          
          {passwordStrength.score < 3 && formData.newPassword && (
            <p className="warning-text">
              Please create a stronger password to continue
            </p>
          )}
        </div>

        <div className="security-notice">
          <strong>Security Notice:</strong> Changing your password will log you out of all other devices 
          for security reasons. You'll remain logged in on this device.
        </div>
      </form>
    </div>
  );
};

export default ChangePassword;
