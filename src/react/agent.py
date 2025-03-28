from groq import Groq
from config.settings import Config
from typing import Dict, List
from tools.tool_registery import Tool
import json
from config.logging import logger
from model.groq import safety_check, get_plan

class Agent:
    def __init__(self):
        """Initialize Agent with empty tool registry."""
        self.tools: Dict[str, Tool] = {}
        
    def add_tool(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self.tools[tool.name] = tool
        
    def get_available_tools(self) -> List[str]:
        """Get list of available tool descriptions."""
        return [f"{tool.name}: {tool.description}" for tool in self.tools.values()]
    
    def use_tool(self, tool_name: str, **kwargs) -> str:
        """Use a registered tool with provided arguments."""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' is not registered with the agent. Available tools: {self.get_available_tools()}"
        
        tool = self.tools[tool_name]
        return tool.func(**kwargs)
        
    def create_system_prompt(self) -> str:
        """Create the system prompt for the LLM with available tools."""
        tools_json = {
            "role": "AI Assistant",
            "capabilities": [
                "Using provided tools to help users when necessary",
                "Responding directly without tools for questions that don't require tool usage",
                "Planning efficient tool usage sequences"
            ],
            "instructions": [
                "Use tools only when they are necessary for the task",
                "If a query can be answered directly, respond with a simple message instead of using tools",
                "When tools are needed, plan their usage efficiently to minimize tool calls"
            ],
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        name: {
                            "type": info["type"],
                            "description": info["description"]
                        }
                        for name, info in tool.parameters.items()
                    }
                }
                for tool in self.tools.values()
            ],
            "response_format": {
                "type": "json",
                "schema": {
                    "requires_tools": {
                        "type": "boolean",
                        "description": "whether tools are needed for this query"
                    },
                    "direct_response": {
                        "type": "string",
                        "description": "response when no tools are needed",
                        "optional": True
                    },
                    "thought": {
                        "type": "string", 
                        "description": "reasoning about how to solve the task (when tools are needed)",
                        "optional": True
                    },
                    "plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "steps to solve the task (when tools are needed)",
                        "optional": True
                    },
                    "tool_calls": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool": {
                                    "type": "string",
                                    "description": "name of the tool"
                                },
                                "args": {
                                    "type": "object",
                                    "description": "parameters for the tool"
                                }
                            }
                        },
                        "description": "tools to call in sequence (when tools are needed)",
                        "optional": True
                    }
                },
                "examples": [
                    {
                        "query": "Who is the president of the United States?",
                        "response": {
                            "requires_tools": True,
                            "thought": "I need to use the Wikipedia tool to look up the current president of the United States.",
                            "plan": [
                                "Use Wikipedia tool to search for the current president of the United States",
                                "Return the result from Wikipedia"
                            ],
                            "tool_calls": [
                                {
                                    "tool": "wikipedia_search",
                                    "args": {
                                        "query": "current president of the United States"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "query": "Where is the Eiffel Tower located?",
                        "response": {
                            "requires_tools": False,
                            "direct_response": "The Eiffel Tower is located in Paris, France. This is common knowledge that doesn't require using the search tool."
                        }
                    },
                    {
                        "query": "What is the capital of Japan?",
                        "response": {
                            "requires_tools": False,
                            "direct_response": "The capital of Japan is Tokyo. This is general knowledge and does not require using external tools."
                        }
                    },
                    {
                        "query": "Who is Albert Einstein?",
                        "response": {
                            "requires_tools": True,
                            "thought": "I need to use the Wikipedia tool to get information about Albert Einstein.",
                            "plan": [
                                "Use Wikipedia tool to search for information about Albert Einstein",
                                "Return the result from Wikipedia"
                            ],
                            "tool_calls": [
                                {
                                    "tool": "wikipedia_search",
                                    "args": {
                                        "query": "Albert Einstein"
                                    }
                                }
                            ]
                        }
                    },
                    # {
                    #     "query": "What happend in the recent match between RR and KKR?",
                    #     "response": {
                    #         "requires_tools": True,
                    #         "thought": "I need to use the Google search tool to get information about the recent match between RR and KKR.",
                    #         "plan": [
                    #             "Use Google search tool to search for information about the recent match between RR and KKR",
                    #             "Return the result from Google"
                    #         ],
                    #         "tool_calls": [
                    #             {
                    #                 "tool": "google_search",
                    #                 "args": {
                    #                     "search_query" : "recent match between RR and KKR"
                    #                 }
                    #             }
                    #         ]
                    #     }
                    # },
                    # {
                    #     "query" : "what happend to donald trump recently?",
                    #     "response": {
                    #         "requires_tools": True,
                    #         "thought": "I need to use the Google search tool to get information about Donald Trump.",
                    #         "plan": [
                    #             "Use Google search tool to search for information about Donald Trump",
                    #             "Return the result from Google"
                    #         ],
                    #         "tool_calls": [
                    #             {
                    #                 "tool": "google_search",
                    #                 "args": {
                    #                     "search_query" : "recent news about Donald Trump"
                    #                 }
                    #             }
                    #         ]
                    #     }
                    # },
                ]
            }
        }
        
        return f"""
            You are an AI assistant that helps users by providing direct answers or using tools when necessary.
            Configuration, instructions, and available tools are provided in JSON format below:

            {json.dumps(tools_json, indent=4)}

            Always respond with a JSON object following the response_format schema above. 
            Remember to use tools only when they are actually needed for the task.
        """
    
    def execute(self, user_query: str) -> str:
        """Execute the full pipeline: plan and execute tools."""
        
        result = safety_check(content = user_query)
        if "unsafe" in result:
            return "the answer contains harmful content."
        
        try:
            plan = get_plan(user_query = user_query, system_prompt = self.create_system_prompt())
            logger.info(f"Plan: {plan}")
            
            if not plan.get("requires_tools", True):
                return plan["direct_response"]
            
            results = []
            for tool_call in plan["tool_calls"]:
                tool_name = tool_call["tool"]
                tool_args = tool_call["args"]
                result = self.use_tool(tool_name, **tool_args)
                results.append(result)
                
            return f"""
                Thought: {plan['thought']} 
                Plan: {'. '.join(plan['plan'])} 
                Results: {'. '.join(results)}
            """
            
        except Exception as e:
            logger.info(f'An error occurred while executing the plan: {e}')
    

def main():
    from tools.serp import google_search
    from tools.wiki import wikipedia_search
    
    agent = Agent()
    # agent.add_tool(google_search)
    agent.add_tool(wikipedia_search)
    
    query_list = ["what is the capital of india?"]
    
    for query in query_list:
        print(f"\nQuery: {query}")
        result = agent.execute(query)
        print("=*"*20)
        print(result)
        print("=*"*20)

if __name__ == "__main__":
    main() 