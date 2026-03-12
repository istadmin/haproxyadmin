import os
import json
import logging
from datetime import datetime, timezone

class AuditService:
    def __init__(self):
        self.log_path = None
        self.logger = None

    def init_app(self, app):
        self.log_path = app.config.get('AUDIT_LOG_PATH', '/opt/haproxy-admin/audit/haproxy_admin.log')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
        # Setup standard Python logger to write to the audit file
        self.logger = logging.getLogger('haproxy_audit')
        self.logger.setLevel(logging.INFO)
        # Prevent logging from propagating to the root logger
        self.logger.propagate = False
        
        # Remove existing handlers to avoid duplicates on reloads
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
            
        handler = logging.FileHandler(self.log_path)
        # We handle formatting ourselves
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def log(self, action, username, result, ip=None, **context):
        """
        Log an event to the audit trail.
        Format: timestamp username ip action result [context key=value]
        """
        timestamp = datetime.now(timezone.utc).astimezone().isoformat()
        
        # Build base string matching required format
        # e.g. 2026-03-12T10:19:10+04:00 user=admin ip=10.0.0.5 action=apply_config result=success file=/etc/...
        log_parts = [
            timestamp,
            f"user={username}",
            f"ip={ip or 'unknown'}",
            f"action={action}",
            f"result={result}"
        ]
        
        # Add additional context key-value pairs
        for k, v in context.items():
            if v is not None:
                # Basic escaping of values containing spaces
                val_str = str(v)
                if ' ' in val_str and not (val_str.startswith('"') and val_str.endswith('"')):
                    val_str = f'"{val_str}"'
                log_parts.append(f"{k}={val_str}")
                
        log_line = " ".join(log_parts)
        
        if self.logger:
            self.logger.info(log_line)
        else:
            # Fallback if init_app wasn't called properly
            try:
                with open(self.log_path or '/tmp/haproxy_admin.log', 'a') as f:
                    f.write(log_line + '\n')
            except Exception as e:
                print(f"Failed to write audit log: {e}")

    def get_recent_logs(self, limit=100):
        """
        Tail the audit log file for recent entries to display in UI.
        """
        if not self.log_path or not os.path.exists(self.log_path):
            return []
            
        try:
            # Simple tail implementation by reading lines and keeping last 'limit'
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            # Return reversed so newest is first
            return [line.strip() for line in lines[-limit:]][::-1]
        except Exception as e:
            return [f"Error reading audit log: {e}"]

# Create a singleton instance to be imported and used throughout the application
audit = AuditService()
