import subprocess
from flask import current_app

class HAProxyService:
    @staticmethod
    def _run_command(cmd_list):
        """Helper to run a command with sudo and return (success, output, error)."""
        try:
            # We prefix all system commands with sudo since the webapp won't run as root.
            # -n flag ensures it immediately fails instead of hanging waiting for a password prompt.
            full_cmd = ['sudo', '-n'] + cmd_list
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            success = result.returncode == 0
            # Combine stdout and stderr for display
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            # haproxy -c often writes to stderr even on success
            combined_output = f"{output}\n{error}".strip()
            return success, combined_output
            
        except Exception as e:
            return False, f"Exception executing command: {str(e)}"

    @classmethod
    def validate_config(cls, config_path=None):
        """
        Run HAProxy validation command against a specific config file.
        `haproxy -c -f /path/to/config`
        """
        # Default to main config if none provided, though usually we validate temp files
        path_to_check = config_path or current_app.config['HAPROXY_CONFIG_PATH']
        haproxy_bin = current_app.config.get('HAPROXY_BIN', '/usr/sbin/haproxy')
        
        cmd = [haproxy_bin, '-c', '-f', path_to_check]
        return cls._run_command(cmd)

    @classmethod
    def reload_service(cls):
        """
        Reload the HAProxy service via systemctl.
        """
        service_name = current_app.config.get('SYSTEMCTL_SERVICE', 'haproxy')
        systemctl = current_app.config.get('SYSTEMCTL_BIN', '/bin/systemctl')
        cmd = [systemctl, 'reload', service_name]
        return cls._run_command(cmd)

    @classmethod
    def start_service(cls):
        """
        Start the HAProxy service via systemctl.
        """
        service_name = current_app.config.get('SYSTEMCTL_SERVICE', 'haproxy')
        systemctl = current_app.config.get('SYSTEMCTL_BIN', '/bin/systemctl')
        cmd = [systemctl, 'start', service_name]
        return cls._run_command(cmd)

    @classmethod
    def stop_service(cls):
        """
        Stop the HAProxy service via systemctl.
        """
        service_name = current_app.config.get('SYSTEMCTL_SERVICE', 'haproxy')
        systemctl = current_app.config.get('SYSTEMCTL_BIN', '/bin/systemctl')
        cmd = [systemctl, 'stop', service_name]
        return cls._run_command(cmd)

    @classmethod
    def restart_service(cls):
        """
        Restart the HAProxy service via systemctl.
        """
        service_name = current_app.config.get('SYSTEMCTL_SERVICE', 'haproxy')
        systemctl = current_app.config.get('SYSTEMCTL_BIN', '/bin/systemctl')
        cmd = [systemctl, 'restart', service_name]
        return cls._run_command(cmd)

    @classmethod
    def get_status(cls):
        """
        Get the current systemctl status of the HAProxy service.
        """
        service_name = current_app.config.get('SYSTEMCTL_SERVICE', 'haproxy')
        systemctl = current_app.config.get('SYSTEMCTL_BIN', '/bin/systemctl')
        cmd = [systemctl, 'status', service_name]
        # systemctl status returns non-zero if stopped, so we just want the output
        _, output = cls._run_command(cmd)
        
        # Simple parsing logic to see if it's active
        is_active = 'Active: active (running)' in output
        return {
            'is_active': is_active,
            'raw_output': output
        }

    @classmethod
    def parse_full_config(cls, config_text: str) -> dict:
        """
        Parses a full HAProxy config file into a nested dictionary, preserving unrecognized lines.
        """
        config = {
            'global': [],
            'defaults': [],
            'frontends': {},
            'backends': {}
        }
        
        current_section = None
        current_name = None
        
        lines = config_text.split('\n')
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            parts = stripped.split()
            keyword = parts[0]
            
            # Determine section boundaries
            if keyword == 'global':
                current_section = 'global'
                current_name = None
                continue
            elif keyword == 'defaults':
                current_section = 'defaults'
                current_name = None
                continue
            elif keyword == 'frontend':
                current_section = 'frontend'
                current_name = parts[1] if len(parts) > 1 else 'unknown'
                config['frontends'][current_name] = {
                    'bind': '', 'mode': '', 'default_backend': '',
                    'acls': [], 'use_backends': [], 'raw_lines': [],
                    'ssl_cert': ''
                }
                continue
            elif keyword == 'backend':
                current_section = 'backend'
                current_name = parts[1] if len(parts) > 1 else 'unknown'
                config['backends'][current_name] = {
                    'mode': '', 'balance': '', 'servers': [], 'raw_lines': []
                }
                continue
                
            # Parse inside sections
            if current_section == 'global':
                config['global'].append(stripped)
            elif current_section == 'defaults':
                config['defaults'].append(stripped)
            elif current_section == 'frontend' and current_name:
                fe = config['frontends'][current_name]
                if keyword == 'bind':
                    bind_str = " ".join(parts[1:])
                    # extract ssl cert if present
                    if 'ssl crt ' in bind_str:
                        fe['ssl_cert'] = bind_str.split('ssl crt ')[1].split()[0]
                        fe['bind'] = bind_str.split(' ssl crt ')[0]
                    else:
                        fe['bind'] = bind_str
                elif keyword == 'mode':
                    fe['mode'] = parts[1] if len(parts) > 1 else ''
                elif keyword == 'default_backend':
                    fe['default_backend'] = parts[1] if len(parts) > 1 else ''
                elif keyword == 'acl':
                    name = parts[1] if len(parts) > 1 else ''
                    cond = " ".join(parts[2:]) if len(parts) > 2 else ''
                    fe['acls'].append({'name': name, 'condition': cond, 'raw': stripped})
                elif keyword == 'use_backend':
                    be = parts[1] if len(parts) > 1 else ''
                    cond = " ".join(parts[2:]) if len(parts) > 2 else ''
                    fe['use_backends'].append({'backend': be, 'condition': cond, 'raw': stripped})
                else:
                    fe['raw_lines'].append(stripped)
                    
            elif current_section == 'backend' and current_name:
                be = config['backends'][current_name]
                if keyword == 'mode':
                    be['mode'] = parts[1] if len(parts) > 1 else ''
                elif keyword == 'balance':
                    be['balance'] = parts[1] if len(parts) > 1 else ''
                elif keyword == 'server':
                    srv_name = parts[1] if len(parts) > 1 else ''
                    srv_addr = parts[2] if len(parts) > 2 else ''
                    srv_opts = " ".join(parts[3:]) if len(parts) > 3 else ''
                    be['servers'].append({
                        'name': srv_name,
                        'address': srv_addr,
                        'options': srv_opts,
                        'raw': stripped
                    })
                else:
                    be['raw_lines'].append(stripped)
                    
        return config

    @classmethod
    def generate_full_config(cls, config_json: dict) -> str:
        """
        Takes a fully parsed JSON representation of the config and safely reconstructs it.
        """
        lines = []
        
        # 1. Global
        if config_json.get('global'):
            lines.append("global")
            for line in config_json['global']:
                lines.append(f"    {line}")
            lines.append("")
            
        # 2. Defaults
        if config_json.get('defaults'):
            lines.append("defaults")
            for line in config_json['defaults']:
                lines.append(f"    {line}")
            lines.append("")
            
        # 3. Frontends
        for fe_name, fe_data in config_json.get('frontends', {}).items():
            lines.append(f"frontend {fe_name}")
            if fe_data.get('bind'):
                bind_str = fe_data['bind']
                if fe_data.get('ssl_cert'):
                    bind_str += f" ssl crt {fe_data['ssl_cert']}"
                lines.append(f"    bind {bind_str}")
            if fe_data.get('mode'):
                lines.append(f"    mode {fe_data['mode']}")
                
            # Add acls
            for acl in fe_data.get('acls', []):
                if isinstance(acl, str):
                    lines.append(f"    {acl}")
                else:
                    raw_acl = acl.get('raw', '')
                    if raw_acl:
                        lines.append(f"    {raw_acl}")
                    else:
                        lines.append(f"    acl {acl.get('name', '')} {acl.get('condition', '')}")
                
            # Add use_backends
            for ub in fe_data.get('use_backends', []):
                if isinstance(ub, str):
                    lines.append(f"    {ub}")
                else:
                    raw_ub = ub.get('raw', '')
                    if raw_ub:
                        lines.append(f"    {raw_ub}")
                    else:
                        lines.append(f"    use_backend {ub.get('backend', '')} {ub.get('condition', '')}")
                
            if fe_data.get('default_backend'):
                lines.append(f"    default_backend {fe_data['default_backend']}")
                
            # Add preserved raw lines (custom headers, stick tables etc)
            for raw in fe_data.get('raw_lines', []):
                lines.append(f"    {raw}")
                
            lines.append("")
            
        # 4. Backends
        for be_name, be_data in config_json.get('backends', {}).items():
            lines.append(f"backend {be_name}")
            if be_data.get('mode'):
                lines.append(f"    mode {be_data['mode']}")
            if be_data.get('balance'):
                lines.append(f"    balance {be_data['balance']}")
                
            # Add preserved raw lines FIRST (cookies, stick tables typically go before servers)
            for raw in be_data.get('raw_lines', []):
                lines.append(f"    {raw}")
                
            # Add servers
            for srv in be_data.get('servers', []):
                raw_srv = srv.get('raw', '')
                if raw_srv:
                    lines.append(f"    {raw_srv}")
                else:
                    # fallback generation if edited through UI
                    parts = [f"server {srv['name']} {srv['address']}"]
                    if srv.get('options'):
                        parts.append(srv['options'])
                    lines.append("    " + " ".join(parts))
                
            lines.append("")
            
        return "\n".join(lines)

    @classmethod
    def get_existing_components(cls, config_content):
        """
        Parses a raw HAProxy config string to extract existing frontends, their ACLs,
        their associated backends, and all global backends.
        Returns a dict:
        {
            'frontends': {
                'fe_name': {
                    'acls': {
                        'acl1': {'host': 'app.local', 'path': ''}
                    },
                    'use_backends': [{'acl': 'acl1', 'backend': 'be1'}]
                }
            },
            'backends': ['be1', 'be2']
        }
        """
        frontends: dict = {}
        backends: dict = {}
        
        current_section = None
        current_name = None
        
        lines = config_content.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
                
            if line_stripped.startswith('frontend '):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    current_section = 'frontend'
                    current_name = parts[1]
                    if current_name not in frontends:
                        frontends[current_name] = {'acls': {}, 'use_backends': []}
            elif line_stripped.startswith('backend '):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    current_section = 'backend'
                    current_name = parts[1]
                    if current_name not in backends:
                        backends[current_name] = {'servers': []}
            # Parse servers inside backend blocks
            elif current_section == 'backend' and current_name:
                if line_stripped.startswith('server '):
                    parts = line_stripped.split()
                    if len(parts) >= 3:
                        srv_name = parts[1]
                        # IP and Port e.g. 10.0.0.1:80
                        addr_parts = parts[2].split(':')
                        srv_ip = addr_parts[0]
                        srv_port = addr_parts[1] if len(addr_parts) > 1 else ''
                        
                        opts = parts[3:]
                        check = 'check' in opts
                        ssl = 'ssl' in opts
                        
                        backends[current_name]['servers'].append({
                            'name': srv_name,
                            'ip': srv_ip,
                            'port': srv_port,
                            'check': check,
                            'ssl': ssl
                        })
            # Only care about acl and use_backend if inside a frontend block
            elif current_section == 'frontend' and current_name:
                if line_stripped.startswith('acl '):
                    parts = line_stripped.split(maxsplit=2)
                    if len(parts) >= 3:
                        acl_name = parts[1]
                        condition = parts[2]
                        
                        if acl_name not in frontends[current_name]['acls']:
                            frontends[current_name]['acls'][acl_name] = {'host': '', 'path': ''}
                            
                        # Extremely naive extraction for MVP
                        if 'hdr(host) -i' in condition:
                            # acl <name> hdr(host) -i value
                            host_val = condition.split('-i')[-1].strip()
                            frontends[current_name]['acls'][acl_name]['host'] = host_val
                        elif 'path_beg' in condition:
                            # acl <name> path_beg value
                            path_val = condition.split('path_beg')[-1].strip()
                            frontends[current_name]['acls'][acl_name]['path'] = path_val
                            
                elif line_stripped.startswith('use_backend '):
                    parts = line_stripped.split()
                    if len(parts) >= 4 and parts[2] == 'if':
                        be_name = parts[1]
                        cond = " ".join(parts[3:])
                        frontends[current_name]['use_backends'].append({
                            'backend': be_name,
                            'condition': cond
                        })
                    elif len(parts) == 2:
                        frontends[current_name]['use_backends'].append({
                            'backend': parts[1],
                            'condition': ''
                        })
                elif line_stripped.startswith('default_backend '):
                    parts = line_stripped.split()
                    if len(parts) >= 2:
                        frontends[current_name]['use_backends'].append({
                            'backend': parts[1],
                            'condition': 'default'
                        })
                        
        return {'frontends': frontends, 'backends': backends}
        
haproxy_service = HAProxyService()
