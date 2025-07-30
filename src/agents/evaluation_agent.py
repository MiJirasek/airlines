import litellm
from typing import List, Dict, Any
from datetime import datetime

from ..models import AirlineState, MarketState, EvaluationFeedback, SemesterPlan, AgentResponse
from ..database import FirestoreManager
from ..config import Config
from ..observability import trace_evaluation_agent


class EvaluationAgent:
    def __init__(self):
        self.db = FirestoreManager()
    
    @trace_evaluation_agent
    def evaluate_team_performance(
        self, 
        team_id: str, 
        plan: SemesterPlan,
        company_response: AgentResponse,
        market_results: Dict[str, Any]
    ) -> EvaluationFeedback:
        
        airline_state = self.db.get_airline_state(team_id)
        market_state = self.db.get_market_state()
        
        if not airline_state:
            raise ValueError(f"Airline state not found for team {team_id}")
        
        # Generate comprehensive evaluation
        evaluation_prompt = self._build_evaluation_prompt(
            plan, company_response, airline_state, market_state, market_results
        )
        
        try:
            response = litellm.completion(
                model="gemini/gemini-pro",
                messages=[{"role": "user", "content": evaluation_prompt}],
                api_key=Config.GEMINI_API_KEY
            )
            
            ai_feedback = response.choices[0].message.content
            
            # Parse AI response and calculate score
            parsed_feedback = self._parse_ai_feedback(ai_feedback)
            
            feedback = EvaluationFeedback(
                team_id=team_id,
                score=parsed_feedback["score"],
                feedback_text=parsed_feedback["feedback_text"],
                strengths=parsed_feedback["strengths"],
                improvement_areas=parsed_feedback["improvement_areas"],
                created_at=datetime.now()
            )
            
            # Save feedback to database
            self.db.save_evaluation_feedback(feedback)
            
            return feedback
            
        except Exception as e:
            # Fallback evaluation if AI fails
            return self._generate_fallback_evaluation(
                team_id, plan, company_response, airline_state
            )
    
    def _build_evaluation_prompt(
        self,
        plan: SemesterPlan,
        company_response: AgentResponse,
        airline_state: AirlineState,
        market_state: MarketState,
        market_results: Dict[str, Any]
    ) -> str:
        
        return f"""
        You are an expert business strategy evaluator for an airline simulation game. 
        Provide comprehensive feedback on a student team's strategic implementation.
        
        TEAM SUBMISSION:
        Team: {plan.team_id}
        Semester: {plan.semester}
        Proposed Budget: ${plan.total_budget:,}
        
        PROPOSED ACTIONS:
        {self._format_actions(plan.actions)}
        
        COMPANY AGENT RESULTS:
        Approved Actions: {len(company_response.approved_actions)}
        Rejected Actions: {len(company_response.rejected_actions)}
        Cash Used: ${company_response.cash_used:,}
        
        Reasoning: {company_response.reasoning}
        
        CURRENT AIRLINE STATE:
        - Cash Available: ${airline_state.cash:,}
        - Aircraft Fleet: {airline_state.aircraft_count}
        - Active Routes: {len(airline_state.routes)} ({', '.join(airline_state.routes[:3])}...)
        - Market Share: {airline_state.market_share:.2%}
        - Reputation: {airline_state.reputation}/100
        
        MARKET CONDITIONS:
        - Economic Conditions: {market_state.economic_conditions}
        - Competition Level: {market_state.competition_level:.2f}
        - Recent Events: {', '.join(market_state.events)}
        
        Please provide your evaluation in the following JSON format:
        {{
            "score": 0-100,
            "feedback_text": "Detailed paragraph explaining performance...",
            "strengths": ["strength1", "strength2", "strength3"],
            "improvement_areas": ["area1", "area2", "area3"],
            "strategic_assessment": {{
                "planning_quality": 0-10,
                "resource_allocation": 0-10,
                "market_awareness": 0-10,
                "execution_feasibility": 0-10
            }},
            "recommendations": ["recommendation1", "recommendation2"]
        }}
        
        EVALUATION CRITERIA:
        1. Strategic Coherence (25%): Do actions align with airline's situation and market conditions?
        2. Resource Management (25%): Efficient use of budget and assets?
        3. Market Awareness (25%): Understanding of competitive landscape and opportunities?
        4. Implementation Feasibility (25%): Realistic and executable plans?
        
        Be constructive, specific, and educational. This is formative feedback for student learning.
        """
    
    def _format_actions(self, actions) -> str:
        formatted = []
        for i, action in enumerate(actions, 1):
            formatted.append(
                f"{i}. {action.action_type}: {action.description} (${action.cost:,})"
            )
        return "\n".join(formatted)
    
    def _parse_ai_feedback(self, ai_response: str) -> Dict[str, Any]:
        try:
            # Simple parsing - in production, use proper JSON parsing with error handling
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                return {
                    "score": min(100, max(0, parsed.get("score", 50))),
                    "feedback_text": parsed.get("feedback_text", "No detailed feedback available."),
                    "strengths": parsed.get("strengths", ["Strategic thinking"]),
                    "improvement_areas": parsed.get("improvement_areas", ["Resource planning"])
                }
            else:
                # Fallback parsing if JSON not found
                return self._simple_text_parsing(ai_response)
                
        except Exception as e:
            print(f"Error parsing AI feedback: {e}")
            return self._simple_text_parsing(ai_response)
    
    def _simple_text_parsing(self, text: str) -> Dict[str, Any]:
        # Extract score if mentioned
        import re
        score_match = re.search(r'score[:\s]*(\d+)', text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 75
        
        # Basic strengths and weaknesses extraction
        strengths = []
        improvement_areas = []
        
        if "good" in text.lower() or "strong" in text.lower():
            strengths.append("Strategic execution")
        if "coherent" in text.lower():
            strengths.append("Plan coherence")
        if "realistic" in text.lower():
            strengths.append("Realistic planning")
            
        if "improve" in text.lower():
            improvement_areas.append("Strategic refinement")
        if "budget" in text.lower() and ("over" in text.lower() or "exceed" in text.lower()):
            improvement_areas.append("Budget management")
        if "risk" in text.lower():
            improvement_areas.append("Risk assessment")
        
        return {
            "score": min(100, max(0, score)),
            "feedback_text": text[:500] + "..." if len(text) > 500 else text,
            "strengths": strengths if strengths else ["Strategic thinking"],
            "improvement_areas": improvement_areas if improvement_areas else ["Implementation planning"]
        }
    
    def _generate_fallback_evaluation(
        self,
        team_id: str,
        plan: SemesterPlan,
        company_response: AgentResponse,
        airline_state: AirlineState
    ) -> EvaluationFeedback:
        
        # Basic scoring based on approval rate and budget usage
        approval_rate = len(company_response.approved_actions) / len(plan.actions) if plan.actions else 0
        budget_efficiency = company_response.cash_used / plan.total_budget if plan.total_budget > 0 else 0
        
        base_score = (approval_rate * 50) + (budget_efficiency * 30) + 20  # Base 20 points
        score = min(100, max(0, int(base_score)))
        
        strengths = []
        improvement_areas = []
        
        if approval_rate > 0.8:
            strengths.append("High plan feasibility")
        if budget_efficiency > 0.7:
            strengths.append("Efficient resource allocation")
        if len(plan.actions) > 5:
            strengths.append("Comprehensive planning")
            
        if approval_rate < 0.5:
            improvement_areas.append("Plan feasibility and validation")
        if budget_efficiency < 0.5:
            improvement_areas.append("Budget planning and utilization")
        if len(company_response.rejected_actions) > 3:
            improvement_areas.append("Resource constraint awareness")
        
        feedback_text = f"""
        Your semester plan achieved a {approval_rate:.1%} approval rate with {len(company_response.approved_actions)} 
        out of {len(plan.actions)} actions implemented. You utilized ${company_response.cash_used:,} 
        of your ${plan.total_budget:,} budget ({budget_efficiency:.1%} efficiency).
        
        Focus on aligning your strategic actions with your airline's current capabilities and market position.
        """
        
        return EvaluationFeedback(
            team_id=team_id,
            score=score,
            feedback_text=feedback_text.strip(),
            strengths=strengths if strengths else ["Strategic initiative"],
            improvement_areas=improvement_areas if improvement_areas else ["Strategic alignment"],
            created_at=datetime.now()
        )
    
    def generate_instructor_summary(self) -> Dict[str, Any]:
        all_airlines = self.db.get_all_airline_states()
        
        if not all_airlines:
            return {"message": "No airline data available"}
        
        # Calculate class statistics
        scores = []  # Would need to get recent evaluation scores
        market_shares = [airline.market_share for airline in all_airlines]
        reputations = [airline.reputation for airline in all_airlines]
        
        summary = {
            "total_teams": len(all_airlines),
            "market_distribution": {
                airline.team_id: {
                    "market_share": airline.market_share,
                    "reputation": airline.reputation,
                    "aircraft_count": airline.aircraft_count,
                    "cash": airline.cash
                }
                for airline in all_airlines
            },
            "class_averages": {
                "reputation": sum(reputations) / len(reputations) if reputations else 0,
                "market_share": sum(market_shares) / len(market_shares) if market_shares else 0
            }
        }
        
        return summary