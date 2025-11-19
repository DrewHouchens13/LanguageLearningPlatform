# Language Learning Platform

An interactive web application that helps users incorporate AI into their language learning process. Track your progress, complete lessons, and monitor your language learning journey.

## Features

### Learning & Progress
- 📝 **Placement Test**: Adaptive onboarding assessment to determine your proficiency level (Beginner, Intermediate, Advanced)
- 📚 **Interactive Lessons**: Two lesson types - flashcards for vocabulary and quizzes for comprehension
- 🎯 **Daily Quests**: Two daily challenges refresh at midnight (time-based and lesson-based)
- ⭐ **XP & Leveling System**: Earn experience points and level up as you learn
- 🔥 **Streak Tracking**: Maintain your learning momentum with consecutive day tracking
- 📊 **Progress Dashboard**: Comprehensive overview with XP, quests, and personalized recommendations
- 📈 **Weekly & Lifetime Stats**: Monitor study time, lessons completed, and quiz accuracy
- 🏆 **Quest History**: View all completed quests and total XP earned

### User Experience
- 🎨 **Modern UI**: Clean, responsive design with smooth animations and gradients
- 📱 **Mobile-First**: Fully responsive across all device sizes
- 🖼️ **Avatar System**: Custom profile pictures with automatic Gravatar integration
- 🎮 **Gamification**: Level badges, progress indicators, and achievement tracking
- 💬 **Immediate Feedback**: Instant results and detailed answer reviews

### Account & Security
- 🔐 **Secure Authentication**: Email/username-based login with comprehensive validation
- 👤 **Account Management**: Update email, name, username, password, and avatar
- 🔑 **Password Recovery**: Secure token-based password reset (simulated email for demo)
- 📧 **Username Recovery**: Forgot username reminder via email (simulated for demo)
- 🛡️ **Security Features**: IP validation, login attempt logging, password validation, account change tracking

### Administration
- 👨‍💼 **Admin Panel**: Enhanced Django admin with unified navigation and bulk operations
- 📊 **Analytics Dashboard**: Track user engagement, lesson completion rates, and quest performance
- 🔧 **Content Management**: Create and manage lessons, quizzes, and daily quests

### Technical
- ✅ **Comprehensive Testing**: 443 tests with 91% code coverage including security edge cases
- 🔄 **Production Ready**: Deployed on Render.com with PostgreSQL database
- 🚀 **Performance Optimized**: Static file caching, efficient queries, and CDN integration

## Tech Stack

- **Backend**: Django 5.2.7
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Static Files**: WhiteNoise
- **Deployment**: Render.com
- **Python**: 3.11+

## Quick Start (Local Development)

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/LanguageLearningPlatform.git
   cd LanguageLearningPlatform
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your API keys (required for AI Chatbot & TTS)
   # See ENV_SETUP_GUIDE.md for detailed instructions
   ```

   **📖 See [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md) for complete environment configuration guide**

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Load guest data (optional)**
   ```bash
   python manage.py loaddata home/fixtures/guest_data.json
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Home: http://localhost:8000/
   - Admin Panel: http://localhost:8000/admin/
   - Help & AI Chatbot: http://localhost:8000/help/

## Admin Panel

The platform includes a comprehensive Django admin interface with unified navigation and enhanced security features.

### Creating an Admin Account

**Local Development:**
```bash
python manage.py createsuperuser
```

**Production (Render):**
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Select your service → **Shell** tab
3. Run: `python manage.py createsuperuser`
4. Enter username, email, and secure password
5. Access admin at: `https://language-learning-platform-xb6f.onrender.com/admin/`

### Admin Features

- **Unified Navigation**: Admin panel uses same purple gradient header as main site
- **Staff-Only Access**: Admin button appears in navigation only for staff users
- **User Management**: View all users, reset passwords (generates secure 12-char random passwords)
- **Progress Management**: View and reset user progress, lesson completions, quiz results
- **Bulk Actions**: Perform operations on multiple users at once
- **Search & Filter**: Find users and data quickly
- **Security Logging**: All login attempts logged with IP addresses for monitoring
- **Custom Logout**: Properly handles redirects in proxy environments

📖 **See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for complete administrator documentation**

## User Account Management

Users can manage their accounts through the **Account** page (accessible after login):

### Account Settings
- **Update Email Address**: Change your email (requires current password)
- **Update Name**: Change your first and last name
- **Update Username**: Change your login username
- **Change Password**: Update your password (requires current password)

### Password & Username Recovery
- **Forgot Password**: Request a password reset link via email (expires in 20 minutes)
- **Forgot Username**: Get a username reminder sent to your email

All account changes are logged for security purposes.

📖 **See [USER_GUIDE.md](USER_GUIDE.md) for complete user documentation**

## Deployment to Render

**📖 See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions.**

### Deployment Process

**⚠️ Auto-deploy is DISABLED for safety** - Manual deployment required:

1. **Merge to main branch:**
   ```bash
   git checkout main
   git merge feature/your-feature
   git push origin main
   ```

2. **Manual Deploy from Render Dashboard:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Select service: `language-learning-platform`
   - Click **"Manual Deploy"** → **"Deploy latest commit"**
   - Monitor build logs for any issues

3. **Verify deployment:**
   - Visit: `https://language-learning-platform-xb6f.onrender.com`
   - Test login, admin panel, and key features
   - Create admin account via Shell if needed

**Note**: Merging to `main` does NOT automatically deploy. You have full control over when changes go live.

## Project Structure

```
LanguageLearningPlatform/
├── config/              # Django project settings
│   ├── settings.py     # Main settings (development & production)
│   ├── urls.py         # Root URL configuration
│   └── wsgi.py         # WSGI application
├── home/               # Main application
│   ├── models.py       # Database models
│   ├── views.py        # View functions
│   ├── urls.py         # App URL patterns
│   ├── templates/      # HTML templates
│   ├── static/         # CSS, JS, images
│   └── fixtures/       # Sample data
├── build.sh            # Render build script
├── render.yaml         # Render infrastructure config
├── requirements.txt    # Python dependencies
├── manage.py           # Django management script
└── README.md           # This file
```

## Security Features

The platform implements comprehensive security measures with **129 tests (89% coverage)**:

### Authentication & Authorization
- **Email-based Login**: Users authenticate with email addresses
- **Password Validation**: Django validators enforce strong passwords (min 8 chars, complexity requirements)
- **Email Validation**: Format verification before account creation
- **Open Redirect Prevention**: Login redirects validated to prevent attacks
- **Generic Error Messages**: Prevents user enumeration during authentication
- **IP Address Validation**: Python ipaddress module validates format to prevent injection attacks

### Account Security
- **Secure Password Reset**: Token-based reset with 20-minute expiration
- **Account Change Logging**: All email/username/password updates logged with validated IP addresses
- **Password Verification**: Current password required for sensitive changes
- **Session Persistence**: Users remain logged in after password change
- **Username/Email Uniqueness**: Prevents duplicate accounts
- **Email Retry Mechanism**: 3 retry attempts with exponential backoff for reliability

### Security Monitoring
- **Login Attempt Logging**: All authentication events logged with validated IP addresses
- **Failed Login Tracking**: Monitor suspicious activity and brute force attempts
- **Account Activity Logs**: Track all account modifications
- **Malformed IP Logging**: Warns about invalid X-Forwarded-For headers

### Production Security
- **HTTPS Enforcement**: SSL/TLS required in production
- **Secure Cookies**: Session and CSRF cookies secured in production
- **HSTS Headers**: HTTP Strict Transport Security enabled
- **CSRF Protection**: Django CSRF middleware on all forms
- **XSS Protection**: Django automatic escaping (verified via test suite)
- **SQL Injection Protection**: Parameterized queries (verified via test suite)
- **Static File Security**: WhiteNoise serves static files (not Django)
- **Cache Backend Validation**: Runtime warning if using local memory cache in production
- **Email Configuration Validation**: Validates DEFAULT_FROM_EMAIL before sending

### DevEDU Environment Support
- **Proxy Configuration**: Environment variable-based proxy support
- **CSRF Relaxation**: Development-friendly CSRF settings (dev only)
- **Debug Mode**: Auto-enabled for development/testing

## Environment Variables

For production deployment, configure these environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (False in production) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `EMAIL_HOST` | SMTP server (e.g., smtp.sendgrid.net) | For email features |
| `EMAIL_PORT` | SMTP port (usually 587) | For email features |
| `EMAIL_HOST_USER` | SMTP username | For email features |
| `EMAIL_HOST_PASSWORD` | SMTP password/API key | For email features |
| `DEFAULT_FROM_EMAIL` | From email address | For email features |
| `REDIS_URL` | Redis connection string | For production caching |
| `REDIS_PASSWORD` | Redis password | For production caching |
| `RENDER_EXTERNAL_HOSTNAME` | Auto-set by Render | No |
| `IS_DEVEDU` | Enable DevEDU proxy support | No (dev only) |
| `STATIC_URL_PREFIX` | Proxy prefix for static files | No (dev only) |

**Notes**:
- In development, emails are printed to the console instead of being sent
- **Production Cache**: Configure Redis or Memcached for production (local memory cache not suitable)
  - Runtime warning will be displayed if using local memory cache in production
  - See `config/settings.py` lines 280-331 for Redis/Memcached configuration examples

## Database Models

- **UserProfile**: User information and guest accounts
- **WeeklyStats**: Weekly study statistics
- **CareerProgress**: Lifetime learning progress
- **LanguageProgress**: Progress for specific languages
- **UserInsights**: Strengths, weaknesses, and study patterns

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is for educational purposes.

## Support

For deployment issues, see [DEPLOYMENT.md](DEPLOYMENT.md)

For application issues, please open an issue on GitHub.

## Roadmap

- [x] Progress dashboard implementation
- [x] User authentication system with email-based login
- [x] Account management (email, name, username, password updates)
- [x] Password recovery via email
- [x] Username recovery via email
- [x] Django admin panel with enhanced features
- [x] Security logging and monitoring
- [x] Mobile responsive design
- [x] Comprehensive test suite (129 tests, 89% coverage)
- [x] Security hardening (IP validation, XSS/SQL injection protection)
- [x] Production reliability features (email retry, cache validation)
- [ ] Help/Wiki section for user support
- [ ] Real-time lesson progress tracking
- [ ] Interactive quizzes and exercises
- [ ] AI-powered language practice
- [ ] Social features and leaderboards
- [ ] Advanced analytics and insights dashboard

## AI Assistance Documentation

This project was developed with assistance from Claude Code (Anthropic's AI coding assistant). Below is documentation of when and where AI assistance was used, as required for academic integrity and Sprint 2 submission.

### Sprint 0-1: Initial Setup & Core Features
- **Feature**: Initial Django project setup, user authentication, progress tracking
- **AI Tool**: Claude Code (claude.ai/code)
- **Transcript**: [Sprint 0-1 Initial Development](https://claude.ai/share) *(Note: Specific transcript URLs to be added)*
- **Scope**: Project structure, model design, authentication system, basic views

### Sprint 2: User Profile & Password Recovery
- **Feature**: User profile system with avatar uploads, password recovery, username recovery
- **AI Tool**: Claude Code (claude.ai/code)
- **Date**: October-November 2025
- **Transcript**: [Sprint 2 User Profile Development](https://claude.ai/share) *(Note: Specific transcript URLs to be added)*
- **Scope**:
  - User profile models and views (home/models.py, home/views.py)
  - Avatar upload system with Cloudinary integration
  - Password reset flow with email tokens
  - Username recovery system
  - Account management views (email, password, username updates)
  - Security logging (LoginAttempt, AccountChange models)
  - Test suite expansion (372 tests, 93% coverage)

### Sprint 2: Bug Fixes & Deployment Issues (November 6, 2025)
- **Issue**: Avatar upload HTTP 500 errors on Render production
- **AI Tool**: Claude Code (claude.ai/code)
- **Transcript**: [Avatar Upload Bug Fix Session](https://claude.ai/share) *(Current session)*
- **Scope**:
  - Created diagnostic script to test Cloudinary configuration layers
  - Identified incorrect Cloudinary API credentials (typo in secret key)
  - Fixed missing UserProfile exception handling in avatar upload view
  - Added comprehensive error logging with exc_info=True
  - Fixed DEBUG security issue (now defaults to False in production)
  - Updated Sprint 2 report to document resolution

### Sprint 2: Code Quality Improvements (November 6, 2025)
- **Feature**: Pylint refactoring to achieve 9.5+ code quality score
- **AI Tool**: Claude Code (claude.ai/code)
- **Branch**: `pylint_refactor`
- **Transcript**: [Pylint Refactoring Session](https://claude.ai/share) *(Current session)*
- **Scope**:
  - Fixed 18 logging f-string warnings (W1203)
  - Removed 2 unused imports (W0611)
  - Fixed unused variable warnings (W0612)
  - Score improvement: 9.40/10 → 9.55/10
  - All 372 tests maintained at 93% coverage

### AI Assistance Guidelines Followed
- **Transparency**: All AI-assisted code is documented here
- **Review Process**: All AI-generated code reviewed by human developers
- **Testing**: Comprehensive test suite ensures AI-generated code meets quality standards
- **Version Control**: All changes tracked in Git with detailed commit messages
- **Team Collaboration**: AI used as development tool, not replacement for human judgment

### Areas Where AI Was Most Helpful
1. **Django Best Practices**: Model relationships, view patterns, security configurations
2. **Test Suite Development**: Writing comprehensive unit and integration tests
3. **Debugging**: Systematic troubleshooting of production issues
4. **Code Quality**: Refactoring to meet pylint and security standards
5. **Documentation**: Writing clear documentation and code comments
6. **CI/CD Pipeline**: GitHub Actions workflow configuration

### Limitations & Human Oversight
- **Architecture Decisions**: Made by development team, not AI
- **Business Logic**: Designed by team based on requirements
- **Security Review**: All security-critical code manually reviewed
- **Production Deployment**: Managed by team with AI assistance for troubleshooting

---

Made with ❤️ for language learners
