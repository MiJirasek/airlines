import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Google Cloud / Firestore
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID")
    
    # AI API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # LangSmith
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "airline-simulation")
    
    # Streamlit Authentication
    STREAMLIT_AUTH_COOKIE_NAME = os.getenv("STREAMLIT_AUTH_COOKIE_NAME", "airline_sim_auth")
    STREAMLIT_AUTH_COOKIE_KEY = os.getenv("STREAMLIT_AUTH_COOKIE_KEY", "default-dev-key-change-in-production")
    STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS = int(os.getenv("STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS", "30"))
    
    # Simulation Settings
    MAX_SEMESTER_BUDGET = 1000000  # Default budget per semester
    
    @classmethod
    def validate_required_config(cls):
        """Validate that required configuration is present"""
        # Try to get from streamlit secrets if environment variables are missing
        import streamlit as st
        
        firestore_id = cls.FIRESTORE_PROJECT_ID
        gemini_key = cls.GEMINI_API_KEY
        
        # Fallback to direct secrets access if env vars are empty
        if not firestore_id and hasattr(st, 'secrets') and 'FIRESTORE_PROJECT_ID' in st.secrets:
            firestore_id = st.secrets['FIRESTORE_PROJECT_ID']
            
        if not gemini_key and hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
            gemini_key = st.secrets['GEMINI_API_KEY']
        
        required_vars = {
            "FIRESTORE_PROJECT_ID": firestore_id,
            "GEMINI_API_KEY": gemini_key,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True