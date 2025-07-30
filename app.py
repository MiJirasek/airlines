import streamlit as st
import json
from datetime import datetime
import pandas as pd

from src.auth import AuthManager
from src.database import FirestoreManager
from src.models import SemesterPlan, AirlineAction
from src.workflow import SimulationWorkflow


def main():
    st.set_page_config(
        page_title="Airline Simulation",
        page_icon="✈️",
        layout="wide"
    )
    
    st.title("✈️ Airline Competition Simulation")
    
    # Initialize managers
    auth_manager = AuthManager()
    db_manager = FirestoreManager()
    
    # Authentication
    name, authentication_status, username = auth_manager.login()
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
        return
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        return
    elif authentication_status:
        # Main application
        with st.sidebar:
            st.write(f'Welcome *{name}*')
            auth_manager.logout()
            
            st.divider()
            
            page = st.selectbox(
                "Navigation",
                ["Dashboard", "Submit Plan", "Market Analysis", "Feedback History"]
            )
        
        if page == "Dashboard":
            show_dashboard(username, db_manager)
        elif page == "Submit Plan":
            show_plan_submission(username, db_manager)
        elif page == "Market Analysis":
            show_market_analysis(db_manager)
        elif page == "Feedback History":
            show_feedback_history(username, db_manager)


def show_dashboard(team_id: str, db_manager: FirestoreManager):
    st.header("📊 Airline Dashboard")
    
    # Get airline state
    airline_state = db_manager.get_airline_state(team_id)
    market_state = db_manager.get_market_state()
    
    if not airline_state:
        st.error("Airline data not found. Please contact administrator.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Cash Available", f"${airline_state.cash:,.0f}")
    
    with col2:
        st.metric("Aircraft Fleet", airline_state.aircraft_count)
    
    with col3:
        st.metric("Market Share", f"{airline_state.market_share:.2%}")
    
    with col4:
        st.metric("Reputation", f"{airline_state.reputation}/100")
    
    st.divider()
    
    # Airline details
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 Airline Status")
        st.write(f"**Name:** {airline_state.name}")
        st.write(f"**Active Routes:** {len(airline_state.routes)}")
        if airline_state.routes:
            st.write("**Route List:**")
            for route in airline_state.routes:
                st.write(f"- {route}")
        else:
            st.write("No active routes")
        
        st.write(f"**Last Updated:** {airline_state.last_updated.strftime('%Y-%m-%d %H:%M')}")
    
    with col2:
        st.subheader("🌍 Market Conditions")
        if market_state:
            st.write(f"**Total Market Size:** {market_state.total_passengers:,} passengers")
            st.write(f"**Competition Level:** {market_state.competition_level:.2f}/1.0")
            st.write(f"**Economic Conditions:** {market_state.economic_conditions.title()}")
            
            if market_state.events:
                st.write("**Recent Market Events:**")
                for event in market_state.events[-3:]:  # Show last 3 events
                    st.write(f"- {event}")
        else:
            st.warning("Market data not available")


def show_plan_submission(team_id: str, db_manager: FirestoreManager):
    st.header("📋 Submit Semester Plan")
    
    airline_state = db_manager.get_airline_state(team_id)
    if not airline_state:
        st.error("Airline data not found.")
        return
    
    st.info(f"Available Budget: ${airline_state.cash:,.0f}")
    
    # Plan submission form
    with st.form("plan_submission"):
        semester = st.selectbox("Semester", ["2024-1", "2024-2", "2025-1", "2025-2"])
        
        st.subheader("Upload Plan")
        uploaded_file = st.file_uploader(
            "Upload JSON Plan File",
            type=['json'],
            help="Upload a JSON file containing your semester plan"
        )
        
        # Manual plan entry alternative
        st.subheader("Or Create Plan Manually")
        
        num_actions = st.number_input("Number of Actions", min_value=1, max_value=10, value=3)
        
        actions = []
        total_cost = 0
        
        for i in range(num_actions):
            st.write(f"**Action {i+1}**")
            col1, col2 = st.columns(2)
            
            with col1:
                action_type = st.selectbox(
                    f"Action Type {i+1}",
                    ["purchase_aircraft", "add_route", "marketing_campaign", 
                     "staff_training", "maintenance_upgrade"],
                    key=f"action_type_{i}"
                )
                
                description = st.text_input(
                    f"Description {i+1}",
                    key=f"description_{i}",
                    placeholder="Describe this action..."
                )
            
            with col2:
                cost = st.number_input(
                    f"Cost {i+1}",
                    min_value=0,
                    max_value=airline_state.cash,
                    key=f"cost_{i}"
                )
                
                # Action-specific parameters
                if action_type == "purchase_aircraft":
                    aircraft_count = st.number_input(f"Aircraft Count {i+1}", min_value=1, value=1, key=f"aircraft_{i}")
                    parameters = {"count": aircraft_count}
                elif action_type == "add_route":
                    route = st.text_input(f"Route {i+1}", key=f"route_{i}", placeholder="e.g., PRG-LHR")
                    parameters = {"route": route}
                elif action_type == "marketing_campaign":
                    reputation_impact = st.slider(f"Reputation Impact {i+1}", 1, 10, 5, key=f"reputation_{i}")
                    parameters = {"reputation_impact": reputation_impact}
                else:
                    parameters = {}
            
            if description and cost > 0:
                action = AirlineAction(
                    action_type=action_type,
                    description=description,
                    cost=float(cost),
                    parameters=parameters
                )
                actions.append(action)
                total_cost += cost
        
        st.write(f"**Total Plan Cost: ${total_cost:,.0f}**")
        
        if total_cost > airline_state.cash:
            st.error(f"Plan exceeds available budget by ${total_cost - airline_state.cash:,.0f}")
        
        submitted = st.form_submit_button("Submit Plan")
        
        if submitted:
            plan_data = None
            
            # Process uploaded file
            if uploaded_file:
                try:
                    plan_data = json.load(uploaded_file)
                except json.JSONDecodeError:
                    st.error("Invalid JSON file")
                    return
            
            # Process manual entry
            elif actions:
                plan_data = {
                    "team_id": team_id,
                    "semester": semester,
                    "actions": [action.model_dump() for action in actions],
                    "total_budget": total_cost,
                    "submission_timestamp": datetime.now().isoformat()
                }
            
            if plan_data:
                try:
                    # Create SemesterPlan object
                    plan = SemesterPlan(
                        team_id=team_id,
                        semester=semester,
                        actions=[AirlineAction(**action) for action in plan_data["actions"]],
                        total_budget=plan_data["total_budget"],
                        submission_timestamp=datetime.now()
                    )
                    
                    # Save plan
                    if db_manager.save_semester_plan(plan):
                        st.success("Plan submitted successfully!")
                        
                        # Process plan through workflow
                        workflow = SimulationWorkflow()
                        try:
                            results = workflow.process_semester_plans([plan])
                            st.success("Plan processed successfully!")
                            
                            # Show results
                            if team_id in results:
                                result = results[team_id]
                                st.write("### Processing Results")
                                st.write(f"**Approved Actions:** {len(result['company_response'].approved_actions)}")
                                st.write(f"**Rejected Actions:** {len(result['company_response'].rejected_actions)}")
                                st.write(f"**Cash Used:** ${result['company_response'].cash_used:,.0f}")
                                
                                if result['evaluation']:
                                    st.write(f"**Score:** {result['evaluation'].score}/100")
                                    st.write(f"**Feedback:** {result['evaluation'].feedback_text}")
                        
                        except Exception as e:
                            st.error(f"Error processing plan: {str(e)}")
                    
                    else:
                        st.error("Failed to save plan")
                        
                except Exception as e:
                    st.error(f"Error creating plan: {str(e)}")
            else:
                st.warning("Please upload a file or create a manual plan")


def show_market_analysis(db_manager: FirestoreManager):
    st.header("📈 Market Analysis")
    
    market_state = db_manager.get_market_state()
    all_airlines = db_manager.get_all_airline_states()
    
    if not market_state:
        st.warning("Market data not available")
        return
    
    # Market overview
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Market Overview")
        st.metric("Total Passengers", f"{market_state.total_passengers:,}")
        st.metric("Competition Level", f"{market_state.competition_level:.2f}")
        st.write(f"**Economic Conditions:** {market_state.economic_conditions.title()}")
    
    with col2:
        st.subheader("Recent Events")
        if market_state.events:
            for event in market_state.events:
                st.write(f"• {event}")
        else:
            st.write("No recent events")
    
    # Airline comparison
    if all_airlines:
        st.subheader("Airline Performance")
        
        df_data = []
        for airline in all_airlines:
            df_data.append({
                "Team": airline.team_id,
                "Market Share": f"{airline.market_share:.2%}",
                "Reputation": airline.reputation,
                "Aircraft": airline.aircraft_count,
                "Routes": len(airline.routes),
                "Cash": f"${airline.cash:,.0f}"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        # Market share chart
        if len(all_airlines) > 1:
            st.subheader("Market Share Distribution")
            market_share_data = {airline.team_id: airline.market_share for airline in all_airlines}
            st.bar_chart(market_share_data)


def show_feedback_history(team_id: str, db_manager: FirestoreManager):
    st.header("📝 Feedback History")
    
    # This would need to be implemented in the database manager
    st.info("Feedback history feature will be available after plan submissions and evaluations.")


if __name__ == "__main__":
    main()