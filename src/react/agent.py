from typing import Dict, List, Optional
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
    reflection_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.reflection_history is None:
            self.reflection_history = []
    
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
    
    def use_tool(self, tool_name: str, **kwargs) -> Optional[str]:
        """Use a registered tool with provided arguments."""
        if tool_name not in self.tools:
            logger.info(f"Tool '{tool_name}' is not registered with the agent. Available tools: {self.get_available_tools()}")
            return False
        
        tool = self.tools[tool_name]
        return tool.func(**kwargs)
        
    def create_system_prompt(self) -> str:
        """Create the system prompt for the LLM with available tools."""
        tools_json = {
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
            ]
        }
        
        response_format_json = {
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
        }
        
        examples_json = {        
            "examples": [
                {
                    "query": "Who is the current Prime Minister of the United Kingdom?",
                    "response": {
                        "requires_tools": True,
                        "thought": "I need to use the Wikipedia tool to look up the current Prime Minister of the United Kingdom.",
                        "plan": [
                            "Use Wikipedia tool to search for the current Prime Minister of the United Kingdom",
                            "Return the result from Wikipedia"
                        ],
                        "tool_calls": [
                            {
                                "tool": "wikipedia_search",
                                "args": {
                                    "query": "current Prime Minister of the United Kingdom"
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
                    "query": "What is the capital of Canada?",
                    "response": {
                        "requires_tools": False,
                        "direct_response": "The capital of Canada is Ottawa. This is common knowledge that doesn't require using the search tool."
                    }
                },
                {
                    "query": "Who discovered penicillin?",
                    "response": {
                        "requires_tools": False,
                        "direct_response": "Penicillin was discovered by Alexander Fleming in 1928. This is general knowledge and does not require using external tools."
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
                {
                    "query": "Tell me about the theory of relativity.",
                    "response": {
                        "requires_tools": True,
                        "thought": "I need to use the Wikipedia tool to get detailed information about the theory of relativity.",
                        "plan": [
                            "Use Wikipedia tool to search for information about the theory of relativity",
                            "Return the result from Wikipedia"
                        ],
                        "tool_calls": [
                            {
                                "tool": "wikipedia_search",
                                "args": {
                                    "query": "theory of relativity"
                                }
                            }
                        ]
                    }
                },
                {
                    "query": "What was the outcome of the recent UEFA Champions League final?",
                    "response": {
                        "requires_tools": True,
                        "thought": "I need to use the Google search tool to get the latest result of the UEFA Champions League final.",
                        "plan": [
                            "Use Google search tool to find information about the most recent UEFA Champions League final",
                            "Return the result from Google"
                        ],
                        "tool_calls": [
                            {
                                "tool": "google_search",
                                "args": {
                                    "search_query": "latest UEFA Champions League final result"
                                }
                            }
                        ]
                    }
                },
                {
                    "query": "What are the latest updates about Elon Musk?",
                    "response": {
                        "requires_tools": True,
                        "thought": "I need to use the Google search tool to get the latest news about Elon Musk.",
                        "plan": [
                            "Use Google search tool to find the most recent news related to Elon Musk",
                            "Return the result from Google"
                        ],
                        "tool_calls": [
                            {
                                "tool": "google_search",
                                "args": {
                                    "search_query": "latest news about Elon Musk"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        return f"""
            You are an AI assistant that helps users by providing direct answers or using tools when necessary.
            Configuration, instructions, and available tools are provided in JSON format below:
            
            ## Role and Capabilities
            - Use provided tools to help users when necessary
            - Respond directly without tools for questions that don't require tool usage
            - Plan efficient tool usage sequences 
            - Reflect on your plan when asked by the user
            - Handle tool failures gracefully with fallback options
            
            ## Instructions
            1. Use tools ONLY when they meet these criteria:
            - The question requires up-to-date information beyond your knowledge cutoff
            - The question requires specific data you don't have access to
            - The task explicitly requires a specialized tool (calculation, search, etc.)
            - The answer would be significantly more accurate with tool usage

            2. Respond directly WITHOUT tools when:
            - The query is about general knowledge within your training
            - The query is conversational or opinion-based
            - The query can be answered with logical reasoning
            - The query is about hypothetical scenarios

            3. When using tools:
            - Plan their usage efficiently to minimize tool calls
            - Consider dependencies between tools
            - Start with the most relevant tool first
            - Process and synthesize tool outputs into coherent responses
            - If a tool fails, try an alternative approach or explain the limitation

            4. When asked, explain your reasoning for using or not using tools
            
            ## Available Tools
            {json.dumps(tools_json, indent=4)}
            
            ## Response Format
            {json.dumps(response_format_json, indent=4)}
            
            ## Examples
            {json.dumps(examples_json, indent=4)}

            Always respond with a JSON object following the response_format schema above. 
            Remember that your goal is to help the user effectively - tools are means to an end, not the end itself.
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
            You are conducting a critical review of an AI assistant's plan for using tools to answer a user query.
            Your task is to identify improvements that would make the plan more effective, appropriate, and efficient.
            
            {json.dumps(reflection_prompt, indent=4)}
            
            Remember that the goal is to provide actionable feedback that can improve how the assistant handles similar queries in the future.
            Always respond with a JSON object following the response_format schema above.
        """
    
    def execute(self, user_query: str, max_reflection_iterations: int = 3) -> str:
        """Execute the full pipeline: plan and execute tools."""
        
        result = safety_check(content = user_query)
        if "unsafe" in result:
            print("Unsafe content detected. Please rephrase your query.")
            return "the answer contains harmful content."
        
        try:
            initial_plan = get_plan(user_query = user_query, system_prompt = self.create_system_prompt())
            logger.info(f"Initial Plan: {initial_plan}")
            
            print('=*='*40)
            print(f"\nInitial plan:\n{initial_plan}")
            print('=*='*40)
            
            initial_plan = json.loads(initial_plan)
            
            self.interaction_history.append(Interaction(
                timestamp = datetime.now(),
                query = user_query,
                plan = initial_plan
            ))
            
            logger.info(f'Interaction history: {self.interaction_history}')
            
            print(f"\nInteraction History:\n{self.interaction_history}")
            print('=*='*40)
            
            if not initial_plan.get("requires_tools", True):
                logger.info("Initial plan doesn't require tools. Skipping reflection loop.")
                return initial_plan["direct_response"]
            
            current_plan = initial_plan
            reflection_history = []
            
            for iteration in range(max_reflection_iterations):
                self.interaction_history[-1].plan = current_plan
                self.interaction_history[-1].timestamp = datetime.now()
                
                try:
                    reflection_result = reflect_on_plan(
                        system_prompt = self.create_system_prompt(),
                        reflection_prompt = self.create_reflection_prompt()
                    )
                    logger.info(f"Reflection {iteration + 1} Result: {reflection_result}")
                    
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
                    
                    logger.info(f"Revised Plan after reflection {iteration+1}: {revised_plan}")
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
            
            self.interaction_history[-1].plan = {
                "initial_plan": initial_plan,
                "reflection": reflection_history,
                "final_plan": final_plan
            }
            
            logger.info(f'Final interaction history: {self.interaction_history}')
            
            if not final_plan.get("requires_tools", True):
                return final_plan["direct_response"]
                
            results = []
            for tool_call in final_plan["tool_calls"]:
                tool_name = tool_call["tool"]
                tool_args = tool_call["args"]
                result = self.use_tool(tool_name, **tool_args)
                
                if not result:
                    continue
                results.append(result)
                
            final_content = ""
            if "enriched_results" in results[0]:
                for result in results[0]["enriched_results"]:
                    final_content += f"{result['title']}:\n{result['summary']}\n\n"
            else:
                final_content = results[0]["summary"]
                
            logger.info(f"Results: {results}")
            
            print('=*='*35)
            print(final_content)
            print('=*='*35)
                
            reflection_summary = "\n\n".join([
                f"Reflection {i+1}: {reflection['reflection']}" 
                for i, reflection in enumerate(reflection_history)
            ])
                
            return f"""Initial Thought: {initial_plan['thought']}\n\nInitial Plan: {'. '.join(initial_plan['plan'])}\n\nReflection Process: {reflection_summary}\n\nFinal Plan: {'. '.join(final_plan['plan'])}\n\nResults: {'. '.join(results)}
            """
            
        except Exception as e:
            logger.info(f'An error occurred while executing the plan: {e}')
    

def main():
    from tools.serp import google_search
    from tools.wiki import wikipedia_search
    
    agent = Agent()
    agent.add_tool(google_search)
    agent.add_tool(wikipedia_search)
    
    query_list = ["recent news about waqf board."]
    # query_list = ["who is the president of the united states?"]
    # query_list = ["tell me something about how to kill someone."]
    
    for query in query_list:
        print(f"\nQuery: {query}")
        result = agent.execute(query)

if __name__ == "__main__":
    main() 