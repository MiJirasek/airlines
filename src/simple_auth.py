"""
Simple custom authentication system that works reliably
"""

import streamlit as st
import hashlib
from typing import Optional, Tuple
from datetime import datetime

from .database import FirestoreManager
from .models import AirlineState
from .config import Config


class SimpleAuthManager:
    def __init__(self):
        self.db = FirestoreManager()
        
        # Simple test credentials - username: password
        self.test_users = {
            'team1': 'secret',
            'team2': 'secret', 
            'team3': 'secret',
            'admin': 'secret',
            'instructor': 'secret'
        }
    
    def hash_password(self, password: str) -> str:
        """Simple password hashing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify username and password"""
        if username in self.test_users:
            return self.test_users[username] == password
        return False
    
    def login(self) -> Tuple[Optional[str], Optional[bool], Optional[str]]:
        """
        Simple login form
        Returns: (name, authentication_status, username)
        """
        
        # Initialize session state
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'name' not in st.session_state:
            st.session_state.name = None
        
        # If already logged in, return current state
        if st.session_state.authentication_status:
            return st.session_state.name, st.session_state.authentication_status, st.session_state.username
        
        # Show login form
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if self.verify_password(username, password):
                    # Successful login
                    st.session_state.authentication_status = True
                    st.session_state.username = username
                    st.session_state.name = f"Team {username.upper()}" if username.startswith('team') else username.title()
                    
                    # Create airline if needed
                    self._ensure_airline_exists(username)
                    
                    st.success("Login successful!")
                    st.rerun()
                    
                else:
                    st.session_state.authentication_status = False
                    st.error("Invalid username or password")
        
        # Show available test accounts
        if st.session_state.authentication_status is None:
            with st.expander("🧪 Test Accounts"):
                st.write("**Available test accounts:**")
                for user in self.test_users.keys():
                    st.write(f"- Username: `{user}` / Password: `{self.test_users[user]}`")
        
        return st.session_state.name, st.session_state.authentication_status, st.session_state.username
    
    def logout(self):
        """Clear session and logout"""
        st.session_state.authentication_status = None
        st.session_state.username = None
        st.session_state.name = None
        st.rerun()
    
    def _ensure_airline_exists(self, team_id: str):
        """Create airline state for new teams"""
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
        """Get current logged in user"""
        return st.session_state.get('username')
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authentication_status', False)