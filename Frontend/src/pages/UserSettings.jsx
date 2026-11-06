import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services';
import ChangePassword from '../components/ChangePassword';
import './UserSettings.css';

const UserSettings = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  const [settings, setSettings] = useState({
    username: '',
    email: '',
    avatar_url: null,
    privacy: false,
    private_analytics_token: null,
    private_analytics_url: null
  });
  
  const [showToken, setShowToken] = useState(false);
  const [copied, setCopied] = useState(false);
  
  // Avatar upload state
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/auth/me/');
      setSettings(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching settings:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePrivacy = async () => {
    try {
      setSaving(true);
      const response = await api.post('/auth/users/privacy/toggle/');
      setSettings({
        ...settings,
        privacy: response.data.privacy,
        private_analytics_token: response.data.private_analytics_token,
        private_analytics_url: response.data.private_analytics_url
      });
      setSuccessMessage(
        response.data.privacy 
          ? 'Privacy enabled - Your stats are now hidden from public view' 
          : 'Privacy disabled - Your stats are now public'
      );
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error('Error toggling privacy:', err);
      setError('Failed to update privacy settings');
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerateToken = async () => {
    if (!window.confirm('Are you sure? This will invalidate any previously shared links.')) {
      return;
    }
    
    try {
      setSaving(true);
      const response = await api.post('/auth/users/privacy/regenerate-token/');
      setSettings({
        ...settings,
        private_analytics_token: response.data.private_analytics_token,
        private_analytics_url: response.data.private_analytics_url
      });
      setSuccessMessage('New private analytics link generated');
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error('Error regenerating token:', err);
      setError('Failed to regenerate token');
    } finally {
      setSaving(false);
    }
  };

  const handleCopyLink = () => {
    if (settings.private_analytics_url) {
      navigator.clipboard.writeText(settings.private_analytics_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  
  const handleAvatarSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Invalid file type. Please upload JPG, PNG, or WebP');
      return;
    }
    
    // Validate file size (2MB)
    const maxSize = 2 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 2MB');
      return;
    }
    
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
    setError(null);
  };
  
  const handleAvatarUpload = async () => {
    if (!avatarFile) return;
    
    const formData = new FormData();
    formData.append('avatar', avatarFile);
    
    try {
      setUploadingAvatar(true);
      const response = await api.post('/auth/avatar/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setSettings({
        ...settings,
        avatar_url: response.data.avatar_url
      });
      
      setAvatarFile(null);
      setAvatarPreview(null);
      setSuccessMessage('Avatar uploaded successfully!');
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error('Error uploading avatar:', err);
      setError(err.response?.data?.error || 'Failed to upload avatar');
    } finally {
      setUploadingAvatar(false);
    }
  };
  
  const handleAvatarRemove = async () => {
    if (!settings.avatar_url) return;
    
    if (!window.confirm('Are you sure you want to remove your avatar?')) {
      return;
    }
    
    try {
      setUploadingAvatar(true);
      await api.delete('/auth/avatar/');
      
      setSettings({
        ...settings,
        avatar_url: null
      });
      
      setSuccessMessage('Avatar removed successfully');
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error('Error removing avatar:', err);
      setError('Failed to remove avatar');
    } finally {
      setUploadingAvatar(false);
    }
  };
  
  const handleCancelAvatarUpload = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
  };

  if (loading) {
    return (
      <div className="settings-loading">
        <div className="spinner"></div>
        <p>Loading settings...</p>
      </div>
    );
  }

  if (error && !settings.username) {
    return (
      <div className="settings-error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={fetchSettings}>Retry</button>
      </div>
    );
  }

  return (
    <div className="user-settings">
      <div className="settings-header">
        <h1>User Settings</h1>
        <button className="btn-back" onClick={() => navigate(-1)}>
          Back
        </button>
      </div>

      {successMessage && (
        <div className="alert alert-success">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="settings-section">
        <h2>Profile Information</h2>
        
        <div className="avatar-section">
          <label>Profile Avatar</label>
          <div className="avatar-upload-wrapper">
            <div className="avatar-preview">
              <img 
                src={avatarPreview || settings.avatar_url || '/default-avatar.png'} 
                alt="Profile avatar"
                onError={(e) => {
                  e.target.src = '/default-avatar.png';
                }}
              />
            </div>
            
            <div className="avatar-actions">
              {!avatarFile ? (
                <>
                  <label className="btn-upload">
                    <input
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/webp"
                      onChange={handleAvatarSelect}
                      style={{ display: 'none' }}
                    />
                    Choose Image
                  </label>
                  
                  {settings.avatar_url && (
                    <button
                      className="btn-remove"
                      onClick={handleAvatarRemove}
                      disabled={uploadingAvatar}
                    >
                      Remove Avatar
                    </button>
                  )}
                </>
              ) : (
                <>
                  <button
                    className="btn-confirm"
                    onClick={handleAvatarUpload}
                    disabled={uploadingAvatar}
                  >
                    {uploadingAvatar ? 'Uploading...' : 'Upload'}
                  </button>
                  <button
                    className="btn-cancel"
                    onClick={handleCancelAvatarUpload}
                    disabled={uploadingAvatar}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
          <p className="avatar-hint">
            Recommended: Square image, max 2MB (JPG, PNG, WebP)
          </p>
        </div>
        
        <div className="settings-field">
          <label>Username</label>
          <input type="text" value={settings.username} disabled />
        </div>
        <div className="settings-field">
          <label>Email</label>
          <input type="email" value={settings.email} disabled />
        </div>
      </div>

      <div className="settings-section privacy-section">
        <h2>Privacy Settings</h2>
        
        <div className="privacy-toggle-wrapper">
          <div className="privacy-toggle-info">
            <h3>Hide My Stats</h3>
            <p className="privacy-description">
              When enabled, your stats will be hidden from public leaderboards and profiles. 
              You'll appear as "Private Trader #ID" with only volume ranges visible.
            </p>
          </div>
          
          <button
            className={`toggle-button ${settings.privacy ? 'active' : ''}`}
            onClick={handleTogglePrivacy}
            disabled={saving}
          >
            <span className="toggle-slider"></span>
            <span className="toggle-label">
              {settings.privacy ? 'Private' : 'Public'}
            </span>
          </button>
        </div>

        {settings.privacy && (
          <div className="private-analytics-section">
            <div className="private-analytics-header">
              <h3>Private Analytics Link</h3>
              <p className="info-text">
                Share this link with select people to give them access to your full stats.
                Anyone with this link can view your complete profile.
              </p>
            </div>

            <div className="token-display">
              <div className="token-field">
                <label>Your Private Link</label>
                <div className="token-input-group">
                  <input
                    type={showToken ? 'text' : 'password'}
                    value={settings.private_analytics_url || ''}
                    readOnly
                    className="token-input"
                  />
                  <button
                    className="btn-icon"
                    onClick={() => setShowToken(!showToken)}
                    title={showToken ? 'Hide' : 'Show'}
                  >
                    {showToken ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>

              <div className="token-actions">
                <button
                  className="btn-copy"
                  onClick={handleCopyLink}
                  disabled={!settings.private_analytics_url}
                >
                  {copied ? '✓ Copied!' : 'Copy Link'}
                </button>
                
                <button
                  className="btn-regenerate"
                  onClick={handleRegenerateToken}
                  disabled={saving}
                >
                  Regenerate Link
                </button>
              </div>
            </div>

            <div className="privacy-warning">
              <strong>⚠️ Warning:</strong> Regenerating this link will invalidate any 
              previously shared links. Anyone using the old link will lose access.
            </div>
          </div>
        )}
      </div>

      {/* Password Section */}
      <div className="settings-section">
        <ChangePassword />
      </div>
    </div>
  );
};

export default UserSettings;
