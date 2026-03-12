import pam
from flask import session

def authenticate_os_user(username, password, service='login'):
    """
    Authenticate a user against the OS using PAM.
    Returns True if successful, False otherwise.
    """
    p = pam.pam()
    # Ensure username is safe (basic sanity check)
    if not username or not password or not isinstance(username, str) or not isinstance(password, str):
        return False
        
    return p.authenticate(username, password, service=service)

def login_user(username, ip_address=None):
    """
    Set up the user session.
    """
    session['username'] = username
    session.permanent = True  # Depends on app config PERMANENT_SESSION_LIFETIME
    
    # Ideally IP isn't completely trusted for session bound, but good for tracking
    if ip_address:
        session['login_ip'] = ip_address

def logout_user():
    """
    Clear the user session.
    """
    session.clear()

def get_current_user():
    """
    Get the currently logged-in username from the session.
    Returns None if not logged in.
    """
    return session.get('username')

def is_authenticated():
    """
    Check if the current request has a valid logged-in user.
    """
    return 'username' in session

def login_required(f):
    """
    Decorator for routes that require authentication.
    """
    from functools import wraps
    from flask import redirect, url_for, request
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
