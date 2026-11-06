/**
 * Navigation Bar Component
 * 
 * Site-wide navigation with Aurevia branding
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { isTrader, isPlatformStaff, canManagePlatform, canAdmin, canModerate } from '../utils/permissions';
import './Navbar.css';

// Import logo (will need to be placed in public/assets folder)
const LOGO_PATH = './logo/aurevia-logo.png';

const Navbar = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isStaff = isPlatformStaff(user);
  const isSuperuser = canManagePlatform(user);
  const isAdmin = canAdmin(user);
  const isModerator = canModerate(user);
  const isAdminOrOwner = isStaff;

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo and Brand */}
        <div className="navbar-brand" onClick={() => navigate('/')}>
          <span className="navbar-title">Aurevia</span>
        </div>

        {/* Navigation Links */}
        <div className="navbar-links">
          {!isAuthenticated ? (
            <>
              <button onClick={() => navigate('/')} className="navbar-link">
                Home
              </button>
              <button onClick={() => navigate('/pricing')} className="navbar-link">
                Pricing
              </button>
              <button onClick={() => navigate('/analytics')} className="navbar-link">
                Analytics
              </button>
              <button onClick={() => navigate('/discord')} className="navbar-link">
                Join Aurevia Discord
              </button>
              <button onClick={() => navigate('/login')} className="navbar-btn-login">
                Login
              </button>
              <button onClick={() => navigate('/register')} className="navbar-btn-primary">
                Get Started
              </button>
            </>
          ) : (
            <>
              {/* Regular User Links */}
              {!isAdminOrOwner && (
                <>
                  <button onClick={() => navigate('/dashboard')} className="navbar-link">
                    Dashboard
                  </button>
                  <button onClick={() => navigate('/servers')} className="navbar-link">
                    Servers
                  </button>
                  <button onClick={() => navigate('/payouts')} className="navbar-link">
                    Payouts
                  </button>
                  <button onClick={() => navigate('/analytics')} className="navbar-link">
                    Analytics
                  </button>
                  {isTrader(user) && (
                    <button onClick={() => navigate('/profile')} className="navbar-link">
                      Profile
                    </button>
                  )}
                  <button onClick={() => navigate('/settings')} className="navbar-link">
                    Settings
                  </button>
                </>
              )}

              {/* Admin/Moderator Links */}
              {isAdminOrOwner && (
                <>
                  <button onClick={() => navigate('/dashboard')} className="navbar-link">
                    Dashboard
                  </button>
                  <button onClick={() => navigate('/analytics')} className="navbar-link">
                    Analytics
                  </button>
                  {isSuperuser && (
                    <button onClick={() => navigate('/platform-admin')} className="navbar-link">
                      Admin
                    </button>
                  )}
                  {isAdmin && !isSuperuser && (
                    <button onClick={() => navigate('/admin')} className="navbar-link">
                      Admin
                    </button>
                  )}
                  {isModerator && !isAdmin && (
                    <button onClick={() => navigate('/moderator')} className="navbar-link">
                      Moderator
                    </button>
                  )}
                  <button onClick={() => navigate('/settings')} className="navbar-link">
                    Settings
                  </button>
                </>
              )}

              {/* User Menu */}
              <div className="navbar-user">
                <div className="navbar-user-info">
                  <span className="navbar-username">{user?.username}</span>
                  {user?.subscription_tier && user.subscription_tier !== 'free' && (
                    <span className="navbar-badge">{user.subscription_tier}</span>
                  )}
                </div>
                <button onClick={handleLogout} className="navbar-btn-logout">
                  Logout
                </button>
              </div>
            </>
          )}
        </div>

        {/* Mobile Menu Toggle */}
        <button className="navbar-mobile-toggle">
          ☰
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
