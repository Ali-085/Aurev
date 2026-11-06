/**
 * Login Page
 * 
 * SECURITY:
 * - Client-side validation before submission
 * - Error handling without exposing sensitive info
 * - Redirects to previous page after login
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';
import { Eye, EyeOff } from "lucide-react";

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get the page user was trying to access
  const from = location.state?.from?.pathname || '/profile';

  useEffect(() => {
    // Redirect authenticated users away from login page
    if (isAuthenticated) {
      navigate(from, { replace: true });
      return;
    }
  }, [isAuthenticated, navigate, from]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // SECURITY: Client-side validation
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }

    setLoading(true);

    const result = await login(email, password);

    if (result.success) {
      // Check if user has pending payment (server creator needs to complete checkout)
      if (result.pending_payment && result.redirect_to) {
        navigate(result.redirect_to, { 
          replace: true,
          state: { application_id: result.application_id }
        });
      } else {
        // SECURITY: Determine redirect based on user data without exposing hierarchy
        // Staff users have default_dashboard_url set by backend
        const redirectPath =  location.state?.from?.pathname || result.user?.default_dashboard_url || from;
        navigate(redirectPath, { replace: true });
      }
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="login-page">
      <h1>Login</h1>
      
      {error && (
        <div className="login-error">
          {error}
        </div>
      )}

      <form className="login-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            autoComplete="email"
          />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>

          <div className="password-wrapper">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              autoComplete="current-password"
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <div className="forgot-password-link">
            <Link to="/forgot-password">Forgot password?</Link>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="login-submit"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <p className="login-footer">
        Don't have an account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
};

export default Login;
