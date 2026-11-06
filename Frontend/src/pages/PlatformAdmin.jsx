/**
 * Platform Admin Dashboard
 * 
 * Complete system control for platform owners (superusers):
 * - System overview with key metrics
 * - User management (search, deactivate, change roles)
 * - Server management (suspend, verify, manage subscriptions)
 * - Payout management (quick approve/reject)
 * - Global configuration (markets, categories, limits)
 * - Audit logs (all platform actions)
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { canManagePlatform } from '../utils/permissions';
import api from '../config/api';
import { handlePaginatedResponse, buildPaginationParams } from '../utils/pagination';
import PaginationControls from '../components/PaginationControls';
import RoleSubscriptionModal from '../components/RoleSubscriptionModal';
import PayoutReviewModal from '../components/PayoutReviewModal';
import { payoutService } from '../services';
import './PlatformAdmin.css';

const PlatformAdmin = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // State
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Overview data
  const [stats, setStats] = useState(null);

  // User management
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [userFilter, setUserFilter] = useState('all');

  // Server management
  const [servers, setServers] = useState([]);
  const [serverSearch, setServerSearch] = useState('');
  const [serverFilter, setServerFilter] = useState('all');
  const [serversPagination, setServersPagination] = useState(null);
  const [serversPage, setServersPage] = useState(1);

  // Payout management
  const [payouts, setPayouts] = useState([]);
  const [payoutFilter, setPayoutFilter] = useState('Pending');
  const [payoutsPagination, setPayoutsPagination] = useState(null);
  const [payoutsPage, setPayoutsPage] = useState(1);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState(null);

  // Global config
  const [markets, setMarkets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [limits, setLimits] = useState(null);
  const [platforms, setPlatforms] = useState([]);
  const [propFirms, setPropFirms] = useState([]);

  // Config UI state
  const [showAddMarket, setShowAddMarket] = useState(false);
  const [showAddCategory, setShowAddCategory] = useState(false);
  const [showEditLimits, setShowEditLimits] = useState(false);
  const [showAddPlatform, setShowAddPlatform] = useState(false);
  const [showAddPropFirm, setShowAddPropFirm] = useState(false);
  const [editingMarket, setEditingMarket] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingPlatform, setEditingPlatform] = useState(null);
  const [editingPropFirm, setEditingPropFirm] = useState(null);

  // Audit logs
  const [auditLogs, setAuditLogs] = useState([]);

  // Subscription Plans Management
  const [subscriptionPlans, setSubscriptionPlans] = useState([]);
  const [showAddPlan, setShowAddPlan] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [planFormData, setPlanFormData] = useState({
    name: '',
    tier: '',
    description: '',
    price_per_month: '',
    stripe_price_id: '',
    stripe_product_id: '',
    features: [],
    is_active: true,
    sort_order: 0
  });

  // Role/Subscription Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [loadingSubscription, setLoadingSubscription] = useState(false);

  // SECURITY: Check if user has platform management capability
  useEffect(() => {
    if (!canManagePlatform(user)) {
      navigate('/unauthorized');
    } else {
      loadOverviewData();
    }
  }, [user, navigate]);

  // Load data based on active tab
  useEffect(() => {
    if (!canManagePlatform(user)) return;

    switch (activeTab) {
      case 'overview':
        loadOverviewData();
        break;
      case 'users':
        loadUsers();
        break;
      case 'servers':
        loadServers();
        break;
      case 'payouts':
        loadPayouts();
        break;
      case 'config':
        loadConfig();
        break;
      case 'audit':
        loadAuditLogs();
        break;
      case 'subscriptions':
        loadSubscriptionPlans();
        break;
      default:
        break;
    }
  }, [activeTab, user]);

  // Reload servers when pagination or filters change
  useEffect(() => {
    if (activeTab === 'servers' && canManagePlatform(user)) {
      loadServers();
    }
  }, [serversPage, serverSearch, serverFilter]);

  // Reload payouts when pagination or filters change
  useEffect(() => {
    if (activeTab === 'payouts' && canManagePlatform(user)) {
      loadPayouts();
    }
  }, [payoutsPage, payoutFilter]);

  // === DATA LOADING FUNCTIONS ===

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/platform-admin/overview/');
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load overview data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (userSearch) params.append('search', userSearch);
      if (userFilter) params.append('status', userFilter);

      const response = await api.get(`/platform-admin/users/?${params}`);
      setUsers(response.data.users || []);
      setError(null);
    } catch (err) {
      setError('Failed to load users');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadServers = async () => {
    try {
      setLoading(true);
      const params = buildPaginationParams(serversPage, 20, {
        ...(serverSearch && { search: serverSearch }),
        ...(serverFilter !== 'all' && { filter: serverFilter })
      });

      const response = await api.get('/platform-admin/servers/', { params });
      const { data, pagination } = handlePaginatedResponse(response);

      setServers(data || []);
      setServersPagination(pagination);
      setError(null);
    } catch (err) {
      setError('Failed to load servers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadPayouts = async () => {
    try {
      setLoading(true);
      const params = buildPaginationParams(payoutsPage, 20, {
        ...(payoutFilter && { status: payoutFilter })
      });

      const response = await api.get('/platform-admin/payouts/', { params });
      const { data, pagination } = handlePaginatedResponse(response);

      setPayouts(data || []);
      setPayoutsPagination(pagination);
      setError(null);
    } catch (err) {
      setError('Failed to load payouts');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      setLoading(true);
      const [marketsRes, categoriesRes, limitsRes, platformsRes, propFirmsRes] = await Promise.all([
        api.get('/platform-admin/markets/'),
        api.get('/platform-admin/categories/'),
        api.get('/platform-admin/limits/'),
        api.get('/platform-admin/platforms/'),
        api.get('/platform-admin/prop-firms/')
      ]);

      setMarkets(marketsRes.data.markets || []);
      setCategories(categoriesRes.data.categories || []);
      setLimits(limitsRes.data);
      setPlatforms(platformsRes.data || []);
      setPropFirms(propFirmsRes.data || []);
      setError(null);
    } catch (err) {
      setError('Failed to load configuration');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const response = await api.get('/platform-admin/audit-logs/');
      setAuditLogs(response.data.logs || []);
      setError(null);
    } catch (err) {
      setError('Failed to load audit logs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadSubscriptionPlans = async () => {
    try {
      setLoading(true);
      const response = await api.get('/platform-admin/subscription-plans/');
      setSubscriptionPlans(response.data.plans || []);
      setError(null);
    } catch (err) {
      setError('Failed to load subscription plans');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // === ACTION HANDLERS ===

  const handlePayoutAction = async (payoutId, action, providedReason = null) => {
    if (!confirm(`Are you sure you want to ${action} this payout?`)) return;

    try {
      const reason = providedReason || (action === 'reject' ? prompt('Reason for rejection:') : '');
      await api.post(`/platform-admin/payouts/${payoutId}/action/`, {
        action,
        reason
      });

      alert(`Payout ${action}d successfully!`);
      loadPayouts();
    } catch (err) {
      alert(`Failed to ${action} payout: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeletePayout = async (payoutId) => {
    if (!confirm('Are you sure you want to PERMANENTLY delete this payout submission? This cannot be undone.')) return;

    try {
      await api.delete(`/payouts/submissions/${payoutId}/`);
      alert('Payout deleted successfully!');
      loadPayouts();
      loadPayouts();
    } catch (err) {
      alert(`Failed to delete payout: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleReviewPayout = async (payoutId) => {
    try {
      setLoading(true);
      const data = await payoutService.getSubmission(payoutId);
      setSelectedSubmission(data);
      setReviewModalOpen(true);
    } catch (err) {
      alert('Failed to load submission details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReviewComplete = () => {
    setReviewModalOpen(false);
    setSelectedSubmission(null);
    loadPayouts();
  };


  const handleSuspendServer = async (serverId, suspend) => {
    if (!confirm(`Are you sure you want to ${suspend ? 'suspend' : 'unsuspend'} this server?`)) return;

    try {
      await api.put(`/platform-admin/servers/${serverId}/`, {
        action: suspend ? 'suspend' : 'unsuspend'
      });

      alert(`Server ${suspend ? 'suspended' : 'unsuspended'} successfully!`);
      loadServers();
    } catch (err) {
      alert(`Failed to update server: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleVerifyServer = async (serverId) => {
    if (!confirm('Verify this server?')) return;

    try {
      await api.put(`/platform-admin/servers/${serverId}/`, {
        action: 'verify'
      });

      alert('Server verified successfully!');
      loadServers();
    } catch (err) {
      alert(`Failed to verify server: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeactivateUser = async (userId) => {
    if (!confirm('Are you sure you want to deactivate this user?')) return;

    try {
      await api.put(`/platform-admin/users/${userId}/`, {
        action: 'deactivate'
      });

      alert('User deactivated successfully!');
      loadUsers();
    } catch (err) {
      alert(`Failed to deactivate user: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleActivateUser = async (userId) => {
    if (!confirm('Are you sure you want to activate this user?')) return;

    try {
      await api.put(`/platform-admin/users/${userId}/`, {
        action: 'activate'
      });

      alert('User activated successfully!');
      loadUsers();
    } catch (err) {
      alert(`Failed to activate user: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleChangeUserRole = async (userId) => {
    // Find the user in the list
    const userToEdit = users.find(u => u.id === userId);
    if (!userToEdit) {
      alert('User not found');
      return;
    }

    setSelectedUser(userToEdit);
    setLoadingSubscription(true);
    setIsModalOpen(true);

    try {
      // Fetch current subscription status
      const response = await api.get(`/platform-admin/users/${userId}/subscription-status/`);
      setCurrentSubscription(response.data);
    } catch (err) {
      console.error('Failed to fetch subscription status:', err);
      setCurrentSubscription(null);
    } finally {
      setLoadingSubscription(false);
    }
  };

  const handleModalSubmit = async (roleData) => {
    try {
      await api.put(`/platform-admin/users/${selectedUser.id}/`, {
        action: 'change_role',
        ...roleData
      });

      // Show success message with logout instruction
      const successMsg = roleData.subscription
        ? `User role changed to ${roleData.role} with ${roleData.subscription.tier} subscription!\n\nIMPORTANT: User must LOG OUT and LOG BACK IN for the role change to take effect.`
        : `User role changed to ${roleData.role} successfully!\n\nIMPORTANT: User must LOG OUT and LOG BACK IN for the role change to take effect.`;

      alert(successMsg);

      // Reload users list
      loadUsers();

      // Close modal
      setIsModalOpen(false);
      setSelectedUser(null);
      setCurrentSubscription(null);
    } catch (err) {
      // Error will be handled by the modal's error state
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message;
      throw new Error(errorMsg);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedUser(null);
    setCurrentSubscription(null);
  };

  // === SUBSCRIPTION PLAN HANDLERS ===

  const handleAddPlan = async (e) => {
    e.preventDefault();

    // Validate features array
    const featuresInput = planFormData.features;
    const featuresArray = Array.isArray(featuresInput)
      ? featuresInput
      : (typeof featuresInput === 'string' && featuresInput.trim())
        ? featuresInput.split('\n').map(f => f.trim()).filter(f => f)
        : [];

    const planData = {
      ...planFormData,
      features: featuresArray,
      price_per_month: parseFloat(planFormData.price_per_month),
      sort_order: parseInt(planFormData.sort_order) || 0
    };

    try {
      await api.post('/platform-admin/subscription-plans/', planData);
      alert('Subscription plan created successfully!');
      setShowAddPlan(false);
      setPlanFormData({
        name: '',
        tier: '',
        description: '',
        price_per_month: '',
        stripe_price_id: '',
        stripe_product_id: '',
        features: [],
        is_active: true,
        sort_order: 0
      });
      loadSubscriptionPlans();
    } catch (err) {
      alert(`Failed to create plan: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdatePlan = async (e) => {
    e.preventDefault();
    if (!editingPlan) return;

    // Validate features array
    const featuresInput = planFormData.features;
    const featuresArray = Array.isArray(featuresInput)
      ? featuresInput
      : (typeof featuresInput === 'string' && featuresInput.trim())
        ? featuresInput.split('\n').map(f => f.trim()).filter(f => f)
        : [];

    const planData = {
      ...planFormData,
      features: featuresArray,
      price_per_month: parseFloat(planFormData.price_per_month),
      sort_order: parseInt(planFormData.sort_order) || 0
    };

    try {
      await api.patch(`/platform-admin/subscription-plans/${editingPlan.id}/`, planData);
      alert('Subscription plan updated successfully!');
      setEditingPlan(null);
      setPlanFormData({
        name: '',
        tier: '',
        description: '',
        price_per_month: '',
        stripe_price_id: '',
        stripe_product_id: '',
        features: [],
        is_active: true,
        sort_order: 0
      });
      loadSubscriptionPlans();
    } catch (err) {
      alert(`Failed to update plan: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeletePlan = async (planId, planName) => {
    if (!confirm(`Are you sure you want to delete the "${planName}" plan? This cannot be undone.`)) return;

    try {
      await api.delete(`/platform-admin/subscription-plans/${planId}/`);
      alert('Plan deleted successfully!');
      loadSubscriptionPlans();
    } catch (err) {
      alert(`Failed to delete plan: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleTogglePlanActive = async (planId, currentStatus) => {
    const action = currentStatus ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} this plan?`)) return;

    try {
      await api.patch(`/platform-admin/subscription-plans/${planId}/`, {
        is_active: !currentStatus
      });
      alert(`Plan ${action}d successfully!`);
      loadSubscriptionPlans();
    } catch (err) {
      alert(`Failed to ${action} plan: ${err.response?.data?.error || err.message}`);
    }
  };

  const startEditPlan = (plan) => {
    setEditingPlan(plan);
    setPlanFormData({
      name: plan.name,
      tier: plan.tier,
      description: plan.description,
      price_per_month: plan.price_per_month,
      stripe_price_id: plan.stripe_price_id || '',
      stripe_product_id: plan.stripe_product_id || '',
      features: plan.features,
      is_active: plan.is_active,
      sort_order: plan.sort_order
    });
  };

  const cancelPlanEdit = () => {
    setEditingPlan(null);
    setShowAddPlan(false);
    setPlanFormData({
      name: '',
      tier: '',
      description: '',
      price_per_month: '',
      stripe_price_id: '',
      stripe_product_id: '',
      features: [],
      is_active: true,
      sort_order: 0
    });
  };

  // === RENDER FUNCTIONS ===

  const renderOverview = () => (
    <>
      <h2 className="section-title">Platform Overview</h2>

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <p>{stats.users?.total || 0}</p>
              <h3>Total Users</h3>
              <small>{stats.users?.active_this_week || 0} active this week</small>
            </div>
            <div className="stat-card">
              <p>{stats.servers?.total || 0}</p>
              <h3>Total Servers</h3>
              <small>{stats.servers?.active_this_week || 0} active / {stats.servers?.suspended || 0} suspended</small>
            </div>
            <div className="stat-card">
              <p>{stats.payouts?.total_count || 0}</p>
              <h3>Total Payouts</h3>
              <small>{stats.payouts?.pending_queue || 0} pending</small>
            </div>
            <div className="stat-card">
              <p>${(stats.payouts?.total_volume || 0).toLocaleString()}</p>
              <h3>Total Volume</h3>
              <small>All approved payouts</small>
            </div>
          </div>

          {stats.payouts?.high_value_recent?.length > 0 && (
            <div className="platform-section">
              <h3>Recent High Value Payouts (&gt;$5,000)</h3>
              <div className="platform-table-container">
                <table className="platform-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Server</th>
                      <th>Amount</th>
                      <th>Market</th>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.payouts.high_value_recent.map(p => (
                      <tr key={p.id}>
                        <td>{p.user}</td>
                        <td>{p.server}</td>
                        <td><strong>${p.amount.toLocaleString()}</strong></td>
                        <td>{p.market}</td>
                        <td>{new Date(p.date).toLocaleDateString()}</td>
                        <td>
                          <span className={`platform-badge ${p.status === 'Approved' ? 'success' : 'warning'}`}>
                            {p.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="platform-section">
            <h3>System Status</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <h3>Maintenance Mode</h3>
                <p style={{ color: stats.system_status?.maintenance_mode ? '#dc3545' : '#28a745' }}>
                  {stats.system_status?.maintenance_mode ? 'ON' : 'OFF'}
                </p>
              </div>
              <div className="stat-card">
                <h3>AI Fraud Detection</h3>
                <p style={{ color: stats.system_status?.ai_fraud_detection ? '#28a745' : '#6c757d' }}>
                  {stats.system_status?.ai_fraud_detection ? 'ENABLED' : 'DISABLED'}
                </p>
              </div>
              <div className="stat-card">
                <h3>Payout Queue</h3>
                <p>{stats.system_status?.payout_queue_size || 0}</p>
              </div>
              <div className="stat-card">
                <h3>Data Retention</h3>
                <p>{stats.system_status?.data_retention_days || 'Unlimited'} days</p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );

  const renderUsers = () => (
    <>
      <h2 className="section-title">User Management</h2>

      <div className="platform-filters">
        <input
          type="text"
          placeholder="Search by username or email..."
          value={userSearch}
          onChange={(e) => setUserSearch(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && loadUsers()}
        />
        <select
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
        >
          <option value="">All Status</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>
        <select
          onChange={(e) => {
            const params = new URLSearchParams();
            if (userSearch) params.append('search', userSearch);
            if (userFilter) params.append('status', userFilter);
            if (e.target.value) params.append('role', e.target.value);
            api.get(`/platform-admin/users/?${params}`).then(res => setUsers(res.data.users || []));
          }}
        >
          <option value="">All Roles</option>
          <option value="Owner">Server Owners</option>
          <option value="Admin">Admins</option>
          <option value="Moderator">Moderators</option>
          <option value="NormalUser">Normal Users</option>
        </select>
        <button onClick={loadUsers}>Search</button>
      </div>

      <div className="platform-table-container">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role(s)</th>
              <th>Server(s)</th>
              <th>Last Login</th>
              <th>Total Payouts</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td><strong>{u.username}</strong></td>
                <td>{u.email}</td>
                <td>
                  {u.roles && u.roles.length > 0 ? (
                    u.roles.map((role, idx) => (
                      <span key={idx} className="platform-badge primary">
                        {role}
                      </span>
                    ))
                  ) : (
                    <span className="platform-badge secondary">None</span>
                  )}
                </td>
                <td>
                  <span className="server-count">
                    Owned: <strong>{u.servers?.owned || 0}</strong> | Member: <strong>{u.servers?.member_of || 0}</strong>
                  </span>
                </td>
                <td>{u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</td>
                <td>
                  <div>
                    <strong>{u.total_payouts?.count || 0}</strong> payouts
                    <br />
                    <small>${(u.total_payouts?.total || 0).toLocaleString()}</small>
                  </div>
                </td>
                <td>
                  <span className={`status-badge ${u.is_active ? 'active' : 'suspended'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="min-width">
                  <div className="plt-action-buttons">
                    {u.is_active ? (
                      <button
                        onClick={() => handleDeactivateUser(u.id)}
                        className="plt-action-button danger"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivateUser(u.id)}
                        className="plt-action-button success"
                      >
                        Activate
                      </button>
                    )}
                    <button
                      onClick={() => handleChangeUserRole(u.id)}
                      className="plt-action-button primary"
                    >
                      Change Role
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );

  const renderServers = () => (
    <>
      <h2 className="section-title">Server Management</h2>

      <div className="platform-filters">
        <input
          type="text"
          placeholder="Search by server name or owner..."
          value={serverSearch}
          onChange={(e) => setServerSearch(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && loadServers()}
        />
        <select
          value={serverFilter}
          onChange={(e) => setServerFilter(e.target.value)}
        >
          <option value="">All Servers</option>
          <option value="verified">Verified Only</option>
          <option value="unverified">Unverified Only</option>
          <option value="suspended">Suspended Only</option>
        </select>
        <button onClick={loadServers}>Search</button>
      </div>

      <div className="platform-table-container">
        <table className="platform-table">
          <thead>
            <tr>
              <th>Server Name</th>
              <th>Owner</th>
              <th>Platform</th>
              <th>Status</th>
              <th>Members</th>
              <th>Payouts</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {servers.map(s => (
              <tr key={s.id}>
                <td><strong>{s.name}</strong></td>
                <td>{s.owner_username}</td>
                <td>{s.platform}</td>
                <td>
                  {s.is_verified && <span className="platform-badge success">Verified</span>}
                  {s.suspended && <span className="platform-badge danger">Suspended</span>}
                  {!s.is_verified && !s.suspended && <span className="platform-badge warning">Pending</span>}
                </td>
                <td>{s.member_count || 0}</td>
                <td>{s.payout_count || 0}</td>
                <td>
                  <div className="plt-action-buttons">
                    {!s.is_verified && (
                      <button
                        onClick={() => handleVerifyServer(s.id)}
                        className="plt-action-button success"
                      >
                        Verify
                      </button>
                    )}
                    <button
                      onClick={() => handleSuspendServer(s.id, !s.suspended)}
                      className={`plt-action-button ${s.suspended ? 'warning' : 'danger'}`}
                    >
                      {s.suspended ? 'Unsuspend' : 'Suspend'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <PaginationControls
        pagination={serversPagination}
        currentPage={serversPage}
        onPageChange={setServersPage}
        pageSize={20}
        showPageSize={false}
      />
    </>
  );

  const renderPayouts = () => (
    <>
      <h2 className="section-title">Payout Management</h2>

      <div className="platform-filters">
        <select
          value={payoutFilter}
          onChange={(e) => setPayoutFilter(e.target.value)}
        >
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Rejected">Rejected</option>
          <option value="">All Payouts</option>
        </select>
        <button onClick={loadPayouts}>Refresh</button>
      </div>

      <div className="platform-table-container">
        <table className="platform-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Server</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {payouts.map(p => (
              <tr key={p.id}>
                <td>#{p.id}</td>
                <td>{p.user_username}</td>
                <td>{p.server_name}</td>
                <td><strong>${p.amount}</strong></td>
                <td>
                  <span className={`status-badge ${p.status === 'Approved' ? 'active' :
                    p.status === 'Rejected' ? 'suspended' : 'pending'
                    }`}>
                    {p.status}
                  </span>
                </td>
                <td>{new Date(p.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="plt-action-buttons">
                    <button
                      onClick={() => handleReviewPayout(p.id)}
                      className="plt-action-button primary"
                    >
                      Review
                    </button>
                    {p.status === 'Pending' && (
                      <>
                        <button
                          onClick={() => handlePayoutAction(p.id, 'approve')}
                          className="plt-action-button success"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handlePayoutAction(p.id, 'reject')}
                          className="plt-action-button danger"
                        >
                          Reject
                        </button>
                      </>
                    )}
                    {p.status === 'Approved' && (
                      <button
                        onClick={() => {
                          const reason = prompt('Reason for rejecting this approved payout:');
                          if (reason !== null) {
                            handlePayoutAction(p.id, 'reject', reason);
                          }
                        }}
                        className="action-button danger"
                      >
                        Revert & Reject
                      </button>
                    )}
                    <button
                      onClick={() => handleDeletePayout(p.id)}
                      className="plt-action-button danger"
                      style={{ marginLeft: 'auto' }}
                      title="Permanently Delete"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <PaginationControls
        pagination={payoutsPagination}
        currentPage={payoutsPage}
        onPageChange={setPayoutsPage}
        pageSize={20}
        showPageSize={false}
      />
    </>
  );

  const handleAddMarket = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
      await api.post('/platform-admin/markets/', {
        name: formData.get('name'),
        description: formData.get('description'),
        icon: formData.get('icon'),
        is_active: formData.get('is_active') === 'on'
      });

      alert('Market added successfully!');
      setShowAddMarket(false);
      loadConfig();
    } catch (err) {
      alert(`Failed to add market: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdateMarket = async (marketId, updates) => {
    try {
      await api.put(`/platform-admin/markets/${marketId}/`, updates);
      alert('Market updated successfully!');
      setEditingMarket(null);
      loadConfig();
    } catch (err) {
      alert(`Failed to update market: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeleteMarket = async (marketId) => {
    if (!confirm('Are you sure you want to delete this market?')) return;

    try {
      await api.delete(`/platform-admin/markets/${marketId}/`);
      alert('Market deleted successfully!');
      loadConfig();
    } catch (err) {
      alert(`Failed to delete market: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
      await api.post('/platform-admin/categories/', {
        name: formData.get('name'),
        category_type: formData.get('category_type'),
        description: formData.get('description'),
        is_active: formData.get('is_active') === 'on'
      });

      alert('Category added successfully!');
      setShowAddCategory(false);
      loadConfig();
    } catch (err) {
      alert(`Failed to add category: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdateCategory = async (categoryId, updates) => {
    try {
      await api.put(`/platform-admin/categories/${categoryId}/`, updates);
      alert('Category updated successfully!');
      setEditingCategory(null);
      loadConfig();
    } catch (err) {
      alert(`Failed to update category: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (!confirm('Are you sure you want to delete this category?')) return;

    try {
      await api.delete(`/platform-admin/categories/${categoryId}/`);
      alert('Category deleted successfully!');
      loadConfig();
    } catch (err) {
      alert(`Failed to delete category: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdateLimits = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    const updates = {
      min_payout_count_for_ranking: parseInt(formData.get('min_payout_count_for_ranking')),
      min_total_volume_for_ranking: parseFloat(formData.get('min_total_volume_for_ranking')),
      max_payout_amount: parseFloat(formData.get('max_payout_amount')),
      max_submissions_per_user_per_day: parseInt(formData.get('max_submissions_per_user_per_day')),
      max_screenshot_file_size_mb: parseInt(formData.get('max_screenshot_file_size_mb')),
      allowed_file_formats: formData.get('allowed_file_formats'),
      max_server_members: parseInt(formData.get('max_server_members')),
      max_submissions_per_server_per_day: parseInt(formData.get('max_submissions_per_server_per_day')),
      max_server_members_elite: parseInt(formData.get('max_server_members_elite')),
      max_submissions_per_server_per_day_elite: parseInt(formData.get('max_submissions_per_server_per_day_elite')),
      elite_auto_approve_threshold: parseFloat(formData.get('elite_auto_approve_threshold')),
      data_retention_days: parseInt(formData.get('data_retention_days')),
      analytics_display_days: parseInt(formData.get('analytics_display_days'))
    };

    try {
      await api.put('/platform-admin/limits/', updates);
      alert('Limits updated successfully!');
      setShowEditLimits(false);
      loadConfig();
    } catch (err) {
      alert(`Failed to update limits: ${err.response?.data?.error || err.message}`);
    }
  };

  // === PLATFORM CHOICE HANDLERS ===

  const handleAddPlatform = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
      await api.post('/platform-admin/platforms/', {
        name: formData.get('name'),
        is_active: formData.get('is_active') === 'on',
        display_order: parseInt(formData.get('display_order') || 0)
      });

      alert('Platform added successfully!');
      setShowAddPlatform(false);
      loadConfig();
    } catch (err) {
      alert(`Failed to add platform: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdatePlatform = async (platformId, updates) => {
    try {
      await api.put(`/platform-admin/platforms/${platformId}/`, updates);
      alert('Platform updated successfully!');
      setEditingPlatform(null);
      loadConfig();
    } catch (err) {
      alert(`Failed to update platform: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeletePlatform = async (platformId) => {
    if (!confirm('Are you sure you want to delete this platform?')) return;

    try {
      await api.delete(`/platform-admin/platforms/${platformId}/`);
      alert('Platform deleted successfully!');
      loadConfig();
    } catch (err) {
      alert(`Failed to delete platform: ${err.response?.data?.error || err.message}`);
    }
  };

  // === PROP FIRM HANDLERS ===

  const handleAddPropFirm = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    try {
      await api.post('/platform-admin/prop-firms/', {
        name: formData.get('name'),
        logo_url: formData.get('logo_url') || '',
        website_url: formData.get('website_url') || '',
        is_active: formData.get('is_active') === 'on',
        display_order: parseInt(formData.get('display_order') || 0)
      });

      alert('Prop firm added successfully!');
      setShowAddPropFirm(false);
      loadConfig();
    } catch (err) {
      alert(`Failed to add prop firm: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleUpdatePropFirm = async (firmId, updates) => {
    try {
      await api.put(`/platform-admin/prop-firms/${firmId}/`, updates);
      alert('Prop firm updated successfully!');
      setEditingPropFirm(null);
      loadConfig();
    } catch (err) {
      alert(`Failed to update prop firm: ${err.response?.data?.error || err.message}`);
    }
  };

  const handleDeletePropFirm = async (firmId) => {
    if (!confirm('Are you sure you want to delete this prop firm?')) return;

    try {
      await api.delete(`/platform-admin/prop-firms/${firmId}/`);
      alert('Prop firm deleted successfully!');
      loadConfig();
    } catch (err) {
      alert(`Failed to delete prop firm: ${err.response?.data?.error || err.message}`);
    }
  };

  const renderConfig = () => (
    <>
      <h2 className="section-title">Global Configuration</h2>

      {/* PLATFORM CHOICES SECTION */}
      <div className="platform-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3>Platform Choices ({platforms.length})</h3>
          <button onClick={() => setShowAddPlatform(!showAddPlatform)} className="add-button">
            {showAddPlatform ? 'Cancel' : '+ Add Platform'}
          </button>
        </div>
        <p className="section-description">
          Available platforms for server creation (Discord, Telegram, WhatsApp, etc.). These appear in dropdowns across the platform.
        </p>

        {showAddPlatform && (
          <form onSubmit={handleAddPlatform} className="platform-form">
            <input name="name" placeholder="Platform Name (e.g., Discord)" required className="form-input" />
            <input name="display_order" type="number" placeholder="Display Order (0)" defaultValue="0" className="form-input" />
            <label className="checkbox-label">
              <input type="checkbox" name="is_active" defaultChecked />
              Active
            </label>
            <button type="submit" className="submit-button">Create Platform</button>
          </form>
        )}

        <div className="config-list">
          {platforms.map((p, index) => (
            <div key={p.id} className="config-item-expanded">
              {editingPlatform === p.id ? (
                <div className="edit-form">
                  <input
                    defaultValue={p.name}
                    onBlur={(e) => handleUpdatePlatform(p.id, { name: e.target.value })}
                    className="edit-input"
                  />
                  <button onClick={() => setEditingPlatform(null)} className="done-button">Done</button>
                </div>
              ) : (
                <>
                  <div className="config-item-info">
                    <span className="config-order">#{p.display_order}</span>
                    <span className="config-name">{p.name}</span>
                  </div>
                  <div className="config-actions">
                    <span className={`platform-badge ${p.is_active ? 'success' : 'secondary'}`}>
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => handleUpdatePlatform(p.id, { is_active: !p.is_active })}
                      className="plt-action-button warning"
                    >
                      {p.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => setEditingPlatform(p.id)}
                      className="plt-action-button primary"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeletePlatform(p.id)}
                      className="plt-action-button danger"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* PROP FIRMS SECTION */}
      <div className="platform-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3>Prop Firms ({propFirms.length})</h3>
          <button onClick={() => setShowAddPropFirm(!showAddPropFirm)} className="add-button">
            {showAddPropFirm ? 'Cancel' : '+ Add Prop Firm'}
          </button>
        </div>
        <p className="section-description">
          Proprietary trading firms available for payout submissions (FTMO, TopstepTrader, The5%ers, etc.)
        </p>

        {showAddPropFirm && (
          <form onSubmit={handleAddPropFirm} className="platform-form">
            <input name="name" placeholder="Prop Firm Name (e.g., FTMO)" required className="form-input" />
            <input name="logo_url" placeholder="Logo URL (optional)" className="form-input" />
            <input name="website_url" placeholder="Website URL (optional)" className="form-input" />
            <input name="display_order" type="number" placeholder="Display Order (0)" defaultValue="0" className="form-input" />
            <label className="checkbox-label">
              <input type="checkbox" name="is_active" defaultChecked />
              Active
            </label>
            <button type="submit" className="submit-button">Create Prop Firm</button>
          </form>
        )}

        <div className="config-list">
          {propFirms.map((f, index) => (
            <div key={f.id} className="config-item-expanded">
              {editingPropFirm === f.id ? (
                <div className="edit-form">
                  <input
                    defaultValue={f.name}
                    onBlur={(e) => handleUpdatePropFirm(f.id, { name: e.target.value })}
                    className="edit-input"
                  />
                  <button onClick={() => setEditingPropFirm(null)} className="done-button">Done</button>
                </div>
              ) : (
                <>
                  <div className="config-item-info">
                    <span className="config-order">#{f.display_order}</span>
                    <span className="config-name">{f.name}</span>
                    {f.slug && <span className="config-desc">Slug: {f.slug}</span>}
                  </div>
                  <div className="config-actions">
                    <span className={`platform-badge ${f.is_active ? 'success' : 'secondary'}`}>
                      {f.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => handleUpdatePropFirm(f.id, { is_active: !f.is_active })}
                      className="plt-action-button warning"
                    >
                      {f.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => setEditingPropFirm(f.id)}
                      className="plt-action-button primary"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeletePropFirm(f.id)}
                      className="plt-action-button danger"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* MARKETS SECTION */}
      <div className="platform-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3>Markets ({markets.length})</h3>
          <button onClick={() => setShowAddMarket(!showAddMarket)} className="add-button">
            {showAddMarket ? 'Cancel' : '+ Add Market'}
          </button>
        </div>
        <p className="section-description">
          Trading segments servers can submit payouts under (Futures, Forex, Crypto, Options, etc.)
        </p>

        {showAddMarket && (
          <form onSubmit={handleAddMarket} className="platform-form">
            <input name="name" placeholder="Market Name (e.g., Futures)" required className="form-input" />
            <input name="icon" placeholder="Icon (emoji)" className="form-input" />
            <input name="description" placeholder="Description" className="form-input" />
            <label className="checkbox-label">
              <input type="checkbox" name="is_active" defaultChecked />
              Active
            </label>
            <button type="submit" className="submit-button">Create Market</button>
          </form>
        )}

        <div className="config-list">
          {markets.map((m, index) => (
            <div key={m.id} className="config-item-expanded">
              {editingMarket === m.id ? (
                <div className="edit-form">
                  <input
                    defaultValue={m.name}
                    onBlur={(e) => handleUpdateMarket(m.id, { name: e.target.value })}
                    className="edit-input"
                  />
                  <button onClick={() => setEditingMarket(null)} className="done-button">Done</button>
                </div>
              ) : (
                <>
                  <div className="config-item-info">
                    <span className="config-order">#{index + 1}</span>
                    <span className="config-name">{m.icon} {m.name}</span>
                    {m.description && <span className="config-desc">{m.description}</span>}
                  </div>
                  <div className="config-actions">
                    <span className={`platform-badge ${m.is_active ? 'success' : 'secondary'}`}>
                      {m.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => handleUpdateMarket(m.id, { is_active: !m.is_active })}
                      className="plt-action-button warning"
                    >
                      {m.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => setEditingMarket(m.id)}
                      className="plt-action-button primary"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteMarket(m.id)}
                      className="plt-action-button danger"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* CATEGORIES SECTION */}
      <div className="platform-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3>Categories ({categories.length})</h3>
          <button onClick={() => setShowAddCategory(!showAddCategory)} className="add-button">
            {showAddCategory ? 'Cancel' : '+ Add Category'}
          </button>
        </div>
        <p className="section-description">
          Organize payouts by server type, skill level, region, account size, etc.
        </p>

        {showAddCategory && (
          <form onSubmit={handleAddCategory} className="platform-form">
            <input name="name" placeholder="Category Name" required className="form-input" />
            <select name="category_type" required className="form-select">
              <option value="">Select Type</option>
              <option value="server">Server Category</option>
              <option value="skill">Trader Skill Level</option>
              <option value="payout_type">Payout Type</option>
              <option value="region">Region</option>
              <option value="account_tier">Account Size Tier</option>
              <option value="scaling">Scaling Tier</option>
            </select>
            <input name="description" placeholder="Description" className="form-input" />
            <label className="checkbox-label">
              <input type="checkbox" name="is_active" defaultChecked />
              Active
            </label>
            <button type="submit" className="submit-button">Create Category</button>
          </form>
        )}

        <div className="config-list">
          {categories.map((c, index) => (
            <div key={c.id} className="config-item-expanded">
              {editingCategory === c.id ? (
                <div className="edit-form">
                  <input
                    defaultValue={c.name}
                    onBlur={(e) => handleUpdateCategory(c.id, { name: e.target.value })}
                    className="edit-input"
                  />
                  <button onClick={() => setEditingCategory(null)} className="done-button">Done</button>
                </div>
              ) : (
                <>
                  <div className="config-item-info">
                    <span className="config-order">#{index + 1}</span>
                    <span className="config-name">{c.name}</span>
                    <span className="config-type">{c.category_type}</span>
                  </div>
                  <div className="config-actions">
                    <span className={`platform-badge ${c.is_active ? 'success' : 'secondary'}`}>
                      {c.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => handleUpdateCategory(c.id, { is_active: !c.is_active })}
                      className="plt-action-button warning"
                    >
                      {c.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => setEditingCategory(c.id)}
                      className="plt-action-button primary"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteCategory(c.id)}
                      className="plt-action-button danger"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* LIMITS SECTION */}
      {limits && (
        <div className="platform-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <h3>Platform Limits</h3>
            <button onClick={() => setShowEditLimits(!showEditLimits)} className="add-button">
              {showEditLimits ? 'Cancel' : 'Edit Limits'}
            </button>
          </div>
          <p className="section-description">
            Universal system limits controlling rankings, payouts, servers, and analytics
          </p>

          {showEditLimits ? (
            <form onSubmit={handleUpdateLimits} className="limits-form">
              <div className="limits-section">
                <h4>Ranking Eligibility</h4>
                <label className="form-label">
                  Min Payout Count
                  <input name="min_payout_count_for_ranking" type="number" defaultValue={limits.min_payout_count_for_ranking} className="form-input" />
                </label>
                <label className="form-label">
                  Min Total Volume ($)
                  <input name="min_total_volume_for_ranking" type="number" step="0.01" defaultValue={limits.min_total_volume_for_ranking} className="form-input" />
                </label>
              </div>

              <div className="limits-section">
                <h4>Payout Limits</h4>
                <label className="form-label">
                  Max Payout Amount ($)
                  <input name="max_payout_amount" type="number" step="0.01" defaultValue={limits.max_payout_amount} className="form-input" />
                </label>
                <label className="form-label">
                  Max Submissions per User per Day
                  <input name="max_submissions_per_user_per_day" type="number" defaultValue={limits.max_submissions_per_user_per_day} className="form-input" />
                </label>
                <label className="form-label">
                  Max Screenshot Size (MB)
                  <input name="max_screenshot_file_size_mb" type="number" defaultValue={limits.max_screenshot_file_size_mb} className="form-input" />
                </label>
                <label className="form-label">
                  Allowed File Formats
                  <input name="allowed_file_formats" defaultValue={limits.allowed_file_formats} className="form-input" />
                </label>
              </div>

              <div className="limits-section">
                <h4>Server Limits (All users: 1 server)</h4>
                <label className="form-label">
                  Max Members per Server (0 = unlimited)
                  <input name="max_server_members" type="number" defaultValue={limits.max_server_members} className="form-input" />
                </label>
                <label className="form-label">
                  Max Submissions per Server per Day (0 = unlimited)
                  <input name="max_submissions_per_server_per_day" type="number" defaultValue={limits.max_submissions_per_server_per_day} className="form-input" />
                </label>
              </div>

              <div className="limits-section">
                <h4>Elite Server Limits</h4>
                <label className="form-label">
                  Max Members per Elite Server (0 = unlimited)
                  <input name="max_server_members_elite" type="number" defaultValue={limits.max_server_members_elite || 0} className="form-input" />
                </label>
                <label className="form-label">
                  Max Submissions per Elite Server per Day (0 = unlimited)
                  <input name="max_submissions_per_server_per_day_elite" type="number" defaultValue={limits.max_submissions_per_server_per_day_elite || 0} className="form-input" />
                </label>
                <label className="form-label">
                  Elite Auto-Approve Threshold ($, 0 = use global)
                  <input name="elite_auto_approve_threshold" type="number" step="0.01" defaultValue={limits.elite_auto_approve_threshold || 0} className="form-input" />
                </label>
              </div>

              <div className="limits-section">
                <h4>Analytics Limits</h4>
                <label className="form-label">
                  Data Retention (days, 0 = unlimited)
                  <input name="data_retention_days" type="number" defaultValue={limits.data_retention_days} className="form-input" />
                </label>
                <label className="form-label">
                  Display Range (days)
                  <input name="analytics_display_days" type="number" defaultValue={limits.analytics_display_days} className="form-input" />
                </label>
              </div>

              <button type="submit" className="submit-button-large">Save All Limits</button>
            </form>
          ) : (
            <div className="limits-display">
              <div className="limits-category">
                <h4>Ranking Eligibility</h4>
                <p>Min Payouts: <strong>{limits.min_payout_count_for_ranking}</strong></p>
                <p>Min Volume: <strong>${limits.min_total_volume_for_ranking}</strong></p>
              </div>
              <div className="limits-category">
                <h4>Payout Limits</h4>
                <p>Max Amount: <strong>${limits.max_payout_amount}</strong></p>
                <p>Max Per Day: <strong>{limits.max_submissions_per_user_per_day}</strong></p>
                <p>Max File Size: <strong>{limits.max_screenshot_file_size_mb}MB</strong></p>
                <p>Formats: <strong>{limits.allowed_file_formats}</strong></p>
              </div>
              <div className="limits-category">
                <h4>Server Limits</h4>
                <p>Max Servers per Owner: <strong>1 (all tiers)</strong></p>
                <p>Max Members: <strong>{limits.max_server_members || 'Unlimited'}</strong></p>
                <p>Max Daily Submissions: <strong>{limits.max_submissions_per_server_per_day || 'Unlimited'}</strong></p>
              </div>
              <div className="limits-category">
                <h4>Elite Limits</h4>
                <p>Max Members: <strong>{limits.max_server_members_elite || 'Unlimited'}</strong></p>
                <p>Max Daily: <strong>{limits.max_submissions_per_server_per_day_elite || 'Unlimited'}</strong></p>
                <p>Auto-Approve: <strong>${limits.elite_auto_approve_threshold || 'Use Global'}</strong></p>
              </div>
              <div className="limits-category">
                <h4>Analytics</h4>
                <p>Retention: <strong>{limits.data_retention_days || 'Unlimited'} days</strong></p>
                <p>Display: <strong>{limits.analytics_display_days} days</strong></p>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  };

  const renderSubscriptions = () => (
    <>
      <h2 className="section-title">Subscription Plans Management</h2>
      <p className="section-description">
        Manage subscription tiers, pricing, features, and Stripe integration
      </p>

      <div className="platform-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3>Subscription Plans</h3>
          <button
            onClick={() => setShowAddPlan(!showAddPlan)}
            className="add-button"
          >
            {showAddPlan ? 'Cancel' : '+ Add New Plan'}
          </button>
        </div>

        {/* Add Plan Form */}
        {showAddPlan && (
          <div className="platform-form-container" style={{ marginBottom: '20px' }}>
            <h4>Create New Subscription Plan</h4>
            <form onSubmit={handleAddPlan} className="platform-form">
              <div className="form-row">
                <label className="form-label">
                  Plan Name *
                  <input
                    type="text"
                    value={planFormData.name}
                    onChange={(e) => setPlanFormData({ ...planFormData, name: e.target.value })}
                    className="form-input"
                    placeholder="e.g., Premium Plan"
                    required
                  />
                </label>
                <label className="form-label">
                  Tier *
                  <input
                    type="text"
                    value={planFormData.tier}
                    onChange={(e) => setPlanFormData({ ...planFormData, tier: e.target.value.toLowerCase() })}
                    className="form-input"
                    placeholder="e.g., premium (lowercase)"
                    required
                  />
                  <small style={{ color: 'var(--text-secondary)' }}>Must be unique, lowercase</small>
                </label>
              </div>
              <div className="form-row">
                <label className="form-label">
                  Price per Month ($) *
                  <input
                    type="number"
                    step="0.01"
                    value={planFormData.price_per_month}
                    onChange={(e) => setPlanFormData({ ...planFormData, price_per_month: e.target.value })}
                    className="form-input"
                    placeholder="e.g., 49.99"
                    required
                  />
                </label>
                <label className="form-label">
                  Sort Order
                  <input
                    type="number"
                    value={planFormData.sort_order}
                    onChange={(e) => setPlanFormData({ ...planFormData, sort_order: e.target.value })}
                    className="form-input"
                    placeholder="0"
                  />
                </label>
              </div>
              <label className="form-label">
                Description *
                <textarea
                  value={planFormData.description}
                  onChange={(e) => setPlanFormData({ ...planFormData, description: e.target.value })}
                  className="form-input"
                  rows="3"
                  placeholder="Plan description"
                  required
                />
              </label>
              <div className="form-row">
                <label className="form-label">
                  Stripe Price ID
                  <input
                    type="text"
                    value={planFormData.stripe_price_id}
                    onChange={(e) => setPlanFormData({ ...planFormData, stripe_price_id: e.target.value })}
                    className="form-input"
                    placeholder="price_... (optional, update later)"
                  />
                  <small style={{ color: 'var(--text-secondary)' }}>From Stripe Dashboard → Products</small>
                </label>
                <label className="form-label">
                  Stripe Product ID
                  <input
                    type="text"
                    value={planFormData.stripe_product_id}
                    onChange={(e) => setPlanFormData({ ...planFormData, stripe_product_id: e.target.value })}
                    className="form-input"
                    placeholder="prod_... (optional, update later)"
                  />
                </label>
              </div>
              <label className="form-label">
                Features (one per line)
                <textarea
                  value={Array.isArray(planFormData.features) ? planFormData.features.join('\n') : planFormData.features}
                  onChange={(e) => setPlanFormData({ ...planFormData, features: e.target.value })}
                  className="form-input"
                  rows="5"
                  placeholder="Feature 1&#10;Feature 2&#10;Feature 3"
                />
              </label>
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  checked={planFormData.is_active}
                  onChange={(e) => setPlanFormData({ ...planFormData, is_active: e.target.checked })}
                />
                Active (visible to users)
              </label>
              <div className="form-actions">
                <button type="submit" className="save-button">Create Plan</button>
                <button type="button" onClick={cancelPlanEdit} className="cancel-button">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Edit Plan Form */}
        {editingPlan && (
          <div className="platform-form-container" style={{ marginBottom: '20px', border: '2px solid var(--primary-blue)' }}>
            <h4>Edit Plan: {editingPlan.name}</h4>
            <form onSubmit={handleUpdatePlan} className="platform-form">
              <div className="form-row">
                <label className="form-label">
                  Plan Name *
                  <input
                    type="text"
                    value={planFormData.name}
                    onChange={(e) => setPlanFormData({ ...planFormData, name: e.target.value })}
                    className="form-input"
                    required
                  />
                </label>
                <label className="form-label">
                  Tier (cannot change)
                  <input
                    type="text"
                    value={planFormData.tier}
                    className="form-input"
                    disabled
                    style={{ backgroundColor: 'var(--surface-dark)', cursor: 'not-allowed' }}
                  />
                </label>
              </div>
              <div className="form-row">
                <label className="form-label">
                  Price per Month ($) *
                  <input
                    type="number"
                    step="0.01"
                    value={planFormData.price_per_month}
                    onChange={(e) => setPlanFormData({ ...planFormData, price_per_month: e.target.value })}
                    className="form-input"
                    required
                  />
                </label>
                <label className="form-label">
                  Sort Order
                  <input
                    type="number"
                    value={planFormData.sort_order}
                    onChange={(e) => setPlanFormData({ ...planFormData, sort_order: e.target.value })}
                    className="form-input"
                  />
                </label>
              </div>
              <label className="form-label">
                Description *
                <textarea
                  value={planFormData.description}
                  onChange={(e) => setPlanFormData({ ...planFormData, description: e.target.value })}
                  className="form-input"
                  rows="3"
                  required
                />
              </label>
              <div className="form-row">
                <label className="form-label">
                  Stripe Price ID
                  <input
                    type="text"
                    value={planFormData.stripe_price_id}
                    onChange={(e) => setPlanFormData({ ...planFormData, stripe_price_id: e.target.value })}
                    className="form-input"
                  />
                </label>
                <label className="form-label">
                  Stripe Product ID
                  <input
                    type="text"
                    value={planFormData.stripe_product_id}
                    onChange={(e) => setPlanFormData({ ...planFormData, stripe_product_id: e.target.value })}
                    className="form-input"
                  />
                </label>
              </div>
              <label className="form-label">
                Features (one per line)
                <textarea
                  value={Array.isArray(planFormData.features) ? planFormData.features.join('\n') : planFormData.features}
                  onChange={(e) => setPlanFormData({ ...planFormData, features: e.target.value })}
                  className="form-input"
                  rows="5"
                />
              </label>
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  checked={planFormData.is_active}
                  onChange={(e) => setPlanFormData({ ...planFormData, is_active: e.target.checked })}
                />
                Active (visible to users)
              </label>
              <div className="form-actions">
                <button type="submit" className="save-button">Update Plan</button>
                <button type="button" onClick={cancelPlanEdit} className="cancel-button">Cancel</button>
              </div>
            </form>
          </div>
        )}

        {/* Plans List */}
        <div className="platform-table-container">
          <table className="platform-table">
            <thead>
              <tr>
                <th>Plan Name</th>
                <th>Tier</th>
                <th>Price/Month</th>
                <th>Status</th>
                <th>Active Subs</th>
                <th>Stripe Price ID</th>
                <th>Stripe Product ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {subscriptionPlans.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                    No subscription plans found. Create one to get started!
                  </td>
                </tr>
              ) : (
                subscriptionPlans.map(plan => (
                  <tr key={plan.id}>
                    <td>
                      <strong>{plan.name}</strong>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {plan.description}
                      </div>
                    </td>
                    <td>
                      <span className="platform-badge primary">{plan.tier}</span>
                    </td>
                    <td>
                      <strong>${parseFloat(plan.price_per_month).toFixed(2)}</strong>
                    </td>
                    <td>
                      <span className={`platform-badge ${plan.is_active ? 'success' : 'secondary'}`}>
                        {plan.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: plan.active_subscriptions_count > 0 ? 'var(--success)' : 'var(--text-secondary)' }}>
                        {plan.active_subscriptions_count || 0}
                      </span>
                    </td>
                    <td>
                      <code style={{ fontSize: '11px', color: plan.stripe_price_id?.includes('PLACEHOLDER') ? 'var(--warning)' : 'var(--text-secondary)' }}>
                        {plan.stripe_price_id || 'Not set'}
                      </code>
                    </td>
                    <td>
                      <code style={{ fontSize: '11px', color: plan.stripe_product_id?.includes('PLACEHOLDER') ? 'var(--warning)' : 'var(--text-secondary)' }}>
                        {plan.stripe_product_id || 'Not set'}
                      </code>
                    </td>
                    <td>
                      <div className="plt-action-buttons">
                        <button
                          onClick={() => startEditPlan(plan)}
                          className="action-btn edit"
                          style={{ color: 'rgba(255,255,255,1)' }}
                          title="Edit plan"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleTogglePlanActive(plan.id, plan.is_active)}
                          className={`action-btn ${plan.is_active ? 'warning' : 'success'}`}
                          style={{ color: 'rgba(255,255,255,1)' }}
                          title={plan.is_active ? 'Deactivate plan' : 'Activate plan'}
                        >
                          {plan.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          onClick={() => handleDeletePlan(plan.id, plan.name)}
                          className="action-btn danger"
                          title="Delete plan"
                          disabled={plan.active_subscriptions_count > 0}
                          style={plan.active_subscriptions_count > 0 ? { opacity: 0.5, cursor: 'not-allowed', color: 'rgba(255,255,255,1)' } : {}}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Features Section */}
        {subscriptionPlans.length > 0 && (
          <div style={{ marginTop: '30px' }}>
            <h4>Plan Features Comparison</h4>
            <div className="features-grid">
              {subscriptionPlans.map(plan => (
                <div key={plan.id} className="feature-card">
                  <div className="feature-card-header">
                    <h5>{plan.name}</h5>
                    <span className={`platform-badge ${plan.is_active ? 'success' : 'secondary'}`}>
                      {plan.tier}
                    </span>
                  </div>
                  <div className="feature-card-body">
                    {plan.features && plan.features.length > 0 ? (
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {plan.features.map((feature, idx) => (
                          <li key={idx} style={{ padding: '6px 0', color: 'var(--text-secondary)', fontSize: '14px' }}>
                            ✓ {feature}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>No features defined</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );

  const renderAudit = () => (
    <>
      <h2 className="section-title">Audit Logs</h2>

      <div className="config-list">
        {auditLogs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            No audit logs found
          </div>
        ) : (
          auditLogs.map(log => (
            <div key={log.id} className="config-item-expanded">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>{log.actor_username || 'System'}</strong>
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                  {formatTimestamp(log.created_at)}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '14px', flexWrap: 'wrap' }}>
                <span className="platform-badge primary">{log.action_type}</span>
                <span style={{ color: 'var(--text-secondary)' }}>on</span>
                <span className="platform-badge secondary">{log.target_table}</span>
                {log.target_id && <span style={{ color: 'var(--text-secondary)' }}>#{log.target_id}</span>}
              </div>
              {log.metadata && Object.keys(log.metadata).length > 0 && (
                <div style={{ marginTop: '10px', padding: '10px', backgroundColor: 'var(--bg-dark)', borderRadius: 'var(--radius-sm)', fontSize: '12px', overflow: 'auto' }}>
                  <pre style={{ margin: 0, color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{JSON.stringify(log.metadata, null, 2)}</pre>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );

  // Main render
  if (!canManagePlatform(user)) {
    return null;
  }

  return (
    <div className="platform-admin">
      {/* Header */}
      <div className="platform-admin-header">
        <div>
          <h1>Platform Admin</h1>
          <p className="platform-admin-subtitle">Complete system control panel</p>
        </div>
        <div>
          <button onClick={() => navigate('/dashboard')} className="plt-action-button primary">
            User Dashboard
          </button>
          <button onClick={logout} className="plt-action-button danger">
            Logout
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="platform-admin-tabs">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'users', label: 'Users' },
          { id: 'servers', label: 'Servers' },
          { id: 'payouts', label: 'Payouts' },
          { id: 'subscriptions', label: 'Subscriptions' },
          { id: 'config', label: 'Config' },
          { id: 'audit', label: 'Audit Logs' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`platform-admin-tab ${activeTab === tab.id ? 'active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="platform-loading">Loading...</div>
      ) : error ? (
        <div className="platform-error">{error}</div>
      ) : (
        <div className="platform-admin-content">
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'users' && renderUsers()}
          {activeTab === 'servers' && renderServers()}
          {activeTab === 'payouts' && renderPayouts()}
          {activeTab === 'subscriptions' && renderSubscriptions()}
          {activeTab === 'config' && renderConfig()}
          {activeTab === 'audit' && renderAudit()}
        </div>
      )}

      {/* Role/Subscription Modal */}
      <RoleSubscriptionModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSubmit={handleModalSubmit}
        user={selectedUser}
        currentSubscription={loadingSubscription ? null : currentSubscription}
      />

      {/* Payout Review Modal */}
      {reviewModalOpen && selectedSubmission && (
        <PayoutReviewModal
          submission={selectedSubmission}
          onClose={() => {
            setReviewModalOpen(false);
            setSelectedSubmission(null);
          }}
          onReviewComplete={handleReviewComplete}
        />
      )}
    </div>
  );
};

export default PlatformAdmin;
