from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
from typing_extensions import TypedDict
import operator
import litellm
from datetime import datetime

from ..models import SemesterPlan, AirlineState, AirlineAction, AgentResponse
from ..database import FirestoreManager
from ..config import Config
from ..observability import trace_company_agent


class CompanyAgentState(TypedDict):
    plan: SemesterPlan
    airline_state: AirlineState
    approved_actions: Annotated[List[AirlineAction], operator.add]
    rejected_actions: Annotated[List[AirlineAction], operator.add]
    validation_messages: Annotated[List[str], operator.add]
    cash_used: float


class CompanyAgent:
    def __init__(self):
        self.db = FirestoreManager()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(CompanyAgentState)
        
        # Add nodes
        workflow.add_node("validator", self._validator_node)
        workflow.add_node("implementer", self._implementer_node)
        
        # Add edges
        workflow.set_entry_point("validator")
        workflow.add_edge("validator", "implementer")
        workflow.add_edge("implementer", END)
        
        return workflow.compile()
    
    def _validator_node(self, state: CompanyAgentState) -> CompanyAgentState:
        plan = state["plan"]
        airline_state = state["airline_state"]
        
        # Validate budget constraints
        total_cost = sum(action.cost for action in plan.actions)
        if total_cost > airline_state.cash:
            over_budget = total_cost - airline_state.cash
            state["validation_messages"].append(
                f"Plan is over budget by ${over_budget:,.2f}. Available: ${airline_state.cash:,.2f}, Requested: ${total_cost:,.2f}"
            )
        
        # Validate capacity constraints
        aircraft_intensive_actions = [
            action for action in plan.actions 
            if action.action_type in ["add_route", "increase_frequency"]
        ]
        
        if len(aircraft_intensive_actions) > airline_state.aircraft_count:
            state["validation_messages"].append(
                f"Insufficient aircraft for route operations. Available: {airline_state.aircraft_count}, Required: {len(aircraft_intensive_actions)}"
            )
        
        # Use AI to validate strategic coherence
        validation_prompt = f"""
        Analyze this airline's semester plan for strategic coherence and feasibility:
        
        Airline State:
        - Cash: ${airline_state.cash:,}
        - Aircraft: {airline_state.aircraft_count}
        - Current Routes: {airline_state.routes}
        - Market Share: {airline_state.market_share:.2%}
        - Reputation: {airline_state.reputation}/100
        
        Proposed Actions:
        {[f"- {action.action_type}: {action.description} (${action.cost:,})" for action in plan.actions]}
        
        Total Budget: ${plan.total_budget:,}
        
        Provide a brief assessment of:
        1. Strategic coherence
        2. Risk factors
        3. Feasibility concerns
        
        Keep response under 200 words.
        """
        
        try:
            response = litellm.completion(
                model="gemini/gemini-pro",
                messages=[{"role": "user", "content": validation_prompt}],
                api_key=Config.GEMINI_API_KEY
            )
            
            ai_validation = response.choices[0].message.content
            state["validation_messages"].append(f"AI Strategic Assessment: {ai_validation}")
            
        except Exception as e:
            state["validation_messages"].append(f"AI validation failed: {str(e)}")
        
        return state
    
    def _implementer_node(self, state: CompanyAgentState) -> CompanyAgentState:
        plan = state["plan"]
        airline_state = state["airline_state"]
        available_cash = airline_state.cash
        
        # Sort actions by priority/cost ratio for optimal implementation
        sorted_actions = sorted(plan.actions, key=lambda x: x.cost)
        
        cash_used = 0
        approved_actions = []
        rejected_actions = []
        
        for action in sorted_actions:
            if cash_used + action.cost <= available_cash:
                # Additional feasibility checks
                if self._is_action_feasible(action, airline_state):
                    approved_actions.append(action)
                    cash_used += action.cost
                else:
                    rejected_actions.append(action)
            else:
                rejected_actions.append(action)
        
        state["approved_actions"] = approved_actions
        state["rejected_actions"] = rejected_actions
        state["cash_used"] = cash_used
        
        return state
    
    def _is_action_feasible(self, action: AirlineAction, airline_state: AirlineState) -> bool:
        if action.action_type == "purchase_aircraft":
            return True  # Can always buy aircraft if budget allows
        
        elif action.action_type == "add_route":
            return airline_state.aircraft_count > len(airline_state.routes)
        
        elif action.action_type == "marketing_campaign":
            return True  # Can always do marketing
        
        elif action.action_type == "staff_training":
            return True  # Can always train staff
        
        elif action.action_type == "maintenance_upgrade":
            return airline_state.aircraft_count > 0
        
        return True  # Default to feasible
    
    @trace_company_agent
    def process_plan(self, plan: SemesterPlan, team_id: str) -> AgentResponse:
        airline_state = self.db.get_airline_state(team_id)
        
        if not airline_state:
            raise ValueError(f"Airline state not found for team {team_id}")
        
        initial_state = CompanyAgentState(
            plan=plan,
            airline_state=airline_state,
            approved_actions=[],
            rejected_actions=[],
            validation_messages=[],
            cash_used=0.0
        )
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Update airline state
        updated_airline = airline_state.model_copy()
        updated_airline.cash -= result["cash_used"]
        updated_airline.last_updated = datetime.now()
        
        # Apply approved actions to airline state
        for action in result["approved_actions"]:
            self._apply_action_to_state(action, updated_airline)
        
        # Save updated state
        self.db.update_airline_state(updated_airline)
        
        return AgentResponse(
            approved_actions=result["approved_actions"],
            rejected_actions=result["rejected_actions"],
            cash_used=result["cash_used"],
            reasoning="\n".join(result["validation_messages"])
        )
    
    def _apply_action_to_state(self, action: AirlineAction, airline_state: AirlineState):
        if action.action_type == "purchase_aircraft":
            count = action.parameters.get("count", 1)
            airline_state.aircraft_count += count
        
        elif action.action_type == "add_route":
            route = action.parameters.get("route")
            if route and route not in airline_state.routes:
                airline_state.routes.append(route)
        
        elif action.action_type == "marketing_campaign":
            reputation_boost = action.parameters.get("reputation_impact", 5)
            airline_state.reputation = min(100, airline_state.reputation + reputation_boost)