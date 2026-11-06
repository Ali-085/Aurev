/**
 * Verify Notice Page
 * 
 * Shown after registration - tells user to check email
 * Includes resend verification functionality
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../config/api';
import './VerifyNotice.css';

const VerifyNotice = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const [email, setEmail] = useState('');
  const [resending, setResending] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // success | error
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  useEffect(() => {
    // Get email from location state (if navigated from registration)
    if (location.state?.email) {
      setEmail(location.state.email);
    }
  }, [location]);

  useEffect(() => {
    // Cooldown timer
    if (cooldownSeconds > 0) {
      const timer = setTimeout(() => {
        setCooldownSeconds(cooldownSeconds - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldownSeconds]);

  const handleResend = async (e) => {
    e.preventDefault();

    if (!email) {
      setMessage('Please enter your email address');
      setMessageType('error');
      return;
    }

    // Client-side cooldown check
    if (cooldownSeconds > 0) {
      setMessage(`Please wait ${cooldownSeconds} seconds before resending`);
      setMessageType('error');
      return;
    }

    try {
      setResending(true);
      setMessage('');

      const response = await api.post('/auth/resend-verification/', {
        email: email.trim().toLowerCase()
      });

      setMessage(response.data.detail || 'If an account exists for this email, a verification link has been sent.');
      setMessageType('success');
      
      // Start 60 second cooldown
      setCooldownSeconds(60);

    } catch (error) {
      console.error('Resend error:', error);
      
      if (error.response?.status === 429) {
        setMessage('Too many requests. Please try again later.');
        setMessageType('error');
        setCooldownSeconds(60); // Force cooldown on rate limit
      } else if (error.response?.data?.detail) {
        setMessage(error.response.data.detail);
        setMessageType('success'); // Show generic message as success
      } else {
        setMessage('Failed to resend verification email. Please try again.');
        setMessageType('error');
      }
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="verify-notice-page">
      <div className="verify-notice-container">
        {/* Header */}
        <div className="notice-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 8L10.89 13.26C11.21 13.47 11.59 13.59 12 13.59C12.41 13.59 12.79 13.47 13.11 13.26L21 8M5 19H19C20.1046 19 21 18.1046 21 17V7C21 5.89543 20.1046 5 19 5H5C3.89543 5 3 5.89543 3 7V17C3 18.1046 3.89543 19 5 19Z" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <defs>
              <linearGradient id="gradient" x1="3" y1="5" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                <stop stopColor="#0066FF"/>
                <stop offset="1" stopColor="#00CCFF"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1>Check Your Email</h1>
        <p className="notice-subtitle">
          We've sent a verification link to <span className="email-highlight">{email || 'your email'}</span>
        </p>

        {/* Instructions */}
        <div className="notice-instructions">
          <h3>What's next?</h3>
          <ol>
            <li>
              <strong>Check your inbox</strong>
              <p>Look for an email from Aurevia</p>
            </li>
            <li>
              <strong>Click the verification link</strong>
              <p>The link is valid for 24 hours</p>
            </li>
            <li>
              <strong>Start using Aurevia</strong>
              <p>Access all features after verification</p>
            </li>
          </ol>
        </div>

        {/* Spam Notice */}
        <div className="notice-warning">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 9V13M12 17H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div className="warning-content">
            <strong>Don't see the email?</strong>
            <p>Check your spam or junk folder. Add noreply@aureviadata.com to your contacts.</p>
          </div>
        </div>

        {/* Resend Form */}
        <div className="resend-section">
          <h3>Didn't receive the email?</h3>
          
          {message && (
            <div className={`message-alert ${messageType}`}>
              {messageType === 'success' ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
              <span>{message}</span>
            </div>
          )}

          <form onSubmit={handleResend} className="resend-form">
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={resending || cooldownSeconds > 0}
              className="resend-input"
              required
            />
            
            <button
              type="submit"
              disabled={resending || cooldownSeconds > 0}
              className="resend-btn"
            >
              {resending ? (
                <>
                  <span className="loading-spinner"></span>
                  Sending...
                </>
              ) : cooldownSeconds > 0 ? (
                <>
                  Wait {cooldownSeconds}s
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 12V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V12M16 6L12 2M12 2L8 6M12 2V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Resend Email
                </>
              )}
            </button>
          </form>
        </div>

        {/* Actions */}
        <div className="notice-actions">
          <button
            onClick={() => navigate('/login')}
            className="action-btn primary"
          >
            Already verified? Login →
          </button>
          <button
            onClick={() => navigate('/')}
            className="action-btn secondary"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyNotice;
