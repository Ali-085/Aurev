import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { serverService, analyticsService } from '../services';
import { useAuth } from '../context/AuthContext';
import './ServerBrandingSettings.css';

const ServerBrandingSettings = () => {
  const { serverId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [server, setServer] = useState(null);
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');

  // Form state
  const [primaryColor, setPrimaryColor] = useState('#4CAF50');
  const [secondaryColor, setSecondaryColor] = useState('#2196F3');
  const [highlightColor, setHighlightColor] = useState('#FFD700');
  const [badgeBorderColor, setBadgeBorderColor] = useState('#FFD700');
  const [leaderboardTheme, setLeaderboardTheme] = useState('default');
  const [whiteLabel, setWhiteLabel] = useState(false);
  const [themeChoices, setThemeChoices] = useState([]);

  // Image previews
  const [logoPreview, setLogoPreview] = useState(null);
  const [bannerPreview, setBannerPreview] = useState(null);
  const [backgroundPreview, setBackgroundPreview] = useState(null);

  // Image files
  const [logoFile, setLogoFile] = useState(null);
  const [bannerFile, setBannerFile] = useState(null);
  const [backgroundFile, setBackgroundFile] = useState(null);

  useEffect(() => {
    fetchServerAndBranding();
  }, [serverId]);

  const fetchServerAndBranding = async () => {
    try {
      setLoading(true);

      // Fetch server details
      const serverData = await serverService.getServerById(serverId);
      setServer(serverData);

      // Check if Elite
      const subscriptionData = await analyticsService.getUserSubscription(serverData.id);

      if (!subscriptionData.is_elite) {
        setError('Elite subscription required for custom branding');
        setLoading(false);
        return;
      }

      // Fetch branding
      try {
        const brandingData = await serverService.getServerBranding(serverData.id);
        setBranding(brandingData);
        
        // Set form values from existing branding
        if (brandingData) {
          setPrimaryColor(brandingData.primary_color || '#4CAF50');
          setSecondaryColor(brandingData.secondary_color || '#2196F3');
          setHighlightColor(brandingData.highlight_color || '#FFD700');
          setBadgeBorderColor(brandingData.badge_border_color || '#FFD700');
          setLeaderboardTheme(brandingData.leaderboard_theme || 'default');
          setWhiteLabel(brandingData.white_label || false);
          setThemeChoices(brandingData.theme_choices || []);
          
          // Set image previews
          if (brandingData.logo) {
            setLogoPreview(brandingData.logo);
          }
          if (brandingData.banner) {
            setBannerPreview(brandingData.banner);
          }
          if (brandingData.custom_background) {
            setBackgroundPreview(brandingData.custom_background);
          }
        }
      } catch (brandingError) {
        // No branding found, will create new on save
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.response?.data?.error || 'Failed to load server data');
      setLoading(false);
    }
  };

  const handleImageChange = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Validate file size
    const maxSize = type === 'logo' ? 2 : 5; // MB
    if (file.size > maxSize * 1024 * 1024) {
      alert(`File size must be less than ${maxSize}MB`);
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      if (type === 'logo') {
        setLogoPreview(reader.result);
        setLogoFile(file);
      } else if (type === 'banner') {
        setBannerPreview(reader.result);
        setBannerFile(file);
      } else if (type === 'background') {
        setBackgroundPreview(reader.result);
        setBackgroundFile(file);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSaveBranding = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage('');

      const formData = new FormData();
      
      // Add images if changed
      if (logoFile) formData.append('logo', logoFile);
      if (bannerFile) formData.append('banner', bannerFile);
      if (backgroundFile) formData.append('custom_background', backgroundFile);
      
      // Add colors
      formData.append('primary_color', primaryColor);
      formData.append('secondary_color', secondaryColor);
      formData.append('highlight_color', highlightColor);
      formData.append('badge_border_color', badgeBorderColor);
      formData.append('leaderboard_theme', leaderboardTheme);
      formData.append('white_label', whiteLabel);

      await serverService.updateServerBranding(server.id, formData);

      setSuccessMessage('Branding updated successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
      fetchServerAndBranding();
    } catch (err) {
      console.error('Error saving branding:', err);
      setError(err.response?.data?.error || 'Failed to save branding');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="branding-settings-loading">
        <div className="spinner"></div>
        <p>Loading branding settings...</p>
      </div>
    );
  }

  if (error && !server) {
    return (
      <div className="branding-settings-error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => navigate(-1)}>Go Back</button>
      </div>
    );
  }

  return (
    <div className="branding-settings">
      <div className="branding-header">
        <div>
          <h1>Elite Branding Settings</h1>
          <p className="server-name">{server?.name}</p>
        </div>
        <button className="btn-back" onClick={() => navigate(`/servers/${serverId}/dashboard`)}>
          ← Back to Server
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

      <div className="branding-content">
        {/* Logo Upload */}
        <section className="branding-section">
          <h2>Logo</h2>
          <p className="section-description">
            Upload your server logo (Max 2MB, 512x512px recommended)
          </p>
          <div className="image-upload-container">
            {logoPreview && (
              <div className="image-preview logo-preview">
                <img src={logoPreview} alt="Logo preview" />
              </div>
            )}
            <label className="btn-upload">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => handleImageChange(e, 'logo')}
                hidden
              />
              {logoPreview ? 'Change Logo' : 'Upload Logo'}
            </label>
          </div>
        </section>

        {/* Banner Upload */}
        <section className="branding-section">
          <h2>Banner</h2>
          <p className="section-description">
            Upload your server banner (Max 5MB, 2560x1440px recommended)
          </p>
          <div className="image-upload-container">
            {bannerPreview && (
              <div className="image-preview banner-preview">
                <img src={bannerPreview} alt="Banner preview" />
              </div>
            )}
            <label className="btn-upload">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => handleImageChange(e, 'banner')}
                hidden
              />
              {bannerPreview ? 'Change Banner' : 'Upload Banner'}
            </label>
          </div>
        </section>

        {/* Custom Background */}
        <section className="branding-section">
          <h2>Custom Background</h2>
          <p className="section-description">
            Upload a custom background for your server page (Max 5MB)
          </p>
          <div className="image-upload-container">
            {backgroundPreview && (
              <div className="image-preview background-preview">
                <img src={backgroundPreview} alt="Background preview" />
              </div>
            )}
            <label className="btn-upload">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => handleImageChange(e, 'background')}
                hidden
              />
              {backgroundPreview ? 'Change Background' : 'Upload Background'}
            </label>
          </div>
        </section>

        {/* Color Scheme */}
        <section className="branding-section">
          <h2>Color Scheme</h2>
          <p className="section-description">
            Customize your server's color palette
          </p>
          <div className="color-grid">
            <div className="color-input-group">
              <label>Primary Color</label>
              <div className="color-input-wrapper">
                <input
                  type="color"
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="color-picker"
                />
                <input
                  type="text"
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="color-text"
                  placeholder="#4CAF50"
                />
              </div>
            </div>

            <div className="color-input-group">
              <label>Secondary Color</label>
              <div className="color-input-wrapper">
                <input
                  type="color"
                  value={secondaryColor}
                  onChange={(e) => setSecondaryColor(e.target.value)}
                  className="color-picker"
                />
                <input
                  type="text"
                  value={secondaryColor}
                  onChange={(e) => setSecondaryColor(e.target.value)}
                  className="color-text"
                  placeholder="#2196F3"
                />
              </div>
            </div>

            <div className="color-input-group">
              <label>Highlight Color</label>
              <div className="color-input-wrapper">
                <input
                  type="color"
                  value={highlightColor}
                  onChange={(e) => setHighlightColor(e.target.value)}
                  className="color-picker"
                />
                <input
                  type="text"
                  value={highlightColor}
                  onChange={(e) => setHighlightColor(e.target.value)}
                  className="color-text"
                  placeholder="#FFD700"
                />
              </div>
            </div>

            <div className="color-input-group">
              <label>Badge Border Color</label>
              <div className="color-input-wrapper">
                <input
                  type="color"
                  value={badgeBorderColor}
                  onChange={(e) => setBadgeBorderColor(e.target.value)}
                  className="color-picker"
                />
                <input
                  type="text"
                  value={badgeBorderColor}
                  onChange={(e) => setBadgeBorderColor(e.target.value)}
                  className="color-text"
                  placeholder="#FFD700"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Leaderboard Theme */}
        <section className="branding-section">
          <h2>Leaderboard Theme</h2>
          <p className="section-description">
            Choose from 5 pre-designed leaderboard themes
          </p>
          <div className="theme-selector">
            {themeChoices.map((theme) => (
              <div
                key={theme.value}
                className={`theme-option ${leaderboardTheme === theme.value ? 'active' : ''}`}
                onClick={() => setLeaderboardTheme(theme.value)}
              >
                <div className={`theme-preview theme-${theme.value}`}>
                  <div className="theme-preview-header">Rank</div>
                  <div className="theme-preview-content">
                    <span>1. Trader</span>
                    <span>$10,000</span>
                  </div>
                </div>
                <div className="theme-name">{theme.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* White Label */}
        <section className="branding-section">
          <h2>White Label</h2>
          <p className="section-description">
            Remove Aurevia branding from your server page
          </p>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={whiteLabel}
              onChange={(e) => setWhiteLabel(e.target.checked)}
            />
            <span className="toggle-slider"></span>
            <span className="toggle-label">
              {whiteLabel ? 'White Label Enabled' : 'White Label Disabled'}
            </span>
          </label>
        </section>

        {/* Save Button */}
        <div className="branding-actions">
          <button
            className="btn-save"
            onClick={handleSaveBranding}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save All Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ServerBrandingSettings;
