# Release Notes - HAProxy Admin Panel v1.0

We are excited to announce the official release of HAProxy Admin Panel v1.0. This release provides a robust, secure, and user-friendly interface for managing HAProxy 2.8 instances directly from your web browser.

## 🚀 Key Features

### 1. Visual Configuration Editor
Manage your HAProxy configuration without touching a single line of code!
- Create, Update, and Delete Frontends and Backends.
- Define Servers with health check options.
- Manage ACLs and "Use Backend" routing rules with an intuitive UI.

### 2. Advanced Raw Editor
For power users, we've integrated the **Ace Code Editor**.
- Full syntax highlighting for HAProxy configuration files.
- Line numbers and advanced text selection.
- Real-time syntax validation.

### 3. Integrated Security & Compliance
- **OS-Level Authentication:** Securely login using your existing Linux system credentials via PAM.
- **Strict Validation:** Every change is automatically validated using `haproxy -c` before being applied to prevent downtime.
- **Audit Logging:** Comprehensive tracking of configuration changes, including timestamps, user IDs, and source IP addresses.
- **Privilege Drop:** The application runs as an unprivileged user, calling only necessary HAProxy commands via restricted sudo access.

### 4. Safety & Recovery
- **Automatic Backups:** Every configuration change triggers an automatic backup.
- **1-Click Rollback:** Quickly revert to any previous configuration state directly from the History page.

### 5. Streamlined Operations
- Execute HAProxy commands (Start, Stop, Restart, Reload, Status) directly from the **Operations** page.
- Real-time feedback on command execution results.

## 🛠 Installation & Setup

Installation is simplified with our one-step installer script. Refer to the [README.md](README.md) for quick start instructions or [readme_install.md](readme_install.md) for a deep dive into manual setup and management.

---

*Thank you for using HAProxy Admin Panel! For support or feature requests, please contact the development team.*
