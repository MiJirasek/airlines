"""
Instructor Dashboard for Managing Airline Simulation
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import json

from .database import FirestoreManager
from .models import *
from .workflow import SimulationWorkflow
from .user_management import UserManager, AdminInterface


class InstructorDashboard:
    def __init__(self):
        self.db = FirestoreManager()
        self.workflow = SimulationWorkflow()
        self.user_manager = UserManager()
        self.admin_interface = AdminInterface()
    
    def show_dashboard(self):
        """Main instructor dashboard interface"""
        st.title("👨‍🏫 Instructor Dashboard")
        
        # Tabs for different instructor functions
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Overview", 
            "📋 Plan Status", 
            "🚀 Run Simulation", 
            "📝 Feedback Review",
            "🏢 Airline Details",
            "📈 Market Management"
        ])
        
        with tab1:
            self._show_overview()
        
        with tab2:
            self._show_plan_status()
        
        with tab3:
            self._show_simulation_control()
        
        with tab4:
            self._show_feedback_review()
        
        with tab5:
            self._show_airline_details()
        
        with tab6:
            self._show_market_management()
    
    def _show_overview(self):
        """Dashboard overview with key metrics"""
        st.header("📊 Simulation Overview")
        
        # Get current simulation state
        status = self.workflow.get_simulation_status()
        
        if 'error' in status:
            st.error(f"Error loading simulation status: {status['error']}")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Teams", status.get('total_airlines', 0))
        
        with col2:
            # Count submitted plans (this would need to be implemented)
            submitted_plans = self._count_submitted_plans()
            st.metric("Plans Submitted", submitted_plans)
        
        with col3:
            if status.get('market_state'):
                market_state = status['market_state']
                st.metric("Market Passengers", f"{market_state.get('total_passengers', 0):,}")
        
        with col4:
            # Average reputation
            if status.get('airlines_summary'):
                avg_reputation = sum(a['reputation'] for a in status['airlines_summary']) / len(status['airlines_summary'])
                st.metric("Avg Reputation", f"{avg_reputation:.1f}")
        
        # Top performers
        if status.get('top_performers'):
            st.subheader("🏆 Current Leaders")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                leader = status['top_performers'].get('market_leader')
                if leader:
                    st.write("**Market Leader**")
                    st.write(f"Team: {leader['team_id']}")
                    st.write(f"Share: {leader['market_share']:.2%}")
            
            with col2:
                rep_leader = status['top_performers'].get('highest_reputation')
                if rep_leader:
                    st.write("**Best Reputation**")
                    st.write(f"Team: {rep_leader['team_id']}")
                    st.write(f"Score: {rep_leader['reputation']:.1f}")
            
            with col3:
                cash_leader = status['top_performers'].get('most_cash')
                if cash_leader:
                    st.write("**Most Cash**")
                    st.write(f"Team: {cash_leader['team_id']}")
                    st.write(f"Cash: ${cash_leader['cash']:,.0f}")
    
    def _show_plan_status(self):
        """Show status of team plan submissions"""
        st.header("📋 Team Plan Submission Status")
        
        # Get all teams and their plan status
        airlines = self.db.get_all_airline_states()
        
        if not airlines:
            st.warning("No teams found. Create teams first using the admin interface.")
            return
        
        # Create status table
        status_data = []
        
        for airline in airlines:
            # Check for submitted plans (simplified - check latest plan)
            latest_plan = self._get_latest_plan(airline.team_id)
            
            status_data.append({
                'Team ID': airline.team_id,
                'Team Name': airline.name,
                'Cash': f"${airline.cash:,.0f}",
                'Aircraft': airline.aircraft_count,
                'Routes': len(airline.routes),
                'Last Plan': latest_plan['date'] if latest_plan else 'None',
                'Plan Status': '✅ Submitted' if latest_plan else '❌ Missing',
                'Actions': latest_plan['action_count'] if latest_plan else 0
            })
        
        df = pd.DataFrame(status_data)
        st.dataframe(df, use_container_width=True)
        
        # Summary
        submitted_count = sum(1 for row in status_data if row['Plan Status'] == '✅ Submitted')
        total_count = len(status_data)
        
        st.write(f"**Summary:** {submitted_count}/{total_count} teams have submitted plans")
        
        if submitted_count < total_count:
            missing_teams = [row['Team ID'] for row in status_data if row['Plan Status'] == '❌ Missing']
            st.warning(f"Missing plans from: {', '.join(missing_teams)}")
    
    def _show_simulation_control(self):
        """Control simulation workflow execution"""
        st.header("🚀 Simulation Control")
        
        st.write("**Workflow Steps:**")
        st.write("1. Teams submit semester plans")
        st.write("2. Company agents validate and process plans")
        st.write("3. Market agent evaluates competition")
        st.write("4. Evaluation agent provides feedback")
        st.write("5. Results distributed to teams")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Current Status")
            
            # Show submission status
            submitted_plans = self._count_submitted_plans()
            total_teams = len(self.db.get_all_airline_states())
            
            st.write(f"Plans submitted: {submitted_plans}/{total_teams}")
            
            if submitted_plans > 0:
                st.success("Ready to run simulation!")
            else:
                st.warning("No plans submitted yet")
        
        with col2:
            st.subheader("⚡ Actions")
            
            # Run simulation button
            if st.button("🚀 Run Full Simulation", type="primary", disabled=submitted_plans == 0):
                self._run_simulation()
            
            st.write("---")
            
            # Individual workflow steps
            if st.button("1️⃣ Process Company Plans Only"):
                self._process_company_plans()
            
            if st.button("2️⃣ Run Market Analysis Only"):
                self._run_market_analysis()
            
            if st.button("3️⃣ Generate Evaluations Only"):
                self._generate_evaluations()
            
            st.write("---")
            
            # Simulation reset
            if st.button("🔄 Reset Simulation", help="Reset all teams to initial state"):
                if st.button("⚠️ Confirm Reset"):
                    self._reset_simulation()
    
    def _show_feedback_review(self):
        """Review and manage team feedback"""
        st.header("📝 Team Feedback Review")
        
        # Get all teams
        airlines = self.db.get_all_airline_states()
        
        if not airlines:
            st.warning("No teams found")
            return
        
        # Team selection
        team_options = [airline.team_id for airline in airlines]
        selected_team = st.selectbox("Select Team", team_options)
        
        if selected_team:
            self._show_team_feedback(selected_team)
    
    def _show_airline_details(self):
        """Detailed view of individual airlines"""
        st.header("🏢 Airline Details")
        
        airlines = self.db.get_all_airline_states()
        
        if not airlines:
            st.warning("No airlines found")
            return
        
        # Team selection
        team_options = [airline.team_id for airline in airlines]
        selected_team = st.selectbox("Select Airline", team_options)
        
        if selected_team:
            airline = next((a for a in airlines if a.team_id == selected_team), None)
            if airline:
                self._show_detailed_airline_view(airline)
    
    def _show_market_management(self):
        """Market data management and event injection"""
        st.header("📈 Market Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Current Market State")
            market_state = self.db.get_market_state()
            
            if market_state:
                st.write(f"**Total Passengers:** {market_state.total_passengers:,}")
                st.write(f"**Competition Level:** {market_state.competition_level:.2f}")
                st.write(f"**Economic Conditions:** {market_state.economic_conditions}")
                st.write(f"**Last Updated:** {market_state.last_updated}")
                
                if market_state.events:
                    st.write("**Recent Events:**")
                    for event in market_state.events[-5:]:
                        st.write(f"• {event}")
            else:
                st.warning("No market state found")
        
        with col2:
            st.subheader("⚙️ Market Controls")
            
            # Upload market data
            st.write("**Upload Market Data:**")
            uploaded_market = st.file_uploader("Upload Market JSON", type=['json'])
            
            if uploaded_market and st.button("Upload Market Data"):
                try:
                    market_data = json.load(uploaded_market)
                    self._update_market_data(market_data)
                    st.success("Market data updated!")
                except Exception as e:
                    st.error(f"Error uploading market data: {e}")
            
            st.write("---")
            
            # Manual market event injection
            st.write("**Inject Market Event:**")
            event_text = st.text_area("Event Description", placeholder="New regulation affects fuel costs...")
            
            if st.button("Add Market Event") and event_text:
                self._add_market_event(event_text)
                st.success("Market event added!")
                st.rerun()
    
    # Helper methods
    def _count_submitted_plans(self) -> int:
        """Count how many teams have submitted plans"""
        # This is a simplified implementation
        # In reality, you'd query the plans collection
        try:
            plans_ref = self.db.db.collection('plans')
            docs = list(plans_ref.stream())
            return len(docs)
        except:
            return 0
    
    def _get_latest_plan(self, team_id: str) -> Dict[str, Any]:
        """Get the latest plan for a team"""
        try:
            plans_ref = self.db.db.collection('plans')
            query = plans_ref.where('team_id', '==', team_id).order_by('submission_timestamp', direction='DESCENDING').limit(1)
            docs = list(query.stream())
            
            if docs:
                plan_data = docs[0].to_dict()
                return {
                    'date': plan_data.get('submission_timestamp', 'Unknown'),
                    'action_count': len(plan_data.get('actions', []))
                }
            return None
        except:
            return None
    
    def _run_simulation(self):
        """Run the complete simulation workflow"""
        with st.spinner("Running simulation..."):
            try:
                # Get all submitted plans
                plans = self._get_all_submitted_plans()
                
                if not plans:
                    st.error("No plans found to process")
                    return
                
                # Run workflow
                results = self.workflow.process_semester_plans(plans)
                
                # Show results summary
                st.success(f"Simulation completed! Processed {len(plans)} plans.")
                
                # Display summary
                successful = sum(1 for r in results.values() if r.get('status') == 'completed')
                st.write(f"✅ Successful: {successful}")
                st.write(f"❌ Failed: {len(plans) - successful}")
                
            except Exception as e:
                st.error(f"Simulation failed: {e}")
    
    def _get_all_submitted_plans(self) -> List[SemesterPlan]:
        """Get all submitted plans for processing"""
        # This would implement actual plan retrieval from Firestore
        # For now, return empty list
        return []
    
    def _show_team_feedback(self, team_id: str):
        """Show detailed feedback for a specific team"""
        st.subheader(f"Feedback for {team_id}")
        
        # This would show feedback history
        st.info("Feedback history implementation pending")
    
    def _show_detailed_airline_view(self, airline: AirlineState):
        """Show detailed view of an airline"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Financial Status")
            st.write(f"**Cash:** ${airline.cash:,.0f}")
            st.write(f"**Market Share:** {airline.market_share:.2%}")
            st.write(f"**Reputation:** {airline.reputation}/100")
        
        with col2:
            st.subheader("✈️ Operations")
            st.write(f"**Aircraft Count:** {airline.aircraft_count}")
            st.write(f"**Active Routes:** {len(airline.routes)}")
            if airline.routes:
                st.write("**Route List:**")
                for route in airline.routes:
                    st.write(f"• {route}")
        
        st.write(f"**Last Updated:** {airline.last_updated}")
    
    def _update_market_data(self, market_data: Dict[str, Any]):
        """Update market state from uploaded data"""
        try:
            # Update market state
            current_market = self.db.get_market_state()
            
            if current_market:
                # Update fields from uploaded data
                if 'total_passengers' in market_data:
                    current_market.total_passengers = market_data['total_passengers']
                if 'competition_level' in market_data:
                    current_market.competition_level = market_data['competition_level']
                if 'economic_conditions' in market_data:
                    current_market.economic_conditions = market_data['economic_conditions']
                if 'events' in market_data:
                    current_market.events.extend(market_data['events'])
                
                current_market.last_updated = datetime.now()
                self.db.update_market_state(current_market)
        
        except Exception as e:
            st.error(f"Failed to update market data: {e}")
    
    def _add_market_event(self, event_text: str):
        """Add a market event"""
        try:
            market_state = self.db.get_market_state()
            if market_state:
                market_state.events.append(event_text)
                market_state.last_updated = datetime.now()
                self.db.update_market_state(market_state)
        except Exception as e:
            st.error(f"Failed to add market event: {e}")
    
    def _process_company_plans(self):
        """Process only company agent step"""
        st.info("Company plan processing - implementation pending")
    
    def _run_market_analysis(self):
        """Run only market analysis step"""
        st.info("Market analysis - implementation pending")
    
    def _generate_evaluations(self):
        """Generate only evaluation step"""
        st.info("Evaluation generation - implementation pending")
    
    def _reset_simulation(self):
        """Reset simulation to initial state"""
        st.info("Simulation reset - implementation pending")