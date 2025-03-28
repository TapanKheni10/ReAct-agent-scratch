from typing import Dict, List
from tools.tool_registery import Tool
import json
from typing import Any
from config.logging import logger
from model.groq import safety_check, get_plan, reflect_on_plan
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Interaction:
    """Record of a single interaction with the agent"""
    timestamp: datetime
    query: str
    plan: Dict[str, Any]
    
class Agent:
    def __init__(self):
        """Initialize Agent with empty tool registry."""
        self.tools: Dict[str, Tool] = {}
        self.interaction_history: List[Interaction] = []
        
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
                "Planning efficient tool usage sequences",
                "If asked by the user, reflecting on the plan and suggesting changes if needed"
            ],
            "instructions": [
                "Use tools only when they are necessary for the task",
                "If a query can be answered directly, respond with a simple message instead of using tools",
                "When tools are needed, plan their usage efficiently to minimize tool calls",
                "If asked by the user, reflect on the plan and suggest changes if needed"
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
    
    def create_reflection_prompt(self) -> str:
        if not self.interaction_history:
            return {
                "reflection": "No interactions have occurred yet. So no plan to reflect on.",
                "require_changes" : False
            } 
            
        last_interaction = self.interaction_history[-1]
        
        reflection_prompt = {
            "task": "reflection",
            "context": {
                "user_query": last_interaction.query,
                "generated_plan": last_interaction.plan
            },
            "instructions": [
                "Review the generated plan for potential improvements",
                "Consider if the chosen tools are appropriate",
                "Verify tool parameters are correct",
                "Check if the plan is efficient",
                "Determine if tools are actually needed"
            ],
            "response_format": {
                "type": "json",
                "schema": {
                    "requires_changes": {
                        "type": "boolean",
                        "description": "whether the plan needs modifications"
                    },
                    "reflection": {
                        "type": "string",
                        "description": "explanation of what changes are needed or why no changes are needed"
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "specific suggestions for improvements",
                        "optional": True
                    }
                }
            }
        }
        
        return f"""
            {json.dumps(reflection_prompt, indent=4)}
        """
    
    def execute(self, user_query: str) -> str:
        """Execute the full pipeline: plan and execute tools."""
        
        result = safety_check(content = user_query)
        if "unsafe" in result:
            return "the answer contains harmful content."
        
        try:
            plan = get_plan(user_query = user_query, system_prompt = self.create_system_prompt())
            logger.info(f"Plan: {plan}")
            
            self.interaction_history.append(Interaction(
                timestamp = datetime.now(),
                query = user_query,
                plan = plan
            ))
            
            logger.info(f'Interaction history: {self.interaction_history}')
            
            reflection_result = reflect_on_plan(system_prompt = self.create_system_prompt(), reflection_prompt = self.create_reflection_prompt())
            
            # if not plan.get("requires_tools", True):
            #     return plan["direct_response"]
            
            # results = []
            # for tool_call in plan["tool_calls"]:
            #     tool_name = tool_call["tool"]
            #     tool_args = tool_call["args"]
            #     result = self.use_tool(tool_name, **tool_args)
            #     results.append(result)
                
            # return f"""
            #     Thought: {plan['thought']} 
            #     Plan: {'. '.join(plan['plan'])} 
            #     Results: {'. '.join(results)}
            # """
            
            if reflection_result.get("require_changes", False):
                
                reflected_plan = get_plan(
                    user_query = user_query, 
                    system_prompt = self.create_system_prompt(), 
                    initial_plan = plan, 
                    reflection_feedback = reflection_result
                )
                
                logger.info(f'reflected plan after changes: {reflected_plan}')
                
                if reflected_plan:
                    final_plan = reflected_plan
                else:
                    final_plan = plan
    
            else:
                final_plan = plan
                
            self.interaction_history[-1].plan = {
                "initial_plan": plan,
                "reflection": reflection_result,
                "final_plan": final_plan
            }
            
            logger.info(f'Interaction history: {self.interaction_history}')
            
            if not final_plan.get("requires_tools", True):
                return final_plan["direct_response"]
                
            results = []
            for tool_call in final_plan["tool_calls"]:
                tool_name = tool_call["tool"]
                tool_args = tool_call["args"]
                result = self.use_tool(tool_name, **tool_args)
                results.append(result)
                
            return f"""Initial Thought: {plan['thought']}\n\nInitial Plan: {'. '.join(plan['plan'])}\n\nReflection: {reflection_result.get('reflection', 'No improvements suggested')}\n\nFinal Plan: {'. '.join(final_plan['plan'])}\n\nResults: {'. '.join(results)}
            """
            
        except Exception as e:
            logger.info(f'An error occurred while executing the plan: {e}')
    

def main():
    from tools.serp import google_search
    from tools.wiki import wikipedia_search
    
    agent = Agent()
    # agent.add_tool(google_search)
    agent.add_tool(wikipedia_search)
    
    query_list = ["what happend to donald trump recently?"]
    
    for query in query_list:
        print(f"\nQuery: {query}")
        result = agent.execute(query)
        print("=*"*20)
        print(result)
        print("=*"*20)

if __name__ == "__main__":
    main() 