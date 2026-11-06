/**
 * Server Settings Page
 * 
 * Allows server owners to update basic server information:
 * - Server name, description
 * - Platform and invite link
 * - Logo upload and management
 * - Market categories selection
 * 
 * SECURITY: Only accessible by server owner
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { serverService, marketService } from '../services';
import { useAuth } from '../context/AuthContext';
import api from '../config/api';
import './ServerSettings.css';

const ServerSettings = () => {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  const [server, setServer] = useState(null);
  const [availableCategories, setAvailableCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [platform, setPlatform] = useState('Discord');
  const [inviteLink, setInviteLink] = useState('');
  const [selectedCategories, setSelectedCategories] = useState([]);
  
  // Contact info state
  const [website, setWebsite] = useState('');
  const [twitterUrl, setTwitterUrl] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [instagramUrl, setInstagramUrl] = useState('');
  const [supportEmail, setSupportEmail] = useState('');
  
  // Logo state
  const [logoPreview, setLogoPreview] = useState(null);
  const [logoFile, setLogoFile] = useState(null);
  const [removeLogo, setRemoveLogo] = useState(false);
  const [platformChoices, setPlatformChoices] = useState([]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchServerData();
    fetchMarketCategories();
    fetchPlatforms();
  }, [serverId, isAuthenticated]);

  const fetchPlatforms = async () => {
    try {
      const response = await api.get('/platform-admin/platforms/?active_only=true');
      if (Array.isArray(response.data)) {
        setPlatformChoices(response.data.map(p => p.name));
      } else {
        setPlatformChoices(['Discord']); // Fallback to Discord
      }
    } catch (err) {
      console.error('Failed to fetch platforms:', err);
      setPlatformChoices(['Discord']); // Fallback to Discord on error
    }
  };

  const fetchServerData = async () => {
    try {
      setLoading(true);
      const data = await serverService.getServerById(serverId);
      
      // Check if user is owner
      if (data.owner_user?.id !== user?.id) {
        setError('You do not have permission to edit this server');
        setLoading(false);
        return;
      }

      setServer(data);
      setName(data.name || '');
      setDescription(data.description || '');
      setPlatform(data.platform || 'Discord');
      setInviteLink(data.invite_link || '');
      
      // Parse market categories - handle both array and JSON string formats
      let categories = [];
      if (data.market_categories) {
        if (Array.isArray(data.market_categories)) {
          categories = data.market_categories;
        } else if (typeof data.market_categories === 'string') {
          try {
            categories = JSON.parse(data.market_categories);
          } catch (e) {
            console.warn('Failed to parse market_categories:', e);
            categories = [];
          }
        }
      }
      setSelectedCategories(categories);
      
      // Load contact info
      setWebsite(data.website || '');
      setTwitterUrl(data.twitter_url || '');
      setYoutubeUrl(data.youtube_url || '');
      setInstagramUrl(data.instagram_url || '');
      setSupportEmail(data.support_email || '');
      
      if (data.logo_url) {
        setLogoPreview(data.logo_url);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching server:', err);
      setError('Failed to load server data 22222');
      setLoading(false);
    }
  };

  const fetchMarketCategories = async () => {
    try {
      const data = await marketService.getMarketCategories();
      // Defensive check: ensure data is an array before filtering
      if (Array.isArray(data)) {
        setAvailableCategories(data.filter(cat => cat.is_active));
      } else {
        setAvailableCategories([]);
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
      setAvailableCategories([]); // Set empty array on error
    }
  };

  const handleLogoChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Invalid file type. Please upload JPG, PNG, or WebP');
      return;
    }

    // Validate file size (2MB)
    if (file.size > 2 * 1024 * 1024) {
      setError('Logo file size must be less than 2MB');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setLogoPreview(reader.result);
      setLogoFile(file);
      setRemoveLogo(false);
      setError(null);
    };
    reader.readAsDataURL(file);
  };

  const handleLogoUpload = async () => {
    if (!logoFile) return;
    
    const formData = new FormData();
    formData.append('logo', logoFile);
    
    try {
      setSaving(true);
      const response = await api.post(`/servers/${serverId}/logo/upload/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setLogoPreview(response.data.logo_url);
      setLogoFile(null);
      setSuccessMessage('Logo uploaded successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
      
      // Refresh server data
      fetchServerData();
    } catch (err) {
      console.error('Error uploading logo:', err);
      setError(err.response?.data?.error || 'Failed to upload logo');
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveLogo = async () => {
    if (!window.confirm('Are you sure you want to remove the server logo?')) {
      return;
    }
    
    try {
      setSaving(true);
      await api.delete(`/servers/${serverId}/logo/`);
      
      setLogoPreview(null);
      setLogoFile(null);
      setRemoveLogo(false);
      setSuccessMessage('Logo removed successfully');
      setTimeout(() => setSuccessMessage(''), 3000);
      
      // Refresh server data
      fetchServerData();
    } catch (err) {
      console.error('Error removing logo:', err);
      setError('Failed to remove logo');
    } finally {
      setSaving(false);
    }
  };
  
  const handleCancelLogoUpload = () => {
    setLogoFile(null);
    setLogoPreview(server?.logo_url || null);
    setRemoveLogo(false);
  };

  const handleCategoryToggle = (categoryName) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryName)) {
        return prev.filter(c => c !== categoryName);
      } else {
        return [...prev, categoryName];
      }
    });
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!name.trim()) {
      setError('Server name is required');
      return;
    }
    if (!description.trim()) {
      setError('Description is required');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage('');

      const formData = new FormData();
      formData.append('name', name.trim());
      formData.append('description', description.trim());
      formData.append('platform', platform);
      formData.append('invite_link', inviteLink.trim());
      formData.append('market_categories', JSON.stringify(selectedCategories));
      
      // Add contact info (empty strings are allowed for optional fields)
      formData.append('website', website.trim());
      formData.append('twitter_url', twitterUrl.trim());
      formData.append('youtube_url', youtubeUrl.trim());
      formData.append('instagram_url', instagramUrl.trim());
      formData.append('support_email', supportEmail.trim());

      await serverService.updateServer(serverId, formData);

      setSuccessMessage('Server settings updated successfully!');
      setTimeout(() => {
        setSuccessMessage('');
        navigate(`/servers/${serverId}/dashboard`);
      }, 2000);
      
      // Refresh server data
      fetchServerData();
    } catch (err) {
      console.error('Error saving settings:', err);
      console.error('Full error response:', JSON.stringify(err.response?.data, null, 2));
      const errorMsg = err.response?.data?.logo?.[0] 
        || err.response?.data?.market_categories?.[0]
        || err.response?.data?.error 
        || 'Failed to save settings';
      setError(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="server-settings-loading">
        <div className="spinner"></div>
        <p>Loading server settings...</p>
      </div>
    );
  }

  if (error && !server) {
    return (
      <div className="server-settings-error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => navigate(-1)}>Go Back</button>
      </div>
    );
  }

  return (
    <div className="server-settings">
      <div className="settings-header">
        <div>
          <h1>Server Settings</h1>
          <p className="server-name-subtitle">{server?.name}</p>
        </div>
        <button className="btn-back" onClick={() => navigate(`/servers/${serverId}/dashboard`)}>
          ← Back to Dashboard
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success">
          {successMessage}
        </div>
      )}

      <form className="settings-form" onSubmit={handleSaveSettings}>
        {/* Logo Section */}
        <section className="settings-section">
          <h2>Server Logo</h2>
          <p className="section-description">
            Upload a logo for your server (Max 2MB, will be resized to 512x512px)
          </p>
          <div className="logo-upload-container">
            <div className="logo-preview-wrapper">
              <img 
                src={logoPreview || '/default-server-logo.png'} 
                alt="Server logo" 
                className="logo-preview"
                onError={(e) => {
                  e.target.src = '/default-server-logo.png';
                }}
              />
              <div className="logo-actions">
                {!logoFile ? (
                  <>
                    <label className="btn-secondary btn-small">
                      <input
                        type="file"
                        accept="image/jpeg,image/jpg,image/png,image/webp"
                        onChange={handleLogoChange}
                        hidden
                      />
                      {logoPreview ? 'Change Logo' : 'Upload Logo'}
                    </label>
                    
                    {logoPreview && (
                      <button 
                        type="button" 
                        className="btn-danger btn-small"
                        onClick={handleRemoveLogo}
                        disabled={saving}
                      >
                        Remove Logo
                      </button>
                    )}
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="btn-confirm btn-small"
                      onClick={handleLogoUpload}
                      disabled={saving}
                    >
                      {saving ? 'Uploading...' : 'Upload'}
                    </button>
                    <button
                      type="button"
                      className="btn-cancel btn-small"
                      onClick={handleCancelLogoUpload}
                      disabled={saving}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Basic Information */}
        <section className="settings-section">
          <h2>Basic Information</h2>
          
          <div className="form-group">
            <label htmlFor="name">Server Name *</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter server name"
              maxLength="200"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description *</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your server and trading community"
              rows="4"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="platform">Platform *</label>
            <select
              id="platform"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              required
            >
              {platformChoices && platformChoices.length > 0 ? (
                platformChoices.map(choice => (
                  <option key={choice} value={choice}>{choice}</option>
                ))
              ) : (
                <option value="Discord">Discord</option>
              )}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="inviteLink">Invite Link (Optional)</label>
            <input
              type="url"
              id="inviteLink"
              value={inviteLink}
              onChange={(e) => setInviteLink(e.target.value)}
              placeholder="Your server invite link"
            />
            <p className="field-hint">
              The link members use to join your server/community
            </p>
          </div>
        </section>

        {/* Market Categories */}
        <section className="settings-section">
          <h2>Market Categories</h2>
          <p className="section-description">
            Select the markets your server focuses on. This helps traders find relevant communities.
          </p>
          <div className="category-grid">
            {availableCategories && availableCategories.length > 0 ? (
              availableCategories.map(category => (
                <label key={category.name} className="category-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category.name)}
                    onChange={() => handleCategoryToggle(category.name)}
                  />
                  <span className="category-label">
                    {category.name}
                  </span>
                </label>
              ))
            ) : (
              <p className="field-hint">No market categories available. Contact platform admin.</p>
            )}
          </div>
          {selectedCategories.length === 0 && (
            <p className="field-hint warning">
              No categories selected. Consider selecting at least one to help traders find your server.
            </p>
          )}
        </section>

        {/* Contact Information */}
        <section className="settings-section">
          <h2>Contact & Links</h2>
          <p className="section-description">
            Add contact information and social links for your server's public profile. All fields are optional.
          </p>
          
          <div className="form-group">
            <label htmlFor="website">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '6px'}}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="2" y1="12" x2="22" y2="12"/>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
              </svg>
              Website
            </label>
            <input
              type="url"
              id="website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="Your website URL"
            />
            <p className="field-hint">Link to your official website</p>
          </div>

          <div className="form-group">
            <label htmlFor="twitterUrl">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{verticalAlign: 'middle', marginRight: '6px'}}>
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
              Twitter / X
            </label>
            <input
              type="url"
              id="twitterUrl"
              value={twitterUrl}
              onChange={(e) => setTwitterUrl(e.target.value)}
              placeholder="Your Twitter/X profile URL"
            />
            <p className="field-hint">Link to your Twitter/X account</p>
          </div>

          <div className="form-group">
            <label htmlFor="youtubeUrl">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{verticalAlign: 'middle', marginRight: '6px', color: '#ff0000'}}>
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              YouTube
            </label>
            <input
              type="url"
              id="youtubeUrl"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="Your YouTube channel URL"
            />
            <p className="field-hint">Link to your YouTube channel</p>
          </div>

          <div className="form-group">
            <label htmlFor="instagramUrl">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style={{verticalAlign: 'middle', marginRight: '6px', color: '#e1306c'}}>
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
              </svg>
              Instagram
            </label>
            <input
              type="url"
              id="instagramUrl"
              value={instagramUrl}
              onChange={(e) => setInstagramUrl(e.target.value)}
              placeholder="Your Instagram profile URL"
            />
            <p className="field-hint">Link to your Instagram account</p>
          </div>

          <div className="form-group">
            <label htmlFor="supportEmail">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{verticalAlign: 'middle', marginRight: '6px'}}>
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
              </svg>
              Support Email
            </label>
            <input
              type="email"
              id="supportEmail"
              value={supportEmail}
              onChange={(e) => setSupportEmail(e.target.value)}
              placeholder="Your support email"
            />
            <p className="field-hint">Email for support inquiries</p>
          </div>

          <div className="contact-info-note">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span>These links will appear on your server's public profile page to help traders connect with your community.</span>
          </div>
        </section>

        {/* Action Buttons */}
        <div className="settings-actions">
          <button 
            type="button" 
            className="btn-secondary"
            onClick={() => navigate(`/servers/${serverId}/dashboard`)}
            disabled={saving}
          >
            Cancel
          </button>
          <button 
            type="submit" 
            className="btn-primary"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ServerSettings;
