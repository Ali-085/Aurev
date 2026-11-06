import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { serverService, payoutService, marketService } from '../services';
import api from '../config/api';
import './PayoutSubmission.css';

const PayoutSubmission = () => {
  console.log('PayoutSubmission component rendering...');
  const location = useLocation();
  const preselectedServer = location.state?.preselectedServer;
  console.log('Location state:', location.state);

  const [formData, setFormData] = useState({
    amount: '',
    currency: 'USD',
    market_category: '',
    instrument: '',
    payout_date: '',
    server: preselectedServer || '',
    prop_firm: '',
    screenshot: null,
    private_verification_image: null,
    discord_contact_info: ''
  });

  const [servers, setServers] = useState([]);
  const [marketCategories, setMarketCategories] = useState([]);
  const [propFirms, setPropFirms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [screenshotPreview, setScreenshotPreview] = useState(null);
  const [privateImagePreview, setPrivateImagePreview] = useState(null);

  useEffect(() => {
    fetchUserServers();
    loadMarketCategories();
    fetchPropFirms();
  }, []);

  useEffect(() => {
    // Update server if preselected
    if (preselectedServer && servers.length > 0) {
      setFormData(prev => ({ ...prev, server: preselectedServer }));
    }
  }, [preselectedServer, servers]);

  const fetchUserServers = async () => {
    try {
      const data = await serverService.getMyServers();
      const serverList = Array.isArray(data) ? data : (data.results || []);
      setServers(serverList);
    } catch (error) {
      if (error.response?.status === 403 && error.response?.data?.error_code === 'EMAIL_NOT_VERIFIED') {
        setSubmitError('Please verify your email address to submit payouts.');
      }
    }
  };

  const loadMarketCategories = async () => {
    try {
      console.log('Loading market categories...');
      const markets = await marketService.getMarketCategories();
      console.log('Markets loaded:', markets);
      setMarketCategories(markets);
    } catch (error) {
      console.error('Error loading market categories:', error);
      setMarketCategories([]);
    }
  };

  const fetchPropFirms = async () => {
    try {
      console.log('Fetching prop firms...');
      const response = await api.get('/payouts/prop-firms/');
      const data = response.data;
      // Handle both array response and paginated response
      const firms = Array.isArray(data) ? data : (data.results || []);
      console.log('Prop firms fetched:', firms);
      setPropFirms(firms);
    } catch (error) {
      console.error('Error fetching prop firms:', error);
      setPropFirms([]);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({
        ...formData,
        screenshot: file
      });

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setScreenshotPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handlePrivateImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData({
        ...formData,
        private_verification_image: file
      });

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPrivateImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSubmitError('');
    setSubmitSuccess(false);

    try {
      // Create FormData for file upload
      const formDataToSend = new FormData();
      formDataToSend.append('amount', formData.amount);
      formDataToSend.append('currency', formData.currency);
      formDataToSend.append('market_category', formData.market_category);
      formDataToSend.append('instrument', formData.instrument);
      formDataToSend.append('payout_date', formData.payout_date);
      formDataToSend.append('server_id', formData.server);
      formDataToSend.append('prop_firm_id', formData.prop_firm);
      formDataToSend.append('discord_contact_info', formData.discord_contact_info);
      if (formData.screenshot) {
        formDataToSend.append('screenshot', formData.screenshot);
      }
      if (formData.private_verification_image) {
        formDataToSend.append('private_verification_image', formData.private_verification_image);
      } else {
        setSubmitError('Private verification image is required');
        setLoading(false);
        return;
      }

      await payoutService.submitPayout(formDataToSend);

      setSubmitSuccess(true);

      // Reset form
      setFormData({
        amount: '',
        currency: 'USD',
        market_category: '',
        instrument: '',
        payout_date: '',
        server: '',
        prop_firm: '',
        screenshot: null,
        private_verification_image: null,
        discord_contact_info: ''
      });
      setScreenshotPreview(null);
      setPrivateImagePreview(null);

      // Clear file inputs
      document.getElementById('screenshot-input').value = '';
      const privateInput = document.getElementById('private-verification-input');
      if (privateInput) {
        privateInput.value = '';
      }

    } catch (error) {
      console.error('Error submitting payout:', error);
      setSubmitError(
        error.response?.data?.message ||
        error.response?.data?.error ||
        'Failed to submit payout. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  console.log('About to render, state:', {
    servers: servers.length,
    marketCategories: marketCategories.length,
    propFirms: propFirms.length,
    loading,
    submitSuccess,
    submitError
  });

  return (
    <div className="payout-submission-container">
      <div className="payout-submission-card">
        <h1>Submit Payout</h1>
        <p className="subtitle">
          Submit your verified payout with proof. Moderators will review and approve your submission.
        </p>

        {submitSuccess && (
          <div className="alert alert-success">
            Payout submitted successfully! It will be reviewed by moderators.
          </div>
        )}

        {submitError && (
          <div className="alert alert-error">
            ✗ {submitError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="payout-form">
          {/* Server Selection */}
          <div className="form-group">
            <label htmlFor="server">Server *</label>
            <select
              id="server"
              name="server"
              value={formData.server}
              onChange={handleInputChange}
              required
              className="form-control"
            >
              <option value="">Select a server...</option>
              {servers.map(server => (
                <option key={server.id} value={server.id}>
                  {server.name}
                </option>
              ))}
            </select>
            <small className="form-text">Select which trading community this payout is for</small>
          </div>

          {/* Prop Firm Selection */}
          <div className="form-group">
            <label htmlFor="prop_firm">Prop Firm *</label>
            <select
              id="prop_firm"
              name="prop_firm"
              value={formData.prop_firm}
              onChange={handleInputChange}
              required
              className="form-control"
            >
              <option value="">Select prop firm...</option>
              {propFirms.map(firm => (
                <option key={firm.id} value={firm.id}>
                  {firm.name}
                </option>
              ))}
            </select>
            <small className="form-text">Which prop firm issued this payout?</small>
          </div>

          {/* Amount */}
          <div className="form-group">
            <label htmlFor="amount">Payout Amount (USD) *</label>
            <div className="input-with-prefix">
              <span className="prefix">$</span>
              <input
                type="number"
                id="amount"
                name="amount"
                value={formData.amount}
                onChange={handleInputChange}
                step="0.01"
                min="0.01"
                required
                className="form-control"
                placeholder="1250.00"
              />
            </div>
            <small className="form-text">Enter the exact payout amount in USD</small>
          </div>

          {/* Market Category */}
          <div className="form-group">
            <label htmlFor="market_category">Market Category *</label>
            <select
              id="market_category"
              name="market_category"
              value={formData.market_category}
              onChange={handleInputChange}
              required
              className="form-control"
            >
              <option value="">Select market type...</option>
              {marketCategories.filter(m => m.is_active).map(market => (
                <option key={market.id || market.name} value={market.name}>
                  {market.icon ? `${market.icon} ` : ''}{market.name}
                </option>
              ))}
            </select>
            <small className="form-text">What type of trading generated this payout?</small>
          </div>

          {/* Instrument */}
          <div className="form-group">
            <label htmlFor="instrument">Instrument *</label>
            <input
              type="text"
              id="instrument"
              name="instrument"
              value={formData.instrument}
              onChange={handleInputChange}
              required
              className="form-control"
              placeholder="e.g., ES, EURUSD, BTCUSDT, SPX, AAPL"
              maxLength="100"
            />
            <small className="form-text">
              Specific instrument traded (e.g., ES, NQ, EURUSD, BTCUSDT, SPX, AAPL)
            </small>
          </div>

          {/* Payout Date */}
          <div className="form-group">
            <label htmlFor="payout_date">Payout Date *</label>
            <input
              type="date"
              id="payout_date"
              name="payout_date"
              value={formData.payout_date}
              onChange={handleInputChange}
              required
              className="form-control"
              max={new Date().toISOString().split('T')[0]}
            />
            <small className="form-text">When did you receive this payout?</small>
          </div>

          {/* Discord Contact Info */}
          <div className="form-group">
            <label htmlFor="discord_contact_info">Discord Username/Contact Info *</label>
            <input
              type="text"
              id="discord_contact_info"
              name="discord_contact_info"
              value={formData.discord_contact_info}
              onChange={handleInputChange}
              required
              className="form-control"
              placeholder="e.g., username#1234 or your contact info"
              maxLength="100"
            />
            <small className="form-text">
              Your Discord username or contact information. This will only be visible to platform staff if they need to contact you.
            </small>
          </div>

          {/* Screenshot Upload */}
          <div className="form-group">
            <label htmlFor="screenshot">Proof Screenshot *</label>
            <input
              type="file"
              id="screenshot-input"
              name="screenshot"
              onChange={handleFileChange}
              accept="image/*"
              required
              className="form-control"
            />
            <small className="form-text">
              Upload proof of payout (screenshot of email, payout confirmation page, etc.)
              Disclaimer: This image will be publicly visible so make sure to blur any sensitive information.
            </small>

            {/* Screenshot Requirements */}
            <div className="screenshot-requirements">
              <p className="requirements-title">The screenshot must show:</p>
              <ul className="requirements-list">
                <li>✔ Payout Amount</li>
                <li>✔ Prop Firm Name</li>
                <li>✔ Date</li>
                <li>✔ Status (Approved / Completed / Paid Out)</li>
                <li>✔ Payout ID </li>
                <li>✔ Trader's Name </li>
                <li>Note:Only payouts from the current month will be accepted </li>
              </ul>
              <p className="requirements-subtitle">Blurred areas allowed:</p>
              <ul className="allowed-blur-list">
                <li>• Email / name</li>
                <li>• Dashboard balances</li>
                <li>• Internal messages</li>
              </ul>
            </div>

            {screenshotPreview && (
              <div className="screenshot-preview">
                <img src={screenshotPreview} alt="Screenshot preview" />
              </div>
            )}
          </div>

          {/* Private Verification Image Upload (Required) */}
          <div className="form-group">
            <label htmlFor="private-verification-input">
              Bank Invoice / Transaction Screenshot / Payment Receipt
            </label>
            <input
              type="file"
              id="private-verification-input"
              name="private_verification_image"
              onChange={handlePrivateImageChange}
              accept="image/*"
              className="form-control"
              required
            />
            <small className="form-text">
              🔒 <strong>Private & Secure:</strong> This image is required for verification purposes.
              Only platform staff (admins/moderators) can access it. Never publicly visible.
            </small>

            <div className="verification-image-info">
              <p className="info-title">Use this for additional verification (optional):</p>
              <ul className="info-list">
                <li>✔ Bank transaction screenshot</li>
                <li>✔ Wise payment receipt</li>
                <li>✔ Paypal</li>
                <li>✔ Crypto Transaction (TX Hash screenshot)</li>
                <li>Must Show: </li>
                <ul>
                  <li>✔ Payout Amount</li>
                  <li>✔ Payout Date</li>
                  <li>✔ Partial Name or Wallet Id</li>
                  <li>✔ Payout Currency</li>
                </ul>
              </ul>
            </div>

            {privateImagePreview && (
              <div className="screenshot-preview">
                <img src={privateImagePreview} alt="Private verification preview" />
                <small className="privacy-reminder">
                  🔒 This image will only be visible to platform staff
                </small>
              </div>
            )}
          </div>

          {/* Submission Info */}
          <div className="info-box">
            <strong>What happens next?</strong>
            <ul>
              <li>Your submission will be reviewed by server moderators/admins</li>
              <li>Verification typically takes 24-48 hours</li>
              <li>Once approved, your stats will be automatically updated</li>
              <li>You'll receive a notification about the review decision</li>
              <li>For considerable larger payouts submissions contact Aurevia support team</li>
              <li>
                <a href="https://discord.gg/ma98Km2dxX/">Aurevia</a>
              </li>
            </ul>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-submit"
          >
            {loading ? 'Submitting...' : 'Submit Payout'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default PayoutSubmission;
