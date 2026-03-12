#!/bin/bash
# HAProxy Admin Full Production Installer Script
# Must be run with sudo

set -e

APP_OWNER="istadmin"
APP_DIR="/opt/haproxy-admin"
SRC_DIR=$(pwd)
DOMAIN="localhost" # Can be changed to actual domain/IP via args or post-install

if [ "$EUID" -ne 0 ]; then
  echo "Please run this installer as root (using sudo)"
  exit 1
fi

echo "========================================="
echo " Installing HAProxy Admin MVP Panel..."
echo "========================================="

echo "1. Installing system dependencies (Python, Nginx)..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv libpam-dev haproxy nginx

echo "2. Creating application directory..."
mkdir -p ${APP_DIR}
# Copy current source to the destination
cp -r ${SRC_DIR}/* ${APP_DIR}/
# Ensure correct ownership
chown -R ${APP_OWNER}:${APP_OWNER} ${APP_DIR}

echo "3. Creating Python Virtual Environment and installing packages..."
# Run as the app owner to ensure venv permissions are correct
sudo -u ${APP_OWNER} bash -c "cd ${APP_DIR} && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pip install gunicorn"

echo "4. Configuring passwordless sudo for the application user..."
SUDOERS_FILE="/etc/sudoers.d/haproxy-admin"
cat <<EOF > ${SUDOERS_FILE}
${APP_OWNER} ALL=(ALL) NOPASSWD: /usr/sbin/haproxy -c -f *
${APP_OWNER} ALL=(ALL) NOPASSWD: /bin/systemctl reload haproxy
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
Environment="PATH=${APP_DIR}/venv/bin"
# Using 4 workers, binding to localhost port 5000
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable haproxy-admin
systemctl restart haproxy-admin

echo "6. Configuring Nginx Reverse Proxy..."
NGINX_CONF="/etc/nginx/sites-available/haproxy-admin"
cat <<EOF > ${NGINX_CONF}
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Link and enable
ln -sf ${NGINX_CONF} /etc/nginx/sites-enabled/
# Remove default nginx page if it exists
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

echo "========================================="
echo " Installation Complete!"
echo "========================================="
echo "The application is now running in the background."
echo "You can access it at: http://${DOMAIN} or your server IP."
echo "Your application code now lives at: ${APP_DIR}"
