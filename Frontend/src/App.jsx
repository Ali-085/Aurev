/**
 * Main App Component
 * 
 * SECURITY:
 * - Protected routes with authentication checks
 * - Role-based access control
 * - Proper routing with React Router
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import PendingPaymentGuard from './components/PendingPaymentGuard';
import Navbar from './components/Navbar';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Unauthorized from './pages/Unauthorized';
import Servers from './pages/Servers';
import Pricing from './pages/Pricing';
import Analytics from './pages/Analytics';
import TraderProfile from './pages/TraderProfile';
import ServerOwnerDashboard from './pages/ServerOwnerDashboard';
import ServerOwnerAnalytics from './pages/ServerOwnerAnalytics';
import PlatformAdmin from './pages/PlatformAdmin';
import PayoutSubmission from './pages/PayoutSubmission';
import AdminDashboard from './pages/AdminDashboard';
import ModeratorDashboard from './pages/ModeratorDashboard';
import ServerDashboard from './pages/ServerDashboard';
import ServerPublicView from './pages/ServerPublicView';
import CreateServer from './pages/CreateServer';
import ServerSettings from './pages/ServerSettings';
import JoinedServers from './pages/JoinedServers';
import Verify from './pages/Verify';
import VerifyNotice from './pages/VerifyNotice';
import ServerCreatorCheckout from './pages/ServerCreatorCheckout';
import ServerCreatorSuccess from './pages/ServerCreatorSuccess';
import ServerCreatorCancel from './pages/ServerCreatorCancel';
import Subscription from './pages/Subscription';
import UserSettings from './pages/UserSettings';
import PublicTraderProfile from './pages/PublicTraderProfile';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import DiscordJoin from './pages/DiscordJoin';

// Role-specific Dashboards
import TraderDashboard from './pages/dashboards/TraderDashboard';
import ServerOwnerDashboardPage from './pages/dashboards/ServerOwnerDashboard';
import ModeratorDashboardPage from './pages/dashboards/ModeratorDashboard';
import AdminDashboardPage from './pages/dashboards/AdminDashboard';
import PlatformAdminDashboard from './pages/dashboards/PlatformAdminDashboard';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PendingPaymentGuard>
          <Navbar />
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/discord" element={<DiscordJoin />} />
            <Route path="/unauthorized" element={<Unauthorized />} />
            
            {/* Email Verification Routes */}
            <Route path="/verify" element={<Verify />} />
            <Route path="/verify-notice" element={<VerifyNotice />} />

            {/* Password Reset Routes */}
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />

            {/* Server Creator Payment Routes */}
          <Route 
            path="/server-creator/checkout" 
            element={
              <ProtectedRoute>
                <ServerCreatorCheckout />
              </ProtectedRoute>
            } 
          />
          <Route path="/server-creator/success" element={<ServerCreatorSuccess />} />
          <Route path="/server-creator/cancel" element={<ServerCreatorCancel />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Role-Specific Dashboard Routes */}
          <Route
            path="/dashboard/trader"
            element={
              <ProtectedRoute>
                <TraderDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/server-owner"
            element={
              <ProtectedRoute>
                <ServerOwnerDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/moderator"
            element={
              <ProtectedRoute requiredCapability="can_review_content">
                <ModeratorDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/admin"
            element={
              <ProtectedRoute requiredCapability="can_manage_content">
                <AdminDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/platform-admin"
            element={
              <ProtectedRoute requiresSuperuser={true}>
                <PlatformAdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Server Routes */}
          <Route path="/servers" element={<Servers />} />
          <Route
            path="/joined-servers"
            element={
              <ProtectedRoute>
                <JoinedServers />
              </ProtectedRoute>
            }
          />
          <Route
            path="/servers/create"
            element={
              <ProtectedRoute>
                <CreateServer />
              </ProtectedRoute>
            }
          />
          {/* Public Server Analytics */}
          <Route path="/servers/:serverId/public" element={<ServerPublicView />} />
          {/* Member/Owner Server Dashboard */}
          <Route path="/servers/:serverId/dashboard" element={<ServerDashboard />} />
          {/* Server Settings (Owner Only) */}
          <Route
            path="/servers/:serverId/settings"
            element={
              <ProtectedRoute>
                <ServerSettings />
              </ProtectedRoute>
            }
          />

          <Route
            path="/payouts"
            element={
              <ProtectedRoute>
                <PayoutSubmission />
              </ProtectedRoute>
            }
          />

          {/* Analytics - Public */}
          <Route path="/analytics" element={<Analytics />} />

          {/* Trader Profile - Protected */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <TraderProfile />
              </ProtectedRoute>
            }
          />

          {/* Public Trader Profile - No Auth Required */}
          <Route path="/trader/:userId/public" element={<PublicTraderProfile />} />

          {/* User Settings - Protected */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <UserSettings />
              </ProtectedRoute>
            }
          />

          {/* Server Owner Dashboard - Protected */}
          <Route
            path="/my-servers"
            element={
              <ProtectedRoute>
                <ServerOwnerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-servers/:serverId/analytics"
            element={
              <ProtectedRoute>
                <ServerOwnerAnalytics />
              </ProtectedRoute>
            }
          />

          <Route
            path="/subscription"
            element={
              <ProtectedRoute>
                <Subscription />
              </ProtectedRoute>
            }
          />

          {/* Platform Admin - Superuser only */}
          <Route
            path="/platform-admin"
            element={
              <ProtectedRoute requiresSuperuser={true}>
                <PlatformAdmin />
              </ProtectedRoute>
            }
          />

          {/* Admin Routes - Require content management capability */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requiredCapability="can_manage_content">
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          {/* Moderator Routes - Require content review capability */}
          <Route
            path="/moderator"
            element={
              <ProtectedRoute requiredCapability="can_review_content">
                <ModeratorDashboard />
              </ProtectedRoute>
            }
          />

          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </PendingPaymentGuard>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
