/**
 * Server Creator Success Page
 * 
 * SECURITY:
 * - Polls user activation status from backend
 * - No sensitive data in URL params
 * - Waits for webhook to complete before allowing access
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getUserStatus } from '../services/serverCreatorService';
import api from '../config/api';
import './ServerCreatorSuccess.css';

export default function ServerCreatorSuccess() {
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [countdown, setCountdown] = useState(3);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const sessionId = searchParams.get('session_id');
  const [debugInfo, setDebugInfo] = useState(null);
  const [processing, setProcessing] = useState(false);

  const manuallyProcessPayment = async () => {
    if (!sessionId) {
      alert('No session ID found');
      return;
    }

    setProcessing(true);
    try {
      const processResult = await api.post('/subscriptions/process-session/', {
        session_id: sessionId
      });
      
      // Wait a moment then check status
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const user = await getUserStatus();
      const isServerCreator = user.is_active && user.current_role === 'ServerCreator';
      
      if (isServerCreator) {
        setStatus('success');
      } else {
        alert('Processing completed but role not yet assigned. Please wait a moment and try again.');
      }
    } catch (err) {
      console.error('❌ Manual processing error:', err);
      alert(`Failed to process payment: ${err.response?.data?.error || err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    let pollInterval;
    let pollCount = 0;
    const MAX_POLLS = 30; // 60 seconds total
    
    const verifyActivation = async () => {
      // FIRST: Try to manually process the checkout session
      if (sessionId) {
        try {
          const processResult = await api.post('/subscriptions/process-session/', {
            session_id: sessionId
          });
        } catch (err) {
          // Continue anyway - webhook might have already processed it
        }
      }
      
      // Wait 2 seconds for processing to complete
      await new Promise(resolve => setTimeout(resolve, 2000));

      try {
        // Check if user is now activated and has ServerCreator role
        const user = await getUserStatus();
        
        const isServerCreator = user.is_active && user.current_role === 'ServerCreator';
        
        if (isServerCreator) {
          setStatus('success');
          
          // Start countdown
          const countdownInterval = setInterval(() => {
            setCountdown(prev => {
              if (prev <= 1) {
                clearInterval(countdownInterval);
                navigate('/servers/create');
                return 0;
              }
              return prev - 1;
            });
          }, 1000);
          
          // Clear polling
          if (pollInterval) clearInterval(pollInterval);
        } else {
          // Get debug info
          try {
            const statusResponse = await api.get('/subscriptions/server-creator/status/');
            console.log('Application status:', statusResponse.data);
            setDebugInfo(statusResponse.data);
          } catch (err) {
            console.error('Failed to get debug info:', err);
          }
          
          // Still not active, continue polling every 2 seconds
          pollInterval = setInterval(async () => {
            pollCount++;
            console.log(`Polling attempt ${pollCount}/${MAX_POLLS}`);
            
            if (pollCount >= MAX_POLLS) {
              clearInterval(pollInterval);
              setStatus('error');
              return;
            }
            
            try {
              const user = await getUserStatus();
              const isServerCreator = user.is_active && user.current_role === 'ServerCreator';
              
              if (isServerCreator) {
                setStatus('success');
                clearInterval(pollInterval);
              } else {
                // Update debug info
                const statusResponse = await api.get('/subscriptions/server-creator/status/');
                setDebugInfo(statusResponse.data);
              }
            } catch (err) {
              console.error('Polling error:', err);
            }
          }, 2000);
        }
      } catch (err) {
        console.error('Verification error:', err);
        setStatus('error');
      }
    };

    verifyActivation();

    // Cleanup
    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [navigate, sessionId]);

  return (
    <div className="success-container">
      <div className="success-card">
        {status === 'verifying' && (
          <>
            <div className="spinner-large">⏳</div>
            <h1>Payment Successful!</h1>
            <p className="message">We're activating your account...</p>
            <div className="loading-bar">
              <div className="loading-bar-fill"></div>
            </div>
            <p className="sub-message">This usually takes just a few seconds</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="success-icon"></div>
            <h1>Account Activated!</h1>
            <p className="message">Your server creator account is now active.</p>
            
            <div className="success-details">
              <p>Payment confirmed</p>
              <p>ServerCreator role granted</p>
              <p>Subscription activated</p>
            </div>

            <p className="redirect-message">
              Redirecting to server creation in {countdown} seconds...
            </p>

            <button 
              onClick={() => navigate('/servers/create')}
              className="create-button"
            >
              Create Server Now
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="warning-icon"></div>
            <h1>Activation Pending</h1>
            <p className="message">
              Your payment was successful but activation is taking longer than expected.
            </p>
            <p className="sub-message">
              The webhook may not have been received yet. Please check the details below.
            </p>
            
            {debugInfo && (
              <div style={{ 
                textAlign: 'left', 
                background: '#f5f5f5', 
                padding: '15px', 
                borderRadius: '8px', 
                marginTop: '20px',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}>
                <strong>Debug Information:</strong>
                <pre style={{ margin: '10px 0', overflow: 'auto' }}>
                  {JSON.stringify(debugInfo, null, 2)}
                </pre>
              </div>
            )}
            
            <div className="action-buttons">
              <button 
                onClick={manuallyProcessPayment}
                disabled={processing}
                className="retry-button"
                style={{ 
                  backgroundColor: '#4CAF50', 
                  color: 'white',
                  fontWeight: 'bold',
                  marginBottom: '10px'
                }}
              >
                {processing ? 'Processing...' : '🔄 Force Process Payment'}
              </button>
              <button 
                onClick={() => window.location.reload()}
                className="retry-button"
              >
                Check Again
              </button>
              <button 
                onClick={() => navigate('/dashboard')}
                className="dashboard-button"
              >
                Go to Dashboard
              </button>
            </div>

            <p className="help-text">
              Session ID: <code>{sessionId?.slice(0, 20)}...</code>
              <br />
              Check Stripe Dashboard webhook logs and Render backend logs for errors.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
