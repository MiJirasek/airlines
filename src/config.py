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
    STREAMLIT_AUTH_COOKIE_KEY = os.getenv("STREAMLIT_AUTH_COOKIE_KEY")
    STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS = int(os.getenv("STREAMLIT_AUTH_COOKIE_EXPIRY_DAYS", "30"))
    
    # Simulation Settings
    MAX_SEMESTER_BUDGET = 1000000  # Default budget per semester