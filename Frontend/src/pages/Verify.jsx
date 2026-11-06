/**
 * Email Verification Page
 * 
 * Handles email verification from link in email.
 * Extracts uid and token from URL query params and calls backend.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import api from '../config/api';
import './Verify.css';

const Verify = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [status, setStatus] = useState('verifying'); // verifying | success | error
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    verifyEmail();
  }, []);

  const verifyEmail = async () => {
    const uid = searchParams.get('uid');
    const token = searchParams.get('token');

    if (!uid || !token) {
      setStatus('error');
      setMessage('Verification link is invalid. Please check the link or request a new one.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      
      const response = await api.post('/auth/verify/', {
        uid,
        token
      });

      setStatus('success');
      setMessage(response.data.detail || 'Email verified successfully!');
      
      // Check if this is a server creator requiring payment
      if (response.data.requires_payment) {
        // Store application_id if needed
        if (response.data.application_id) {
          localStorage.setItem('application_id', response.data.application_id);
        }
        
        // Redirect to checkout
        setTimeout(() => {
          navigate('/server-creator/checkout');
        }, 2000);
      } else {
        // Trader user - redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }

    } catch (error) {
      console.error('Verification error:', error);
      
      setStatus('error');
      
      if (error.response?.data?.detail) {
        setMessage(error.response.data.detail);
      } else if (error.response?.status === 429) {
        setMessage('Too many verification attempts. Please try again later.');
      } else {
        setMessage('Verification failed. Please try again or request a new verification link.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="verify-page">
      <div className="verify-container">
        {/* Verifying State */}
        {status === 'verifying' && (
          <>
            <div className="verify-icon verifying">
              <div className="loading-spinner-large"></div>
            </div>
            <h1>Verifying Your Email</h1>
            <p className="verify-message">
              Please wait while we verify your account...
            </p>
          </>
        )}

        {/* Success State */}
        {status === 'success' && (
          <>
            <div className="verify-icon success">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="url(#successGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <defs>
                  <linearGradient id="successGradient" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#10B981"/>
                    <stop offset="1" stopColor="#059669"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1>Email Verified!</h1>
            <p className="verify-message success">
              {message}
            </p>
            <div className="verify-info">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M13 16H12V12H11M12 8H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#4D94FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <p>Redirecting to login page in a few seconds...</p>
            </div>
            <Link to="/login" className="btn btn-primary">
              Go to Login →
            </Link>
          </>
        )}

        {/* Error State */}
        {status === 'error' && (
          <>
            <div className="verify-icon error">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="url(#errorGradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <defs>
                  <linearGradient id="errorGradient" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#EF4444"/>
                    <stop offset="1" stopColor="#DC2626"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <h1>Verification Failed</h1>
            <p className="verify-message error">
              {message}
            </p>
            <div className="verify-actions">
              <Link to="/verify-notice" className="btn btn-primary">
                Request New Link
              </Link>
              <Link to="/login" className="btn btn-secondary">
                Back to Login
              </Link>
            </div>
            <div className="verify-help">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8.228 9C8.418 8.418 8.807 7.933 9.324 7.634C9.842 7.335 10.45 7.244 11.03 7.378C11.609 7.513 12.112 7.863 12.438 8.358C12.764 8.854 12.89 9.458 12.79 10.05C12.488 11.688 10 11.5 10 14M10 18H10.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="#F59E0B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="help-content">
                <p>Need help? Common issues:</p>
                <ul>
                  <li>Link expired (valid for 24 hours)</li>
                  <li>Link already used</li>
                  <li>Invalid or corrupted link</li>
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Verify;
