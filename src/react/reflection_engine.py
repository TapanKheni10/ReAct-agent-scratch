from typing import Dict, List, Optional
from datetime import datetime
import json
from config.logging import logger
from model.groq import reflect_on_plan, get_plan
from schemas.interaction_schema import Interaction
from prompt.prompt_builder import PromptBuilder
from memory.interaction_history import state_manager, StateManager

class ReflectionEngine:
    """
    Handles the reflection and plan improvement process for the Agent.
    
    This class is responsible for:
    1. Analyzing initial plans
    2. Generating reflections
    3. Improving plans based on reflections
    4. Managing the reflection iteration process
    """
    
    def __init__(self) -> None:
        self._prompt_builder: PromptBuilder = PromptBuilder()
        self._interaction_manager: StateManager = state_manager
        
    def _create_reflection_prompt(self) -> str:
        if not self._interaction_manager.get_interaction_history():
            return {
                "reflection": "No interactions have occurred yet. So no plan to reflect on.",
                "require_changes" : False
            } 
            
        last_interaction = self._interaction_manager.get_last_interaction()
        
        return self._prompt_builder.build_reflection_prompt(last_interaction = last_interaction)
        
    def reflect_and_improve(
        self, 
        user_query: str,
        initial_plan: Dict,
        system_prompt: str,
        max_reflection_iterations: int = 3
    ) -> Dict:
        
        """
        Execute the reflection and improvement loop for a given plan.
        
        Args:
            user_query: The original user query
            initial_plan: The initial plan to reflect on
            system_prompt: The system prompt for the LLM
            max_reflection_iterations: Maximum number of reflection iterations
            
        Returns:
            Dict containing the final plan and reflection history
        """
        
        current_plan = initial_plan
        reflection_history = []
        
        for iteration in range(max_reflection_iterations):
            self._interaction_manager.add_interaction(
                interaction = Interaction(
                    query = user_query,
                    plan = current_plan,
                    timestamp = datetime.now().isoformat()
                )
            )
            try:
                reflection_result = reflect_on_plan(
                    system_prompt = system_prompt,
                    reflection_prompt = self._create_reflection_prompt(),
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
                    system_prompt = system_prompt,
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
            
        return {
            "final_plan": current_plan,
            "reflection_history": reflection_history
        }