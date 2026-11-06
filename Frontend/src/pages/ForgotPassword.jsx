import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../services/authService';
import './ForgotPassword.css';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect authenticated users away from forgot password page
    if (isAuthenticated) {
      navigate('/profile', { replace: true });
      return;
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      // Even on error, show success message (prevents user enumeration)
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="forgot-password-container">
        <div className="forgot-password-card">
          <div className="forgot-success-icon">✓</div>
          <h1>Check Your Email</h1>
          <p className="forgot-success-message">
            If an account with that email exists, a password reset link has been sent.
          </p>
          <p className="help-text">
            Please check your email inbox (and spam folder) for the reset link. 
            The link will expire in 30 minutes.
          </p>
          <div className="actions">
            <Link to="/login" className="forgot-btn-primary">
              Back to Login
            </Link>
            <button 
              onClick={() => setSubmitted(false)} 
              className="btn-secondary"
            >
              Send Another Link
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="forgot-password-container">
      <div className="forgot-password-card">
        <h1>Reset Password</h1>
        <p className="subtitle">
          Enter your email address and we'll send you a link to reset your password.
        </p>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              disabled={loading}
              autoFocus
            />
          </div>

          <button 
            type="submit" 
            className="forgot-btn-primary"
            disabled={loading || !email}
          >
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <div className="footer-links">
          <Link to="/login">Back to Login</Link>
          <span className="separator">•</span>
          <Link to="/register">Create Account</Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
