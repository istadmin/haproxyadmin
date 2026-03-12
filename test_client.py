import requests
from bs4 import BeautifulSoup
import sys

def test_app():
    s = requests.Session()
    resp = s.get('http://localhost:5000/login')
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    if not csrf_token:
        print("Failed to find CSRF token")
        sys.exit(1)
        
    print(f"Found CSRF: {csrf_token['value']}")
    
    # In a real PAM test we'd need a real username/pass, but we can see if it fails auth correctly
    login_data = {
        'username': 'istadmin',
        'password': 'wrongpassword',
        'csrf_token': csrf_token['value']
    }
    
    resp_login = s.post('http://localhost:5000/login', data=login_data)
    if 'Invalid username or password' in resp_login.text:
        print("Login rejection working successfully (PAM fallback is active).")
    else:
        print("Login behaved unexpectedly.")
        
    # Test health endpoint again
    h = s.get('http://localhost:5000/health')
    print("Health:", h.json())

if __name__ == '__main__':
    test_app()
