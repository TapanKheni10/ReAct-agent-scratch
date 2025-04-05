import json
from typing import Dict, Iterable
from tools.tool_registery import Tool
from schemas.interaction_schema import Interaction

class PromptBuilder:
    """Class responsible for building prompts for the LLM."""
    
    def build_system_prompt(self, tools: Iterable[Tool]) -> str:
        """Create the system prompt for the LLM with available tools."""
        
        tools_json = self._create_tools_json(tools)
        response_format_json = self._create_response_format_json()
        examples_json = self._create_examples_json()
        
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
            
            5. Always use the tools that are provided to you, don't fabricate tools by yourself.
            
            ## Available Tools
            {json.dumps(tools_json, indent=4)}
            
            ## Response Format
            {json.dumps(response_format_json, indent=4)}
            
            ## Examples
            {json.dumps(examples_json, indent=4)}

            Always respond with a JSON object following the response_format schema above. 
            Remember that your goal is to help the user effectively - tools are means to an end, not the end itself.
        """
        
    def build_reflection_prompt(self, last_interaction: Interaction) -> str:
        """Create the reflection prompt for the LLM."""
        reflection_json = self._create_reflection_json(last_interaction)
        
        return f"""
            You are conducting a critical review of an AI assistant's plan for using tools to answer a user query.
            Your task is to identify improvements that would make the plan more effective, appropriate, and efficient.
            
            {json.dumps(reflection_json, indent=4)}
            
            Remember that the goal is to provide actionable feedback that can improve how the assistant handles similar queries in the future.
            Always respond with a JSON object following the response_format schema above.
        """
        
    def _create_tools_json(self, tools: Iterable[Tool]) -> Dict:
        """Create JSON representation of available tools."""
        return {
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
                for tool in tools
            ]
        }   
        
    def _create_response_format_json(self) -> Dict:
        """Create JSON schema for response format."""
        
        return {
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
        
    def _create_examples_json(self) -> Dict:
        """Create examples for the prompt."""
        
        return {        
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
        
    def _create_reflection_json(self, last_interaction: Interaction) -> Dict:
        
        return {
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