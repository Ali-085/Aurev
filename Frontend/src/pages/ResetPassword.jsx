import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../services/authService';
import './ResetPassword.css';

const ResetPassword = () => {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  const [formData, setFormData] = useState({
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, feedback: [] });

  useEffect(() => {
    // Redirect authenticated users away from password reset page
    if (isAuthenticated) {
      navigate('/profile', { replace: true });
      return;
    }
    
    // Validate token parameters
    if (!uid || !token) {
      setError('Invalid reset link. Please request a new password reset.');
    }
  }, [isAuthenticated, navigate, uid, token]);

  // Calculate password strength
  useEffect(() => {
    if (!formData.newPassword) {
      setPasswordStrength({ score: 0, feedback: [] });
      return;
    }

    const password = formData.newPassword;
    let score = 0;
    const feedback = [];

    // Length check
    if (password.length >= 8) {
      score += 1;
    } else {
      feedback.push('At least 8 characters');
    }

    // Uppercase check
    if (/[A-Z]/.test(password)) {
      score += 1;
    } else {
      feedback.push('One uppercase letter');
    }

    // Lowercase check
    if (/[a-z]/.test(password)) {
      score += 1;
    } else {
      feedback.push('One lowercase letter');
    }

    // Number check
    if (/[0-9]/.test(password)) {
      score += 1;
    } else {
      feedback.push('One number');
    }

    // Special character check
    if (/[^A-Za-z0-9]/.test(password)) {
      score += 1;
    } else {
      feedback.push('One special character');
    }

    setPasswordStrength({ score, feedback });
  }, [formData.newPassword]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear validation error for this field
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.newPassword) {
      errors.newPassword = 'Password is required';
    } else if (formData.newPassword.length < 8) {
      errors.newPassword = 'Password must be at least 8 characters';
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

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      await authService.resetPassword(
        uid,
        token,
        formData.newPassword,
        formData.confirmPassword
      );
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.response?.data) {
        // Handle validation errors
        const errors = {};
        Object.keys(err.response.data).forEach(key => {
          if (Array.isArray(err.response.data[key])) {
            errors[key] = err.response.data[key][0];
          } else {
            errors[key] = err.response.data[key];
          }
        });
        setValidationErrors(errors);
        setError('Please fix the errors below');
      } else {
        setError('Failed to reset password. Please try again.');
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

  if (success) {
    return (
      <div className="reset-password-container">
        <div className="reset-password-card">
          <div className="success-icon">✓</div>
          <h1>Password Reset Successful!</h1>
          <p className="res-success-message">
            Your password has been reset successfully.
          </p>
          <p className="help-text">
            Redirecting to login page...
          </p>
          <Link to="/login" className="res-btn-primary">
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  if (error && (!uid || !token)) {
    return (
      <div className="reset-password-container">
        <div className="reset-password-card">
          <div className="error-icon">✕</div>
          <h1>Invalid Reset Link</h1>
          <p className="error-text">
            This password reset link is invalid or has expired.
          </p>
          <div className="actions">
            <Link to="/forgot-password" className="res-btn-primary">
              Request New Link
            </Link>
            <Link to="/login" className="btn-secondary">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="reset-password-container">
      <div className="reset-password-card">
        <h1>Create New Password</h1>
        <p className="subtitle">
          Please enter a strong password for your account.
        </p>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="newPassword">New Password</label>
            <input
              id="newPassword"
              type="password"
              name="newPassword"
              value={formData.newPassword}
              onChange={handleChange}
              placeholder="Enter new password"
              required
              disabled={loading}
              autoFocus
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
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm new password"
              required
              disabled={loading}
            />
            {validationErrors.confirmPassword && (
              <span className="field-error">{validationErrors.confirmPassword}</span>
            )}
            {formData.confirmPassword && formData.newPassword === formData.confirmPassword && (
              <span className="field-success">✓ Passwords match</span>
            )}
          </div>

          <button 
            type="submit" 
            className="res-btn-primary"
            disabled={loading || passwordStrength.score < 3}
          >
            {loading ? 'Resetting Password...' : 'Reset Password'}
          </button>

          {passwordStrength.score < 3 && formData.newPassword && (
            <p className="warning-text">
              Please create a stronger password to continue
            </p>
          )}
        </form>

        <div className="footer-links">
          <Link to="/login">Back to Login</Link>
        </div>
      </div>
    </div>
  );
};

export default ResetPassword;
