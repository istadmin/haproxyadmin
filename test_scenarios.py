from services.haproxy import haproxy_service

current_config = """global
    log /dev/log local0

defaults
    mode http
    timeout client 50000

frontend main_fe
    bind *:80
    mode http
    acl existing_acl path_beg /oldpath
    use_backend old_be if existing_acl

backend old_be
    server s1 10.0.0.1:80
"""

def print_test(name, form_data):
    print(f"\n--- Scenario: {name} ---")
    summary, full = haproxy_service.generate_service_group(form_data, current_config)
    print("SUMMARY:\n", summary, "\n")
    # print("FULL:\n", full)

print_test("1. Edit existing ACL, change path, keep backend", {
    'service_name': 'test1', 'frontend_mode': 'existing', 'frontend_name': 'main_fe',
    'existing_acl': 'existing_acl', 'route_host': '', 'route_path': '/newpath',
    'backend_mode': 'existing', 'backend_name': 'old_be', 'server_count': '0'
})

print_test("2. Edit existing ACL, change path, NEW backend", {
    'service_name': 'test2', 'frontend_mode': 'existing', 'frontend_name': 'main_fe',
    'existing_acl': 'existing_acl', 'route_host': '', 'route_path': '/newpath',
    'backend_mode': 'new', 'new_backend_name': 'new_be', 'server_count': '1',
    'server_name_0': 's2', 'server_ip_0': '10.0.0.2', 'server_port_0': '80', 'balance_algorithm': 'roundrobin'
})

print_test("3. New ACL, new Backend on existing FE", {
    'service_name': 'test3', 'frontend_mode': 'existing', 'frontend_name': 'main_fe',
    'existing_acl': '', 'route_host': 'test3.com', 'route_path': '',
    'backend_mode': 'new', 'new_backend_name': 'be_test3', 'server_count': '0'
})

