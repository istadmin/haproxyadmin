from services.haproxy import haproxy_service

current_config = """global
    log /dev/log local0

defaults
    mode http

frontend main_fe
    bind *:80
    mode http
"""

form_data = {
    'service_name': 'my_app',
    'frontend_mode': 'existing',
    'frontend_name': 'main_fe',
    
    'route_mode': 'new',
    'new_acl_name': 'custom_acl_prefix',
    'route_host': 'test.com',
    'route_path': '/api',
    
    'backend_mode': 'new',
    'new_backend_name': 'my_be',
    'server_count': '0'
}

summary, full = haproxy_service.generate_service_group(form_data, current_config)
print(summary)
