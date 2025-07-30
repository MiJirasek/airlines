import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from typing import Dict, Optional
import streamlit as st
from datetime import datetime

from .config import Config
from .database import FirestoreManager
from .models import AirlineState
from .user_management import UserManager


class AuthManager:
    def __init__(self):
        self.db = FirestoreManager()
        self.authenticator = None
        self._setup_authenticator()
    
    def _setup_authenticator(self):
        import streamlit_authenticator as stauth
        import yaml
        import os
        
        print("DEBUG: Setting up authenticator")
        
        # Try multiple credential sources in order of preference
        config = None
        
        # 1. Try Firestore-based credentials (production)
        try:
            user_manager = UserManager()
            firestore_users = user_manager.get_all_users()
            if firestore_users:
                print(f"DEBUG: Loaded {len(firestore_users)} users from Firestore")
                config = {
                    'credentials': {
                        'usernames': firestore_users
                    },
                    'cookie': {
                        'name': Config.STREAMLIT_AUTH_COOKIE_NAME,
                        'key': Config.STREAMLIT_AUTH_COOKIE_KEY,
                        'expiry_days': Config.STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS
                    },
                    'preauthorized': []
                }
        except Exception as e:
            print(f"DEBUG: Could not load Firestore credentials: {e}")
        
        # 2. Try local credentials file
        if not config:
            credentials_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.yaml')
            try:
                if os.path.exists(credentials_path):
                    with open(credentials_path, 'r') as file:
                        config = yaml.safe_load(file)
                        config['cookie']['name'] = Config.STREAMLIT_AUTH_COOKIE_NAME
                        config['cookie']['key'] = Config.STREAMLIT_AUTH_COOKIE_KEY
                        config['cookie']['expiry_days'] = Config.STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS
                        print("DEBUG: Loaded credentials from local file")
            except Exception as e:
                print(f"DEBUG: Could not load credentials file: {e}")
        
        # 3. Fallback to hardcoded credentials for testing
        if not config:
            print("DEBUG: Using hardcoded test credentials")
            
            # For now, let's use a simple known password
            password_hash = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'  # "secret"
            
            config = {
                'credentials': {
                    'usernames': {
                        'team1': {
                            'email': 'team1@university.edu',
                            'name': 'Team 1',
                            'password': password_hash
                        },
                        'admin': {
                            'email': 'admin@university.edu',
                            'name': 'Administrator',
                            'password': password_hash
                        }
                    }
                },
                'cookie': {
                    'name': Config.STREAMLIT_AUTH_COOKIE_NAME,
                    'key': Config.STREAMLIT_AUTH_COOKIE_KEY,
                    'expiry_days': Config.STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS
                },
                'preauthorized': []
            }
        
        # Debug: Show loaded usernames
        usernames = list(config['credentials']['usernames'].keys())
        print(f"DEBUG: Loaded usernames: {usernames}")
        
        self.authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )
        print("DEBUG: Authenticator created successfully")
    
    def login(self) -> tuple[Optional[str], Optional[str], Optional[bool]]:
        """
        Returns: (name, authentication_status, username)
        """
        try:
            print("DEBUG: Calling authenticator.login()")
            result = self.authenticator.login(location='main')
            print(f"DEBUG: Login result: {result}")
            
            if result is None:
                print("DEBUG: Login returned None")
                return None, None, None
            
            name, authentication_status, username = result
            print(f"DEBUG: Parsed login - name: {name}, status: {authentication_status}, username: {username}")
            
            if authentication_status:
                print(f"DEBUG: Login successful for {username}")
                self._ensure_airline_exists(username)
            elif authentication_status is False:
                print("DEBUG: Login failed - invalid credentials")
            else:
                print("DEBUG: Login status is None - waiting for input")
            
            return name, authentication_status, username
        except Exception as e:
            print(f"DEBUG: Authentication error: {e}")
            st.error(f"Authentication error: {e}")
            return None, None, None
    
    def logout(self):
        self.authenticator.logout(location='main')
    
    def _ensure_airline_exists(self, team_id: str):
        existing_airline = self.db.get_airline_state(team_id)
        
        if not existing_airline:
            default_airline = AirlineState(
                team_id=team_id,
                name=f"Airline {team_id.upper()}",
                cash=Config.MAX_SEMESTER_BUDGET,
                aircraft_count=0,
                routes=[],
                market_share=0.0,
                reputation=50.0,
                last_updated=datetime.now()
            )
            self.db.update_airline_state(default_airline)
    
    def get_current_user(self) -> Optional[str]:
        if 'username' in st.session_state:
            return st.session_state['username']
        return None
    
    def is_authenticated(self) -> bool:
        return st.session_state.get('authentication_status', False)