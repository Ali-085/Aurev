# Trading Communities Platform

A comprehensive platform for verified trading communities and payout tracking to distinguish real leaders from fakes.

## 🚀 Features

- **Server Management**: Create and manage trading communities
- **Payout Tracking**: Submit and verify trading payouts with screenshot evidence
- **Analytics Dashboard**: Comprehensive server and trader analytics with leaderboards.(verified)
- **Role-Based Access**: Multi-tier permission system (Admin, Moderator, Server Owner, Trader)
- **Subscription System**: Stripe-integrated tiered subscriptions
- **Privacy Controls**: Trader data masking and privacy settings
- **Public Profiles**: Shareable trader and server profiles
- **Moderation Tools**: Payout review and approval system

## 🛡️ Security

- ✅ JWT cookie-based authentication
- ✅ Email verification enforcement
- ✅ Rate limiting on sensitive endpoints
- ✅ CSRF protection
- ✅ Secure file uploads (magic byte validation, EXIF stripping)
- ✅ Atomic database transactions
- ✅ RBAC permission system

## 📋 Tech Stack

### Backend
- Django 5.2.8
- Django REST Framework
- PostgreSQL / SQLite
- Stripe API
- Cloudflare R2 Storage
- JWT Authentication

### Frontend
- React 18
- Vite
- React Router
- Recharts (Analytics)
- Axios

## 🔧 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (production)

### Backend Setup

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup

```bash
cd Frontend
npm install
npm run dev
```

## 🌍 Environment Variables

Create `.env` files in Backend directory:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tradingplatform
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Cloudflare R2 (optional)
USE_R2_STORAGE=False
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ACCOUNT_ID=

# Frontend
FRONTEND_URL=http://localhost:3000
```

## 📁 Project Structure

```
Av/
├── Backend/              # Django REST API
│   ├── analytics/       # Server & user analytics
│   ├── audit/           # Audit logging
│   ├── core/            # Settings & config
│   ├── payouts/         # Payout submission system
│   ├── platform_admin/  # Admin dashboard
│   ├── servers/         # Server management
│   ├── subscriptions/   # Stripe integration
│   ├── users/           # Authentication & users
│   └── utils/           # Shared utilities
│
├── Frontend/            # React application
│   ├── src/
│   │   ├── components/  # Reusable components
│   │   ├── pages/       # Route pages
│   │   ├── context/     # React context
│   │   └── utils/       # Helper functions
│   └── public/          # Static assets
│
└── docs/                # Documentation

```

## 🚀 Deployment

See [DEPLOYMENT.md](1/DEPLOYMENT.md) for production deployment guide.

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure PostgreSQL
- [ ] Set strong `SECRET_KEY`
- [ ] Configure Stripe production keys
- [ ] Set up SSL/HTTPS
- [ ] Configure CORS origins
- [ ] Set up R2 storage
- [ ] Test webhook endpoints

## 📊 API Documentation

API documentation available at `/api/docs/` when running the development server.

## 🧪 Testing

```bash
# Backend tests
cd Backend
python manage.py test

# Frontend tests
cd Frontend
npm test
```
## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is proprietary software.

## 🆘 Support

For issues and questions, please open an issue in the GitHub repository.

---

**Built with ❤️ for the trading community**
