from typing import Dict, List, Optional
from tools.tool_registery import Tool
import json
from typing import Any
from config.logging import logger
from model.groq import safety_check, get_plan, reflect_on_plan
from dataclasses import dataclass
from datetime import datetime
from prompt.prompt_builder import PromptBuilder
from schemas.interaction_schema import Interaction
from react.plan_executor import PlanExecutor
    
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
        self._interaction_history: List[Interaction] = []
        self._prompt_builder = PromptBuilder()
        self._plan_executor = PlanExecutor(tools_registry = self._tools)
        
    def add_tool(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self._tools[tool.name] = tool
        
    def get_available_tools(self) -> List[str]:
        """Get list of available tool descriptions."""
        return [f"{tool.name}: {tool.description}" for tool in self._tools.values()]
        
    def create_system_prompt(self) -> str:
        """Create the system prompt for the LLM with available tools."""
        return self._prompt_builder.build_system_prompt(tools = self._tools.values())
    
    def create_reflection_prompt(self) -> str:
        if not self._interaction_history:
            return {
                "reflection": "No interactions have occurred yet. So no plan to reflect on.",
                "require_changes" : False
            } 
            
        last_interaction = self._interaction_history[-1]
        
        return self._prompt_builder.build_reflection_prompt(last_interaction = last_interaction)
    
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
                "warning" : "the answer contains harmful content.",
                "status" : "failed"
            }
        
        try:
            initial_plan = get_plan(user_query = user_query, system_prompt = self.create_system_prompt())
            logger.info(f"Initial Plan: {initial_plan}")
            
            print('=*='*40)
            print(f"\nInitial plan:\n{initial_plan}")
            print('=*='*40)
            
            initial_plan = json.loads(initial_plan)
            
            self._interaction_history.append(Interaction(
                timestamp = datetime.now(),
                query = user_query,
                plan = initial_plan
            ))
            
            logger.info(f'Interaction history: {self._interaction_history}')
            
            print(f"\nInteraction History:\n{self._interaction_history}")
            print('=*='*40)
            
            if not initial_plan["requires_tools"]:
                logger.info("Initial plan doesn't require tools. Skipping reflection loop.")
                return {
                    "response" : initial_plan["direct_response"],
                    "status" : "success"
                }
            
            current_plan = initial_plan
            reflection_history = []
            
            for iteration in range(max_reflection_iterations):
                self._interaction_history[-1].plan = current_plan
                self._interaction_history[-1].timestamp = datetime.now()
                
                try:
                    reflection_result = reflect_on_plan(
                        system_prompt = self.create_system_prompt(),
                        reflection_prompt = self.create_reflection_prompt()
                    )

                    print(f"\nReflection {iteration + 1}:\n{reflection_result}")
                    print('=*='*40)
                    
                    reflection_result = json.loads(reflection_result)
                
                    reflection_history.append(reflection_result)
                    
                    if not reflection_result.get("requires_changes", False):
                        logger.info("No changes required. Exiting reflection loop.")
                        print("\nNo changes required. Exiting reflection loop.")
                        print('=*='*40)
                        break
                    
                    revised_plan = get_plan(
                        user_query = user_query,
                        system_prompt = self.create_system_prompt(),
                        initial_plan = current_plan,
                        reflection_feedback = reflection_result
                    )
                    
                    if not revised_plan:
                        logger.info(f"Failed to generate revised plan after reflection {iteration+1}")
                        print(f"\nFailed to generate revised plan after reflection {iteration+1}")
                        print('=*='*40)   
                        continue
                    
                    print(f"\nRevised plan after iteration {iteration + 1}:\n{revised_plan}")
                    print("=*="*40)
                    
                    revised_plan = json.loads(revised_plan)
                    
                    current_plan = revised_plan
                
                except Exception as e:
                    logger.error(f"Error during reflection iteration {iteration+1}: {e}")
                    reflection_history.append({
                        "reflection": f"Reflection failed due to error: {str(e)}",
                        "requires_changes": False
                    })
                    
                    continue
                
            final_plan = current_plan
            
            print(f"\nFinal plan:\n{final_plan}")
            print("=*="*40)
            
            self._interaction_history[-1].plan = {
                "initial_plan": initial_plan,
                "reflection": reflection_history,
                "final_plan": final_plan
            }
            
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
                "status" : "failed" 
            }
        except Exception as e:
            logger.error(f'An error occurred while executing the plan: {e}', exc_info = True)
            return {
                "error" : "An unexpected error occurred. Please try again later.",
                "status" : "failed"
            }