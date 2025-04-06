from typing import Dict, List
from tools.tool_decorator import Tool
import json
from typing import Any
from config.logging import logger
from model.groq import safety_check, get_plan
from datetime import datetime
from prompt.prompt_builder import PromptBuilder
from schemas.interaction_schema import Interaction
from react.plan_executor import PlanExecutor
from react.reflection_engine import ReflectionEngine
from memory.interaction_history import state_manager, StateManager
    
class Agent:
    """
    An AI agent that uses tools to assist with user queries.
    
    The Agent class coordinates the process of:
    1. Receiving a user query
    2. Planning how to respond (with or without tools)
    3. Reflecting on and improving the plan
    4. Executing the plan using available tools
    5. Returning the final response
    
    """
    
    def __init__(self):
        """Initialize Agent with empty tool registry."""
        self._tools: Dict[str, Tool] = {}
        self._interaction_manager: StateManager = state_manager 
        self._prompt_builder = PromptBuilder()
        self._plan_executor = PlanExecutor(tools_registry = self._tools)
        self._reflection_engine = ReflectionEngine()
    
    def add_tool(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self._tools[tool.name] = tool
        
    def get_available_tools(self) -> List[str]:
        """Get list of available tool descriptions."""
        return [f"{tool.name}: {tool.description}" for tool in self._tools.values()]
        
    def create_system_prompt(self) -> str:
        """Create the system prompt for the LLM with available tools."""
        return self._prompt_builder.build_system_prompt(tools = self._tools.values())
    
    def execute(self, user_query: str, max_reflection_iterations: int = 3) -> Dict[str, Any]:
        """Execute the full pipeline: plan and execute tools."""
        
        if not user_query or not isinstance(user_query, str):
            raise ValueError("User query must be a non-empty string")
        
        if max_reflection_iterations < 0:
            raise ValueError("Max reflection iterations must be a positive integer")
            
        
        result = safety_check(content = user_query)
        if "unsafe" in result:
            print("Unsafe content detected. Please rephrase your query.")
            return {
                "warning": "The query contains potentially harmful content.",
                "status": "failed",
                "error_type": "content_safety",
                "original_query": user_query 
            }
        
        try:
            initial_plan = get_plan(user_query = user_query, system_prompt = self.create_system_prompt())
            logger.info(f"Initial Plan: {initial_plan}")
            
            print('=*='*40)
            print(f"\nInitial plan:\n{initial_plan}")
            print('=*='*40)
            
            initial_plan = json.loads(initial_plan)
            
            self._interaction_manager.add_interaction(
                interaction = Interaction(
                    timestamp = datetime.now(),
                    query = user_query,
                    plan = initial_plan
                )
            )
            
            logger.info(f'Interaction history: {self._interaction_manager.get_interaction_history()}')
            
            print(f"\nInteraction History:\n{self._interaction_manager.get_interaction_history()}")
            print('=*='*40)
            
            if not initial_plan["requires_tools"]:
                logger.info("Initial plan doesn't require tools. Skipping reflection loop.")
                return {
                    "response" : initial_plan["direct_response"],
                    "status" : "success"
                }
                
            reflection_result = self._reflection_engine.reflect_and_improve(
                user_query = user_query,
                initial_plan = initial_plan,
                system_prompt = self.create_system_prompt(),
            )
                
            final_plan = reflection_result["final_plan"]
            reflection_history = reflection_result["reflection_history"]
            
            print(f"\nFinal plan:\n{final_plan}")
            print("=*="*40)
            
            self._interaction_manager.add_interaction(
                interaction = Interaction(
                    timestamp = datetime.now(),
                    query = user_query,
                    plan = {
                        "initial_plan": initial_plan,
                        "reflection": reflection_history,
                        "final_plan": final_plan
                    }
                )
            )
            
            final_content = self._plan_executor.execute_plan(plan = final_plan)
                
            reflection_summary = "\n\n".join([
                f"Reflection {i+1}: {reflection['reflection']}" 
                for i, reflection in enumerate(reflection_history)
            ])
                
            return {
                "response" : final_content,
                "metadata" : {
                    "initial_thought" : initial_plan["thought"],
                    "initial_plan" : ". ".join(initial_plan["plan"]),
                    "reflection_performed" : True,
                    "final_plan" : ". ".join(final_plan["plan"]),
                    "tools_used": [tool_call["tool"] for tool_call in final_plan["tool_calls"]]
                },
                "status" : "success"
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {
                "error" : "I encountered an error processing your request. Please try again.",
                "status" : "failed" ,
                "error_type": "json_parse",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f'An error occurred while executing the plan: {e}', exc_info = True)
            return {
                "error" : "An unexpected error occurred. Please try again later.",
                "status" : "failed",
                "error_type": "general",
                "details": str(e)
            }