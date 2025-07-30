from typing import List, Dict, Any
from datetime import datetime

from .models import SemesterPlan, AgentResponse, EvaluationFeedback
from .agents.company_agent import CompanyAgent
from .agents.market_agent import MarketAgent
from .agents.evaluation_agent import EvaluationAgent
from .database import FirestoreManager


class SimulationWorkflow:
    def __init__(self):
        self.company_agent = CompanyAgent()
        self.market_agent = MarketAgent()
        self.evaluation_agent = EvaluationAgent()
        self.db = FirestoreManager()
    
    def process_semester_plans(self, plans: List[SemesterPlan]) -> Dict[str, Any]:
        """
        Execute the complete 5-step workflow:
        1. Students submit plans
        2. Company agents evaluate and process plans
        3. Market agent evaluates market performance
        4. Evaluation agent provides feedback
        5. Results are returned to students
        """
        
        results = {}
        company_responses = []
        
        # Step 1: Plans are already submitted (input parameter)
        print(f"Processing {len(plans)} semester plans...")
        
        # Step 2: Company agent processes each plan
        print("Step 2: Company agents evaluating plans...")
        for plan in plans:
            try:
                company_response = self.company_agent.process_plan(plan, plan.team_id)
                company_responses.append(company_response)
                
                results[plan.team_id] = {
                    "plan": plan,
                    "company_response": company_response,
                    "status": "company_processed"
                }
                
            except Exception as e:
                print(f"Error processing plan for team {plan.team_id}: {e}")
                results[plan.team_id] = {
                    "plan": plan,
                    "error": str(e),
                    "status": "company_failed"
                }
        
        # Step 3: Market agent evaluates overall market performance
        print("Step 3: Market agent evaluating market performance...")
        try:
            market_results = self.market_agent.evaluate_market_performance(company_responses)
            
            # Update results with market information
            for team_id in results:
                if results[team_id]["status"] == "company_processed":
                    results[team_id]["market_results"] = market_results
                    results[team_id]["status"] = "market_processed"
            
        except Exception as e:
            print(f"Error in market evaluation: {e}")
            # Continue with individual evaluations even if market fails
            market_results = None
        
        # Step 4: Evaluation agent provides feedback
        print("Step 4: Evaluation agent providing feedback...")
        for team_id, result in results.items():
            if result["status"] in ["company_processed", "market_processed"]:
                try:
                    evaluation = self.evaluation_agent.evaluate_team_performance(
                        team_id=team_id,
                        plan=result["plan"],
                        company_response=result["company_response"],
                        market_results=market_results or {}
                    )
                    
                    result["evaluation"] = evaluation
                    result["status"] = "completed"
                    
                except Exception as e:
                    print(f"Error evaluating team {team_id}: {e}")
                    result["evaluation_error"] = str(e)
                    result["status"] = "evaluation_failed"
        
        # Step 5: Results are now ready for students (returned by this method)
        print("Step 5: Results ready for students")
        
        # Generate summary for instructors
        try:
            instructor_summary = self.evaluation_agent.generate_instructor_summary()
            results["_instructor_summary"] = instructor_summary
        except Exception as e:
            print(f"Error generating instructor summary: {e}")
        
        return results
    
    def process_single_plan(self, plan: SemesterPlan) -> Dict[str, Any]:
        """Process a single plan through the workflow"""
        return self.process_semester_plans([plan])
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status and statistics"""
        try:
            all_airlines = self.db.get_all_airline_states()
            market_state = self.db.get_market_state()
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "total_airlines": len(all_airlines),
                "market_state": market_state.model_dump() if market_state else None,
                "airlines_summary": [
                    {
                        "team_id": airline.team_id,
                        "name": airline.name,
                        "market_share": airline.market_share,
                        "reputation": airline.reputation,
                        "cash": airline.cash,
                        "aircraft_count": airline.aircraft_count
                    }
                    for airline in all_airlines
                ],
                "top_performers": self._get_top_performers(all_airlines)
            }
            
            return status
            
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _get_top_performers(self, airlines: List) -> Dict[str, Any]:
        """Identify top performing airlines across different metrics"""
        if not airlines:
            return {}
        
        # Sort by different metrics
        by_market_share = sorted(airlines, key=lambda x: x.market_share, reverse=True)
        by_reputation = sorted(airlines, key=lambda x: x.reputation, reverse=True)
        by_cash = sorted(airlines, key=lambda x: x.cash, reverse=True)
        
        return {
            "market_leader": {
                "team_id": by_market_share[0].team_id,
                "market_share": by_market_share[0].market_share
            } if by_market_share else None,
            "highest_reputation": {
                "team_id": by_reputation[0].team_id,
                "reputation": by_reputation[0].reputation
            } if by_reputation else None,
            "most_cash": {
                "team_id": by_cash[0].team_id,
                "cash": by_cash[0].cash
            } if by_cash else None
        }
    
    def reset_simulation(self) -> bool:
        """Reset simulation to initial state (for testing/new semester)"""
        try:
            # This would implement reset logic
            # For now, just initialize default market data
            self.db.initialize_default_data()
            return True
        except Exception as e:
            print(f"Error resetting simulation: {e}")
            return False
    
    def batch_process_from_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple plan files in batch"""
        import json
        from .models import AirlineAction
        
        plans = []
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r') as f:
                    plan_data = json.load(f)
                
                plan = SemesterPlan(
                    team_id=plan_data["team_id"],
                    semester=plan_data["semester"],
                    actions=[AirlineAction(**action) for action in plan_data["actions"]],
                    total_budget=plan_data["total_budget"],
                    submission_timestamp=datetime.now()
                )
                
                plans.append(plan)
                
            except Exception as e:
                print(f"Error loading plan from {file_path}: {e}")
        
        if plans:
            return self.process_semester_plans(plans)
        else:
            return {"error": "No valid plans found in provided files"}