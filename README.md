# Language Learning Platform

An interactive web application that helps users incorporate AI into their language learning process. Track your progress, complete lessons, and monitor your language learning journey.

## Features

- 📊 **Progress Dashboard**: Track your learning statistics and achievements
- 📚 **Lesson System**: Structured language learning courses
- 📈 **Weekly Stats**: Monitor your study time, units completed, and quiz accuracy
- 🎯 **Career Progress**: Lifetime learning statistics
- 🌍 **Multi-Language Support**: Learn different languages with tier-based progression
- 💡 **Insights**: Identify your strongest and weakest skills

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

## Deployment to Render

**📖 See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions.**

### Quick Deploy

1. Ensure code is on `main` branch
2. Push to GitHub: `git push origin main`
3. Go to [Render Dashboard](https://dashboard.render.com/)
4. New + → Blueprint → Connect repository
5. Render detects `render.yaml` and auto-deploys

Your app will be live at: `https://language-learning-platform.onrender.com`

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

## Environment Variables

For production deployment, configure these environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (False in production) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `RENDER_EXTERNAL_HOSTNAME` | Auto-set by Render | No |

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

- [ ] Progress dashboard implementation
- [ ] User authentication system
- [ ] Real-time lesson progress tracking
- [ ] Interactive quizzes and exercises
- [ ] AI-powered language practice
- [ ] Social features and leaderboards
- [ ] Mobile responsive design improvements

---

Made with ❤️ for language learners
