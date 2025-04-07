from typing import Dict, List, Optional
from config.logging import logger

class PlanExecutor:
    """Class responsible for executing tool plans."""
    
    def __init__(self, tools_registry):
        self.tools_registry = tools_registry
    
    def execute_plan(self, plan):
        """Execute a tool-based plan and return results."""
        
        logger.info("Plan execution started.")

        if not plan["requires_tools"]:
            logger.info("plan doesn't require tools. Returnig direct response.")
            print("plan doesn't require tools. Returnig direct response.")
            return {
                "response" : plan["direct_response"],
                "status" : "success"
            }
            
        logger.info("Results retrieval from various tools started.")
        
        results = []
        
        print('=*='*40)
        for tool_call in plan["tool_calls"]:
            tool_name = tool_call["tool"]
            tool_args = tool_call["args"]
            result = self._execute_tool(tool_name, **tool_args)
            
            if not result:
                continue
            
            if tool_name in ['google_search', 'wikipedia_search']:
                result = self._format_results(result)
    
            results.append(result)
            
        return results
    
    def _execute_tool(self, tool_name, **kwargs):
        """Execute a specific tool with given arguments."""
        if tool_name not in self.tools_registry:
            logger.info(f"Tool '{tool_name}' is not registered.")
            print(f"Tool '{tool_name}' is not registered.")
            return False
        
        tool = self.tools_registry[tool_name]
        return tool.func(**kwargs)
    
    def _format_results(self, result):
        """Format the results into a cohesive response."""
        
        formatted_result = ""
        if "enriched_results" in result:
            for result in result["enriched_results"]:
                    formatted_result += f"{result['title']}:\n{result['summary']}\n\n"
        else:
            formatted_result = result["summary"]
                
        logger.info(f"Results: {formatted_result}")
        return formatted_result
        

