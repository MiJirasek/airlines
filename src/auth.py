import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from typing import Dict, Optional
import streamlit as st
from datetime import datetime

from .config import Config
from .database import FirestoreManager
from .models import AirlineState


class AuthManager:
    def __init__(self):
        self.db = FirestoreManager()
        self.authenticator = None
        self._setup_authenticator()
    
    def _setup_authenticator(self):
        # Hash passwords for demo teams (password: "password123")
        import streamlit_authenticator as stauth
        
        config = {
            'credentials': {
                'usernames': {
                    'team1': {
                        'email': 'team1@university.edu',
                        'name': 'Team 1',
                        'password': '$2b$12$kEz1VhznDJRWN4pTuZkV7eIQ6qZi6yNNvWe/fLUCZhztG4ydT5SLy'  # password123
                    },
                    'team2': {
                        'email': 'team2@university.edu', 
                        'name': 'Team 2',
                        'password': '$2b$12$kEz1VhznDJRWN4pTuZkV7eIQ6qZi6yNNvWe/fLUCZhztG4ydT5SLy'  # password123
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
        
        self.authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )
    
    def login(self) -> tuple[Optional[str], Optional[str], Optional[bool]]:
        """
        Returns: (name, authentication_status, username)
        """
        try:
            result = self.authenticator.login(location='main')
            if result is None:
                return None, None, None
            
            name, authentication_status, username = result
            
            if authentication_status:
                self._ensure_airline_exists(username)
            
            return name, authentication_status, username
        except Exception as e:
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