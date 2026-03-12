from services.haproxy import haproxy_service

current_config = """global
    log /dev/log local0

defaults
    mode http

frontend main_fe
    bind *:80
    mode http
    acl sub path_beg /sub
    use_backend sub_be if sub

backend sub_be
    server s1 10.0.0.1:80
"""

form_data = {
    'service_name': 'test_app',
    'frontend_mode': 'existing',
    'frontend_name': 'main_fe',
    'route_host': 'new.example.com',
    'route_path': '/new',
    'backend_mode': 'existing',
    'backend_name': 'sub_be',
    'server_count': '1',
    'server_name_0': 's2',
    'server_ip_0': '10.0.0.2',
    'server_port_0': '80',
    'server_check_0': '1'
}

summary, full = haproxy_service.generate_service_group(form_data, current_config)
print("=== SUMMARY ===")
print(summary)
print("=== FULL ===")
print(full)
