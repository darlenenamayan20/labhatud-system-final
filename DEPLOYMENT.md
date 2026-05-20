# Deployment Guide - Labhatud System

## Pre-Deployment Checklist

1. **Environment Variables**
   - Copy `.env.example` to `.env`
   - Generate new Django secret key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - Add your PayMongo API keys
   - Set `DJANGO_DEBUG=False`
   - Configure `DJANGO_ALLOWED_HOSTS` with your domain

2. **Database Setup**
   - For production, use PostgreSQL
   - Set `DATABASE_URL` in environment variables
   - Run migrations: `python manage.py migrate`
   - Create superuser: `python manage.py createsuperuser`

3. **Static Files**
   - Collect static files: `python manage.py collectstatic --noinput`

## Deployment Options

### Option 1: Heroku

```bash
# Install Heroku CLI and login
heroku login

# Create new app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set DJANGO_SECRET_KEY="your-secret-key"
heroku config:set DJANGO_DEBUG=False
heroku config:set PAYMONGO_SECRET_KEY="your-key"
heroku config:set PAYMONGO_PUBLIC_KEY="your-key"
heroku config:set PAYMONGO_WEBHOOK_SECRET="your-secret"

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Option 2: Railway

1. Connect your GitHub repository
2. Add environment variables in Railway dashboard
3. Railway auto-detects Django and deploys

### Option 3: Render

1. Create new Web Service
2. Connect repository
3. Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Start Command: `gunicorn labhatud_system.wsgi`
5. Add environment variables
6. Add PostgreSQL database

### Option 4: PythonAnywhere

1. Upload code via Git or Files
2. Create virtual environment: `mkvirtualenv --python=/usr/bin/python3.12 labhatud`
3. Install requirements: `pip install -r requirements.txt`
4. Configure WSGI file
5. Set environment variables in WSGI file
6. Run migrations in Bash console
7. Configure static files mapping

## Post-Deployment

1. Test all functionality
2. Set up SSL certificate (most platforms provide free SSL)
3. Configure PayMongo webhook URL
4. Monitor logs for errors
5. Set up database backups

## Security Notes

- Never commit `.env` file
- Use strong secret keys
- Enable HTTPS in production
- Regularly update dependencies
- Monitor for security vulnerabilities
