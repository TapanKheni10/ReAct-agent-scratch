from typing import Dict, List, Any
from config.logging import logger
from memory.interaction_history import state_manager
from model.groq import generate

class PlanExecutor:
    """Class responsible for executing tool plans."""
    
    def __init__(self, tools_registry):
        self.tools_registry = tools_registry
        self._interaction_manager = state_manager
    
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
        
        tool_results = []
        
        print('=*='*40)
        for tool_call in plan["tool_calls"]:
            tool_name = tool_call["tool"]
            tool_args = tool_call["args"]
            result = self._execute_tool(tool_name, **tool_args)
            
            if not result:
                continue
    
            tool_results.append({
                "tool" : tool_name,
                "result" : result
            })
            
        if tool_results:
            return self._synthesize_results(tool_results)
        
        return "I couldn't find any relevant information. Please try again with a different query."
    
    def _execute_tool(self, tool_name, **kwargs):
        """Execute a specific tool with given arguments."""
        if tool_name not in self.tools_registry:
            logger.info(f"Tool '{tool_name}' is not registered.")
            print(f"Tool '{tool_name}' is not registered.")
            return False
        
        tool = self.tools_registry[tool_name]
        return tool.func(**kwargs)
    
    def _format_tool_result(self, tool_name: str, result: Any):
        """Format the results into a cohesive response."""
        
        if isinstance(result, dict) and "error" in result:
            return f"Error from {tool_name}: {result['error']}"
        
        if tool_name in ["google_search", "wikipedia_search"]:
            formatted_result = ""
            if "enriched_results" in result:
                for result in result["enriched_results"]:
                        formatted_result += f"{result['title']}:\n{result['summary']}\n\n"
            else:
                formatted_result = result["summary"]
                    
            logger.info(f"Results: {formatted_result}")
            return formatted_result
        
        elif tool_name == "get_weather" and isinstance(result, dict):
            if "temperature" in result:
                return (
                    f"The temperature in {result['location']} is {result['temperature']}°C, "
                    f"Feels like: {result['feels_like']}°C, "
                    f"Description: {result['description']}, "
                    f"Humidity: {result['humidity']}%, "
                    f"Wind Speed: {result['wind_speed']} m/s."
                )
            return str(result)
        
        return str(result)
        
    def _synthesize_results(self, tool_results: List[Dict]):
        """Synthesize results from multiple tools into a single response."""
        
        logger.info("Synthesizing results from multiple tools.")
        print("Synthesizing results from multiple tools.")
        
        formatted_results = []
        
        for tool_result in tool_results:
            tool_name = tool_result["tool"]
            result = tool_result["result"]
            
            if not result:
                continue
            
            formatted_result = self._format_tool_result(tool_name, result)
            formatted_results.append({
                "tool" : tool_name,
                "result" : formatted_result
            })
        
        if len(formatted_results) == 1:
            return formatted_results[0]["result"]
        
        context = "\n\n".join([
            f"Information from {fr['tool']}:\n{fr['result']}"
            for fr in formatted_results
        ])
        
        original_query = self._interaction_manager.get_last_interaction().query
        
        prompt = f"""
        I need to provide a comprehensive answer to this query: "{original_query}"
        
        I have gathered the following information from different tools:
        
        {context}
        
        Please synthesize this information into a coherent, helpful response that
        directly addresses the user's query. Make sure the response flows naturally
        and doesn't explicitly mention which tool provided which information unless
        it's relevant to the answer.
        """
        
        try:
            synthesized_response = generate(
                content = prompt,
                system_prompt = "You are a helpful assistant synthesizing information from multiple sources."
            )
            
            return synthesized_response
        
        except Exception as e:
            logger.error(f"Error synthesizing results: {e}")
            return "\n\n".join([
                f"Information from {fr['tool']}:\n{fr['formatted_result']}" 
                for fr in formatted_results
            ])
        