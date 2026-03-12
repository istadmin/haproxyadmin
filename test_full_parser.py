from services.haproxy import haproxy_service
import json

def parse_full_config(config_text):
    """
    Parses a full HAProxy config file into an object retaining raw lines for unknown directives.
    Returns: {
        'global': ['line1', 'line2'],
        'defaults': ['line1', 'line2'],
        'frontends': {
            'name': {
                'bind': 'IP:PORT',
                'mode': 'http',
                'default_backend': 'be_name',
                'acls': [],
                'use_backends': [],
                'raw_lines': [] # Lines we don't understand but must preserve
            }
        },
        'backends': {
            'name': {
                'mode': 'http',
                'balance': 'roundrobin',
                'servers': [],
                'raw_lines': [] # Stick tables, cookie inserts, etc.
            }
        }
    }
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
            # TODO: decide if we keep comments. For now, skip to keep JSON clean.
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
                'acls': [], 'use_backends': [], 'raw_lines': []
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
                fe['bind'] = " ".join(parts[1:])
            elif keyword == 'mode':
                fe['mode'] = parts[1] if len(parts) > 1 else ''
            elif keyword == 'default_backend':
                fe['default_backend'] = parts[1] if len(parts) > 1 else ''
            elif keyword == 'acl':
                fe['acls'].append(stripped)
            elif keyword == 'use_backend':
                fe['use_backends'].append(stripped)
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

def generate_full_config(config_json):
    """Takes the parsed JSON and rebuilds the raw text configuration securely."""
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
            lines.append(f"    bind {fe_data['bind']}")
        if fe_data.get('mode'):
            lines.append(f"    mode {fe_data['mode']}")
            
        # Add acls
        for acl in fe_data.get('acls', []):
            lines.append(f"    {acl}")
            
        # Add use_backends
        for ub in fe_data.get('use_backends', []):
            lines.append(f"    {ub}")
            
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
            lines.append(f"    {srv['raw']}")
            
        lines.append("")
        
    return "\n".join(lines)


current_config = """global
    log /dev/log local0
    maxconn 4000
    user haproxy
    group haproxy

defaults
    log global
    mode http
    option httplog
    timeout client 50000

frontend http_front
    bind *:80
    mode http
    acl url_api path_beg /api
    use_backend api_backend if url_api
    http-request set-header X-Forwarded-Port %[dst_port]
    default_backend web_backend

backend api_backend
    balance roundrobin
    server api1 10.0.0.1:8080 check

backend web_backend
    balance roundrobin
    cookie SERVERID insert indirect nocache
    server web1 10.0.0.2:80 check cookie web1
"""

parsed = parse_full_config(current_config)
print("=== PARSED JSON ===")
print(json.dumps(parsed, indent=2))

generated = generate_full_config(parsed)
print("=== GENERATED CONFIG ===")
print(generated)

