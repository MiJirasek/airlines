import litellm
from typing import List, Dict, Any
from datetime import datetime
import random

from ..models import AirlineState, MarketState, AgentResponse
from ..database import FirestoreManager
from ..config import Config
from ..observability import trace_market_agent


class MarketAgent:
    def __init__(self):
        self.db = FirestoreManager()
    
    @trace_market_agent
    def evaluate_market_performance(self, all_responses: List[AgentResponse]) -> Dict[str, Any]:
        all_airlines = self.db.get_all_airline_states()
        current_market = self.db.get_market_state()
        
        if not current_market:
            current_market = MarketState(
                total_passengers=1000000,
                competition_level=0.5,
                economic_conditions="stable",
                events=[],
                last_updated=datetime.now()
            )
        
        # Calculate market dynamics
        market_analysis = self._analyze_market_competition(all_airlines)
        
        # Generate market events
        new_events = self._generate_market_events(current_market, all_airlines)
        
        # Update airline performance based on actions
        updated_airlines = []
        for airline in all_airlines:
            updated_airline = self._calculate_airline_performance(
                airline, all_airlines, current_market, market_analysis
            )
            updated_airlines.append(updated_airline)
            self.db.update_airline_state(updated_airline)
        
        # Update market state
        updated_market = MarketState(
            total_passengers=self._calculate_total_demand(market_analysis, current_market),
            competition_level=market_analysis["competition_intensity"],
            economic_conditions=self._determine_economic_conditions(new_events),
            events=new_events,
            last_updated=datetime.now()
        )
        
        self.db.update_market_state(updated_market)
        
        return {
            "market_state": updated_market,
            "airlines": updated_airlines,
            "market_analysis": market_analysis
        }
    
    def _analyze_market_competition(self, airlines: List[AirlineState]) -> Dict[str, Any]:
        if not airlines:
            return {
                "competition_intensity": 0.1,
                "market_concentration": 0.0,
                "total_capacity": 0,
                "average_reputation": 50.0
            }
        
        total_aircraft = sum(airline.aircraft_count for airline in airlines)
        total_routes = len(set().union(*[airline.routes for airline in airlines]))
        market_shares = [airline.market_share for airline in airlines]
        reputations = [airline.reputation for airline in airlines]
        
        # Calculate Herfindahl-Hirschman Index for market concentration
        hhi = sum(share ** 2 for share in market_shares) if market_shares else 0
        
        competition_intensity = min(1.0, total_aircraft / 20)  # Normalize to 0-1
        
        return {
            "competition_intensity": competition_intensity,
            "market_concentration": hhi,
            "total_capacity": total_aircraft,
            "total_routes": total_routes,
            "average_reputation": sum(reputations) / len(reputations) if reputations else 50.0
        }
    
    def _generate_market_events(self, current_market: MarketState, airlines: List[AirlineState]) -> List[str]:
        events = []
        
        # Economic events (30% probability)
        if random.random() < 0.3:
            economic_events = [
                "Fuel prices increased by 15% due to geopolitical tensions",
                "Tourism boom increases passenger demand by 20%", 
                "Economic recession reduces business travel by 25%",
                "New airport opens, creating expansion opportunities",
                "Government introduces new aviation taxes"
            ]
            events.append(random.choice(economic_events))
        
        # Competition events (25% probability)
        if random.random() < 0.25:
            competition_events = [
                "New low-cost carrier enters the market",
                "Major competitor files for bankruptcy",
                "International airline alliance forms",
                "Price war initiated by market leader",
                "New regulatory restrictions on routes"
            ]
            events.append(random.choice(competition_events))
        
        # Operational events (20% probability)
        if random.random() < 0.2:
            operational_events = [
                "Air traffic control strikes cause delays",
                "Weather disruptions affect 30% of flights",
                "New safety regulations require aircraft modifications",
                "Pilot shortage affects industry capacity",
                "Technology upgrade improves efficiency"
            ]
            events.append(random.choice(operational_events))
        
        return events
    
    def _calculate_airline_performance(
        self, 
        airline: AirlineState, 
        all_airlines: List[AirlineState],
        market_state: MarketState,
        market_analysis: Dict[str, Any]
    ) -> AirlineState:
        
        updated_airline = airline.model_copy()
        
        # Calculate market share based on capacity and reputation
        total_capacity = market_analysis["total_capacity"]
        if total_capacity > 0:
            capacity_share = airline.aircraft_count / total_capacity
            reputation_factor = airline.reputation / 100
            
            # Market share influenced by capacity and reputation
            base_share = capacity_share * reputation_factor
            updated_airline.market_share = min(1.0, base_share * (1 + random.uniform(-0.1, 0.1)))
        
        # Use AI to evaluate strategic performance
        performance_analysis = self._ai_performance_evaluation(
            airline, market_state, market_analysis
        )
        
        # Apply performance adjustments
        if "reputation_change" in performance_analysis:
            reputation_delta = performance_analysis["reputation_change"]
            updated_airline.reputation = max(0, min(100, 
                updated_airline.reputation + reputation_delta
            ))
        
        updated_airline.last_updated = datetime.now()
        
        return updated_airline
    
    def _ai_performance_evaluation(
        self, 
        airline: AirlineState, 
        market_state: MarketState,
        market_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        evaluation_prompt = f"""
        Evaluate this airline's market performance:
        
        Airline: {airline.name}
        - Aircraft: {airline.aircraft_count}
        - Routes: {len(airline.routes)}
        - Market Share: {airline.market_share:.2%}
        - Reputation: {airline.reputation}/100
        - Cash: ${airline.cash:,}
        
        Market Conditions:
        - Total Passengers: {market_state.total_passengers:,}
        - Competition Level: {market_state.competition_level:.2f}
        - Economic Conditions: {market_state.economic_conditions}
        - Recent Events: {market_state.events}
        
        Market Analysis:
        - Competition Intensity: {market_analysis['competition_intensity']:.2f}
        - Average Reputation: {market_analysis['average_reputation']:.1f}
        
        Provide a JSON response with:
        {{
            "reputation_change": -5 to +5,
            "performance_rating": "poor|average|good|excellent",
            "key_factors": ["factor1", "factor2"]
        }}
        """
        
        try:
            response = litellm.completion(
                model="gemini/gemini-pro",
                messages=[{"role": "user", "content": evaluation_prompt}],
                api_key=Config.GEMINI_API_KEY
            )
            
            # Parse AI response (simplified - in production, use proper JSON parsing)
            content = response.choices[0].message.content
            
            # Extract reputation change (simple regex-like approach)
            if "reputation_change" in content:
                import re
                match = re.search(r'"reputation_change":\s*(-?\d+)', content)
                if match:
                    reputation_change = int(match.group(1))
                    return {"reputation_change": max(-5, min(5, reputation_change))}
            
            return {"reputation_change": 0}
            
        except Exception as e:
            print(f"AI evaluation failed: {e}")
            return {"reputation_change": 0}
    
    def _calculate_total_demand(self, market_analysis: Dict[str, Any], current_market: MarketState) -> int:
        base_demand = current_market.total_passengers
        
        # Adjust demand based on market conditions
        competition_factor = 1 + (market_analysis["competition_intensity"] * 0.2)
        reputation_factor = 1 + ((market_analysis["average_reputation"] - 50) / 100 * 0.1)
        
        # Random market fluctuation
        random_factor = 1 + random.uniform(-0.05, 0.05)
        
        new_demand = int(base_demand * competition_factor * reputation_factor * random_factor)
        return max(800000, min(1500000, new_demand))  # Keep within reasonable bounds
    
    def _determine_economic_conditions(self, events: List[str]) -> str:
        negative_keywords = ["recession", "crisis", "strike", "disruption", "tax"]
        positive_keywords = ["boom", "growth", "opportunity", "efficiency", "upgrade"]
        
        negative_count = sum(1 for event in events 
                           for keyword in negative_keywords 
                           if keyword in event.lower())
        
        positive_count = sum(1 for event in events
                           for keyword in positive_keywords
                           if keyword in event.lower())
        
        if positive_count > negative_count:
            return "growing"
        elif negative_count > positive_count:
            return "declining"
        else:
            return "stable"