import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as firestore_client
from google.oauth2 import service_account
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from .config import Config
from .models import AirlineState, MarketState, SemesterPlan, EvaluationFeedback


class FirestoreManager:
    def __init__(self):
        self.db = None
        self._initialize_firestore()
    
    def _initialize_firestore(self):
        try:
            import os
            import streamlit as st
            
            # Debug info
            print(f"DEBUG: Initializing Firestore with project_id: {Config.FIRESTORE_PROJECT_ID}")
            print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS path: {Config.GOOGLE_APPLICATION_CREDENTIALS}")
            
            # Set GOOGLE_CLOUD_PROJECT environment variable as backup
            os.environ['GOOGLE_CLOUD_PROJECT'] = Config.FIRESTORE_PROJECT_ID
            print(f"DEBUG: Set GOOGLE_CLOUD_PROJECT to: {Config.FIRESTORE_PROJECT_ID}")
            
            # Try direct approach with service account from Streamlit secrets
            if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                print("DEBUG: Using direct service account from Streamlit secrets")
                
                # Create credentials directly from secrets
                service_account_info = dict(st.secrets['gcp_service_account'])
                credentials_obj = service_account.Credentials.from_service_account_info(service_account_info)
                
                # Use google-cloud-firestore client directly
                self.db = firestore_client.Client(
                    project=Config.FIRESTORE_PROJECT_ID,
                    credentials=credentials_obj
                )
                print("DEBUG: Firestore client created successfully from secrets")
                return
            
            # Fallback to firebase-admin approach
            if not firebase_admin._apps:
                if Config.GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(Config.GOOGLE_APPLICATION_CREDENTIALS):
                    print("DEBUG: Using service account credentials file")
                    cred = credentials.Certificate(Config.GOOGLE_APPLICATION_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        'projectId': Config.FIRESTORE_PROJECT_ID,
                    })
                else:
                    print("DEBUG: Using default credentials with explicit project")
                    # For Streamlit Cloud, we need to explicitly set the project
                    firebase_admin.initialize_app(options={
                        'projectId': Config.FIRESTORE_PROJECT_ID,
                    })
            
            # Create Firestore client via firebase-admin
            self.db = firestore.client()
            print("DEBUG: Firestore client created successfully via firebase-admin")
            
        except Exception as e:
            print(f"Error initializing Firestore: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_airline_state(self, team_id: str) -> Optional[AirlineState]:
        try:
            doc_ref = self.db.collection('airlines').document(team_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return AirlineState(**data)
            return None
        except Exception as e:
            print(f"Error getting airline state: {e}")
            return None
    
    def update_airline_state(self, airline_state: AirlineState) -> bool:
        try:
            doc_ref = self.db.collection('airlines').document(airline_state.team_id)
            doc_ref.set(airline_state.model_dump())
            return True
        except Exception as e:
            print(f"Error updating airline state: {e}")
            return False
    
    def get_market_state(self) -> Optional[MarketState]:
        try:
            doc_ref = self.db.collection('simulation').document('market_state')
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return MarketState(**data)
            return None
        except Exception as e:
            print(f"Error getting market state: {e}")
            return None
    
    def update_market_state(self, market_state: MarketState) -> bool:
        try:
            doc_ref = self.db.collection('simulation').document('market_state')
            doc_ref.set(market_state.model_dump())
            return True
        except Exception as e:
            print(f"Error updating market state: {e}")
            return False
    
    def save_semester_plan(self, plan: SemesterPlan) -> bool:
        try:
            doc_ref = self.db.collection('plans').document(f"{plan.team_id}_{plan.semester}")
            doc_ref.set(plan.model_dump())
            return True
        except Exception as e:
            print(f"Error saving semester plan: {e}")
            return False
    
    def get_semester_plan(self, team_id: str, semester: str) -> Optional[SemesterPlan]:
        try:
            doc_ref = self.db.collection('plans').document(f"{team_id}_{semester}")
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return SemesterPlan(**data)
            return None
        except Exception as e:
            print(f"Error getting semester plan: {e}")
            return None
    
    def save_evaluation_feedback(self, feedback: EvaluationFeedback) -> bool:
        try:
            doc_ref = self.db.collection('feedback').add(feedback.model_dump())
            return True
        except Exception as e:
            print(f"Error saving evaluation feedback: {e}")
            return False
    
    def get_all_airline_states(self) -> List[AirlineState]:
        try:
            docs = self.db.collection('airlines').stream()
            airlines = []
            for doc in docs:
                data = doc.to_dict()
                airlines.append(AirlineState(**data))
            return airlines
        except Exception as e:
            print(f"Error getting all airline states: {e}")
            return []
    
    def initialize_default_data(self):
        default_market = MarketState(
            total_passengers=1000000,
            competition_level=0.5,
            economic_conditions="stable",
            events=[],
            last_updated=datetime.now()
        )
        self.update_market_state(default_market)