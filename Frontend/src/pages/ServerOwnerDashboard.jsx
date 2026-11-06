/**
 * Server Owner Dashboard - Server Selection
 * 
 * Lists all servers owned by the user and allows selection
 * for detailed analytics
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isServerOwner } from '../utils/permissions';
import { serverService } from '../services';
import './ServerOwnerDashboard.css';

const ServerOwnerDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [servers, setServers] = useState([]);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isServerOwner(user)) {
      setError('not_owner');
      setLoading(false);
      return;
    }
    
    // Check for success message from navigation state
    if (location.state?.message) {
      setSuccessMessage(location.state.message);
      // Clear the message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
      // Clear the navigation state
      window.history.replaceState({}, document.title);
    }
    
    fetchOwnedServers();
  }, [user, location]);

  const fetchOwnedServers = async () => {
    try {
      const data = await serverService.getOwnedServers();
      setServers(data.servers);
    } catch (error) {
      console.error('Error fetching owned servers:', error);
      setError('general');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="server-owner-loading">
        <h2>Loading your servers...</h2>
      </div>
    );
  }

  if (error === 'not_owner') {
    return (
      <div className="server-owner-empty">
        <div className="server-owner-empty-icon"></div>
        <h2>Server Owner Dashboard Not Available</h2>
        <p>
          This dashboard is only available for users who own servers. 
          Create a server to access comprehensive analytics and management tools!
        </p>
        <div className="server-owner-empty-actions">
          <button onClick={() => navigate('/dashboard')} className="primary">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (error === 'general' || !servers) {
    return (
      <div className="server-owner-error">
        <h2>Unable to load servers</h2>
        <p>Please try again later.</p>
      </div>
    );
  }

  if (servers.length === 0) {
    return (
      <div className="server-owner-empty">
        <div className="server-owner-empty-icon"></div>
        <h2>No Servers Yet</h2>
        <p>
          You don't have any servers yet. Create your first server to start building your trading community!
        </p>
        <div className="server-owner-empty-actions">
          <button onClick={() => navigate('/servers/create')} className="primary">
            Create Server
          </button>
          <button onClick={() => navigate('/dashboard')} className="secondary">
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="server-owner-dashboard">
      <div className="server-owner-header">
        <h1>Server Owner Dashboard</h1>
        <p>Select a server to view detailed analytics and insights</p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="server-owner-success">
          <span className="server-owner-success-icon"></span>
          <span>{successMessage}</span>
        </div>
      )}

      <div className="server-cards-grid">
        {servers.map(server => (
          <div
            key={server.id}
            className="server-card"
          >
            <div className="server-card-icon"></div>
            <Link 
              to={server.profile_url || `/servers/${server.id}/public`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <h3>{server.name}</h3>
            </Link>
            <p className="server-card-date">
              Created {new Date(server.created_at).toLocaleDateString()}
            </p>
            <div 
              className="server-card-footer"
              onClick={() => navigate(`/my-servers/${server.id}/analytics`)}
              style={{ cursor: 'pointer' }}
            >
              <span>View Analytics</span>
              <span>→</span>
            </div>
          </div>
        ))}
      </div>

      <div className="server-owner-back">
        <button onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </button>
      </div>
    </div>
  );
};

export default ServerOwnerDashboard;
