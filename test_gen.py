import json
from services.haproxy import HAProxyService

# Minimal payload similar to UI
data = {
    "global": [],
    "defaults": [],
    "frontends": {
        "new_frontend": {
            "bind": "*:80",
            "ssl_cert": "",
            "mode": "http",
            "default_backend": "",
            "acls": [
                {"name": "is_api", "condition": "path_beg /api"}
            ],
            "use_backends": [
                {"backend": "api_be", "condition": "if is_api"}
            ],
            "raw_lines": []
        }
    },
    "backends": {}
}

try:
    print(HAProxyService.generate_full_config(data))
except Exception as e:
    import traceback
    traceback.print_exc()
