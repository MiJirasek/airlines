import os
from typing import Optional, Dict, Any
from datetime import datetime
import json

try:
    from langsmith import Client
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Define dummy decorator if langsmith not available
    def traceable(name: Optional[str] = None):
        def decorator(func):
            return func
        return decorator

from .config import Config


class ObservabilityManager:
    def __init__(self):
        self.client = None
        self.enabled = False
        self._initialize_langsmith()
    
    def _initialize_langsmith(self):
        if not LANGSMITH_AVAILABLE:
            print("LangSmith not available - observability disabled")
            return
        
        if Config.LANGSMITH_API_KEY and Config.LANGSMITH_PROJECT:
            try:
                os.environ["LANGSMITH_API_KEY"] = Config.LANGSMITH_API_KEY
                os.environ["LANGSMITH_PROJECT"] = Config.LANGSMITH_PROJECT
                
                self.client = Client()
                self.enabled = True
                print(f"LangSmith observability enabled for project: {Config.LANGSMITH_PROJECT}")
                
            except Exception as e:
                print(f"Failed to initialize LangSmith: {e}")
                self.enabled = False
        else:
            print("LangSmith credentials not configured - observability disabled")
    
    def log_plan_submission(self, team_id: str, plan_data: Dict[str, Any]):
        """Log when a team submits a plan"""
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name="plan_submission",
                run_type="chain",
                inputs={
                    "team_id": team_id,
                    "semester": plan_data.get("semester"),
                    "action_count": len(plan_data.get("actions", [])),
                    "total_budget": plan_data.get("total_budget")
                },
                outputs={
                    "status": "submitted",
                    "timestamp": datetime.now().isoformat()
                },
                project_name=Config.LANGSMITH_PROJECT
            )
        except Exception as e:
            print(f"Failed to log plan submission: {e}")
    
    def log_agent_evaluation(
        self, 
        agent_type: str, 
        team_id: str, 
        inputs: Dict[str, Any], 
        outputs: Dict[str, Any],
        duration_ms: Optional[int] = None
    ):
        """Log agent evaluation results"""
        if not self.enabled:
            return
        
        try:
            run_data = {
                "name": f"{agent_type}_evaluation",
                "run_type": "llm",
                "inputs": {
                    "team_id": team_id,
                    **inputs
                },
                "outputs": outputs,
                "project_name": Config.LANGSMITH_PROJECT
            }
            
            if duration_ms:
                run_data["duration_ms"] = duration_ms
            
            self.client.create_run(**run_data)
            
        except Exception as e:
            print(f"Failed to log agent evaluation: {e}")
    
    def log_workflow_execution(
        self, 
        workflow_id: str, 
        team_count: int, 
        success_count: int, 
        error_count: int,
        duration_ms: Optional[int] = None
    ):
        """Log complete workflow execution"""
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name="workflow_execution",
                run_type="chain",
                inputs={
                    "workflow_id": workflow_id,
                    "team_count": team_count
                },
                outputs={
                    "success_count": success_count,
                    "error_count": error_count,
                    "success_rate": success_count / team_count if team_count > 0 else 0,
                    "timestamp": datetime.now().isoformat()
                },
                project_name=Config.LANGSMITH_PROJECT
            )
            
        except Exception as e:
            print(f"Failed to log workflow execution: {e}")
    
    def log_market_update(self, market_data: Dict[str, Any]):
        """Log market state updates"""
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name="market_update",
                run_type="chain",
                inputs={
                    "previous_state": "market_analysis"
                },
                outputs={
                    "total_passengers": market_data.get("total_passengers"),
                    "competition_level": market_data.get("competition_level"),
                    "economic_conditions": market_data.get("economic_conditions"),
                    "event_count": len(market_data.get("events", [])),
                    "timestamp": datetime.now().isoformat()
                },
                project_name=Config.LANGSMITH_PROJECT
            )
            
        except Exception as e:
            print(f"Failed to log market update: {e}")
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log errors for debugging"""
        if not self.enabled:
            return
        
        try:
            self.client.create_run(
                name="error_event",
                run_type="chain",
                inputs={
                    "error_type": error_type,
                    "context": context or {}
                },
                outputs={
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat()
                },
                project_name=Config.LANGSMITH_PROJECT
            )
            
        except Exception as e:
            print(f"Failed to log error: {e}")


# Create global instance
observability = ObservabilityManager()


# Decorators for automatic tracing
def trace_company_agent(func):
    """Decorator for Company Agent methods"""
    if not observability.enabled:
        return func
    
    @traceable(name="company_agent_process")
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            
            # Log success
            duration = (datetime.now() - start_time).total_seconds() * 1000
            if hasattr(result, 'model_dump'):
                outputs = result.model_dump()
            else:
                outputs = {"result": str(result)}
            
            observability.log_agent_evaluation(
                agent_type="company",
                team_id=kwargs.get("team_id", "unknown"),
                inputs={"method": func.__name__},
                outputs=outputs,
                duration_ms=int(duration)
            )
            
            return result
            
        except Exception as e:
            # Log error
            observability.log_error(
                error_type="company_agent_error",
                error_message=str(e),
                context={"method": func.__name__, "args": str(args), "kwargs": str(kwargs)}
            )
            raise
    
    return wrapper


def trace_market_agent(func):
    """Decorator for Market Agent methods"""
    if not observability.enabled:
        return func
    
    @traceable(name="market_agent_process")
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            
            # Log success
            duration = (datetime.now() - start_time).total_seconds() * 1000
            observability.log_agent_evaluation(
                agent_type="market",
                team_id="system",
                inputs={"method": func.__name__},
                outputs={"result_type": type(result).__name__},
                duration_ms=int(duration)
            )
            
            return result
            
        except Exception as e:
            # Log error
            observability.log_error(
                error_type="market_agent_error", 
                error_message=str(e),
                context={"method": func.__name__}
            )
            raise
    
    return wrapper


def trace_evaluation_agent(func):
    """Decorator for Evaluation Agent methods"""
    if not observability.enabled:
        return func
    
    @traceable(name="evaluation_agent_process")
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        try:
            result = func(*args, **kwargs)
            
            # Log success
            duration = (datetime.now() - start_time).total_seconds() * 1000
            if hasattr(result, 'model_dump'):
                outputs = {"score": getattr(result, 'score', None)}
            else:
                outputs = {"result_type": type(result).__name__}
            
            observability.log_agent_evaluation(
                agent_type="evaluation",
                team_id=kwargs.get("team_id", "unknown"),
                inputs={"method": func.__name__},
                outputs=outputs,
                duration_ms=int(duration)
            )
            
            return result
            
        except Exception as e:
            # Log error
            observability.log_error(
                error_type="evaluation_agent_error",
                error_message=str(e),
                context={"method": func.__name__, "team_id": kwargs.get("team_id")}
            )
            raise
    
    return wrapper