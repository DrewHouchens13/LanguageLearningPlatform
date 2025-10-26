# Language Learning Platform

An interactive web application that helps users incorporate AI into their language learning process. Track your progress, complete lessons, and monitor your language learning journey.

## Features

- 📊 **Progress Dashboard**: Track your learning statistics and achievements
- 📚 **Lesson System**: Structured language learning courses
- 📈 **Weekly Stats**: Monitor your study time, units completed, and quiz accuracy
- 🎯 **Career Progress**: Lifetime learning statistics
- 🌍 **Multi-Language Support**: Learn different languages with tier-based progression
- 💡 **Insights**: Identify your strongest and weakest skills
- 🔐 **Secure Authentication**: Email-based login with comprehensive validation
- 👤 **Account Management**: Update email, name, username, and password
- 🔑 **Password Recovery**: Email-based password reset with secure tokens
- 📧 **Username Recovery**: Forgot username? Get a reminder via email
- 👨‍💼 **Admin Panel**: Enhanced Django admin with unified navigation and bulk operations
- 🛡️ **Security Features**: Login attempt logging, password validation, account change tracking
- 📱 **Responsive Design**: Works on desktop and mobile devices

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

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Load guest data (optional)**
   ```bash
   python manage.py loaddata home/fixtures/guest_data.json
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Home: http://localhost:8000/
   - Admin Panel: http://localhost:8000/admin/

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

The platform implements comprehensive security measures:

### Authentication & Authorization
- **Email-based Login**: Users authenticate with email addresses
- **Password Validation**: Django validators enforce strong passwords (min 8 chars, complexity requirements)
- **Email Validation**: Format verification before account creation
- **Open Redirect Prevention**: Login redirects validated to prevent attacks
- **Generic Error Messages**: Prevents user enumeration during authentication

### Account Security
- **Secure Password Reset**: Token-based reset with 20-minute expiration
- **Account Change Logging**: All email/username/password updates logged with IP addresses
- **Password Verification**: Current password required for sensitive changes
- **Session Persistence**: Users remain logged in after password change
- **Username/Email Uniqueness**: Prevents duplicate accounts

### Security Monitoring
- **Login Attempt Logging**: All authentication events logged with IP addresses
- **Failed Login Tracking**: Monitor suspicious activity and brute force attempts
- **Account Activity Logs**: Track all account modifications

### Production Security
- **HTTPS Enforcement**: SSL/TLS required in production
- **Secure Cookies**: Session and CSRF cookies secured in production
- **HSTS Headers**: HTTP Strict Transport Security enabled
- **CSRF Protection**: Django CSRF middleware on all forms
- **XSS Protection**: Content escaping and security headers
- **Static File Security**: WhiteNoise serves static files (not Django)

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
| `RENDER_EXTERNAL_HOSTNAME` | Auto-set by Render | No |
| `IS_DEVEDU` | Enable DevEDU proxy support | No (dev only) |
| `STATIC_URL_PREFIX` | Proxy prefix for static files | No (dev only) |

**Note**: In development, emails are printed to the console instead of being sent.

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
- [ ] Help/Wiki section for user support
- [ ] Real-time lesson progress tracking
- [ ] Interactive quizzes and exercises
- [ ] AI-powered language practice
- [ ] Social features and leaderboards
- [ ] Advanced analytics and insights dashboard

---

Made with ❤️ for language learners
