from services.haproxy import haproxy_service

with open('/home/istadmin/001_ist/haproxyadmin/haproxy.cfg', 'r') as f:
    text = f.read()
    
parsed = haproxy_service.parse_full_config(text)
print("Parsed root keys:", parsed.keys())
print(f"Global lines: {len(parsed['global'])}")
print(f"Defaults lines: {len(parsed['defaults'])}")
print(f"Frontends: {list(parsed['frontends'].keys())}")
print(f"Backends: {list(parsed['backends'].keys())}")
