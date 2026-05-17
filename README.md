# Labhatud System

A Django-based laundry management system with payment integration (PayMongo).

## Features
- User authentication (Student, Rider, Shop Owner, Admin)
- Laundry shop management
- Order tracking
- Payment processing via PayMongo
- Notifications system

## Installation

1. Clone the repository
```bash
git clone <your-repo-url>
cd labhatud_system
```

2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file with:
```
PAYMONGO_SECRET_KEY=your_secret_key
PAYMONGO_PUBLIC_KEY=your_public_key
PAYMONGO_WEBHOOK_SECRET=your_webhook_secret
DJANGO_SECRET_KEY=your_django_secret_key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

5. Run migrations
```bash
python manage.py migrate
```

6. Run the development server
```bash
python manage.py runserver
```

## Deployment

See deployment guide for PythonAnywhere or other hosting platforms.

## Tech Stack
- Django 6.0.3
- SQLite (development)
- PayMongo API
- Python 3.10+
