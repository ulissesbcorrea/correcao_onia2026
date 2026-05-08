#!/bin/bash
# Rollback script for ONIA deployment
# Usage: bash deploy/rollback.sh

BACKUP_DIR="/home/ubuntu/backups/onia_$(date +%Y%m%d_%H%M%S)"

echo "=== ONIA Rollback ==="
echo "This will stop the service and restore configurations."
echo "Backups are stored in: $BACKUP_DIR"

# Stop service
sudo systemctl stop onia 2>/dev/null || true

# Remove nginx config
sudo rm -f /etc/nginx/sites-enabled/onia
sudo systemctl reload nginx 2>/dev/null || true

# Remove systemd service
sudo systemctl disable onia 2>/dev/null || true
sudo rm -f /etc/systemd/system/onia.service
sudo systemctl daemon-reload

echo "ONIA service stopped and removed."
echo "Database preserved at: /home/ubuntu/servers/correcao_onia2026/onia.db"
echo "To completely remove: rm -rf /home/ubuntu/servers/correcao_onia2026"
