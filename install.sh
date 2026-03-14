#!/bin/bash
# HAProxy Admin Full Production Installer Script
# Must be run with sudo

set -e

# --- Default Configuration ---
DEFAULT_APP_DIR="/opt/haproxy-admin"
DOMAIN="localhost"
APP_OWNER=${SUDO_USER:-$(whoami)}

# --- Help Function ---
show_help() {
    echo "Usage: sudo ./install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message and exit"
    echo ""
    echo "Environment Variables (Overrides):"
    echo "  APP_DIR       Target installation directory (Default: $DEFAULT_APP_DIR)"
    echo ""
    echo "This script installs HAProxy Admin with Python, Gunicorn, and Systemd."
    exit 0
}

# --- Arg Parsing ---
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
fi

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run this installer as root (using sudo)"
  exit 1
fi

echo "========================================="
echo " Installing HAProxy Admin MVP Panel..."
echo "========================================="

# --- Input Handling ---
echo "App Owner detected as: $APP_OWNER"

read -p "Enter installation directory [$DEFAULT_APP_DIR]: " APP_DIR
APP_DIR=${APP_DIR:-$DEFAULT_APP_DIR}
echo "Using Installation Directory: $APP_DIR"

echo "Domain/IP set to: $DOMAIN"

echo "1. Installing system dependencies (Python , Gunicorn)..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv libpam-dev 

echo "2. Creating application directory and staging area..."
mkdir -p ${APP_DIR}/tmp
# Copy current source to the destination
#cp -r $(pwd)/* ${APP_DIR}/

rsync -a \
  --exclude 'venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  ./ "${APP_DIR}/"



# Ensure correct ownership
chown -R ${APP_OWNER}:${APP_OWNER} ${APP_DIR}
chmod -R 755 ${APP_DIR}
chmod 777 ${APP_DIR}/tmp  # Allow app to write staging configs

echo "3. Creating Python Virtual Environment and installing packages..."
# Run as the app owner to ensure venv permissions are correct
sudo -u ${APP_OWNER} bash -c "cd ${APP_DIR} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pip install gunicorn"

echo "4. Configuring passwordless sudo for the application user..."
SUDOERS_FILE="/etc/sudoers.d/haproxy-admin"
cat <<EOF > ${SUDOERS_FILE}
${APP_OWNER} ALL=(ALL) NOPASSWD: /usr/sbin/haproxy -c -f *
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl reload haproxy
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl start haproxy
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl stop haproxy
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl restart haproxy
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl status haproxy
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/cp ${APP_DIR}/tmp/* /etc/haproxy/haproxy.cfg
EOF
chmod 0440 ${SUDOERS_FILE}

echo "5. Installing and enabling Systemd Service..."
SERVICE_FILE="/etc/systemd/system/haproxy-admin.service"
cat <<EOF > ${SERVICE_FILE}
[Unit]
Description=HAProxy Admin Application
After=network.target

[Service]
User=${APP_OWNER}
Group=${APP_OWNER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${APP_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Using 2 workers, binding to all interfaces on port 8080
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8080 app:create_app()
Restart=always
RestartSec=3


[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable haproxy-admin
systemctl restart haproxy-admin



echo
echo "========================================="
echo " Installation Complete!"
echo "========================================="
echo "Service: haproxy-admin"
echo "App directory: ${APP_DIR}"
echo "Gunicorn bind: 127.0.0.1:8080"
echo
echo "Recommended next step:"
echo "Proxy this app through HAProxy on 80/443 instead of exposing 8080 publicly."
echo
echo "Check service:"
echo "  systemctl status haproxy-admin"
echo
echo "Local test:"
echo "You can access it at: http://${DOMAIN}:8080 or http://<server_ip>:8080"
echo "  curl http://0.0.0.0:8080"
