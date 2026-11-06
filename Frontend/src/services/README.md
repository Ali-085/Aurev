# API Services

All API calls are centralized in this `services/` directory. Each service file handles a specific domain of the application.

## Structure

```
services/
├── index.js              # Central export point for all services
├── authService.js        # Authentication (login, register, logout)
├── serverService.js      # Server CRUD, branding, membership
├── analyticsService.js   # Dashboard, leaderboard, analytics
├── payoutService.js      # Payout submissions and reviews
└── adminService.js       # Admin and moderator dashboards
```

## Usage

Import services from the central index:

```javascript
import { authService, serverService, analyticsService } from '../services';
```

Or import individual services:

```javascript
import { authService } from '../services/authService';
```

## Examples

### Authentication
```javascript
// Login
const data = await authService.login(email, password);

// Register
const data = await authService.register({
  username,
  email,
  password,
  accountType: 'trader',
  serverId: 123
});

// Get current user
const userData = await authService.getCurrentUser();

// Logout
await authService.logout();
```

### Servers
```javascript
// Get all servers
const servers = await serverService.getAllServers();

// Get server by ID
const server = await serverService.getServerById(123);

// Get my servers
const myServers = await serverService.getMyServers();

// Update server branding
const formData = new FormData();
formData.append('logo', logoFile);
formData.append('primary_color', '#0066FF');
await serverService.updateServerBranding(serverId, formData);

// Join server
await serverService.joinServer(slug);
```

### Analytics
```javascript
// Get server dashboard
const dashboard = await analyticsService.getServerDashboard(slug);

// Get leaderboard
const leaderboard = await analyticsService.getServerLeaderboard(slug);

// Get trader profile
const profile = await analyticsService.getTraderProfile(slug, traderId);

// Get public analytics
const analytics = await analyticsService.getPublicServerAnalytics(serverId);
```

### Payouts
```javascript
// Submit payout
const formData = new FormData();
formData.append('amount', 1000);
formData.append('screenshot', file);
await payoutService.submitPayout(formData);

// Review submission (approve/reject)
await payoutService.reviewSubmission(submissionId, {
  action: 'approve',
  notes: 'Verified'
});

// Get my submissions
const submissions = await payoutService.getMySubmissions();
```

### Admin
```javascript
// Get admin overview
const overview = await adminService.getAdminOverview();

// Get pending submissions
const pending = await adminService.getAdminPendingSubmissions();

// Pause server submissions
await adminService.pauseServerSubmissions(serverId, { reason: 'Investigation' });

// Download report
const blob = await adminService.downloadReport('monthly');

// Moderator dashboard
const queue = await adminService.getModeratorReviewQueue();
```

## Authentication

All services automatically include authentication cookies (HttpOnly) via the configured axios instance in `config/api.js`. No need to manually pass tokens.

## Error Handling

Services throw errors that should be caught by the calling component:

```javascript
try {
  const data = await serverService.getServerById(123);
  setServerData(data);
} catch (error) {
  console.error('Error:', error);
  setError(error.response?.data?.error || 'Failed to load server');
}
```

## Benefits

1. **Single Source of Truth**: All API endpoints defined in one place
2. **Type Safety**: JSDoc comments provide IDE autocomplete
3. **Maintainability**: Easy to update endpoints or add new methods
4. **Reusability**: Import same service across multiple components
5. **Testing**: Easy to mock services for unit tests
6. **Security**: Centralized authentication handling via cookies

## Migration Notes

Previously, API calls were inline with axios:
```javascript
const response = await axios.get('http://localhost:8000/api/servers/', {
  headers: { Authorization: `Bearer ${token}` }
});
setServers(response.data);
```

Now, use services:
```javascript
const data = await serverService.getAllServers();
setServers(data);
```

No more:
- ❌ Manual token management with localStorage
- ❌ Hardcoded URLs in components
- ❌ Repetitive header configuration
- ❌ Direct axios imports in components
