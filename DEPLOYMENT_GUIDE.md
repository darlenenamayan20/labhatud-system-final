# Django Deployment Guide - Hostinger VPS

## Step 1: Choose OS
**Recommended:** Ubuntu 22.04 LTS (most popular and well-documented)

## Step 2: Connect to VPS via SSH
```bash
ssh root@your-vps-ip
```

## Step 3: Update System
```bash
apt update && apt upgrade -y
```

## Step 4: Install Required Software
```bash
# Install Python and pip
apt install python3 python3-pip python3-venv -y

# Install Nginx (web server)
apt install nginx -y

# Install Supervisor (process manager)
apt install supervisor -y

# Install Git
apt install git -y
```

## Step 5: Create Application User
```bash
adduser labhatud
usermod -aG sudo labhatud
su - labhatud
```

## Step 6: Clone Your Project
```bash
cd /home/labhatud
git clone <your-repo-url> labhatud_system
cd labhatud_system
```

## Step 7: Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
```

## Step 8: Configure Environment Variables
```bash
nano .env
```

Add:
```env
DJANGO_SECRET_KEY=your-production-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,your-vps-ip

PAYMONGO_SECRET_KEY=sk_test_YOUR_KEY
PAYMONGO_PUBLIC_KEY=pk_test_YOUR_KEY
PAYMONGO_WEBHOOK_SECRET=whsk_YOUR_SECRET

# Security settings for production
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
```

## Step 9: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

## Step 10: Run Migrations
```bash
python manage.py migrate
```

## Step 11: Create Superuser
```bash
python manage.py createsuperuser
```

## Step 12: Configure Gunicorn
Create `/etc/supervisor/conf.d/labhatud.conf`:
```bash
sudo nano /etc/supervisor/conf.d/labhatud.conf
```

Add:
```ini
[program:labhatud]
directory=/home/labhatud/labhatud_system
command=/home/labhatud/labhatud_system/venv/bin/gunicorn --workers 3 --bind unix:/home/labhatud/labhatud_system/labhatud.sock labhatud_system.wsgi:application
user=labhatud
autostart=true
autorestart=true
stderr_logfile=/var/log/labhatud.err.log
stdout_logfile=/var/log/labhatud.out.log
```

Update supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start labhatud
```

## Step 13: Configure Nginx
Create `/etc/nginx/sites-available/labhatud`:
```bash
sudo nano /etc/nginx/sites-available/labhatud
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com your-vps-ip;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /home/labhatud/labhatud_system/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/labhatud/labhatud_system/labhatud.sock;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/labhatud /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 14: Configure Firewall
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

## Step 15: Set Up SSL (Optional but Recommended)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## Step 16: Create Static Files Directory
```bash
mkdir -p /home/labhatud/labhatud_system/staticfiles
```

Update `settings.py`:
```python
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

## Useful Commands

### Check Application Status
```bash
sudo supervisorctl status labhatud
```

### Restart Application
```bash
sudo supervisorctl restart labhatud
```

### View Logs
```bash
sudo tail -f /var/log/labhatud.err.log
sudo tail -f /var/log/labhatud.out.log
```

### Update Code
```bash
cd /home/labhatud/labhatud_system
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo supervisorctl restart labhatud
```

## Troubleshooting

### 502 Bad Gateway
- Check if gunicorn is running: `sudo supervisorctl status labhatud`
- Check logs: `sudo tail -f /var/log/labhatud.err.log`

### Static files not loading
- Run: `python manage.py collectstatic --noinput`
- Check nginx config for correct static path

### Database errors
- Check if migrations ran: `python manage.py showmigrations`
- Run migrations: `python manage.py migrate`

## Security Checklist
- [ ] Set DEBUG=False in production
- [ ] Use strong SECRET_KEY
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up SSL certificate
- [ ] Enable firewall
- [ ] Regular backups of database
- [ ] Keep system updated
- [ ] Use environment variables for secrets

## Performance Tips
- Use PostgreSQL instead of SQLite for production
- Enable caching (Redis/Memcached)
- Use CDN for static files
- Monitor with tools like New Relic or Sentry
