# HAProxy Admin Panel

A secure, internal web application to manage an HAProxy instance.
Built with Python Flask, Jinja2, and Bootstrap 5.

![HAProxy Admin Screen 1](images/haproxyadmin1.png)
![HAProxy Admin Screen 2](images/haproxyadmin2.png)
![HAProxy Admin Screen 3](images/haproxyadmin3.png)

**Supported Versions:** Fully tested and supported with **HAProxy 2.8**.

## Core Features
1. **Visual Editor:** A fully UI-driven experience to easily Create, Read, Update, and Delete HAProxy configurations (Global, Defaults, Frontends, Backends, ACLs, and Routing Rules) without touching raw text.
2. **Raw Editor:** A syntax-highlighted code editor (Ace Editor) to make advanced manual modifications to your `haproxy.cfg`.
3. **Safe Validation:** Never break your live site. Automatically runs `haproxy -c` for syntax validation before any config is applied.
4. **Configuration History:** Automatically backups your configurations to disk on every change. 1-click rollback support.
5. **OS-Level Auth:** Zero database required. Authenticates natively against Linux OS credentials via PAM.
6. **Audit Logs:** Full tracking of who changed what, and from which IP address.

## Prerequisites
To deploy this application, your target server must meet the following requirements:
* **OS:** Ubuntu/Debian (or compatible Linux distribution)
* **Web Server:** Nginx (for Reverse Proxy)
* **Application:** HAProxy 2.8+ installed and running
* **Python:** Python 3.8+ with `pip` and `venv`
* **Access:** Root privileges (`sudo`) are required for the initial installation.

---

## 🚀 1-Click Production Installation (Recommended)

The easiest and safest way to deploy this application to a production server is using the included installer script. This fully automates installing dependencies, setting up the Python virtual environment, configuring specific passwordless `sudo` rights for HAProxy commands, and generating a systemd background service.

1. SSH into your HAProxy server.
2. Clone or place this repository on the server.
3. Switch into the directory:
   ```bash
   cd /path/to/haproxyadmin
   ```
4. Run the installer script as root:
   ```bash
   sudo ./install.sh
   ```

**What the installer does:**
* Installs required apt packages (`python3`, `nginx`, `libpam-dev`, etc.).
* Moves the app to `/opt/haproxy-admin`.
* Installs dependencies via `pip` in an isolated virtual environment.
* Configures `/etc/sudoers.d/haproxy-admin` so the web user can validate and reload HAProxy securely *without* needing a password.
* Configures and starts a `systemd` service (`haproxy-admin`) running via `gunicorn`.
* Configures Nginx to proxy traffic to the web application over port 80.

You can now access the admin panel by visiting your server's IP address or Domain Name in your web browser.

---

## Manual Installation (Development / Custom Deployment)

If you prefer to set up the application manually or are running it locally for development, follow these steps:

### 1. Install System Dependencies
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv libpam-dev haproxy nginx
```

### 2. Application Setup
```bash
sudo mkdir -p /opt/haproxy-admin
sudo chown -R myadminuser:myadminuser /opt/haproxy-admin
cd /opt/haproxy-admin

# Clone or copy application files into this directory

# Setup Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Sudoers Configuration (Critical)
The application runs as a standard user but requires elevated privileges to validate and reload HAProxy. Create a file `/etc/sudoers.d/haproxy-admin`:
```bash
sudo visudo -f /etc/sudoers.d/haproxy-admin
```
Add the following rules tailored to your application user (e.g., `myadminuser`):
```text
myadminuser ALL=(ALL) NOPASSWD: /usr/sbin/haproxy -c -f *
myadminuser ALL=(ALL) NOPASSWD: /bin/systemctl reload haproxy
myadminuser ALL=(ALL) NOPASSWD: /bin/systemctl start haproxy
myadminuser ALL=(ALL) NOPASSWD: /bin/systemctl stop haproxy
myadminuser ALL=(ALL) NOPASSWD: /bin/systemctl restart haproxy
myadminuser ALL=(ALL) NOPASSWD: /bin/systemctl status haproxy
myadminuser ALL=(ALL) NOPASSWD: /bin/cp /opt/haproxy-admin/tmp/* /etc/haproxy/haproxy.cfg
```

### 4. Running the Application
**For Development:**
```bash
python3 app.py
```

**For Production (Gunicorn + Systemd):**
Create the Systemd file:
```bash
sudo nano /etc/systemd/system/haproxy-admin.service
```
Paste:
```ini
[Unit]
Description=HAProxy Admin Application
After=network.target

[Service]
User=myadminuser
Group=myadminuser
WorkingDirectory=/opt/haproxy-admin
Environment="PATH=/opt/haproxy-admin/venv/bin"
ExecStart=/opt/haproxy-admin/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```
Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now haproxy-admin
```

## Security & Architecture Notes
* **Authentication:** The application checks credentials against the underlying `/etc/shadow` file via PAM. Any active Linux user on the machine with a password can log in.
* **Privilege Drop:** The web application and web server (Gunicorn) run entirely as unprivileged users. The only commands executing as root are tightly restricted HAProxy validation/reload flags granted explicitly via `/etc/sudoers`.
* **State:** The application uses file-system tracking in the `/data` folder for history and audits. No external database engine is required.

## Application Pages & Navigation
* **Dashboard:** The landing page showing HAProxy status, active nodes, and recent system changes.
* **Visual Editor:** A UI-driven interface to manage HAProxy configurations (Frontends, Backends, ACLs, and Routing Rules) without writing code.
* **Raw Editor:** An Ace-powered code editor with syntax highlighting and line numbers for direct `haproxy.cfg` manipulation.
* **History & Rollback:** View backup configurations automatically saved before every change, with the ability to rollback with 1-click.
* **Audit Log:** Track all configuration changes, identifying which user made them and from what IP address.

## How to Use the Visual Editor
The Visual Editor provides a structured way to modify your HAProxy settings safely:

### 1. Frontends
Manage incoming traffic listeners.
* **Name:** The internal identifier for the frontend (e.g., `web_frontend`).
* **Bind:** The IP and port to listen on (e.g., `*:80` or `192.168.1.10:443`).
* **Default Backend:** The fallback backend to route traffic to if no specific rules match (e.g., `app_backend`).

### 2. Backends & Servers
Manage pools of servers handling the traffic.
* **Name:** The internal identifier for the backend (e.g., `app_backend`).
* **Balance Algorithm:** The load balancing strategy (e.g., `roundrobin`, `leastconn`).
* **Servers:** Add individual servers by defining their **Name** (e.g., `web1`), **IP:Port** (e.g., `10.0.0.1:8080`), and **Options** (e.g., `check` to enable health checks).

### 3. ACLs (Access Control Lists)
Define conditions based on request properties within your Frontends or Backends.
* **ACL Name:** The variable name for the condition (e.g., `is_blog`).
* **Criterion:** What to inspect in the request (e.g., `path_beg` for path beginning, `hdr(host)` for host header).
* **Value:** The value to match against (e.g., `/blog`, `example.com`).

### 4. Routing Rules (Use Backend)
Apply logic to route traffic based on your ACLs.
* **Condition:** The logical condition referencing an ACL (e.g., `if is_blog`).
* **Target Backend:** The backend to send matching traffic to (e.g., `blog_backend`).

## Common HAProxy Scenarios & Configuration Examples
Here are some imaginary configurations and routing scenarios you can build. For more detailed configuration options, refer to the [HAProxy 2.8 Configuration Manual](https://docs.haproxy.org/2.8/configuration.html).

### Scenario 1: Path-Based Routing (Microservices)
Route traffic to different applications based on the URL path.
* **Frontend:** `main_proxy` bound to `*:80`.
* **ACL 1:** Name: `is_api`, Criterion: `path_beg`, Value: `/api`
* **ACL 2:** Name: `is_blog`, Criterion: `path_beg`, Value: `/blog`
* **Rule 1:** Target: `api_backend`, Condition: `if is_api`
* **Rule 2:** Target: `blog_backend`, Condition: `if is_blog`
* **Default Backend:** `web_backend`

### Scenario 2: Host-Based Routing (Virtual Hosts)
Serve multiple domains securely from the same IP address.
* **Frontend:** `public_https` bound to `*:443 ssl crt /etc/ssl/certs/`.
* **ACL 1:** Name: `host_app1`, Criterion: `hdr(host) -i`, Value: `app1.example.com`
* **ACL 2:** Name: `host_app2`, Criterion: `hdr(host) -i`, Value: `app2.example.com`
* **Rule 1:** Target: `app1_backend`, Condition: `if host_app1`
* **Rule 2:** Target: `app2_backend`, Condition: `if host_app2`

### Scenario 3: Security & Rate Limiting (DDoS Protection)
Protect your service by limiting requests per second from a single IP.
* **Backend:** `ratelimit_storage` (used to store IP states).
  * **Option:** `stick-table type ip size 100k expire 30s store http_req_rate(10s)`
* **Frontend:** 
  * Track requests: `http-request track-sc0 src table ratelimit_storage`
  * **ACL:** Name: `is_abuse`, Criterion: `sc_http_req_rate(0)`, Value: `gt 50`
  * Block abusers: `http-request deny deny_status 429` with Condition: `if is_abuse`

*(Note: Advanced security rules using sticky tables and custom directives are best managed via the **Raw Editor**).*

## Raw Configuration Editing Examples
While the Visual Editor covers most standard use cases, the **Raw Editor** allows you to leverage the full power of HAProxy by directly writing configuration blocks. Here are some complete, imaginary configurations you might write directly into `haproxy.cfg`.

### 1. HTTP to HTTPS Redirection
A classic scenario where all incoming HTTP traffic on port 80 is immediately redirected to the secure HTTPS port 443.

```haproxy
frontend catch_all_http
    bind *:80
    mode http
    
    # Redirect all traffic to HTTPS with a 301 Moved Permanently status
    http-request redirect scheme https code 301 if !{ ssl_fc }
```

### 2. Blue/Green Deployment Routing
Route traffic to different application versions based on a specific HTTP header (`X-App-Version`) or a cookie. 

```haproxy
frontend main_gateway
    bind *:443 ssl crt /etc/ssl/certs/cert.pem
    mode http

    # Define ACLs based on a custom header
    acl is_green_version req.hdr(X-App-Version) -i v2

    # Route based on the ACL
    use_backend app_backend_green if is_green_version
    default_backend app_backend_blue

backend app_backend_blue
    mode http
    balance roundrobin
    server blue_srv1 10.0.1.10:8080 check
    server blue_srv2 10.0.1.11:8080 check

backend app_backend_green
    mode http
    balance roundrobin
    server green_srv1 10.0.2.10:8080 check
```

### 3. IP Geo-blocking or Allowlisting
Restrict access to an internal admin area to only specific corporate IP addresses, while allowing all other traffic to proceed normally.

```haproxy
frontend secure_portal
    bind *:443 ssl crt /etc/ssl/certs/portal.pem
    mode http

    # Define a list of allowed corporate IPs 
    # (could also be loaded from a file: -f /etc/haproxy/corp_ips.lst)
    acl is_corporate_ip src 192.168.100.0/24 10.50.0.0/16
    
    # Define an ACL for the admin path
    acl is_admin_path path_beg /admin

    # Deny access to the admin path if not from a corporate IP
    http-request deny if is_admin_path !is_corporate_ip

    default_backend main_portal_nodes

backend main_portal_nodes
    mode http
    server node1 10.0.5.100:80 check
```

### 4. WebSocket Proxying
HAProxy natively supports WebSocket traffic. Here is a configuration routing standard web traffic to a frontend app cluster, and WebSocket traffic to a real-time messaging backend.

```haproxy
frontend realtime_proxy
    bind *:443 ssl crt /etc/ssl/certs/app.pem
    mode http

    # Connection upgrades
    acl is_websocket hdr(Upgrade) -i WebSocket
    acl is_websocket_path path_beg /socket.io /ws

    # Check both an upgrade header or the specific URL path
    use_backend websocket_servers if is_websocket or is_websocket_path
    default_backend static_web_servers

backend static_web_servers
    mode http
    server web1 10.0.0.50:80 check

backend websocket_servers
    mode http
    # WebSockets usually require longer timeouts and tunnel modes
    timeout tunnel 1h
    server ws1 10.0.0.60:3000 check
```
