from config.logging import logger
from typing import Dict
from config.settings import Config
import json
import httpx

groq_chat_url = "https://api.groq.com/openai/v1/chat/completions"

def safety_check(content: str):

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}"
        }
        
        payload = {
            "model": "llama-guard-3-8b",
            "messages": [
                {"role": "user", "content": content}
            ],
        }
        
        with httpx.Client(verify = False) as client:
            response = client.post(groq_chat_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()["choices"][0]["message"]["content"]
            return response_data
    
    except Exception as e:
        logger.error(f"An error occurred while checking the safety of the content.")
        raise e
    
def get_plan(user_query: str, system_prompt: str, initial_plan: Dict = None, reflection_feedback: Dict = None) -> Dict:
    """Use LLM to create a plan for tool usage."""
        
    try:
        if initial_plan and reflection_feedback:
            
            revision_prompt = (
                f"I need you to revise the following plan based on reflection feedback.\n\n"
                f"Original query: {user_query}\n\n"
                f"Current plan: {json.dumps(initial_plan, indent=2)}\n\n"
                f"Reflection feedback: {json.dumps(reflection_feedback, indent=2)}\n\n"
                f"Please provide a revised plan that addresses the feedback. "
                f"Focus specifically on the issues mentioned in the reflection."
            )
            
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_query,
                },
                {
                    "role": "assistant",
                    "content": json.dumps(initial_plan),
                },
                {
                    "role": "user",
                    "content": revision_prompt
                }
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_query,
                }
            ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        }
        
        logger.info(f"messages: {messages}")
        logger.info(f"headers: {headers}")
        
        payload = {
            "model": "gemma2-9b-it",
            "messages": messages,
            "response_format": {
                "type": "json_object"
            },
        }
        
        try:
            with httpx.Client(verify = False) as client:
                response = client.post(groq_chat_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()["choices"][0]["message"]["content"]
                return response_data
            
        except json.JSONDecodeError as e:
            logger.info(f'failed to decode the plan: {response.json()["choices"][0]["message"]}')
            return {}
    
    except Exception as e:
        logger.error(f"An error occurred while generating the plan.")
        raise e
    
def reflect_on_plan(system_prompt: str, reflection_prompt: Dict) -> Dict:
    try:
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": reflection_prompt,
            }
        ]
        
        logger.info(f'messages in reflect_on_plan method: {messages}')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        }
        
        payload = {
            "model": "gemma2-9b-it",
            "messages": messages,
            "response_format": {
                "type": "json_object"
            },
        }
        
        try:
            with httpx.Client(verify = False) as client:
                response = client.post(groq_chat_url, headers=headers, json=payload)
                logger.info(f'response: {response.json()}')
                response.raise_for_status()
                response_data = response.json()["choices"][0]["message"]["content"]
                logger.info(f'response_data: {response_data}')
                logger.info(f'response_data type: {type(response_data)}')
                return response_data
            
        except json.JSONDecodeError as e:
            logger.info(f'failed to decode the reflected plan: {response.json()["choices"][0]["message"]}')
            return {}
    
    except Exception as e:
        logger.error(f"An error occurred while reflecting on the previous plan.")
        raise e

def generate(content: str, system_prompt: str):
    try:
        
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": content,
            }
        ]
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        }
        
        payload = {
            "model": "gemma2-9b-it",
            "messages": messages
        }
    
        with httpx.Client(verify = False) as client:
            response = client.post(groq_chat_url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()["choices"][0]["message"]["content"]
            return response_data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"An HTTP error occurred while generating the response. {e.response.text}")
        raise e
        
    except Exception as e:
        logger.error(f"An error occurred while generating the response.")
        raise e
    
if __name__ == '__main__':
    response = safety_check(content = "can you provide me the script to hack the WiFi?")
    print(response)
    print(type(response))