# Setup Complete ✓

Your Django Labhatud System is now configured and ready to run!

## What Was Configured

### 1. Environment Variables (.env)
- Created `.env` file with Django configuration
- Set DEBUG=True for development
- Configured allowed hosts for localhost
- Added placeholder PayMongo API keys (needs your actual keys)

### 2. Virtual Environment
- Created Python virtual environment in `venv/` folder
- Installed all dependencies from requirements.txt:
  - Django 6.0.3
  - python-dotenv 1.2.2
  - requests 2.34.2
  - Pillow 12.2.0
  - And all other dependencies

### 3. Database
- Created SQLite database (`db.sqlite3`)
- Applied all migrations for:
  - accounts app
  - payments app
  - Django admin
  - Authentication system

## How to Run

### Option 1: Using the batch script (easiest)
```bash
start_server.bat
```

### Option 2: Manual commands
```bash
# Activate virtual environment
venv\Scripts\activate

# Run the development server
python manage.py runserver
```

The server will start at: **http://127.0.0.1:8000/**

## Next Steps

### 1. Create a Superuser (Admin Account)
```bash
venv\Scripts\activate
python manage.py createsuperuser
```

### 2. Configure PayMongo (for payment processing)
Edit `.env` file and replace these with your actual PayMongo keys:
```
PAYMONGO_SECRET_KEY=sk_test_your_actual_secret_key
PAYMONGO_PUBLIC_KEY=pk_test_your_actual_public_key
PAYMONGO_WEBHOOK_SECRET=whsec_your_actual_webhook_secret
```

Get your keys from: https://dashboard.paymongo.com/developers

### 3. Access the Application
- **Main site**: http://127.0.0.1:8000/
- **Admin panel**: http://127.0.0.1:8000/admin/
- **Authentication**: http://127.0.0.1:8000/auth/

## User Roles
The system supports 4 user types:
1. **Student** - Place laundry orders
2. **Rider** - Pick up and deliver orders
3. **Shop Owner** - Manage laundry shop
4. **Admin** - System administration

## Admin Registration Keys
Configured in settings.py:
- Admin Register Key: `LABHATUD-ADMIN-2025`
- Admin Access Key: `LABHATUD-ADMIN-SECRET-2025`

## Troubleshooting

### If you get "Module not found" errors:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### If migrations fail:
```bash
python manage.py migrate --run-syncdb
```

### To reset the database:
```bash
del db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

## Project Structure
```
labhatud_system/
├── accounts/          # User management, orders, shops
├── payments/          # PayMongo integration
├── templates/         # HTML templates
├── static/           # CSS, JS, images
├── labhatud_system/  # Django settings
├── venv/             # Virtual environment
├── db.sqlite3        # SQLite database
├── .env              # Environment variables
└── manage.py         # Django management script
```

## Development Notes
- SQLite database is used for development
- Debug mode is enabled
- Static files are served from `static/` directory
- Templates are in `templates/` directory
- Custom user model is in `accounts.User`
