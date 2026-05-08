#!/bin/bash
# ONIA Fraud Detection Dashboard - Install Script
# Run on Ubuntu 22.04+

set -e

APP_DIR="/home/ubuntu/servers/correcao_onia2026"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="onia"

echo "=== ONIA Dashboard Install ==="

# Install system dependencies
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip nginx

# Create venv and install Python deps
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"
pip install gunicorn

# Create uploads directory
mkdir -p "$APP_DIR/uploads"

# Copy .env if not exists
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  Edit $APP_DIR/.env with secure keys!"
fi

# Initialize database and create admin
cd "$APP_DIR"
python3 -c "
import bcrypt
from app import create_app
from app.extensions import db
from app.models import Evaluator, ApprovalCounter
app = create_app()
with app.app_context():
    db.create_all()
    if not Evaluator.query.filter_by(email='admin@onia.com').first():
        pw = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        db.session.add(Evaluator(name='Admin', email='admin@onia.com', password_hash=pw, role='admin'))
        db.session.commit()
        print('Admin user created: admin@onia.com / admin123')
    if not db.session.get(ApprovalCounter, 1):
        db.session.add(ApprovalCounter(id=1, count=0, goal=200))
        db.session.commit()
"

# Install systemd service
sudo cp "$APP_DIR/deploy/onia.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Install nginx config
sudo cp "$APP_DIR/deploy/onia-nginx.conf" /etc/nginx/sites-available/onia
sudo ln -sf /etc/nginx/sites-available/onia /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== Installation Complete ==="
echo "Start service: sudo systemctl start $SERVICE_NAME"
echo "Admin: admin@onia.com / admin123"
echo "Access: http://absapt.tk"
