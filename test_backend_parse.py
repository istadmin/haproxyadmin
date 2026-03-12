from services.haproxy import haproxy_service

current_config = """global
    log /dev/log local0

backend sub_be
    balance roundrobin
    server s1 10.0.0.1:80 check
    server s2 10.0.0.2:443 ssl verify none
"""

comp = haproxy_service.get_existing_components(current_config)
print("Backends parsed:")
for b, data in comp['backends'].items():
    print(f"Backend: {b}")
    for srv in data['servers']:
        print(f"  - Server: {srv}")
