"""
Secure user management system using Firestore
Credentials are stored in Firestore, not in code
"""

import streamlit_authenticator as stauth
from typing import Dict, List, Optional
from datetime import datetime
import secrets
import string

from .database import FirestoreManager
from .models import *


class UserManager:
    def __init__(self):
        self.db = FirestoreManager()
    
    def create_team_credentials(self, team_id: str, team_name: str, instructor_email: str) -> str:
        """Create new team with random password"""
        # Generate secure random password
        password = self._generate_password()
        password_hash = stauth.Hasher([password]).generate()[0]
        
        # Store in Firestore
        user_doc = {
            'team_id': team_id,
            'name': team_name,
            'email': f"{team_id}@university-simulation.edu",
            'password_hash': password_hash,
            'created_by': instructor_email,
            'created_at': datetime.now(),
            'is_active': True,
            'last_login': None
        }
        
        try:
            # Store user credentials
            self.db.db.collection('users').document(team_id).set(user_doc)
            
            # Create initial airline state
            from .models import AirlineState
            from .config import Config
            
            initial_airline = AirlineState(
                team_id=team_id,
                name=f"Airline {team_name}",
                cash=Config.MAX_SEMESTER_BUDGET,
                aircraft_count=0,
                routes=[],
                market_share=0.0,
                reputation=50.0,
                last_updated=datetime.now()
            )
            
            self.db.update_airline_state(initial_airline)
            
            return password  # Return plaintext password for distribution
            
        except Exception as e:
            raise Exception(f"Failed to create team credentials: {e}")
    
    def get_all_users(self) -> Dict[str, Dict]:
        """Get all user credentials for authentication"""
        try:
            users_ref = self.db.db.collection('users')
            docs = users_ref.where('is_active', '==', True).stream()
            
            credentials = {}
            for doc in docs:
                data = doc.to_dict()
                credentials[doc.id] = {
                    'email': data['email'],
                    'name': data['name'],
                    'password': data['password_hash']
                }
            
            return credentials
        except Exception as e:
            print(f"Error loading user credentials: {e}")
            return {}
    
    def reset_password(self, team_id: str) -> str:
        """Reset team password and return new password"""
        new_password = self._generate_password()
        password_hash = stauth.Hasher([new_password]).generate()[0]
        
        try:
            self.db.db.collection('users').document(team_id).update({
                'password_hash': password_hash,
                'password_reset_at': datetime.now()
            })
            return new_password
        except Exception as e:
            raise Exception(f"Failed to reset password: {e}")
    
    def deactivate_team(self, team_id: str):
        """Deactivate team access"""
        try:
            self.db.db.collection('users').document(team_id).update({
                'is_active': False,
                'deactivated_at': datetime.now()
            })
        except Exception as e:
            raise Exception(f"Failed to deactivate team: {e}")
    
    def update_last_login(self, team_id: str):
        """Update last login timestamp"""
        try:
            self.db.db.collection('users').document(team_id).update({
                'last_login': datetime.now()
            })
        except Exception as e:
            print(f"Failed to update last login: {e}")
    
    def _generate_password(self, length: int = 12) -> str:
        """Generate secure random password"""
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    def bulk_create_teams(self, team_count: int, instructor_email: str) -> List[Dict[str, str]]:
        """Create multiple teams at once"""
        teams = []
        
        for i in range(1, team_count + 1):
            team_id = f"team{i:02d}"  # team01, team02, etc.
            team_name = f"Team {i}"
            
            try:
                password = self.create_team_credentials(team_id, team_name, instructor_email)
                teams.append({
                    'team_id': team_id,
                    'team_name': team_name,
                    'password': password
                })
            except Exception as e:
                print(f"Failed to create {team_id}: {e}")
        
        return teams


class AdminInterface:
    """Streamlit interface for managing teams"""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    def show_admin_panel(self):
        """Display admin interface for instructors"""
        st.header("👨‍🏫 Instructor Admin Panel")
        
        tab1, tab2, tab3 = st.tabs(["Create Teams", "Manage Teams", "Reset Passwords"])
        
        with tab1:
            self._show_create_teams()
        
        with tab2:
            self._show_manage_teams()
        
        with tab3:
            self._show_reset_passwords()
    
    def _show_create_teams(self):
        st.subheader("Create New Teams")
        
        col1, col2 = st.columns(2)
        
        with col1:
            instructor_email = st.text_input("Instructor Email", value="instructor@university.edu")
            team_count = st.number_input("Number of Teams", min_value=1, max_value=50, value=10)
        
        with col2:
            if st.button("Create Teams", type="primary"):
                with st.spinner("Creating teams..."):
                    teams = self.user_manager.bulk_create_teams(team_count, instructor_email)
                
                if teams:
                    st.success(f"Created {len(teams)} teams!")
                    
                    # Display credentials for distribution
                    st.subheader("📋 Team Credentials (Save These!)")
                    
                    credentials_text = "AIRLINE SIMULATION - TEAM CREDENTIALS\n"
                    credentials_text += "=" * 50 + "\n\n"
                    
                    for team in teams:
                        credentials_text += f"Team: {team['team_name']}\n"
                        credentials_text += f"Username: {team['team_id']}\n"
                        credentials_text += f"Password: {team['password']}\n"
                        credentials_text += "-" * 30 + "\n"
                    
                    st.text_area("Credentials (Copy and Save)", credentials_text, height=300)
                    st.warning("⚠️ Save these credentials securely! They cannot be recovered.")
    
    def _show_manage_teams(self):
        st.subheader("Manage Existing Teams")
        
        # This would show existing teams and allow deactivation
        st.info("Team management interface - to be implemented")
    
    def _show_reset_passwords(self):
        st.subheader("Reset Team Passwords")
        
        team_id = st.text_input("Team ID to Reset")
        
        if st.button("Reset Password") and team_id:
            try:
                new_password = self.user_manager.reset_password(team_id)
                st.success(f"Password reset successful!")
                st.code(f"New password for {team_id}: {new_password}")
                st.warning("⚠️ Save this password securely!")
            except Exception as e:
                st.error(f"Failed to reset password: {e}")