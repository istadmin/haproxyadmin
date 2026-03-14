import os

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'default-insecure-secret-key-change-me'
    
    # Paths (defaults mapped to common Ubuntu/HAProxy directories)
    HAPROXY_CONFIG_PATH = os.environ.get('HAPROXY_CONFIG_PATH', '/etc/haproxy/haproxy.cfg')
    HAPROXY_CONFIG_DIR = os.environ.get('HAPROXY_CONFIG_DIR', '/etc/haproxy/conf.d')  # Optional includes

    # App Data paths
    APP_DATA_DIR = os.environ.get('APP_DATA_DIR', '/opt/haproxy-admin')
    BACKUP_DIR = os.path.join(APP_DATA_DIR, 'backups')
    AUDIT_LOG_PATH = os.path.join(APP_DATA_DIR, 'audit', 'haproxy_admin.log')
    TMP_DIR = os.path.join(APP_DATA_DIR, 'tmp')

    # Ensure app data directories configured exist during app startup
    @classmethod
    def init_app(cls):
        for path in [cls.BACKUP_DIR, os.path.dirname(cls.AUDIT_LOG_PATH), cls.TMP_DIR]:
            os.makedirs(path, exist_ok=True)

    # HAProxy Service commands
    SYSTEMCTL_BIN = os.environ.get('SYSTEMCTL_BIN', '/bin/systemctl')
    HAPROXY_BIN = os.environ.get('HAPROXY_BIN', '/usr/sbin/haproxy')
