# Environment Variables Setup Guide

## Overview

This guide explains how to configure environment variables for local development and how they match with production deployment (Render) and GitHub Secrets.

## 🔑 API Keys Configuration

### Local Development (.env file)

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys:**
   ```bash
   # The .env file is gitignored - your keys are safe!
   ```

3. **Required for AI Chatbot & TTS:**
   ```env
   OPEN_AI_API_KEY=sk-proj-XXXXXXXXXXXXXXXX
   ```

### Environment Variables Naming

**Important:** Use `OPEN_AI_API_KEY` (with underscores) to maintain consistency across all environments:

| Environment | Variable Name | Location |
|-------------|---------------|----------|
| **Local Development** | `OPEN_AI_API_KEY` | `.env` file |
| **GitHub Secrets** | `OPEN_AI_API_KEY` | Repository Settings → Secrets |
| **Render Production** | `OPEN_AI_API_KEY` | Environment Variables |

**Why underscores?** Our code supports both `OPENAI_API_KEY` and `OPEN_AI_API_KEY`, but using underscores matches the Render configuration shown in your screenshot.

## 📋 Complete Environment Variables List

### Required for Core Features

| Variable | Description | Where to Get It | Required For |
|----------|-------------|-----------------|--------------|
| `OPEN_AI_API_KEY` | OpenAI API key | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | AI Chatbot, TTS |
| `DEBUG` | Enable debug mode | Set to `True` for local dev | Development |

### Optional - Enhanced Features

| Variable | Description | Where to Get It | Required For |
|----------|-------------|-----------------|--------------|
| `ELEVENLABS_API_KEY` | ElevenLabs TTS (fallback) | [elevenlabs.io](https://elevenlabs.io/) | Voice generation fallback |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | [cloudinary.com/console](https://cloudinary.com/console) | Avatar uploads |
| `CLOUDINARY_API_KEY` | Cloudinary API key | [cloudinary.com/console](https://cloudinary.com/console) | Avatar uploads |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | [cloudinary.com/console](https://cloudinary.com/console) | Avatar uploads |

### Production Only

| Variable | Description | Where to Get It | Required For |
|----------|-------------|-----------------|--------------|
| `DATABASE_URL` | PostgreSQL connection string | Render provides this automatically | Production database |
| `SECRET_KEY` | Django secret key | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | Production security |
| `RENDER_EXTERNAL_HOSTNAME` | Render hostname | Render provides this automatically | Production deployment |

### Email Configuration (Optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `EMAIL_HOST` | SMTP server | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | Email username | `your_email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Email password/app password | `your_app_password` |
| `DEFAULT_FROM_EMAIL` | From email address | `your_email@gmail.com` |

## 🚀 Quick Start - Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/DrewHouchens13/LanguageLearningPlatform.git
   cd LanguageLearningPlatform
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (see above)
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Test the AI Chatbot**
   - Navigate to http://localhost:8000/help/
   - Click the "AI Assistant" button in bottom-right
   - Ask a question!

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Use `.env` file for local development
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Use environment variables in production (Render)
- ✅ Store secrets in GitHub Secrets for CI/CD
- ✅ Rotate API keys periodically
- ✅ Use different keys for development and production

### ❌ DON'T:
- ❌ **NEVER** commit `.env` file to git
- ❌ **NEVER** hardcode API keys in source code
- ❌ **NEVER** share API keys in Slack/Discord/email
- ❌ **NEVER** commit API keys to GitHub (even in commits you plan to delete)
- ❌ **NEVER** use production keys in development

## 📦 Render Production Configuration

### Current Render Environment Variables

Based on your screenshot, Render is configured with:

```
OPEN_AI_API_KEY=sk-proj-XXXXXXXXXXXXXXXX
CLOUDINARY_API_KEY=***********
CLOUDINARY_API_SECRET=***********
CLOUDINARY_CLOUD_NAME=***********
DATABASE_URL=postgresql://...
DEBUG=***********
ELEVENLABS_API_KEY=***********
PYTHON_VERSION=***********
SECRET_KEY=***********
```

**To add/edit variables in Render:**
1. Go to your Render dashboard
2. Select your web service
3. Click "Environment" tab
4. Click "Add Environment Variable"
5. Enter KEY and VALUE
6. Click "Save Changes"
7. Render will automatically redeploy

## 🔧 GitHub Secrets Configuration

**For CI/CD workflows** (automated tests, code analysis):

1. Go to repository: https://github.com/DrewHouchens13/LanguageLearningPlatform
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add secret:
   - Name: `OPEN_AI_API_KEY`
   - Value: `sk-proj-XXXXXXXXXXXXXXXX`

**Currently configured GitHub Secrets:**
- `OPEN_AI_API_KEY` - For AI chatbot tests in CI/CD

## 🐛 Troubleshooting

### Issue: "Error: The AI assistant is not configured properly"

**Solution:**
1. Check `.env` file exists in project root
2. Verify `OPEN_AI_API_KEY` is set (with underscores)
3. Verify API key is valid: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
4. Restart Django server: `Ctrl+C` then `python manage.py runserver`

### Issue: "Module 'dotenv' has no attribute 'load_dotenv'"

**Solution:**
```bash
pip install python-dotenv
```

### Issue: API key works locally but not in production

**Solution:**
1. Check Render environment variables dashboard
2. Ensure variable name is `OPEN_AI_API_KEY` (exact match)
3. Click "Save Changes" in Render to redeploy
4. Check Render logs for errors: Dashboard → Logs tab

### Issue: Tests fail with "OpenAI API key not found"

**Solution for local testing:**
```bash
# Set temporarily for tests
export OPEN_AI_API_KEY=sk-proj-XXXXXXXXXXXXXXXX  # Linux/Mac
set OPEN_AI_API_KEY=sk-proj-XXXXXXXXXXXXXXXX    # Windows
pytest
```

**Solution for CI/CD:**
- Add `OPEN_AI_API_KEY` to GitHub Secrets (see above)

## 📚 Additional Resources

- **OpenAI Documentation:** https://platform.openai.com/docs
- **Render Environment Variables:** https://render.com/docs/environment-variables
- **GitHub Secrets:** https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **python-dotenv:** https://pypi.org/project/python-dotenv/
- **Django Settings:** https://docs.djangoproject.com/en/5.2/topics/settings/

## 🆘 Getting Help

If you encounter issues:

1. Check this guide first
2. Review error messages in console/logs
3. Check Render logs (for production issues)
4. Ask in team Slack/Discord
5. Create GitHub issue with error details

---

**Last Updated:** 2025-11-19
**Maintainer:** Development Team
