import streamlit as st
import requests
import urllib.parse
import os

# Try to load secrets from streamlit
CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.environ.get("GOOGLE_CLIENT_ID", ""))
CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", os.environ.get("GOOGLE_CLIENT_SECRET", ""))
REDIRECT_URI = st.secrets.get("GOOGLE_REDIRECT_URI", os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8501"))

# Google OAuth endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def is_oauth_configured():
    """Verify if OAuth secrets are set up."""
    return bool(CLIENT_ID and CLIENT_SECRET)

def get_google_auth_url():
    """Generate the Google sign-in redirect URL."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    url_params = urllib.parse.urlencode(params)
    return f"{AUTH_URL}?{url_params}"

def get_user_info_from_code(code):
    """Exchange the OAuth authorization code for profile data."""
    if not code:
        return None
    
    payload = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        # 1. Exchange authorization code for access token
        res = requests.post(TOKEN_URL, data=payload, timeout=10)
        res_data = res.json()
        access_token = res_data.get("access_token")
        
        if not access_token:
            st.error(f"Failed to fetch access token: {res_data.get('error_description', 'Unknown error')}")
            return None
        
        # 2. Fetch user profile from userinfo endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        info_res = requests.get(USERINFO_URL, headers=headers, timeout=10)
        return info_res.json()
        
    except Exception as e:
        st.error(f"OAuth communication failed: {e}")
        return None

def simulate_login(email, name=None):
    """Provide a simulated profile dict for sandbox testing."""
    if not name:
        name = email.split("@")[0].title().replace(".", " ").replace("-", " ")
        
    # Standard profile format mimicking Google API response
    return {
        "email": email,
        "name": name,
        "picture": "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"
    }
