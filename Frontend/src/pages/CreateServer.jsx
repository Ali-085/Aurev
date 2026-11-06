/**
 * Create Server Page
 * 
 * Allows authenticated users to create a new trading server
 * Uses centralized API calls and Aurevia design system
 * 
 * SECURITY:
 * - Client-side validation
 * - Authenticated users only
 * - Backend enforces server creation limits
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { serverService } from '../services';
import api from '../config/api';
import './CreateServer.css';

const CreateServer = () => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    platform: 'Discord',
    invite_link: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const [platformOptions, setPlatformOptions] = useState([]);
  
  const { user } = useAuth();
  const navigate = useNavigate();

  // Fetch available platforms
  useEffect(() => {
    const fetchPlatforms = async () => {
      try {
        const response = await api.get('/platform-admin/platforms/?active_only=true');
        setPlatformOptions(response.data.map(p => ({
          value: p.name,
          label: p.name,
        })));
        // Set first platform as default if available
        if (response.data.length > 0 && !formData.platform) {
          setFormData(prev => ({ ...prev, platform: response.data[0].name }));
        }
      } catch (err) {
        console.error('Failed to fetch platforms:', err);
        // Fallback to empty array - user will see error if they try to submit
      }
    };
    fetchPlatforms();
  }, []);


  // Validation function
  const validateForm = () => {
    const errors = {};
    
    // Name validation
    if (!formData.name.trim()) {
      errors.name = 'Server name is required';
    } else if (formData.name.length < 3) {
      errors.name = 'Server name must be at least 3 characters';
    } else if (formData.name.length > 200) {
      errors.name = 'Server name must be less than 200 characters';
    }
    
    // Description validation
    if (!formData.description.trim()) {
      errors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      errors.description = 'Description must be at least 10 characters';
    } else if (formData.description.length > 1000) {
      errors.description = 'Description must be less than 1000 characters';
    }
    
    // Platform validation
    if (!formData.platform) {
      errors.platform = 'Please select a platform';
    }
    
    // Invite link validation (optional but must be valid URL if provided)
    if (formData.invite_link.trim()) {
      // URL validation only if a value is provided
      try {
        const url = new URL(formData.invite_link);
        if (!['http:', 'https:'].includes(url.protocol)) {
          errors.invite_link = 'Invite link must be a valid HTTP/HTTPS URL';
        }
      } catch (e) {
        errors.invite_link = 'Please enter a valid URL (e.g., https://discord.gg/...)';
      }
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear validation error for this field
    if (validationErrors[name]) {
      setValidationErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Client-side validation
    if (!validateForm()) {
      setError('Please fix the validation errors below');
      return;
    }
    
    setLoading(true);
    
    try {
      // Centralized API call
      const newServer = await serverService.createServer(formData);
      
      // Success - redirect to server owner dashboard
      navigate('/server-owner-dashboard', {
        state: { 
          message: `Server "${newServer.name}" created successfully!`,
          newServerId: newServer.id
        }
      });
    } catch (err) {
      console.error('Error creating server:', err);
      
      // Handle specific error responses
      if (err.response?.data) {
        const errorData = err.response.data;
        
        // Check for field-specific errors
        if (errorData.name) {
          setValidationErrors(prev => ({ ...prev, name: errorData.name[0] }));
        }
        if (errorData.invite_link) {
          setValidationErrors(prev => ({ ...prev, invite_link: errorData.invite_link[0] }));
        }
        
        // General error message
        if (errorData.non_field_errors) {
          setError(errorData.non_field_errors[0]);
        } else if (errorData.detail) {
          setError(errorData.detail);
        } else if (errorData.error) {
          setError(errorData.error);
        } else {
          setError('Failed to create server. Please check your input and try again.');
        }
      } else {
        setError('Network error. Please check your connection and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-server-page">
      <div className="create-server-container">
        {/* Header Section */}
        <div className="create-server-header">
          <div className="icon-wrapper"></div>
          <h1 className="page-title">Create Your Server</h1>
          <p className="page-subtitle">
            Build your trading community and start tracking payouts
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="alert alert-error">
            <span className="alert-icon"></span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="create-server-form">
          {/* Server Name */}
          <div className="form-group">
            <label htmlFor="name" className="form-label">
              Server Name <span className="required">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              disabled={loading}
              className={`form-input ${validationErrors.name ? 'error' : ''}`}
              placeholder="e.g., Elite Trading Community"
              maxLength="200"
            />
            {validationErrors.name && (
              <span className="error-message">{validationErrors.name}</span>
            )}
            <span className="input-hint">
              {formData.name.length}/200 characters
            </span>
          </div>

          {/* Description */}
          <div className="form-group">
            <label htmlFor="description" className="form-label">
              Description <span className="required">*</span>
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={loading}
              className={`form-textarea ${validationErrors.description ? 'error' : ''}`}
              placeholder="Describe your trading community, strategy focus, member benefits, etc."
              rows="5"
              maxLength="1000"
            />
            {validationErrors.description && (
              <span className="error-message">{validationErrors.description}</span>
            )}
            <span className="input-hint">
              {formData.description.length}/1000 characters
            </span>
          </div>

          {/* Platform Selection */}
          <div className="form-group">
            <label htmlFor="platform" className="form-label">
              Platform <span className="required">*</span>
            </label>
            <div className="platform-grid">
              {platformOptions.map(option => (
                <label
                  key={option.value}
                  className={`platform-option ${formData.platform === option.value ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="platform"
                    value={option.value}
                    checked={formData.platform === option.value}
                    onChange={handleChange}
                    disabled={loading}
                  />
                  <span className="Cr-Sr-platform-name">{option.label}</span>
                </label>
              ))}
            </div>
            {validationErrors.platform && (
              <span className="error-message">{validationErrors.platform}</span>
            )}
          </div>

          {/* Invite Link */}
          <div className="form-group">
            <label htmlFor="invite_link" className="form-label">
              Invite Link <span className="optional">(Optional)</span>
            </label>
            <input
              type="url"
              id="invite_link"
              name="invite_link"
              value={formData.invite_link}
              onChange={handleChange}
              disabled={loading}
              className={`form-input ${validationErrors.invite_link ? 'error' : ''}`}
              placeholder="https://discord.gg/your-invite-code"
            />
            {validationErrors.invite_link && (
              <span className="error-message">{validationErrors.invite_link}</span>
            )}
            <span className="input-hint">
              Provide a permanent invite link to your {formData.platform} server
            </span>
          </div>

          {/* Info Box */}
          <div className="info-box">
            <div className="info-icon"></div>
            <div className="info-content">
              <strong>After Creating Your Server:</strong>
              <ul>
                <li>Your server will appear in the public directory</li>
                <li>Members can join and submit payout proofs</li>
                <li>Access analytics and manage your community</li>
                <li>Upgrade to Elite for custom branding and URLs</li>
              </ul>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="form-actions">
            <button
              type="button"
              onClick={() => navigate(-1)}
              disabled={loading}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Creating Server...
                </>
              ) : (
                <>
                  <span></span>
                  Create Server
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateServer;
