# HAProxy Admin Installation & Management Guide

This guide provides instructions for installing, managing, and uninstalling the HAProxy Admin application.

## 1. One-Step Installation (Recommended)

The easiest way to install HAProxy Admin is using the `install.sh` script.

### Prerequisites
- Ubuntu/Debian-based system
- `sudo` privileges

### Installation Steps
1. Navigate to the project directory.
2. Run the installer:
   ```bash
   sudo ./install.sh
   ```
3. Follow the prompts to specify the installation directory (default is `/opt/haproxy-admin`).

The script will:
- Install system dependencies (`python3`, `pip`, `venv`, `libpam-dev`).
- Create a virtual environment and install Python packages.
- Configure `sudoers` for HAProxy management.
- Set up and start the `haproxy-admin` systemd service.

---

## 2. Accessing the Application

Once installed and the service is started, you can access the HAProxy Admin interface via your web browser.

- **Default URL:** `http://<your_server_ip>:8080`
- **Authentication:** The application uses **OS-level login**. Use your existing Linux system username and password to log in.

---

## 3. Service Management

Once installed, use the following commands to manage the HAProxy Admin service:

| Action | Command |
| :--- | :--- |
| **Start** | `sudo systemctl start haproxy-admin` |
| **Stop** | `sudo systemctl stop haproxy-admin` |
| **Restart** | `sudo systemctl restart haproxy-admin` |
| **Status** | `sudo systemctl status haproxy-admin` |
| **Enable (Auto-start)** | `sudo systemctl enable haproxy-admin` |
| **Disable** | `sudo systemctl disable haproxy-admin` |

---

## 4. Manual Installation

If you prefer to set up the application manually, follow these steps:

### Step 1: Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv libpam-dev
```

### Step 2: Prepare Application Directory
```bash
# Choose your installation path, e.g., /opt/haproxy-admin
sudo mkdir -p /opt/haproxy-admin
sudo chown -R $USER:$USER /opt/haproxy-admin
```

### Step 3: Copy Files
Copy the project files to the installation directory, excluding environment and git files:
```bash
rsync -a --exclude 'venv' --exclude '__pycache__' --exclude '.git' ./ /opt/haproxy-admin/
```

### Step 4: Setup Virtual Environment
```bash
cd /opt/haproxy-admin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Step 5: Configure Sudoers
Create a new sudoers file to allow the app to manage HAProxy without a password:
`sudo nano /etc/sudoers.d/haproxy-admin`

Add the following content (replace `<YOUR_USERNAME>` with the user running the app):
```text
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /usr/sbin/haproxy -c -f *
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/systemctl reload haproxy
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/systemctl start haproxy
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/systemctl stop haproxy
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/systemctl restart haproxy
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/systemctl status haproxy
<YOUR_USERNAME> ALL=(ALL) NOPASSWD: /bin/cp /opt/haproxy-admin/tmp/* /etc/haproxy/haproxy.cfg
```
`sudo chmod 0440 /etc/sudoers.d/haproxy-admin`

### Step 6: Create Systemd Service
Create the service file:
`sudo nano /etc/systemd/system/haproxy-admin.service`

Add the following content:
```ini
[Unit]
Description=HAProxy Admin Application
After=network.target

[Service]
User=<YOUR_USERNAME>
Group=<YOUR_USERNAME>
WorkingDirectory=/opt/haproxy-admin
Environment="PATH=/opt/haproxy-admin/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/haproxy-admin/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:8080 app:create_app()
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Step 7: Finalize
```bash
sudo systemctl daemon-reload
sudo systemctl enable haproxy-admin
sudo systemctl start haproxy-admin
```

---

## 5. One-Step Uninstallation

To completely remove the application and its configurations:
```bash
sudo ./uninstall.sh
```
Follow the prompts to confirm deletion of the application directory.

---

## 6. Manual Uninstallation & Cleanup

To manually remove HAProxy Admin from your system:

### 1. Stop and Disable Service
```bash
sudo systemctl stop haproxy-admin
sudo systemctl disable haproxy-admin
```

### 2. Remove System Files
```bash
sudo rm /etc/systemd/system/haproxy-admin.service
sudo rm /etc/sudoers.d/haproxy-admin
```

### 3. Cleanup Systemd
```bash
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

### 4. Remove Application Files
```bash
sudo rm -rf /opt/haproxy-admin
```
