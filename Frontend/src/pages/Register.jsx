/**
 * Register Page
 * 
 * SECURITY:
 * - Client-side validation
 * - Password confirmation
 * - Email validation
 */

import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './Register.css';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountType, setAccountType] = useState('normal');
  const [selectedServer, setSelectedServer] = useState('');
  const [servers, setServers] = useState([]);
  const [loadingServers, setLoadingServers] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Server Creator fields
  const [tier, setTier] = useState('');
  const [serverName, setServerName] = useState('');
  const [serverDescription, setServerDescription] = useState('');
  const [discordServerId, setDiscordServerId] = useState('');
  
  // Subscription plans state
  const [subscriptionPlans, setSubscriptionPlans] = useState([]);
  const [loadingPlans, setLoadingPlans] = useState(false);

  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect authenticated users away from registration page
    if (isAuthenticated) {
      navigate('/profile', { replace: true });
      return;
    }
    
    // Fetch available servers for trader registration
    const fetchServers = async () => {
      setLoadingServers(true);
      try {
        const response = await api.get('/servers/');
        // Handle both paginated and non-paginated responses
        const serverList = Array.isArray(response.data) ? response.data : (response.data.results || []);
        setServers(serverList);
      } catch (error) {
        console.error('Error fetching servers:', error);
        setServers([]);
      } finally {
        setLoadingServers(false);
      }
    };
    
    // Fetch subscription plans for server creator registration
    const fetchSubscriptionPlans = async () => {
      setLoadingPlans(true);
      try {
        const response = await api.get('/subscriptions/plans/');
        const plansList = Array.isArray(response.data) ? response.data : (response.data.results || []);
        // Sort by tier order: standard, premium, elite
        const sortedPlans = plansList.sort((a, b) => a.sort_order - b.sort_order);
        setSubscriptionPlans(sortedPlans);
        // Set default tier to first plan
        if (sortedPlans.length > 0) {
          setTier(sortedPlans[0].tier);
        }
      } catch (error) {
        console.error('Error fetching subscription plans:', error);
        setSubscriptionPlans([]);
      } finally {
        setLoadingPlans(false);
      }
    };
    
    fetchServers();
    fetchSubscriptionPlans();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // SECURITY: Client-side validation
    if (!username || !email || !password || !confirmPassword) {
      setError('All fields are required');
      return;
    }
    
    // Validate server creator registration
    if (accountType === 'server_creator' && !tier) {
      setError('Please select a subscription tier');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);

    const result = await register(
      username, 
      email, 
      password, 
      accountType, 
      selectedServer,
      // Server creator fields
      tier,
      serverName,
      serverDescription,
      discordServerId
    );

    if (result.success) {
      // Navigate to verify notice page after registration
      navigate('/verify-notice', { state: { email } });
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="register-page">
      <h1>Register</h1>
      
      {error && (
        <div className="register-error">
          {error}
        </div>
      )}

      <form className="register-form" onSubmit={handleSubmit}>
        <div className="account-type-section">
          <label>I want to join as:</label>
          <div className="account-type-options">
            <label className={`account-type-option ${accountType === 'trader' ? 'trader-selected' : ''}`}>
              <input
                type="radio"
                name="accountType"
                value="trader"
                checked={accountType === 'trader'}
                onChange={(e) => setAccountType(e.target.value)}
                disabled={loading}
              />
              <strong>Trader</strong>
              <div className="account-type-description">
                Join the platform and optionally join a trading server
              </div>
            </label>
            
            <label className={`account-type-option ${accountType === 'server_creator' ? 'creator-selected' : ''}`}>
              <input
                type="radio"
                name="accountType"
                value="server_creator"
                checked={accountType === 'server_creator'}
                onChange={(e) => setAccountType(e.target.value)}
                disabled={loading}
              />
              <strong>Server Creator</strong>
              <div className="account-type-description">
                Create and manage your own trading community/server (requires subscription)
              </div>
            </label>
          </div>
        </div>

        {/* Server Selection for Traders */}
        {accountType === 'trader' && (
          <div className="server-selection-section">
            <label htmlFor="server">Select a Server to Join (Optional)</label>
            {loadingServers ? (
              <div className="server-selection-loading">Loading servers...</div>
            ) : (
              <select
                id="server"
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                disabled={loading}
              >
                <option value="">-- Choose a server (or skip) --</option>
                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name}
                  </option>
                ))}
              </select>
            )}
            <div className="server-selection-hint">
              You can join servers later from the platform
            </div>
          </div>
        )}

        {/* Tier Selection for Server Creators */}
        {accountType === 'server_creator' && (
          <div className="tier-selection-section">
            <label htmlFor="tier">Select Subscription Tier *</label>
            {loadingPlans ? (
              <div className="tier-selection-loading">Loading subscription plans...</div>
            ) : subscriptionPlans.length > 0 ? (
              <select
                id="tier"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
                disabled={loading}
                required={accountType === 'server_creator'}
              >
                {subscriptionPlans.map((plan) => (
                  <option key={plan.id} value={plan.tier}>
                    {plan.name} - ${plan.price_per_month}/month
                  </option>
                ))}
              </select>
            ) : (
              <div className="tier-selection-error">
                Unable to load subscription plans. Please try again later.
              </div>
            )}

            <label htmlFor="serverName">Server Name (Optional)</label>
            <input
              id="serverName"
              type="text"
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              disabled={loading}
              placeholder="e.g., Elite Traders Hub"
            />

            <label htmlFor="discordServerId">Discord Server ID (Optional)</label>
            <input
              id="discordServerId"
              type="text"
              value={discordServerId}
              onChange={(e) => setDiscordServerId(e.target.value)}
              disabled={loading}
              placeholder="Your Discord server ID"
            />

            <div className="payment-notice">
              You'll be redirected to complete payment after email verification
            </div>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            autoComplete="username"
          />
        </div>

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
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            autoComplete="new-password"
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={loading}
            autoComplete="new-password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="register-submit"
        >
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>

      <p className="register-footer">
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
};

export default Register;
